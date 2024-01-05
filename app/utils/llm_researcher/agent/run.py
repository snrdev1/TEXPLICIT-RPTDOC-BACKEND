import asyncio
import datetime
from typing import Union

from bson import ObjectId

from ...response import Response
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
    """
    The `basic_report` function takes in various parameters, conducts research based on the given task
    and source, generates a report in markdown format, and returns the report markdown, path to the
    saved report, and any extracted tables.

    :param user_id: The user_id parameter is the unique identifier of the user for whom the report is
    being generated. It can be either a string or an ObjectId
    :type user_id: Union[str, ObjectId]
    :param task: The `task` parameter is a string that represents the research question or task that
    needs to be performed. It is the main input for the research process
    :type task: str
    :param websearch: A boolean indicating whether web search is enabled or not
    :type websearch: bool
    :param agent: The `agent` parameter is a string that represents the name or type of the research
    agent being used. It could be the name of a specific research agent or a general type of agent
    (e.g., "Google", "Wikipedia", "CustomAgent")
    :type agent: str
    :param agent_role_prompt: The `agent_role_prompt` parameter is a string that represents the prompt
    or instructions given to the research agent about their role or task. It helps the research agent
    understand what they need to do and what is expected of them in order to generate the report
    :type agent_role_prompt: str
    :param report_type: The `report_type` parameter is a string that specifies the type of report to
    generate. It could be something like "summary", "detailed", "analysis", etc
    :type report_type: str
    :param source: The `source` parameter is a string that specifies the source of the research data. It
    can have two possible values:
    :type source: str
    :param format: The `format` parameter specifies the format in which the report should be generated.
    It can be either "markdown" or "pdf"
    :type format: str
    :param report_generation_id: The `report_generation_id` parameter is used to identify a specific
    report generation. It can be either a string or `None`
    :type report_generation_id: Union[str, None]
    :param websocket: The `websocket` parameter is an optional argument that represents a WebSocket
    connection. It is used to establish a communication channel between the client and the server. If
    provided, it allows for real-time updates and interaction during the research process
    :return: The function `basic_report` returns three values: `report_markdown`, `path`, and
    `assistant.tables`.
    """

    assistant = ResearchAgent(
        user_id=user_id,
        question=task,
        agent=agent,
        agent_role_prompt=agent_role_prompt,
        source=source,
        format=format,
        websocket=websocket,
    )
    # Research on given task will only take place if:
    #     1. websearch=True and source is web('external')
    #     2. source is 'my_documents'
    if (websearch and source == "external") or (source == "my_documents"):
        print("🚦 Starting research")
        await assistant.conduct_research()

    if len(assistant.research_summary.strip()) == 0:
        return "", "", []

    report_markdown = await assistant.write_report(report_type, source)
    report_markdown = report_markdown.strip()

    print("Report markdown : \n", report_markdown)

    path = await assistant.save_report(report_type, report_markdown)

    return report_markdown, path, assistant.tables


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
    """
    The `detailed_report` function generates a detailed report by conducting research on a main task and
    its subtopics, and then combining the results into a single report.

    :param user_id: The user_id parameter is the unique identifier of the user for whom the detailed
    report is being generated. It can be either a string or an ObjectId
    :type user_id: Union[str, ObjectId]
    :param task: The `task` parameter is a string that represents the main task or question for which
    the detailed report is being generated
    :type task: str
    :param websearch: A boolean value indicating whether web search should be performed for the main
    task and subtopics
    :type websearch: bool
    :param agent: The `agent` parameter is a string that represents the name or identifier of the
    research agent that will be used for conducting the research and generating the report
    :type agent: str
    :param agent_role_prompt: The parameter `agent_role_prompt` is a string that represents the role or
    position of the agent. It is used to provide context or instructions to the agent when generating
    the report
    :type agent_role_prompt: str
    :param report_type: The `report_type` parameter is a string that specifies the type of report to be
    generated. It can have values like "detailed_report", "outline_report", "subtopic_report", etc
    :type report_type: str
    :param source: The `source` parameter is a string that specifies the source of the information for
    the research. It can have the following values:
    :type source: str
    :param format: The `format` parameter specifies the format in which the report will be generated. It
    can be either "markdown" or "pdf"
    :type format: str
    :param report_generation_id: The `report_generation_id` parameter is used to identify a specific
    report generation process. It can be a string or None
    :type report_generation_id: Union[str, None]
    :param subtopics: The `subtopics` parameter is a list of dictionaries. Each dictionary represents a
    subtopic and contains the following keys:
    :type subtopics: list
    :param websocket: The `websocket` parameter is used to establish a WebSocket connection for
    real-time communication between the client and the server. It allows for bidirectional
    communication, where the server can send updates or notifications to the client, and the client can
    send requests or messages to the server. In the context of the `
    :return: The function `detailed_report` returns a tuple containing three elements:
    1. A string representing the detailed report.
    2. A string representing the path where the detailed report is saved.
    3. A list of tables extracted from the report.
    """

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

        if len(assistant.research_summary.strip()) == 0:
            print(f"⚠️ Failed to gather data from research on subtopic : {task}")
            return "", "", []

        report_markdown = await assistant.write_subtopic_report(
                subtopic_report_type, task, subtopic_tasks, subtopic_task, websocket
        )
        report_markdown = report_markdown.strip()
        path = await assistant.save_report(subtopic_report_type, report_markdown)
        
        return report_markdown, path, assistant.tables

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
            report_type, detailed_report
        )
        return detailed_report, detailed_report_path

    async def get_all_subtopics() -> list:
        # 1. Get outline report
        outline_report_markdown, outline_report_path, _ = await basic_report(
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
    agent: str,
    agent_role_prompt: str,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[str, None],
    subtopics: list = [],
    websocket=None,
) -> [str, str]:
    """
    The `complete_report` function generates a complete report by combining an outline report, a
    resource report, and a detailed report, and returns the report markdown, file path, and tables.

    :param user_id: The `user_id` parameter is the unique identifier of the user for whom the report is
    being generated. It can be either a string or an `ObjectId` object
    :type user_id: Union[str, ObjectId]
    :param task: The `task` parameter is a string that represents the task or question for which the
    report is being generated
    :type task: str
    :param websearch: The `websearch` parameter is a boolean value that indicates whether or not to
    perform web searches during the report generation process. If `websearch` is set to `True`, the
    assistant will perform web searches to gather information for the report. If `websearch` is set to
    `False`,
    :type websearch: bool
    :param agent: The `agent` parameter is a string that represents the name or type of the research
    agent being used for generating the report
    :type agent: str
    :param agent_role_prompt: The `agent_role_prompt` parameter is a string that represents the prompt
    or instructions given to the research agent about their role or task in generating the report. It
    helps to provide context and guidance to the agent on how to approach the task
    :type agent_role_prompt: str
    :param report_type: The `report_type` parameter is a string that specifies the type of report to
    generate. It can have one of the following values:
    :type report_type: str
    :param source: The `source` parameter is a string that represents the source of the information for
    the report. It could be a website, a database, or any other source from which the assistant gathers
    information to generate the report
    :type source: str
    :param format: The `format` parameter specifies the format in which the report should be generated.
    It can be a string value representing the desired format, such as "markdown", "pdf", "html", etc
    :type format: str
    :param report_generation_id: The `report_generation_id` parameter is used to identify a specific
    report generation process. It can be either a string or `None`. If a `report_generation_id` is
    provided, it is used to track the progress and status of the report generation. If it is `None`, a
    new report
    :type report_generation_id: Union[str, None]
    :param subtopics: The `subtopics` parameter is a list that contains the subtopics to be included in
    the detailed report. It is an optional parameter and its default value is an empty list
    :type subtopics: list
    :param websocket: The `websocket` parameter is an optional argument that represents a WebSocket
    connection. It is used to establish a communication channel between the client and the server,
    allowing for real-time bidirectional communication. In this function, it is passed to the
    `ResearchAgent` class to enable real-time updates and progress tracking
    :return: The function `complete_report` returns three values: `report_markdown`, `path`, and
    `assistant.tables`.
    """

    assistant = ResearchAgent(
        user_id=user_id,
        question=task,
        agent=agent,
        agent_role_prompt=agent_role_prompt,
        source=source,
        format=format,
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
        agent=agent,
        agent_role_prompt=agent_role_prompt,
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
        agent=agent,
        agent_role_prompt=agent_role_prompt,
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
        agent=agent,
        agent_role_prompt=agent_role_prompt,
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

    path = await assistant.save_report(report_type, report_markdown)

    return report_markdown, path, assistant.tables


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
    """
    The `run_agent` function generates different types of reports based on the given parameters and
    returns the report markdown and file path.

    :param user_id: The `user_id` parameter is the unique identifier of the user for whom the report is
    being generated. It can be either a string or an `ObjectId` object
    :type user_id: Union[str, ObjectId]
    :param task: The `task` parameter is a string that represents the task or question for which the
    report is being generated. It specifies the main topic or subject that the report should focus on
    :type task: str
    :param websearch: A boolean value indicating whether web search should be performed during report
    generation
    :type websearch: bool
    :param agent: The `agent` parameter is a string that represents the name or ID of the AI agent that
    will be used for generating the report. This agent is responsible for providing the responses and
    information needed for the report generation process
    :type agent: str
    :param agent_role_prompt: The `agent_role_prompt` parameter is a string that represents the prompt
    to be used for the agent's role in the conversation. It provides context to the agent about its role
    and helps guide its responses
    :type agent_role_prompt: str
    :param report_generation_id: The `report_generation_id` parameter is used to specify the ID of a
    previously generated report. This is useful when you want to generate a new report based on an
    existing report or when you want to update an existing report with new information. By providing the
    `report_generation_id`, the function will use
    :type report_generation_id: Union[str, None]
    :param report_type: The `report_type` parameter is used to specify the type of report to be
    generated. It has three possible values:, defaults to research_report
    :type report_type: str (optional)
    :param source: The `source` parameter is used to specify the source of the information for the
    report. It can be set to either "external" or "internal", defaults to external
    :type source: str (optional)
    :param format: The `format` parameter specifies the format in which the generated report should be
    saved. It can have the following values:, defaults to pdf
    :type format: str (optional)
    :param subtopics: The `subtopics` parameter is a list that contains the subtopics related to the
    main task. These subtopics can be used to provide more specific information or context for the
    report generation process
    :type subtopics: list
    :param websocket: The `websocket` parameter is used to establish a WebSocket connection for
    real-time communication between the server and the client. It allows for the transmission of data
    between the server and the client without the need for continuous HTTP requests. In the given
    function, the `websocket` parameter is used to pass the WebSocket
    :return: The function `run_agent` returns two values: `report_markdown` and `path`.
    """

    check_openai_api_key()

    start_time = datetime.datetime.now()

    print({"type": "logs", "output": f"Start time: {str(start_time)}\n\n"})

    # In depth report generation
    if report_type == "detailed_report":
        report_markdown, path, _ = await detailed_report(
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

    # Complete report generation
    elif report_type == "complete_report":
        report_markdown, path, _ = await complete_report(
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

    else:
        # Basic report generation
        report_markdown, path, _ = await basic_report(
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

    print({"type": "path", "output": path})

    end_time = datetime.datetime.now()
    print({"type": "logs", "output": f"\nEnd time: {end_time}\n"})
    print({"type": "logs", "output": f"\nTotal run time: {end_time - start_time}\n"})

    return report_markdown, path
