"""向量存储、检索、增强生成"""
import os.path

from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.database import get_conn
from core.logger import logger
from core.model import embedding_model, chat_model
from core.config import conf
from utils.file import get_abs_path, load_text,safe_delete


def print_prompt(prompt):
    print("=" * 20)
    print(prompt.to_string())
    print("=" * 20)
    return prompt

class RagService:
    def __init__(self):

        #向量存储、检索
        self.vector = Chroma(
            collection_name=conf['rag']['collection_name'],
            embedding_function=embedding_model,
            persist_directory=get_abs_path(conf['rag']['persist_dir']),
        )

        #分割器
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size = conf['rag']['chunk_size'],
            chunk_overlap=conf['rag']['chunk_overlap'],
            length_function=len,
        )


    def add_document(self,doc_id:int):
        """添加文档到向量库，并保存信息"""
        conn = get_conn()
        try:
            res = conn.execute("""SELECT * FROM documents WHERE id = ?""", (doc_id,)).fetchone()
            if res is None:
                raise ValueError("找不到要入库的文档。")
            elif res["status"] == 1:
                raise ValueError("文档已入库，请勿重复操作。")
            elif res["status"] == -1:
                raise ValueError("文档正在入库中...")

            _,ext = os.path.splitext(res["name"])
            ext = ext.lower()
            if ext not in conf['rag']['allow_file_type']:
                raise ValueError("本程序仅支持文本文件(.txt)、PDF文件(.pdf)向量化。")

            #改变数据库状态，防止重复操作
            conn.execute("""UPDATE documents SET status = -1 WHERE id = ?""", (doc_id,))
            conn.commit()

            docs = ""
            if res["name"].endswith(".txt"):
                docs = TextLoader(get_abs_path(res["path"])).load()
            elif res["name"].endswith(".pdf"):
                docs = PyPDFLoader(get_abs_path(res["path"])).load()

            #分割文档
            split_doc = self.spliter.split_documents(docs)

            document = [
                Document(
                    page_content=text.page_content,
                    metadata={"source":res['name'],"doc_id": doc_id},
                )
                for text in split_doc
            ]

            self.vector.add_documents(document)

            #已入库成功
            conn.execute("""UPDATE documents SET status = 1 WHERE id = ?""", (doc_id,))
            conn.commit()
            conn.close()

        except NotImplementedError as e:
            #把正在入库改成未入库状态
            conn.execute("""UPDATE documents SET status = 0 WHERE id = ?""", (doc_id,))
            conn.commit()
            conn.close()
            raise e
        except Exception as e:
            conn.rollback()
            conn.close()
            #logger.error(e)
            raise e

    def get_retriever(self,doc_ids:list[int]):
        """文档检索器"""
        try:
            if not doc_ids:
                raise ValueError("文档ID不能为空。")
            return self.vector.as_retriever(search_kwargs = {
                "filter": {"doc_id": {"$in": doc_ids}},
                "k": conf['rag']['k'],
            })
        except Exception as e:
            raise e


    def search(self,doc_ids:list[int],query:str):
        """文档检索"""
        try:
            prompt_text = load_text(os.path.join(get_abs_path(conf['prompt_dir']),"rag_search.txt"))

            #老式操作
            #chain = PromptTemplate.from_template(prompt_text) |print_prompt| chat_model | StrOutputParser()

            chain = ChatPromptTemplate.from_messages([("system",prompt_text)]) |print_prompt| chat_model | StrOutputParser()

            #或
            #chain = ChatPromptTemplate.from_template(prompt_text) | print_prompt|chat_model | StrOutputParser()

            retriever = self.get_retriever(doc_ids)

            docs = retriever.invoke(query)

            context = ""

            for doc in docs:
                context+=f"来源：{doc.metadata['source']}\n内容：{doc.page_content}"

            return chain.invoke({"input":query,"context":context})

        except Exception as e:
            raise e

    def remove(self,doc_id:int):
        try:

            self.vector.delete(where = {"doc_id":doc_id})

            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("UPDATE  documents SET status = 0 WHERE id = ?", (doc_id,))
            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            raise e
    def delete(self,doc_id:int):
        conn = get_conn()
        cursor = conn.cursor()
        try:

            #删除向量
            self.vector.delete(where={"doc_id": doc_id})

            doc = cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()

            if doc:
                safe_delete(get_abs_path(doc["path"]))

            cursor.execute("""DELETE FROM documents WHERE id = ?""", (doc_id,))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            raise e
if __name__ == "__main__":
    vector = RagService()
    try:
        vector.add_document(1)
    except Exception as e:
        print(e)

    #vector.remove(1)

    query = "扫地机器人是维护知识。"
    #query = "张无忌会武功吗？"
    for chunk in vector.search([3],query):
       print(chunk,end="",flush=True)

    #vector.delete(1)