# detailed_report.py

import asyncio
from typing import List, Union

from bson import ObjectId

from app.utils import Enumerator
from app.utils.socket import emit_report_status
from app.utils.validator import ReportGenerationOutput

from ...master.functions import extract_headers, table_of_contents
from ...master.research_agent import ResearchAgent


class DetailedReport:
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
        self.main_task_assistant = self._create_task_assistant()
        self.existing_headers = []
        # This is a global variable to store the entire context accumulated at any point through searching and scraping
        self.global_context = []
        # This is a global variable to store the entire url list accumulated at any point through searching and scraping
        self.global_urls = set(self.urls)

    async def generate_report(self) -> ReportGenerationOutput:
        # Conduct initial research using the main assistant
        await self._initial_research()

        # Get list of all subtopics
        subtopics = await self._get_all_subtopics()

        # Generate the subtopic reports based on the subtopics gathered
        _, subtopics_reports_body, tables = await self._generate_subtopic_reports(subtopics)

        # Construct the final list of unique tables
        self.main_task_assistant.tables_extractor.tables.extend(tables)

        # Construct the final list of visited urls
        self.main_task_assistant.visited_urls.update(self.global_urls)

        # Construct the final detailed report
        (
            detailed_report,
            detailed_report_path,
            table_path
        ) = await self._construct_detailed_report(subtopics_reports_body)

        return ReportGenerationOutput(
            report_markdown=detailed_report,
            report_path=detailed_report_path,
            tables=self.main_task_assistant.tables_extractor.tables,
            table_path=table_path,
            visited_urls=self.main_task_assistant.visited_urls,
            error_log=self.main_task_assistant.error_log
        )

    def _create_task_assistant(self) -> ResearchAgent:
        return ResearchAgent(
            user_id=self.user_id,
            query=self.task,
            source=self.source,
            format=self.format,
            report_type=Enumerator.ReportType.ResearchReport.value,
            websocket=self.websocket,
            report_generation_id=self.report_generation_id,
            input_urls=self.urls,
            subtopics=self.subtopics,
            restrict_search=self.restrict_search
        )

    async def _handle_existing_report(self, path: str) -> tuple:
        emit_report_status(
            self.user_id, self.report_generation_id, "💎 Found existing report..."
        )
        await self.main_task_assistant.extract_tables()
        report_markdown = await self.main_task_assistant.get_report_markdown(
            self.report_type
        )
        detailed_report = report_markdown.strip()

        return (
            detailed_report,
            path,
            self.main_task_assistant.tables_extractor.tables,
        )

    async def _initial_research(self):
        # Conduct research using the main task assistant to gather content for generating subtopics
        await self.main_task_assistant.conduct_research(write_report=False)
        # Update context of the global context variable
        self.global_context = self.main_task_assistant.context
        # Update url list of the global list variable
        self.global_urls = self.main_task_assistant.visited_urls

    async def _get_all_subtopics(self) -> list:
        subtopics = await self.main_task_assistant.get_subtopics()
        return subtopics.dict()["subtopics"]

    async def _generate_subtopic_reports(self, subtopics: list) -> tuple:
        reports = []
        report_body = ""
        tables = []

        async def fetch_report(subtopic):
            emit_report_status(
                self.user_id,
                self.report_generation_id,
                f"🚦 Conducting research on subtopic : {subtopic}...",
            )
            (
                subtopic_report_markdown,
                subtopic_path,
                subtopic_tables
            ) = await self._get_subtopic_report(
                subtopic
            )
            return {
                "topic": subtopic,
                "markdown_report": subtopic_report_markdown,
                "path": subtopic_path,
                "tables": subtopic_tables
            }

        tasks = [fetch_report(subtopic) for subtopic in subtopics]
        results = await asyncio.gather(*tasks)

        for result in filter(lambda r: r["markdown_report"], results):
            reports.append(result)
            report_body += "\n\n\n" + result["markdown_report"]
            tables.extend(result["tables"])

        return reports, report_body, tables

    async def _get_subtopic_report(self, subtopic: dict) -> tuple:
        current_subtopic_task = subtopic.get("task")
        subtopic_source = subtopic.get("source")
        subtopic_assistant = ResearchAgent(
            user_id=self.user_id,
            query=current_subtopic_task,
            source=subtopic_source,
            format=self.format,
            report_type=Enumerator.ReportType.SubtopicReport.value,
            websocket=self.websocket,
            parent_query=self.task,
            subtopics=self.subtopics,
            report_generation_id=self.report_generation_id,
            restrict_search=self.restrict_search,
            visited_urls=self.global_urls,
            agent=self.main_task_assistant.agent,
            role=self.main_task_assistant.role
        )

        # The subtopics should start research from the context gathered till now
        subtopic_assistant.context = list(set(self.global_context))

        if self.restrict_search:
            # If search type is restricted then the existing context should be used for writing report
            report_markdown = await subtopic_assistant.write_report(
                existing_headers=self.existing_headers
            )
        else:
            # If search type is mixed then further research needs to be conducted
            report_markdown = await subtopic_assistant.conduct_research(
                max_docs=10, score_threshold=1, existing_headers=self.existing_headers
            )

        # Update context of the global context variable
        self.global_context = list(set(subtopic_assistant.context))
        # Update url list of the global list variable
        self.global_urls.update(subtopic_assistant.visited_urls)

        # After a subtopic report has been generated then append the headers of the report to existing headers
        self.existing_headers.append(
            {
                "subtopic task": current_subtopic_task,
                "headers": extract_headers(report_markdown),
            }
        )

        if not report_markdown.strip():
            print(
                f"⚠️ Failed to gather data from research on subtopic : {self.task}")
            return "", "", []

        return report_markdown, "", subtopic_assistant.tables_extractor.tables

    async def _construct_detailed_report(self, report_body: str) -> tuple:
        # Get the introduction and the conclusion
        introduction, conclusion = await self.main_task_assistant.write_introduction_conclusion()

        # Construct the final detailed report
        detailed_report = (
            introduction + "\n\n"
            + table_of_contents(report_body + '\n\n' + conclusion) + "\n\n"
            + report_body + "\n\n"
            + conclusion
        )

        # Get the detailed report path and the table path
        detailed_report_path, table_path = await self.main_task_assistant.save_report(detailed_report)

        return detailed_report, detailed_report_path, table_path
