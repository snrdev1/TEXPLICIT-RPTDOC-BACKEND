import asyncio
import datetime
from typing import Union

from bson import ObjectId

from ..config import check_openai_api_key
from .llm_utils import llm_process_subtopics
from .research_agent import ResearchAgent


async def basic_report(
    user_id: Union[str, ObjectId],
    task: str,
    websearch: bool,
    agent: str,
    agent_role_prompt: str,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[str, None],
    websocket=None,
) -> [str, str]:
    assistant = ResearchAgent(
        user_id=user_id,
        question=task,
        agent=agent,
        agent_role_prompt=agent_role_prompt,
        source=source,
        format=format,
        websocket=websocket,
    )
    path = await assistant.check_existing_report(report_type)
    if path:
        report_markdown = await assistant.get_report_markdown(report_type)

    else:
        # Research on given task will only take place if:
        #     1. websearch=True and source is web('external')
        #     2. source is 'my_documents'
        if (websearch and source == "external") or (source == "my_documents"):
            print("🚦 Starting research")
            await assistant.conduct_research()

        report_markdown = await assistant.write_report(report_type, source)

        print("Report markdown : \n", report_markdown)

        path = await assistant.save_report(report_type, report_markdown)

    return report_markdown, path


async def detailed_report(
    user_id: Union[str, ObjectId],
    task: str,
    websearch: bool,
    agent: str,
    agent_role_prompt: str,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[str, None],
    subtopics: list = [],
    websocket=None,
) -> [str, str]:
    main_task_assistant = ResearchAgent(
        user_id=user_id,
        question=task,
        agent=agent,
        agent_role_prompt=agent_role_prompt,
        source=source,
        format=format,
        websocket=websocket,
    )

    async def get_subtopic_report(
        subtopic: list, subtopic_report_type="subtopic_report"
    ):
        # Extract relevant information from subtopic dictionaries
        subtopic_task = subtopic.get("task")
        subtopic_web_search = subtopic.get("websearch", False)
        subtopic_source = subtopic.get("source")
        subtopic_tasks = [subtopic.get("task") for subtopic in subtopics]

        assistant = ResearchAgent(
            user_id=user_id,
            question=subtopic_task,
            agent=agent,
            agent_role_prompt=agent_role_prompt,
            source=subtopic_source,
            format=format,
            websocket=websocket,
        )

        path = await assistant.check_existing_report(subtopic_report_type)
        if path:
            report_markdown = await assistant.get_report_markdown(subtopic_report_type)
        else:
            # Research on given task will only take place if:
            #     1. websearch=True and source is web('external')
            #     2. source is 'my_documents'
            if (subtopic_web_search and subtopic_source == "external") or (
                subtopic_source == "my_documents"
            ):
                print("🚦 Starting subtopic research")
                await assistant.conduct_research(
                    num_queries=1, max_docs=10, score_threshold=1
                )
            report_markdown = await assistant.write_subtopic_report(
                subtopic_report_type, task, subtopic_tasks, subtopic_task, websocket
            )
            path = await assistant.save_report(subtopic_report_type, report_markdown)
        return report_markdown, path

    async def generate_subtopic_reports(subtopics):
        reports = []
        report_body = ""

        # Function to fetch subtopic reports asynchronously
        async def fetch_report(subtopic):
            subtopic_report_markdown, subtopic_path = await get_subtopic_report(
                subtopic
            )
            return {
                "topic": subtopic,
                "markdown_report": subtopic_report_markdown,
                "path": subtopic_path,
            }

        # Create a list of tasks for fetching reports
        tasks = [fetch_report(subtopic) for subtopic in subtopics]

        # Gather the results when the tasks are completed
        results = await asyncio.gather(*tasks)

        for result in results:
            reports.append(result)
            report_body = report_body + "\n\n\n" + result["markdown_report"]

        return reports, report_body

    async def generate_detailed_report(report_body):
        (
            introduction,
            conclusion,
        ) = await main_task_assistant.write_introduction_conclusion()
        detailed_report = introduction + "\n\n" + report_body + "\n\n" + conclusion
        detailed_report_path = await main_task_assistant.save_report(
            report_type, detailed_report
        )
        return detailed_report, detailed_report_path

    async def get_all_subtopics() -> list:
        # 1. Get outline report
        outline_report_markdown, outline_report_path = await basic_report(
            user_id=user_id,
            task=task,
            websearch=websearch,
            agent=agent,
            agent_role_prompt=agent_role_prompt,
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
        print(f"💎 All Subtopics : {all_subtopics}")

        # 4. Perform processing on subtopics:
        processed_subtopics = await llm_process_subtopics(
            task=task, subtopics=all_subtopics
        )
        print(f"💎 Processed Subtopics : {processed_subtopics}")

        return processed_subtopics

    # Check if detailed report already exists. If it exists then return it
    detailed_report_path = await main_task_assistant.check_existing_report(report_type)
    if detailed_report_path:
        detailed_report = await main_task_assistant.get_report_markdown(report_type)
        return detailed_report, detailed_report_path

    # Get all the processed subtopics on which the detailed report is to be generated
    processed_subtopics = await get_all_subtopics()

    reports, report_body = await generate_subtopic_reports(processed_subtopics)
    detailed_report, detailed_report_path = await generate_detailed_report(report_body)

    return detailed_report, detailed_report_path


async def run_agent(
    user_id: Union[str, ObjectId],
    task: str,
    websearch: bool,
    agent: str,
    agent_role_prompt: str,
    report_generation_id: Union[str, None],
    report_type: str = "research_report",
    source: str = "external",
    format: str = "pdf",
    subtopics: list = [],
    websocket=None,
) -> [str, str]:
    check_openai_api_key()

    start_time = datetime.datetime.now()

    print({"type": "logs", "output": f"Start time: {str(start_time)}\n\n"})

    # Basic report generation
    if report_type != "detailed_report":
        report_markdown, path = await basic_report(
            user_id=user_id,
            task=task,
            websearch=websearch,
            agent=agent,
            agent_role_prompt=agent_role_prompt,
            report_type=report_type,
            source=source,
            format=format,
            websocket=websocket,
            report_generation_id=report_generation_id,
        )

    # In depth report generation
    if report_type == "detailed_report":
        report_markdown, path = await detailed_report(
            user_id=user_id,
            task=task,
            websearch=websearch,
            agent=agent,
            agent_role_prompt=agent_role_prompt,
            report_type=report_type,
            source=source,
            format=format,
            websocket=websocket,
            report_generation_id=report_generation_id,
            subtopics=subtopics,
        )

    print({"type": "path", "output": path})

    end_time = datetime.datetime.now()
    print({"type": "logs", "output": f"\nEnd time: {end_time}\n"})
    print({"type": "logs", "output": f"\nTotal run time: {end_time - start_time}\n"})

    return report_markdown, path
