from app.rag.vector_store import load_vector_db


def search_knowledge(query):
    db = load_vector_db()
    docs = db.similarity_search(query, k=5)

    return "\n".join(doc.page_content for doc in docs)
