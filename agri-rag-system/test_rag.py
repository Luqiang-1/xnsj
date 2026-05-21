from app.rag.qa_chain import search_knowledge


query = "草莓适合什么环境？"
result = search_knowledge(query)

print(result)
