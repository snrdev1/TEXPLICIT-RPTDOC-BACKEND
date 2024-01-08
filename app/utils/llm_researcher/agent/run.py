import asyncio
import datetime
from typing import Union

from bson import ObjectId

from ..utils.llm import llm_process_subtopics
from .research_agent import ResearchAgent


async def basic_report(
    user_id: Union[str, ObjectId],
    task: str,
    websearch: bool,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[str, None],
    websocket=None,
) -> [str, str]:
    assistant = ResearchAgent(
        user_id=user_id,
        query=task,
        source=source,
        format=format,
        report_type=report_type,
        websocket=websocket,
    )
    print("🚦 Starting research")
    report_markdown = await assistant.conduct_research()
        
    report_markdown = report_markdown.strip()
    if len(report_markdown) == 0:
        return "", "", []
    print("Report markdown : \n", report_markdown)

    path = await assistant.save_report(report_markdown)

    return report_markdown, path, assistant.tables


async def detailed_report(
    user_id: Union[str, ObjectId],
    task: str,
    websearch: bool,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[str, None],
    subtopics: list = [],
    websocket=None,
) -> [str, str]:
    main_task_assistant = ResearchAgent(
        user_id=user_id,
        query=task,
        source=source,
        format=format,
        report_type=report_type,
        websocket=websocket,
    )

    async def get_subtopic_report(subtopic: list):
        # Extract relevant information from subtopic dictionaries
        current_subtopic_task = subtopic.get("task")
        subtopic_source = subtopic.get("source")

        subtopic_assistant = ResearchAgent(
            user_id=user_id,
            query=current_subtopic_task,
            source=subtopic_source,
            format=format,
            report_type="subtopic_report",
            websocket=websocket,
            parent_query=task,
            subtopics=subtopics
        )

        print("🚦 Starting subtopic research")
        report_markdown = await subtopic_assistant.conduct_research(
            max_docs=10, score_threshold=1
        )
        report_markdown = report_markdown.strip()

        if len(report_markdown) == 0:
            print(f"⚠️ Failed to gather data from research on subtopic : {task}")
            return "", "", []
        
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
        detailed_report_path = await main_task_assistant.save_report(detailed_report)
        return detailed_report, detailed_report_path

    async def get_all_subtopics() -> list:
        # 1. Get outline report
        outline_report_markdown, outline_report_path, _ = await basic_report(
            user_id=user_id,
            task=task,
            websearch=websearch,
            report_type="outline_report",
            source=source,
            format=format,
            report_generation_id=report_generation_id,
            websocket=websocket,
        )

        # 2. Extract base subtopics from outline report
        base_subtopics = main_task_assistant.extract_subtopics(
            outline_report_markdown, websearch, source
        )

        # 3. Append all subtopics:
        # a. main task
        # b. subtopics extracted from outline report
        # c. subtopics provided  by user
        all_subtopics = (
            [{"task": task, "websearch": websearch, "source": source}]
            + base_subtopics
            + subtopics
        )
        print(f"💎 Found total of {len(all_subtopics)} subtopics")

        # 4. Perform processing on subtopics:
        processed_subtopics = await llm_process_subtopics(
            task=task, subtopics=all_subtopics
        )
        print(f"💎 Found {len(processed_subtopics)} processed subtopics")

        return processed_subtopics

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


async def complete_report(
    user_id: Union[str, ObjectId],
    task: str,
    websearch: bool,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[str, None],
    subtopics: list = [],
    websocket=None,
) -> [str, str]:
    assistant = ResearchAgent(
        user_id=user_id,
        query=task,
        source=source,
        format=format,
        report_type=report_type,
        websocket=websocket,
    )
    (
        outline_report_markdown,
        outline_report_path,
        outline_report_tables,
    ) = await basic_report(
        user_id=user_id,
        task=task,
        websearch=websearch,
        report_type="outline_report",
        source=source,
        format=format,
        websocket=websocket,
        report_generation_id=report_generation_id,
    )

    (
        resource_report_markdown,
        resource_report_path,
        resource_report_tables,
    ) = await basic_report(
        user_id=user_id,
        task=task,
        websearch=websearch,
        report_type="resource_report",
        source=source,
        format=format,
        websocket=websocket,
        report_generation_id=report_generation_id,
    )

    (
        detailed_report_markdown,
        detailed_report_path,
        detailed_reports_tables,
    ) = await detailed_report(
        user_id=user_id,
        task=task,
        websearch=websearch,
        report_type=report_type,
        source=source,
        format=format,
        websocket=websocket,
        report_generation_id=report_generation_id,
        subtopics=subtopics,
    )

    report_markdown = (
        outline_report_markdown
        + "\n\n\n\n"
        + resource_report_markdown
        + "\n\n\n\n"
        + detailed_report_markdown
    )
    report_markdown = report_markdown.strip()

    print("Report markdown : \n", report_markdown)
    assistant.tables = (
        outline_report_tables + resource_report_tables + detailed_reports_tables
    )

    if len(report_markdown.strip()) == 0:
        return "", "", []

    path = await assistant.save_report(report_markdown)

    return report_markdown, path, assistant.tables


async def run_agent(
    user_id: Union[str, ObjectId],
    task: str,
    websearch: bool,
    report_generation_id: Union[str, None],
    report_type: str = "research_report",
    source: str = "external",
    format: str = "pdf",
    subtopics: list = [],
    websocket=None,
) -> [str, str]:
    start_time = datetime.datetime.now()

    print({"type": "logs", "output": f"Start time: {str(start_time)}\n\n"})

    # In depth report generation
    if report_type == "detailed_report":
        report_markdown, path, _ = await detailed_report(
            user_id=user_id,
            task=task,
            websearch=websearch,
            report_type=report_type,
            source=source,
            format=format,
            websocket=websocket,
            report_generation_id=report_generation_id,
            subtopics=subtopics,
        )

    # Complete report generation
    elif report_type == "complete_report":
        report_markdown, path, _ = await complete_report(
            user_id=user_id,
            task=task,
            websearch=websearch,
            report_type=report_type,
            source=source,
            format=format,
            websocket=websocket,
            report_generation_id=report_generation_id,
            subtopics=subtopics,
        )

    else:
        # Basic report generation
        report_markdown, path, _ = await basic_report(
            user_id=user_id,
            task=task,
            websearch=websearch,
            report_type=report_type,
            source=source,
            format=format,
            websocket=websocket,
            report_generation_id=report_generation_id,
        )

    end_time = datetime.datetime.now()

    print({"type": "path", "output": path})
    print({"type": "logs", "output": f"\nEnd time: {end_time}\n"})
    print({"type": "logs", "output": f"\nTotal run time: {end_time - start_time}\n"})

    return report_markdown, path
