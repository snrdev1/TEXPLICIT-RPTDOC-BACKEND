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
        self.restrict_search = restrict_search
        self.main_task_assistant = self._create_task_assistant()
        self.existing_headers = []

    async def generate_report(self) -> tuple:
        detailed_report_path = await self._check_existing_report()
        if detailed_report_path:
            return await self._handle_existing_report(detailed_report_path)
           
        # Conduct initial research on provided urls
        await self._handle_provided_urls()
            
        subtopics = await self._get_all_subtopics()

        (
            _,
            subtopics_reports_body,
            _,
        ) = await self._generate_subtopic_reports(subtopics)

        if not subtopics_reports_body.strip():
            return "", "", [], set()

        detailed_report, detailed_report_path, table_path = await self._construct_detailed_report(
            subtopics_reports_body
        )

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
            report_type=self.report_type,
            websocket=self.websocket,
            report_generation_id=self.report_generation_id,
            urls=self.urls,
            subtopics=self.subtopics,
            restrict_search=self.restrict_search
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

    async def _get_all_subtopics(self) -> list:
        await self.main_task_assistant.conduct_research(write_report=False)
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
                subtopic_tables,
            ) = await self._get_subtopic_report(subtopic)
            return {
                "topic": subtopic,
                "markdown_report": subtopic_report_markdown,
                "path": subtopic_path,
                "tables": subtopic_tables,
            }

        tasks = [fetch_report(subtopic) for subtopic in subtopics]
        results = await asyncio.gather(*tasks)

        for result in results:
            if len(result["markdown_report"]):
                reports.append(result)
                report_body += "\n\n\n" + result["markdown_report"]
                tables.extend(result["tables"])

        return reports, report_body, tables

    async def _get_subtopic_report(self, subtopic: list) -> tuple:
        current_subtopic_task = subtopic.get("task")
        subtopic_source = subtopic.get("source")

        subtopic_assistant = ResearchAgent(
            user_id=self.user_id,
            query=current_subtopic_task,
            source=subtopic_source,
            format=self.format,
            report_type="subtopic_report",
            websocket=self.websocket,
            parent_query=self.task,
            subtopics=self.subtopics,
            report_generation_id=self.report_generation_id,
            restrict_search=self.restrict_search
        )
        
        # The subtopics should start research from the context gathered by the main assistant
        subtopic_assistant.context = self.main_task_assistant.context
        
        if self.restrict_search:  
            # If search type is restricted then the existing context should be used for writing report
            report_markdown = await subtopic_assistant.write_report(
                existing_headers=self.existing_headers
            )  
        else:
            # If search type is mixed then further research needs to be conducted
            report_markdown = await subtopic_assistant.conduct_research(
                max_docs=10, 
                score_threshold=1, 
                existing_headers=self.existing_headers
            )

        report_markdown = report_markdown.strip()
        # After a subtopic report has been generated then append the headers of the report to existing headers
        self.existing_headers.append({
            "subtopic task": current_subtopic_task,
            "headers": extract_headers(report_markdown)
        })

        if len(report_markdown) == 0:
            print(
                f"⚠️ Failed to gather data from research on subtopic : {self.task}")
            return "", "", []

        self.main_task_assistant.visited_urls.update(
            subtopic_assistant.visited_urls)

        return report_markdown, "", subtopic_assistant.tables_extractor.tables

    async def _construct_detailed_report(self, report_body: str) -> tuple:
        introduction, conclusion = (
            await self.main_task_assistant.write_introduction_conclusion()
        )
        detailed_report = report_body + "\n\n" + conclusion
        detailed_report = introduction + "\n\n" + \
            table_of_contents(detailed_report) + detailed_report
        detailed_report_path, table_path = await self.main_task_assistant.save_report(
            detailed_report
        )
        return detailed_report, detailed_report_path, table_path

    async def _handle_provided_urls(self):
        # If urls were provided by the user then conduct initial research on those urls
        
        if self.urls:
            self.main_task_assistant.conduct_research()