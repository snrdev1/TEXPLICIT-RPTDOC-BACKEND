import datetime
from typing import List, Union

from bson import ObjectId

from app.utils import Enumerator
from app.utils.validator import ReportGenerationOutput


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
        urls: List[str] = [],
        restrict_search: bool = False
    ):
        self.user_id = user_id
        self.task = task
        self.report_type = report_type
        self.source = source
        self.format = format
        self.report_generation_id = report_generation_id
        self.websocket = websocket
        self.subtopics = subtopics
        self.urls = urls
        self.restrict_search = restrict_search

    def get_report_executor(self):
        match self.report_type:
            case Enumerator.ReportType.DetailedReport.value:
                from ..report_types import DetailedReport

                executor = DetailedReport
            case _:
                from ..report_types import BasicReport

                executor = BasicReport

        return executor

    async def run_agent(self) -> ReportGenerationOutput:
        start_time = datetime.datetime.now(datetime.timezone.utc)
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
            urls=self.urls,
            restrict_search=self.restrict_search
        )

        report: ReportGenerationOutput = await executor.generate_report()

        end_time = datetime.datetime.now(datetime.timezone.utc)
        print({"type": "path", "output": report.report_path})
        print({"type": "logs", "output": f"\nEnd time: {end_time}\n"})
        print({"type": "logs", "output": f"\nTotal run time: {end_time - start_time}\n"})

        return report
