from typing import List, Union

from bson import ObjectId

from ..validator import ReportGenerationOutput
from .master.run import AgentExecutor


async def research(
    user_id: Union[str, ObjectId],
    task: str,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[str, None],
    subtopics: list,
    urls: List[str],
    restrict_search: bool
) -> ReportGenerationOutput:

    agent_executor = AgentExecutor(
        user_id=user_id,
        task=task,
        report_type=report_type,
        websocket=None,
        source=source,
        format=format,
        report_generation_id=report_generation_id,
        subtopics=subtopics,
        urls=urls,
        restrict_search=restrict_search
    )

    report: ReportGenerationOutput = await agent_executor.run_agent()

    return report
