import json
import os
from langchain.agents import create_agent
from core.config import conf
from core.database import get_conn,get_chat
from core.model import chat_model
from utils.file import load_text,get_abs_path
from typing import AsyncGenerator, Optional,List
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agent.tools import search_document_tool,search_tool,calculator_tool,generate_image
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from typing import AsyncGenerator, Optional, List, Dict, Any
tools = [search_document_tool,search_tool,calculator_tool,generate_image]
class ChatAgentService:
    """
    Agent 服务类
    支持多主题聊天：通过 thread_id 区分不同的对话上下文
    """
    def __init__(self):
        self.db_path = get_chat()

    async def stream_chat(self,thread_id:str,query:str="",doc_ids:Optional[list[int]] = None) -> AsyncGenerator[str, None]:
        """
        流式处理聊天请求

        Args:
            doc_ids
            query: 用户输入
            thread_id: 主题ID (例如: "topic_1", "topic_2")
        """

        #通用提示词
        prompt = load_text(os.path.join(get_abs_path(conf['prompt_dir']),"chat_agent_1.txt"))
        if doc_ids:
            prompt = load_text(os.path.join(get_abs_path(conf['prompt_dir']),"chat_agent_2.txt"))


        # 【关键】每次请求都建立新的数据库连接
        # 这样保证了并发安全，不同用户的请求不会冲突
        async with AsyncSqliteSaver.from_conn_string(self.db_path) as saver:

            # 1. 构建 Agent
            # 注意：这里不需要在创建时指定 thread_id
            agent = create_agent(
                model = chat_model,
                tools = tools,
                checkpointer=saver,
                system_prompt=prompt
            )

            # 2. 准备输入。选中文档时，显式要求 Agent 先调用文档检索工具。
            user_query = query
            if doc_ids:
                user_query = (
                    "用户已选择参考文档。请先调用 search_document_tool 检索所选文档，"
                    "再基于检索结果回答；如果文档没有相关内容，请明确说明。\n\n"
                    f"用户问题：{query}"
                )
            inputs = {"messages": [("user", user_query)]}

            # 3. 【核心】配置线程 ID
            # LangGraph 会根据这个 ID 去数据库读取对应的历史记忆
            # 如果 ID 是新的，它会自动开启一个新的话题分支
            config = {
                "configurable":{
                    "thread_id":thread_id,
                    "doc_ids":doc_ids,
                }
            }

            # 4. 流式输出
            try:
                async for event in agent.astream_events(inputs,config=config,version="v2"):
                    kind = event["event"]

                    #处理文本流
                    if kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        if chunk.content:
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk.content}, ensure_ascii=False)}\n\n"
                    #处理工具调用
                    elif kind == "on_tool_start":
                        yield f"data: {json.dumps({'type': 'tool_start', 'name': event['name']}, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
                raise e
        # 输出结束符号
        yield "data: [DONE]\n\n"

    async def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        获取指定线程的完整历史
        """
        async with AsyncSqliteSaver.from_conn_string(self.db_path) as saver:
            config = {"configurable": {"thread_id": thread_id}}

            # 返回的是 Checkpoint dict，数据在 channel_values 中
            checkpoint = await saver.aget(config)

            if not checkpoint:
                return []

            # 从 channel_values 中提取 messages
            channel_values = checkpoint.get("channel_values", {})
            messages = channel_values.get("messages", [])

            # 序列化为可 JSON 的格式
            result = []


            for msg in messages:
                # 1. 处理用户输入
                if isinstance(msg, HumanMessage):
                    result.append({
                        "role": "human",
                        "content": msg.content
                    })

                # 2. 处理 AI 回复
                elif isinstance(msg, AIMessage):
                    # 情况 A: AI 直接回复了文本 (content 有值)
                    if msg.content:
                        result.append({
                            "role": "ai",
                            "content": msg.content
                        })
                    # 情况 B: AI 只是调用了工具 (content 为空，但有 tool_calls)
                    # 这种情况通常不需要展示给用户，或者你可以展示 "正在搜索..."
                    # 这里我们选择跳过，等待工具返回结果后的下一次 AI 回复

                # 3. 处理工具返回结果 (ToolMessage)
                # 通常不需要把工具返回的一大堆 JSON 或原始数据展示在聊天窗口里
                # 所以这里直接忽略，不加入 result
                elif isinstance(msg, ToolMessage):
                    pass

            return result

    async def clear_history(self,thread_id:str):
        try:
            async with AsyncSqliteSaver.from_conn_string(self.db_path) as saver:
                #config = {"configurable": {"thread_id": thread_id}}
                # 保存空状态覆盖原有数据
                await saver.adelete_thread(thread_id)
        except Exception as e:
            raise e
