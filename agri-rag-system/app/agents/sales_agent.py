from crewai import Agent, LLM


llm = LLM(
    model="ollama/qwen3.5:latest",
    base_url="http://localhost:11434",
    temperature=0.2,
)

sales_agent = Agent(
    role="农产品供应链与销售专家",
    goal="提供果品定价、渠道对接、冷链保鲜与品牌营销建议",
    backstory="你熟悉国内生鲜农产品流通体系，擅长高附加值水果的采后处理、电商运营与批发对接。",
    llm=llm,
    verbose=True,
)
