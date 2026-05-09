import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import dashscope
from dashscope import ImageSynthesis
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from core.config import conf
from rag.rag_service import RagService


def _http_get_json(url: str, params: dict) -> dict:
    request = Request(
        f"{url}?{urlencode(params)}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_city(query: str) -> str:
    city = query.strip()
    city = re.sub(
        r"(今天|明天|后天|当前|现在|查询|查一下|帮我|请问|高德|天气|气温|温度|湿度|怎么样|如何|多少|的|[?？!！。,.，])",
        "",
        city,
    )
    return city.strip() or "北京"


def _amap_weather(query: str) -> str:
    api_key = conf.get("weather", {}).get("api_key")
    if not api_key:
        return "高德天气查询失败：未配置 weather.api_key"

    city = _extract_city(query)
    geo = _http_get_json(
        "https://restapi.amap.com/v3/geocode/geo",
        {"key": api_key, "address": city},
    )
    if geo.get("status") != "1":
        return f"高德天气查询失败：{geo.get('info', '未知错误')}"
    if not geo.get("geocodes"):
        return f"高德天气查询失败：无法识别城市{city}"

    adcode = geo["geocodes"][0].get("adcode")
    weather = _http_get_json(
        "https://restapi.amap.com/v3/weather/weatherInfo",
        {"key": api_key, "city": adcode, "extensions": "base"},
    )
    if weather.get("status") != "1":
        return f"高德天气查询失败：{weather.get('info', '未知错误')}"

    lives = weather.get("lives") or []
    if not lives:
        return f"高德天气查询失败：未查询到{city}天气"

    live = lives[0]
    return f"天气{live.get('weather')}，温度{live.get('temperature')}℃，湿度{live.get('humidity')}%"


@tool
def search_tool(query: str) -> str:
    """使用高德天气 API 查询实时天气。输入示例：杭州天气。"""
    try:
        return _amap_weather(query)
    except Exception as e:
        return f"高德天气查询失败：{str(e)}"


@tool
def calculator_tool(expression: str) -> float:
    """计算数学表达式。"""
    try:
        return eval(expression)
    except Exception as e:
        return f"计算错误：{str(e)}"


@tool
def search_document_tool(query: str, config: RunnableConfig) -> str:
    """
    检索用户当前选中的参考文档。
    doc_ids 不通过参数传递，而是通过 RunnableConfig 的 configurable.doc_ids 传递。
    """
    metadata = config.get("configurable", {})
    doc_ids = metadata.get("doc_ids", [])

    if not doc_ids:
        return "用户未选中任何文档，请根据通用知识回答。"

    try:
        vector = RagService()
        docs = vector.search(doc_ids, query)
        if not docs:
            return "未找到相关文档。"
        return docs
    except Exception as e:
        return f"搜索工具执行出错：{str(e)}"


@tool
def generate_image(prompt: str) -> str:
    """根据文本提示词生成图片，返回图片 URL。"""
    dashscope.api_key = conf["chat"]["api_key"]
    rsp = ImageSynthesis.call(
        model="wanx-v1",
        prompt=prompt,
        n=1,
        size="1024*1024",
    )
    if rsp.status_code == 200:
        return rsp.output.results[0].url
    return f"生成失败：{rsp.message}"
