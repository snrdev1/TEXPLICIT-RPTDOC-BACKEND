import asyncio
import datetime
from typing import Union

from bson import ObjectId


class AgentExecutor:
    def __init__(
        self,
        user_id: Union[ObjectId, str],
        task: str,
        websearch: bool = True,
        report_type: str = "research_report",
        source: str = "external",
        format: str = "pdf",
        report_generation_id: str = "",
        websocket=None,
        subtopics: list = [],
        check_existing_report: bool = False,
    ):
        self.user_id = user_id
        self.task = task
        self.websearch = websearch
        self.report_type = report_type
        self.source = source
        self.format = format
        self.report_generation_id = report_generation_id
        self.websocket = websocket
        self.subtopics = subtopics
        self.check_existing_report = check_existing_report

    def get_report_executor(self):
        match self.report_type:
            case "detailed_report":
                from ..report_types import DetailedReport

                executor = DetailedReport
            case "complete_report":
                from ..report_types import CompleteReport

                executor = CompleteReport

            case _:
                from ..report_types import BasicReport

                executor = BasicReport

        return executor

    async def run_agent(self) -> tuple:
        start_time = datetime.datetime.utcnow()
        print({"type": "logs", "output": f"Start time: {str(start_time)}\n\n"})

        Executor = self.get_report_executor()
        executor = Executor(
            user_id=self.user_id,
            task=self.task,
            websearch=self.websearch,
            report_type=self.report_type,
            source=self.source,
            format=self.format,
            report_generation_id=self.report_generation_id,
            websocket=self.websocket,
            check_existing_report=self.check_existing_report,
        )
        report_markdown, path, tables, urls = await executor.generate_report()

        end_time = datetime.datetime.utcnow()
        print({"type": "path", "output": path})
        print({"type": "logs", "output": f"\nEnd time: {end_time}\n"})
        print(
            {"type": "logs", "output": f"\nTotal run time: {end_time - start_time}\n"}
        )

        return report_markdown, path, tables, urls
