from crewai import Agent, LLM


llm = LLM(
    model="ollama/qwen3.5:latest",
    base_url="http://localhost:11434",
    temperature=0.1,
)

disease_agent = Agent(
    role="植物保护与病虫害防治专家",
    goal="精准诊断病虫害并提供安全、合规的农药或生物防治方案",
    backstory="你是一名植保专家，擅长常见果树、浆果和瓜果病虫害的病理分析与绿色防控技术。",
    llm=llm,
    verbose=True,
)
