"""向量存储、检索、增强生成"""
import os.path
from typing import List

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.database import get_conn
from core.model import embedding_model, chat_model
from core.config import conf
from utils.file import get_abs_path, load_text, safe_delete


def print_prompt(prompt):
    print("=" * 20)
    print(prompt.to_string())
    print("=" * 20)
    return prompt


class RagService:
    def __init__(self):
        # 向量存储、检索
        self.vector = Chroma(
            collection_name=conf["rag"]["collection_name"],
            embedding_function=embedding_model,
            persist_directory=get_abs_path(conf["rag"]["persist_dir"]),
        )

        # 分块器
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=conf["rag"]["chunk_size"],
            chunk_overlap=conf["rag"]["chunk_overlap"],
            separators=conf["rag"]["separators"],
            length_function=len,
        )

    def _load_txt_documents(self, file_path: str, source_name: str) -> List[Document]:
        """
        兼容不同编码的 txt。
        Windows 上经常遇到 utf-8/gbk/utf-16 混用，避免直接解码失败。
        """
        encodings = [
            "utf-8",
            "utf-8-sig",
            "gb18030",
            "gbk",
            "gb2312",
            "utf-16",
            "utf-16-le",
            "utf-16-be",
        ]
        last_error = None
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    text = f.read()
                return [Document(page_content=text, metadata={"source": source_name})]
            except UnicodeDecodeError as e:
                last_error = e
                continue

        raise ValueError(f"txt 编码无法识别: {file_path}") from last_error

    def add_document(self, doc_id: int):
        """添加文档到向量库，并保存信息"""
        conn = get_conn()
        status_locked = False
        try:
            res = conn.execute("""SELECT * FROM documents WHERE id = ?""", (doc_id,)).fetchone()
            if res is None:
                raise ValueError("找不到要入库的文档")
            if res["status"] == 1:
                raise ValueError("文档已入库，请勿重复操作")
            if res["status"] == -1:
                raise ValueError("文档正在入库中")

            _, ext = os.path.splitext(res["name"])
            ext = ext.lower()
            if ext not in conf["rag"]["allow_file_type"]:
                raise ValueError("仅支持 .txt/.pdf 文件向量化")

            # 标记入库中，防止重复并发请求
            conn.execute("""UPDATE documents SET status = -1 WHERE id = ?""", (doc_id,))
            conn.commit()
            status_locked = True

            file_path = get_abs_path(res["path"])
            if ext == ".txt":
                docs = self._load_txt_documents(file_path, res["name"])
            elif ext == ".pdf":
                docs = PyPDFLoader(file_path).load()
            else:
                raise ValueError(f"不支持的文件类型: {ext}")

            split_doc = self.spliter.split_documents(docs)
            if not split_doc:
                raise ValueError("文档切分结果为空")

            document = [
                Document(
                    page_content=text.page_content,
                    metadata={"source": res["name"], "doc_id": doc_id},
                )
                for text in split_doc
            ]

            self.vector.add_documents(document)

            # 入库成功
            conn.execute("""UPDATE documents SET status = 1 WHERE id = ?""", (doc_id,))
            conn.commit()
            status_locked = False

        except Exception as e:
            conn.rollback()
            # 如果已经标记 -1，则失败后恢复到 0，避免卡死
            if status_locked:
                try:
                    conn.execute("""UPDATE documents SET status = 0 WHERE id = ?""", (doc_id,))
                    conn.commit()
                except Exception:
                    conn.rollback()
            raise e
        finally:
            conn.close()

    def get_retriever(self, doc_ids: list[int]):
        """文档检索器"""
        if not doc_ids:
            raise ValueError("文档ID不能为空")
        return self.vector.as_retriever(
            search_kwargs={
                "filter": {"doc_id": {"$in": doc_ids}},
                "k": conf["rag"]["k"],
            }
        )

    def search(self, doc_ids: list[int], query: str):
        """文档检索"""
        prompt_text = load_text(os.path.join(get_abs_path(conf["prompt_dir"]), "rag_search.txt"))
        chain = ChatPromptTemplate.from_messages([("system", prompt_text)]) | print_prompt | chat_model | StrOutputParser()

        retriever = self.get_retriever(doc_ids)
        docs = retriever.invoke(query)

        context = ""
        for doc in docs:
            context += f"来源：{doc.metadata['source']}\n内容：{doc.page_content}"

        return chain.invoke({"input": query, "context": context})

    def retrieve(self, doc_ids: list[int], query: str):
        """只执行检索，返回原始文档片段。"""
        retriever = self.get_retriever(doc_ids)
        return retriever.invoke(query)

    def remove(self, doc_id: int):
        self.vector.delete(where={"doc_id": doc_id})

        conn = get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE documents SET status = 0 WHERE id = ?", (doc_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def delete(self, doc_id: int):
        conn = get_conn()
        cursor = conn.cursor()
        try:
            # 删除向量
            self.vector.delete(where={"doc_id": doc_id})

            doc = cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if doc:
                safe_delete(get_abs_path(doc["path"]))

            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()


if __name__ == "__main__":
    vector = RagService()
    try:
        vector.add_document(1)
    except Exception as e:
        print(e)

    query = "扫地机器人维护知识"
    for chunk in vector.search([3], query):
        print(chunk, end="", flush=True)
