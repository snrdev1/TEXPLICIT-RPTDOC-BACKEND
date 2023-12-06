from typing import Union

from bson import ObjectId

from .agent.llm_utils import choose_agent
from .agent.run import run_agent


async def research(
    user_id: Union[str, ObjectId],
    task: str,
    websearch: bool,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[str, None],
    subtopics: list = [],
):
    agent_dict = choose_agent(task)
    agent = agent_dict.get("agent")
    agent_role_prompt = agent_dict.get("agent_role_prompt")

    print({"type": "logs", "output": f"Initiated an Agent: {agent}"})
    if task and report_type and agent:
        report, path = await run_agent(
            user_id=user_id,
            task=task,
            websearch=websearch,
            agent=agent,
            report_type=report_type,
            agent_role_prompt=agent_role_prompt,
            websocket=None,
            source=source,
            format=format,
            report_generation_id=report_generation_id,
            subtopics=subtopics,
        )
        return report, path
    else:
        print("⚠️ Error! Not enough parameters provided.")
        return "", ""
