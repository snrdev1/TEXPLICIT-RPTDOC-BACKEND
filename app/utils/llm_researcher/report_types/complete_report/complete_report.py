# complete_report.py

from typing import Union, List

from bson import ObjectId

from app.utils import Enumerator

from ...master.research_agent import ResearchAgent
from ...master.run import AgentExecutor


class CompleteReport:
    def __init__(
        self,
        user_id: Union[ObjectId, str],
        task: str,
        report_type: str,
        source: str,
        format: str,
        report_generation_id: str,
        websocket,
        subtopics: list,
        check_existing_report: bool,
        urls: List[str],
        restrict_search: bool
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
        self.assistant = self._create_assistant()
        self.restrict_search = restrict_search

    async def create_report(self, report_type: str) -> tuple:
        report_executor = AgentExecutor(
            user_id=self.user_id,
            task=self.task,
            report_type=report_type,
            source=self.source,
            format=self.format,
            websocket=self.websocket,
            report_generation_id=self.report_generation_id,
            input_urls=self.urls,
            restrict_search=self.restrict_search
        )
        markdown, path, tables, table_path, urls = await report_executor.run_agent()
        return markdown, path, tables, table_path, urls

    async def generate_report(self) -> tuple:

        complete_report_path = await self._check_existing_report()
        if complete_report_path:
            return await self._handle_existing_report(complete_report_path)

        (
            outline_report_markdown,
            _,
            outline_report_tables,
            _,
            outline_report_urls,
        ) = await self.create_report(Enumerator.ReportType.OutlineReport.value)

        (
            resource_report_markdown,
            _,
            resource_report_tables,
            _,
            resource_report_urls,
        ) = await self.create_report(Enumerator.ReportType.ResourceReport.value)

        (
            detailed_report_markdown,
            _,
            detailed_reports_tables,
            _,
            detailed_report_urls,
        ) = await self.create_report(Enumerator.ReportType.DetailedReport.value)

        report_markdown = (
            "#OUTLINE REPORT\n\n"
            + outline_report_markdown
            + "\n\n\n\n#RESOURCE REPORT\n\n"
            + resource_report_markdown
            + "\n\n\n\n#DETAILED REPORT\n\n"
            + detailed_report_markdown
        )
        report_markdown = report_markdown.strip()

        if not report_markdown:
            return "", "", [], set()
        
        # Accumulate all tables
        self.assistant.tables_extractor.tables = (
            outline_report_tables + resource_report_tables + detailed_reports_tables
        )

        # Accumulate all urls
        self.assistant.visited_urls.update(
            outline_report_urls, resource_report_urls, detailed_report_urls
        )

        report_path, table_path = await self.assistant.save_report(report_markdown)

        return (
            report_markdown,
            report_path, 
            self.assistant.tables_extractor.tables,
            table_path,
            self.assistant.visited_urls,
        )

    def _create_assistant(self) -> ResearchAgent:
        return ResearchAgent(
            user_id=self.user_id,
            query=self.task,
            source=self.source,
            format=self.format,
            report_type=self.report_type,
            websocket=self.websocket,
            report_generation_id=self.report_generation_id,
            input_urls=self.urls,
            restrict_search=self.restrict_search
        )

    async def _check_existing_report(self) -> str:
        if self.check_existing_report:
            return await self.assistant.check_existing_report(self.report_type)
        return None

    async def _handle_existing_report(self, path: str) -> tuple:
        await self.assistant.extract_tables()
        report_markdown = await self.assistant.get_report_markdown(self.report_type)
        complete_report = report_markdown.strip()

        return (
            complete_report,
            path,
            self.assistant.tables_extractor.tables,
        )
