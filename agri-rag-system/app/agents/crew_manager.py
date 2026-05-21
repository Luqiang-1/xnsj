from crewai import Crew, Task

from app.agents.crop_agent import crop_agent
from app.agents.disease_agent import disease_agent
from app.agents.sales_agent import sales_agent


def run_crew(question):
    if "病" in question or "农药" in question or "防治" in question:
        agent = disease_agent
    elif "销售" in question or "运输" in question or "市场" in question:
        agent = sales_agent
    else:
        agent = crop_agent

    task = Task(
        description=question,
        agent=agent,
        expected_output="专业、结构化、可直接指导农业生产的中文回答",
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True,
    )

    return str(crew.kickoff())


if __name__ == "__main__":
    result = run_crew("草莓灰霉病怎么防治？")
    print("\n最终回答：\n", result)
