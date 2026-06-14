"""向量存储、检索、增强生成"""
import json
import os.path
import re
from datetime import datetime
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
                text = self._clean_txt_text(text)
                if not text.strip():
                    return []
                return [
                    Document(
                        page_content=text,
                        metadata={
                            "source": source_name,
                            "page": -1,
                            "loader": "txt",
                        },
                    )
                ]
            except UnicodeDecodeError as e:
                last_error = e
                continue

        raise ValueError(f"txt 编码无法识别: {file_path}") from last_error

    def _normalize_newlines(self, text: str) -> str:
        """统一换行和空白。"""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _clean_txt_text(self, text: str) -> str:
        """TXT 轻量清洗，尽量保留段落结构。"""
        text = self._normalize_newlines(text)
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _clean_pdf_text(self, text: str) -> str:
        """PDF 轻量清洗，去掉明显噪音并保留结构。"""
        text = self._normalize_newlines(text)
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append("")
                continue
            if re.fullmatch(r"\d+", stripped):
                continue
            cleaned_lines.append(stripped)

        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"([。！？；;])\n([^\n])", r"\1\n\2", text)
        return text.strip()

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
                docs = []
                for page_doc in PyPDFLoader(file_path).load():
                    cleaned_text = self._clean_pdf_text(page_doc.page_content)
                    if not cleaned_text.strip():
                        continue
                    metadata = dict(page_doc.metadata or {})
                    metadata.update(
                        {
                            "source": res["name"],
                            "loader": "pdf",
                        }
                    )
                    docs.append(Document(page_content=cleaned_text, metadata=metadata))
            else:
                raise ValueError(f"不支持的文件类型: {ext}")

            split_doc = self.spliter.split_documents(docs)
            if not split_doc:
                raise ValueError("文档切分结果为空")

            document = [
                Document(
                    page_content=text.page_content,
                    metadata={
                        "source": res["name"],
                        "doc_id": doc_id,
                        "chunk_index": index,
                        "page": text.metadata.get("page", -1) if isinstance(text.metadata, dict) else -1,
                        "user_id": res["user_id"],
                        "dept_id": res["dept_id"] or 0,
                        "doc_type": res["type"],
                        "file_hash": res["hash"],
                    },
                )
                for index, text in enumerate(split_doc, start=1)
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

    def _search_with_scores(self, doc_ids: list[int], query: str):
        """优先获取带分数的检索结果，失败则回退到普通检索。"""
        results = None
        if hasattr(self.vector, "similarity_search_with_score"):
            try:
                results = self.vector.similarity_search_with_score(
                    query,
                    k=conf["rag"]["k"],
                    filter={"doc_id": {"$in": doc_ids}},
                )
            except TypeError:
                pass
            except Exception:
                pass

        if results is None:
            docs = self.get_retriever(doc_ids).invoke(query)
            return [(doc, None) for doc in docs]

        max_distance = conf["rag"].get("max_distance")
        if max_distance is None:
            return results

        return [
            (doc, distance)
            for doc, distance in results
            if distance is None or distance <= max_distance
        ]

    def _format_context(self, docs_with_scores):
        """把检索结果格式化为适合喂给模型的上下文。"""
        max_chars = conf["rag"].get("max_context_chars", 1000)
        parts = []
        total = 0

        for index, item in enumerate(docs_with_scores, start=1):
            doc, score = item if isinstance(item, tuple) else (item, None)

            source = doc.metadata.get("source", "未知来源")
            page = doc.metadata.get("page")
            page_text = f"第 {page + 1} 页" if isinstance(page, int) else None
            header = f"[{index}] 来源：{source}"
            if page_text:
                header += f"，{page_text}"
            if score is not None:
                header += f"，distance={score}"

            block = f"{header}\n内容：{doc.page_content}"
            block_len = len(block)
            if parts and total + block_len > max_chars:
                parts.append("...（上下文已截断）")
                break
            parts.append(block)
            parts.append("")
            total += block_len

        return "\n".join(parts).strip()

    def _rerank(self, query: str, docs_with_scores):
        """对召回结果做轻量重排。"""
        if len(docs_with_scores) <= 1:
            return docs_with_scores

        candidate_count = conf["rag"].get("rerank_candidates", len(docs_with_scores))
        candidates = docs_with_scores[:candidate_count]
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是检索结果重排器。根据用户问题和候选片段，按相关性从高到低输出候选编号，格式只允许输出逗号分隔的编号列表，例如：2,1,3。不要输出任何解释。",
                ),
                (
                    "user",
                    "用户问题：{query}\n\n候选片段：\n{candidates}",
                ),
            ]
        )
        formatted_candidates = []
        for index, item in enumerate(candidates, start=1):
            doc, score = item if isinstance(item, tuple) else (item, None)
            source = doc.metadata.get("source", "未知来源")
            page = doc.metadata.get("page")
            chunk_index = doc.metadata.get("chunk_index")
            header = f"[{index}] 来源：{source}"
            if isinstance(page, int) and page >= 0:
                header += f"，第 {page + 1} 页"
            if isinstance(chunk_index, int):
                header += f"，chunk={chunk_index}"
            if score is not None:
                header += f"，distance={score}"
            formatted_candidates.append(f"{header}\n内容：{doc.page_content}")

        try:
            response = (prompt | chat_model | StrOutputParser()).invoke(
                {
                    "query": query,
                    "candidates": "\n\n".join(formatted_candidates),
                }
            )
            order = []
            for token in str(response).replace("，", ",").split(","):
                token = token.strip()
                if token.isdigit():
                    idx = int(token)
                    if 1 <= idx <= len(candidates) and idx not in order:
                        order.append(idx)
            if not order:
                return docs_with_scores

            ranked = [candidates[i - 1] for i in order]
            ranked.extend(item for idx, item in enumerate(candidates, start=1) if idx not in order)
            ranked.extend(docs_with_scores[candidate_count:])
            return ranked
        except Exception:
            return docs_with_scores

    def _save_retrieve_data(self, doc_ids: list[int], query: str, docs: list[Document]):
        """把每次 retrieve 的结果落盘，方便排查召回过程。"""
        log_dir = get_abs_path("data/retrieveData")
        os.makedirs(log_dir, exist_ok=True)

        now = datetime.now()
        path = os.path.join(log_dir, f"retrieve_{now.strftime('%Y%m%d_%H%M%S_%f')}.json")

        payload = {
            "created_at": now.isoformat(timespec="milliseconds"),
            "query": query,
            "doc_ids": doc_ids,
            "count": len(docs),
            "results": [
                {
                    "index": index,
                    "metadata": dict(doc.metadata),
                    "page_content": doc.page_content,
                }
                for index, doc in enumerate(docs, start=1)
            ],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def search(self, doc_ids: list[int], query: str):
        """文档检索"""
        prompt_text = load_text(os.path.join(get_abs_path(conf["prompt_dir"]), "rag_search.txt"))
        chain = ChatPromptTemplate.from_messages([("system", prompt_text)]) | print_prompt | chat_model | StrOutputParser()

        docs_with_scores = self._search_with_scores(doc_ids, query)
        if not docs_with_scores:
            return "在提供的文档中未找到相关信息。"

        docs_with_scores = self._rerank(query, docs_with_scores)
        context = self._format_context(docs_with_scores)
        if not context:
            return "在提供的文档中未找到相关信息。"

        return chain.invoke({"input": query, "context": context})

    def retrieve(self, doc_ids: list[int], query: str):
        """只执行检索，返回原始文档片段。"""
        docs_with_scores = self._search_with_scores(doc_ids, query)
        docs_with_scores = self._rerank(query, docs_with_scores)
        docs = []
        for doc, distance in docs_with_scores:
            if distance is not None:
                doc.metadata["distance"] = distance
            docs.append(doc)
        self._save_retrieve_data(doc_ids, query, docs)
        return docs

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
