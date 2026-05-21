from crewai import Agent, LLM


llm = LLM(
    model="ollama/qwen3.5:latest",
    base_url="http://localhost:11434",
    temperature=0.1,
)

crop_agent = Agent(
    role="农业综合种植专家",
    goal="提供作物栽培、土壤管理、水肥一体化等综合农事指导",
    backstory="你是一位拥有多年田间经验的农技推广员，熟悉果用经济作物的标准化种植流程。",
    llm=llm,
    verbose=True,
)
