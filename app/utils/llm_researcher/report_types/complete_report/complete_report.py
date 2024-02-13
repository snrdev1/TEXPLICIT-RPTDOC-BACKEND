# complete_report.py

from app.utils.socket import emit_report_status
from bson import ObjectId
from typing import Union
from ...master.research_agent import ResearchAgent
from ...master.run import AgentExecutor

class CompleteReport():
    def __init__(
        self,
        user_id: Union[ObjectId, str],
        task: str,
        report_type: str,
        websearch: bool = True,
        source: str = "external",
        format: str = "pdf",
        report_generation_id: str = "",
        websocket=None,
        subtopics: list = [],
        check_existing_report: bool = False,
    ):
        self.user_id = user_id
        self.task = task
        self.report_type = report_type
        self.websearch = websearch
        self.source = source
        self.format = format
        self.report_generation_id = report_generation_id
        self.websocket = websocket
        self.subtopics = subtopics
        self.check_existing_report = check_existing_report
    
    async def create_report(self, report_type: str) -> tuple:
        report_executor = AgentExecutor(
            user_id=self.user_id,
            task=self.task,
            websearch=self.websearch,
            report_type=report_type,
            source=self.source,
            format=self.format,
            websocket=self.websocket,
            report_generation_id=self.report_generation_id,
        )
        markdown, path, tables, urls = await report_executor.run_agent()
        return markdown, path, tables, urls
    
    async def generate_report(self) -> tuple:
        assistant = self._create_assistant()

        complete_report_path = await self._check_existing_report(assistant)
        if complete_report_path:
            return await self._handle_existing_report(assistant, complete_report_path)

        (
            outline_report_markdown,
            outline_report_path,
            outline_report_tables,
            outline_report_urls,
        ) = await self.create_report("outline_report")

        (
            resource_report_markdown,
            resource_report_path,
            resource_report_tables,
            resource_report_urls,
        ) = await self.create_report("resource_report")

        (
            detailed_report_markdown,
            detailed_report_path,
            detailed_reports_tables,
            detailed_report_urls,
        ) = await self.create_report("detailed_report")

        report_markdown = (
            outline_report_markdown
            + "\n\n\n\n"
            + resource_report_markdown
            + "\n\n\n\n"
            + detailed_report_markdown
        )
        report_markdown = report_markdown.strip()

        assistant.tables_extractor.tables = (
            outline_report_tables + resource_report_tables + detailed_reports_tables
        )

        if not report_markdown:
            return "", "", [], set()

        assistant.visited_urls.update(
            outline_report_urls, resource_report_urls, detailed_report_urls
        )

        path = await assistant.save_report(report_markdown)

        return (
            report_markdown,
            path,
            assistant.tables_extractor.tables,
            assistant.visited_urls,
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
        )

    async def _check_existing_report(self, assistant: ResearchAgent) -> str:
        if self.check_existing_report:
            return await assistant.check_existing_report(self.report_type)
        return None

    async def _handle_existing_report(self, assistant: ResearchAgent, path: str) -> tuple:
        await assistant.extract_tables()
        report_markdown = await assistant.get_report_markdown(self.report_type)
        complete_report = report_markdown.strip()

        return (
            complete_report,
            path,
            assistant.tables_extractor.tables,
        )
