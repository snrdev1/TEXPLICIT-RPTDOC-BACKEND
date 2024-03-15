# basic_report.py

from typing import Union, List

from bson import ObjectId

from app.utils.socket import emit_report_status

from ...master.research_agent import ResearchAgent


class BasicReport:
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
        urls: List[str] = []
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
        self.urls = urls
        self.assistant = self._create_research_assistant()

    async def generate_report(self) -> tuple:
        path = await self._check_existing_report()
        if path:
            return await self._handle_existing_report(path)

        return await self._conduct_research()

    def _create_research_assistant(self) -> ResearchAgent:
        return ResearchAgent(
            user_id=self.user_id,
            query=self.task,
            source=self.source,
            format=self.format,
            report_type=self.report_type,
            websocket=self.websocket,
            report_generation_id=self.report_generation_id,
            urls=self.urls
        )

    async def _check_existing_report(self) -> str:
        if self.check_existing_report:
            return await self.assistant.check_existing_report(self.report_type)
        return None

    async def _handle_existing_report(self, path: str) -> tuple:
        emit_report_status(
            self.user_id, self.report_generation_id, "💎 Found existing report..."
        )
        await self.assistant.extract_tables()
        report_markdown = await self.assistant.get_report_markdown(self.report_type)
        report_markdown = report_markdown.strip()

        return (
            report_markdown,
            path,
            self.assistant.tables_extractor.tables,
            self.assistant.visited_urls,
        )

    async def _conduct_research(self) -> tuple:
        print("🚦 Starting research")
        emit_report_status(
            self.user_id, self.report_generation_id, "🚦 Starting research..."
        )
        report_markdown = await self.assistant.conduct_research()

        report_markdown = report_markdown.strip()
        if len(report_markdown) == 0:
            return "", "", [], set()

        path = await self.assistant.save_report(report_markdown)

        return (
            report_markdown,
            path,
            self.assistant.tables_extractor.tables,
            self.assistant.visited_urls,
        )
