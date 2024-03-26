# basic_report.py

from typing import List, Union

from bson import ObjectId

from app.utils.socket import emit_report_status
from app.utils.validator import ReportGenerationOutput

from ...master.research_agent import ResearchAgent


class BasicReport:
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
        self.urls = urls
        self.restrict_search = restrict_search
        self.assistant = self._create_research_assistant()

    async def generate_report(self) -> ReportGenerationOutput:
        print("🚦 Starting research")
        emit_report_status(
            self.user_id, self.report_generation_id, "🚦 Starting research..."
        )
        report_markdown = await self.assistant.conduct_research()

        report_markdown = report_markdown.strip()

        report_path, table_path = await self.assistant.save_report(report_markdown)

        return ReportGenerationOutput(
            report_markdown=report_markdown,
            report_path=report_path,
            tables=self.assistant.tables_extractor.tables,
            table_path=table_path,
            visited_urls=self.assistant.visited_urls,
            error_log=self.assistant.error_log
        )

    def _create_research_assistant(self) -> ResearchAgent:
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
