from typing import Union

from bson import ObjectId

from .agent.run import AgentExecutor


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
    if task:
        agent_executor = AgentExecutor(
            user_id=user_id,
            task=task,
            websearch=websearch,
            report_type=report_type,
            websocket=None,
            source=source,
            format=format,
            report_generation_id=report_generation_id,
            subtopics=subtopics,
            # check_existing_report=True
        )
        report, path, _ = await agent_executor.run_agent()
        return report, path
    else:
        print("⚠️ Error! Not enough parameters provided.")
        return "", ""
