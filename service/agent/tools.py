import os

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
import dashscope
from dashscope import ImageSynthesis
from core.config import conf

from rag.rag_service import RagService
# 定义工具 (Tools)
# 这里定义两个简单的工具，模拟真实场景
@tool
def search_tool(query: str) -> str:
    """搜索关于当前天气的信息。"""
    # 实际使用时，这里可以替换为 SerpAPI 或 Tavily 等真实搜索工具
    return "北京今天天气晴朗，气温 21 度。"


@tool
def calculator_tool(expression: str) -> float:
    """计算数学表达式。"""
    try:
        # 简单的安全计算
        return eval(expression)
    except Exception as e:
        return f"计算错误{str(e)}"


@tool
def search_document_tool(query: str,config:RunnableConfig) -> str:
    """
    检索选定的文档。
    注意：doc_ids 不通过参数传递，而是通过执行上下文(config)传递。
    """
    # 从 config 中获取选中的文档 ID 列表
    metadata = config.get("configurable",{})
    doc_ids = metadata.get("doc_ids",[])

    if not doc_ids:
        return "用户未选中任何文档，请根据你的通用知识库回答。"

    """搜索当上传的文档，获取相关信息"""
    try:
        vector = RagService()
        docs = vector.search(doc_ids, query)
        if not docs:
            return "未找到相关文档。"

        return docs
        # 使用分隔符，让 AI 知道哪里是文档的边界
        #return  "\n---\n".join(docs)
    except Exception as e:
        return f"搜索工具执行出错：{str(e)}"

@tool
def generate_image(prompt: str) -> str:
    """根据文本提示词生成图片，返回图片 URL。支持中文/英文描述。"""
    dashscope.api_key = conf['chat']['api_key']
    rsp = ImageSynthesis.call(
        model="wanx-v1",
        prompt=prompt,
        n=1,
        size="1024*1024"
    )
    if rsp.status_code == 200:
        return rsp.output.results[0].url
    return f"生成失败: {rsp.message}"


