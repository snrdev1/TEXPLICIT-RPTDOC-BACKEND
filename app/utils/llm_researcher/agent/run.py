import asyncio
import datetime
from typing import Union

from bson import ObjectId

from ..utils.llm import llm_process_subtopics
from .research_agent import ResearchAgent


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

    async def basic_report(self) -> tuple:
        assistant = ResearchAgent(
            user_id=self.user_id,
            query=self.task,
            source=self.source,
            format=self.format,
            report_type=self.report_type,
            websocket=self.websocket,
        )

        # Check EXISTING report
        path = (
            await assistant.check_existing_report(self.report_type)
            if self.check_existing_report
            else None
        )
        if path:
            await assistant.extract_tables()
            report_markdown = await assistant.get_report_markdown(self.report_type)
            report_markdown = report_markdown.strip()

            return report_markdown, path, assistant.tables

        print("🚦 Starting research")
        report_markdown = await assistant.conduct_research()

        report_markdown = report_markdown.strip()
        if len(report_markdown) == 0:
            return "", "", []

        path = await assistant.save_report(report_markdown)

        return report_markdown, path, assistant.tables

    async def detailed_report(self) -> tuple:
        main_task_assistant = ResearchAgent(
            user_id=self.user_id,
            query=self.task,
            source=self.source,
            format=self.format,
            report_type=self.report_type,
            websocket=self.websocket,
        )

        async def get_subtopic_report(subtopic: list):
            # Extract relevant information from subtopic dictionaries
            current_subtopic_task = subtopic.get("task")
            subtopic_source = subtopic.get("source")

            subtopic_assistant = ResearchAgent(
                user_id=self.user_id,
                query=current_subtopic_task,
                source=subtopic_source,
                format=format,
                report_type="subtopic_report",
                websocket=self.websocket,
                parent_query=self.task,
                subtopics=self.subtopics,
            )

            print("🚦 Starting subtopic research")
            report_markdown = await subtopic_assistant.conduct_research(
                max_docs=10, score_threshold=1
            )
            report_markdown = report_markdown.strip()

            if len(report_markdown) == 0:
                print(
                    f"⚠️ Failed to gather data from research on subtopic : {self.task}"
                )
                return "", "", []

            # Append all visited_urls from subtopic report generation to the visited_urls set of the main assistant
            main_task_assistant.visited_urls.update(subtopic_assistant.visited_urls)

            # Not incredibly necessary to save the subtopic report (as of now)
            # path = await subtopic_assistant.save_report(report_markdown)

            return report_markdown, "", subtopic_assistant.tables

        async def generate_subtopic_reports(subtopics):
            reports = []
            report_body = ""
            tables = []

            # Function to fetch subtopic reports asynchronously
            async def fetch_report(subtopic):
                (
                    subtopic_report_markdown,
                    subtopic_path,
                    subtopic_tables,
                ) = await get_subtopic_report(subtopic)
                return {
                    "topic": subtopic,
                    "markdown_report": subtopic_report_markdown,
                    "path": subtopic_path,
                    "tables": subtopic_tables,
                }

            # Create a list of tasks for fetching reports
            tasks = [fetch_report(subtopic) for subtopic in subtopics]

            # Gather the results when the tasks are completed
            results = await asyncio.gather(*tasks)

            for result in results:
                if len(result["markdown_report"]):
                    reports.append(result)
                    report_body = report_body + "\n\n\n" + result["markdown_report"]
                    tables.extend(result["tables"])

            return reports, report_body, tables

        async def generate_detailed_report(report_body):
            (
                introduction,
                conclusion,
            ) = await main_task_assistant.write_introduction_conclusion()
            detailed_report = introduction + "\n\n" + report_body + "\n\n" + conclusion
            detailed_report_path = await main_task_assistant.save_report(
                detailed_report
            )
            return detailed_report, detailed_report_path

        async def get_all_subtopics() -> list:
            # 1. Get outline report
            outline_executor = AgentExecutor(
                user_id=self.user_id,
                task=self.task,
                websearch=self.websearch,
                report_type="outline_report",
                source=self.source,
                format=self.format,
                report_generation_id=self.report_generation_id,
                websocket=self.websocket,
            )
            (
                outline_report_markdown,
                outline_report_path,
                _,
            ) = await outline_executor.run_agent()

            # 2. Extract base subtopics from outline report
            base_subtopics = main_task_assistant.extract_subtopics(
                outline_report_markdown, self.websearch, self.source
            )

            # 3. Append all subtopics:
            # a. main task
            # b. subtopics extracted from outline report
            # c. subtopics provided  by user
            all_subtopics = (
                [
                    {
                        "task": self.task,
                        "websearch": self.websearch,
                        "source": self.source,
                    }
                ]
                + base_subtopics
                + self.subtopics
            )
            print(f"💎 Found total of {len(all_subtopics)} subtopics")

            # 4. Perform processing on subtopics:
            processed_subtopics = await llm_process_subtopics(
                task=self.task, subtopics=all_subtopics
            )
            print(f"💎 Found {len(processed_subtopics)} processed subtopics")

            return processed_subtopics

        # Check EXISTING report
        detailed_report_path = (
            await main_task_assistant.check_existing_report(self.report_type)
            if self.check_existing_report
            else None
        )
        if detailed_report_path:
            await main_task_assistant.extract_tables()
            report_markdown = await main_task_assistant.get_report_markdown(
                self.report_type
            )
            detailed_report = report_markdown.strip()

            return detailed_report, detailed_report_path, main_task_assistant.tables

        # Get all the processed subtopics on which the detailed report is to be generated
        processed_subtopics = await get_all_subtopics()

        (
            subtopics_reports,
            subtopics_reports_body,
            subtopics_tables,
        ) = await generate_subtopic_reports(processed_subtopics)

        # If any tables at all are found then store them
        main_task_assistant.tables = subtopics_tables
        if len(main_task_assistant.tables):
            print("📝 Saving extracted tables")
            main_task_assistant.save_tables()

        if len(subtopics_reports_body.strip()) == 0:
            return "", "", []

        detailed_report, detailed_report_path = await generate_detailed_report(
            subtopics_reports_body
        )

        return detailed_report, detailed_report_path, main_task_assistant.tables

    async def complete_report(self) -> tuple:
        async def create_report(report_type: str) -> tuple:
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
            markdown, path, tables = await report_executor.run_agent()
            return markdown, path, tables, report_executor.visited_urls

        assistant = ResearchAgent(
            user_id=self.user_id,
            query=self.task,
            source=self.source,
            format=self.format,
            report_type=self.report_type,
            websocket=self.websocket,
        )

        # Check EXISTING report
        complete_report_path = (
            await assistant.check_existing_report(self.report_type)
            if self.check_existing_report
            else None
        )
        if complete_report_path:
            await assistant.extract_tables()
            report_markdown = await assistant.get_report_markdown(self.report_type)
            complete_report = report_markdown.strip()

            return complete_report, complete_report_path, assistant.tables

        (
            outline_report_markdown,
            outline_report_path,
            outline_report_tables,
            outline_report_urls,
        ) = await create_report("outline_report")
        (
            resource_report_markdown,
            resource_report_path,
            resource_report_tables,
            resource_report_urls,
        ) = await create_report("resource_report")
        (
            detailed_report_markdown,
            detailed_report_path,
            detailed_reports_tables,
            detailed_report_urls,
        ) = await create_report("detailed_report")

        report_markdown = (
            outline_report_markdown
            + "\n\n\n\n"
            + resource_report_markdown
            + "\n\n\n\n"
            + detailed_report_markdown
        )
        report_markdown = report_markdown.strip()

        assistant.tables = (
            outline_report_tables + resource_report_tables + detailed_reports_tables
        )

        if not report_markdown:
            return "", "", []

        # Merge all the sources from all assistants
        assistant.visited_urls.update(
            outline_report_urls, resource_report_urls, detailed_report_urls
        )

        path = await assistant.save_report(report_markdown)

        return report_markdown, path, assistant.tables

    async def run_agent(self) -> tuple:
        start_time = datetime.datetime.now()

        print({"type": "logs", "output": f"Start time: {str(start_time)}\n\n"})

        # In depth report generation
        if self.report_type == "detailed_report":
            report_markdown, path, _ = await self.detailed_report()

        # Complete report generation
        elif self.report_type == "complete_report":
            report_markdown, path, _ = await self.complete_report()

        else:
            # Basic report generation
            report_markdown, path, _ = await self.basic_report()

        end_time = datetime.datetime.now()

        print({"type": "path", "output": path})
        print({"type": "logs", "output": f"\nEnd time: {end_time}\n"})
        print(
            {"type": "logs", "output": f"\nTotal run time: {end_time - start_time}\n"}
        )

        return report_markdown, path
