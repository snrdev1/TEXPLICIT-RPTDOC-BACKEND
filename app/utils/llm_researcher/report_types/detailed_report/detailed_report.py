# detailed_report.py

import asyncio
from typing import List, Union

from bson import ObjectId

from app.utils import Enumerator
from app.utils.socket import emit_report_status

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
        check_existing_report: bool,
        urls: List[str],
        restrict_search: bool,
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
        self.restrict_search = restrict_search
        self.main_task_assistant = self._create_task_assistant()
        self.existing_headers = []
        self.global_context = []
        self.global_urls = set(self.urls)

    async def generate_report(self) -> tuple:
        # Handle existing reports if check_existing_report is True
        detailed_report_path = await self._check_existing_report()
        if detailed_report_path:
            return await self._handle_existing_report(detailed_report_path)

        # Conduct initial research using the main assistant
        await self._initial_research()

        # Generate the subtopic reports sequentially
        subtopics_reports_body, tables = await self._generate_subtopic_reports_async_sequential()

        # Construct the final list of unique tables
        self.main_task_assistant.tables_extractor.tables.extend(tables)

        # Construct the final list of visited urls
        self.main_task_assistant.visited_urls.update(self.global_urls)

        # Construct the final detailed report
        (
            detailed_report,
            detailed_report_path,
            table_path,
        ) = await self._construct_detailed_report(subtopics_reports_body)

        return (
            detailed_report,
            detailed_report_path,
            self.main_task_assistant.tables_extractor.tables,
            table_path,
            self.main_task_assistant.visited_urls,
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
            restrict_search=self.restrict_search,
        )

    async def _check_existing_report(self) -> str:
        if self.check_existing_report:
            return await self.main_task_assistant.check_existing_report(
                self.report_type
            )
        return None

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
        self.global_context = self.main_task_assistant.context
        self.global_urls = self.main_task_assistant.visited_urls

    async def _generate_subtopic_reports_async_sequential(self) -> tuple:
        reports_body = ""
        tables = []
        existing_headers = []

        async def generate_subtopic_report(subtopic):
            nonlocal existing_headers  # Use the outer existing_headers list

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
                role=self.main_task_assistant.role,
            )

            # The subtopics should start research from the context gathered till now
            subtopic_assistant.context = list(set(self.global_context))

            if self.restrict_search:
                # If search type is restricted, then the existing context should be used for writing the report
                report_markdown = await subtopic_assistant.write_report(
                    existing_headers=existing_headers
                )
            else:
                # If search type is mixed, then further research needs to be conducted
                report_markdown = await subtopic_assistant.conduct_research(
                    max_docs=10, score_threshold=1, existing_headers=existing_headers
                )

            # Update context of the global context variable
            self.global_context = list(set(subtopic_assistant.context))
            # Update url list of the global list variable
            self.global_urls.update(subtopic_assistant.visited_urls)

            # Append the headers to the existing_headers list
            existing_headers.append(
                {
                    "subtopic task": current_subtopic_task,
                    "headers": extract_headers(report_markdown),
                }
            )

            if not report_markdown.strip():
                print(
                    f"⚠️ Failed to gather data from research on subtopic : {self.task}"
                )
                return "", []

            return report_markdown, subtopic_assistant.tables_extractor.tables

        # Generate the subtopic reports asynchronously in a sequential manner
        for subtopic in self.subtopics:
            emit_report_status(
                self.user_id,
                self.report_generation_id,
                f"🚦 Conducting research on subtopic : {subtopic['task']}...",
            )
            subtopic_report_markdown, subtopic_tables = await generate_subtopic_report(
                subtopic
            )
            reports_body += "\n\n\n" + subtopic_report_markdown
            tables.extend(subtopic_tables)

        return reports_body, tables

    async def _construct_detailed_report(self, report_body: str) -> tuple:
        # Get the introduction and the conclusion
        introduction, conclusion = await self.main_task_assistant.write_introduction_conclusion()

        # Construct the final detailed report
        detailed_report = (
            introduction + "\n\n"
            + table_of_contents(report_body + "\n\n" + conclusion) + "\n\n"
            + report_body + "\n\n"
            + conclusion
        )

        # Get the detailed report path and the table path
        detailed_report_path, table_path = await self.main_task_assistant.save_report(
            detailed_report
        )

        return detailed_report, detailed_report_path, table_path