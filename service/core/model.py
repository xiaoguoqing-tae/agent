"""模型相关"""
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from core.config import conf

#大语言模型
chat_model =ChatTongyi(
    model=conf['chat']['model'],
    api_key=conf['chat']['api_key'],
    streaming=True,      # 【关键】必须开启流式
    #top_p=0.8,
)

#向量模型
embedding_model = DashScopeEmbeddings(
    model = conf['embedding']['model'],
    dashscope_api_key=conf['embedding']['dashscope_api_key'],
)