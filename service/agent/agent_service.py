import json
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

try:
    from langgraph.checkpoint.mysql.aio import AsyncMySqlSaver as AsyncMySQLSaver
except ImportError:
    try:
        from langgraph.checkpoint.mysql.aio import AsyncMySQLSaver
    except ImportError:
        from langgraph.checkpoint.mysql.aio import AIOMySQLSaver as AsyncMySQLSaver

from agent.tools import calculator_tool, generate_image, search_document_tool, search_tool
from core.config import conf
from core.database import get_chat
from core.model import chat_model
from utils.file import get_abs_path, load_text


tools = [search_document_tool, search_tool, calculator_tool, generate_image]


class ChatAgentService:
    """Agent 服务，支持通过 thread_id 区分不同对话上下文。"""

    def __init__(self):
        self.db_url = get_chat()

    async def _setup_saver(self, saver):
        setup = getattr(saver, "setup", None)
        if setup:
            await setup()
        return saver

    async def stream_chat(
        self,
        thread_id: str,
        query: str = "",
        doc_ids: Optional[list[int]] = None,
    ) -> AsyncGenerator[str, None]:
        """流式处理聊天请求。"""
        prompt = load_text(os.path.join(get_abs_path(conf["prompt_dir"]), "chat_agent_1.txt"))
        if doc_ids:
            prompt = load_text(os.path.join(get_abs_path(conf["prompt_dir"]), "chat_agent_2.txt"))

        async with AsyncMySQLSaver.from_conn_string(self.db_url) as saver:
            saver = await self._setup_saver(saver)
            agent = create_agent(
                model=chat_model,
                tools=tools,
                checkpointer=saver,
                system_prompt=prompt,
            )

            user_query = query
            if doc_ids:
                user_query = (
                    "用户已选择参考文档。请先调用 search_document_tool 检索所选文档，"
                    "再基于检索结果回答；如果文档没有相关内容，请明确说明。\n\n"
                    f"用户问题：{query}"
                )
            inputs = {"messages": [("user", user_query)]}

            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "doc_ids": doc_ids,
                }
            }

            try:
                async for event in agent.astream_events(inputs, config=config, version="v2"):
                    kind = event["event"]

                    if kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        if chunk.content:
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk.content}, ensure_ascii=False)}\n\n"
                    elif kind == "on_tool_start":
                        yield f"data: {json.dumps({'type': 'tool_start', 'name': event['name']}, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
                raise e

        yield "data: [DONE]\n\n"

    async def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """获取指定对话的历史消息。"""
        async with AsyncMySQLSaver.from_conn_string(self.db_url) as saver:
            saver = await self._setup_saver(saver)
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = await saver.aget(config)

            if not checkpoint:
                return []

            channel_values = checkpoint.get("channel_values", {})
            messages = channel_values.get("messages", [])
            result = []

            for msg in messages:
                if isinstance(msg, HumanMessage):
                    result.append(
                        {
                            "role": "human",
                            "content": msg.content,
                        }
                    )
                elif isinstance(msg, AIMessage):
                    if msg.content:
                        result.append(
                            {
                                "role": "ai",
                                "content": msg.content,
                            }
                        )
                elif isinstance(msg, ToolMessage):
                    pass

            return result

    async def clear_history(self, thread_id: str):
        try:
            async with AsyncMySQLSaver.from_conn_string(self.db_url) as saver:
                saver = await self._setup_saver(saver)
                await saver.adelete_thread(thread_id)
        except Exception as e:
            raise e
