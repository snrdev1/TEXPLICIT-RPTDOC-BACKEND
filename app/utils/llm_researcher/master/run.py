import asyncio
import datetime
from typing import Union, List

from bson import ObjectId

from app.utils import Enumerator


class AgentExecutor:
    def __init__(
        self,
        user_id: Union[ObjectId, str],
        task: str,
        report_type: str = Enumerator.ReportType.ResearchReport.value,
        source: str = "external",
        format: str = "pdf",
        report_generation_id: str = "",
        websocket=None,
        subtopics: list = [],
        check_existing_report: bool = False,
        urls: List[str] = []
    ):
        self.user_id = user_id
        self.task = task
        self.report_type = report_type
        self.source = source
        self.format = format
        self.report_generation_id = report_generation_id
        self.websocket = websocket
        self.subtopics = subtopics
        self.check_existing_report = check_existing_report
        self.urls = urls

    def get_report_executor(self):
        match self.report_type:
            case Enumerator.ReportType.DetailedReport.value:
                from ..report_types import DetailedReport

                executor = DetailedReport
            case Enumerator.ReportType.CompleteReport.value:
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
            report_type=self.report_type,
            source=self.source,
            format=self.format,
            report_generation_id=self.report_generation_id,
            websocket=self.websocket,
            subtopics=self.subtopics,
            check_existing_report=self.check_existing_report,
            urls=self.urls
        )
        report_markdown, report_path, tables, table_path, urls = await executor.generate_report()

        end_time = datetime.datetime.utcnow()
        print({"type": "path", "output": report_path})
        print({"type": "logs", "output": f"\nEnd time: {end_time}\n"})
        print({"type": "logs", "output": f"\nTotal run time: {end_time - start_time}\n"})

        return report_markdown, report_path, tables, table_path, urls
