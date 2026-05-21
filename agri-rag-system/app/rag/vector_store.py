from langchain_community.vectorstores import Chroma

from app.config import VECTOR_DB_DIR
from app.rag.embedding import get_embedding_model
from app.rag.loader import load_documents
from app.rag.splitter import split_documents


def build_vector_db():
    print("正在加载文档...")
    documents = load_documents()
    print(f"加载文档数: {len(documents)}")

    print("正在切分文本...")
    chunks = split_documents(documents)
    print(f"切块数量: {len(chunks)}")

    print("正在加载 Embedding 模型...")
    embedding = get_embedding_model()

    print("正在构建 Chroma 向量数据库...")
    db = Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        persist_directory=str(VECTOR_DB_DIR),
    )

    db.persist()
    print("向量数据库构建完成")


def load_vector_db():
    embedding = get_embedding_model()

    return Chroma(
        persist_directory=str(VECTOR_DB_DIR),
        embedding_function=embedding,
    )
