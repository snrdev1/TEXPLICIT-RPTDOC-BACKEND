from datetime import datetime


def generate_agent_role_prompt(agent) -> str:
    """Generates the agent role prompt.
    Args: agent (str): The type of the agent.
    Returns: str: The agent role prompt.
    """
    prompts = {
        "Finance Agent": "You are a seasoned finance analyst AI assistant. Your primary goal is to compose comprehensive, astute, impartial, and methodically arranged financial reports based on provided data and trends.",
        "Travel Agent": "You are a world-travelled AI tour guide assistant. Your main purpose is to draft engaging, insightful, unbiased, and well-structured travel reports on given locations, including history, attractions, and cultural insights.",
        "Academic Research Agent": "You are an AI academic research assistant. Your primary responsibility is to create thorough, academically rigorous, unbiased, and systematically organized reports on a given research topic, following the standards of scholarly work.",
        "Business Analyst": "You are an experienced AI business analyst assistant. Your main objective is to produce comprehensive, insightful, impartial, and systematically structured business reports based on provided business data, market trends, and strategic analysis.",
        "Computer Security Analyst Agent": "You are an AI specializing in computer security analysis. Your principal duty is to generate comprehensive, meticulously detailed, impartial, and systematically structured reports on computer security topics. This includes Exploits, Techniques, Threat Actors, and Advanced Persistent Threat (APT) Groups. All produced reports should adhere to the highest standards of scholarly work and provide in-depth insights into the complexities of computer security.",
        "Default Agent": "You are an AI critical thinker research assistant. Your sole purpose is to write well written, critically acclaimed, objective and structured reports on given text.",
    }

    return prompts.get(agent, "No such agent")


def generate_search_queries_prompt(question: str, num_queries: int = 3) -> str:
    """
    The function `generate_search_queries_prompt` generates a prompt asking the user to write a
    specified number of Google search queries to form an objective opinion on a given question.

    Args:
      question: The question that you want to generate search queries for. It should be a string.
      num_queries: The `num_queries` parameter is an optional parameter that specifies the number of
    search queries to generate. By default, it is set to 3. Defaults to 3

    Returns:
      To generate search queries that form an objective opinion about the question "What is being
    returned?", you can use the following code:
    """

    return (
        f'Write {num_queries} google search queries to search online that form an objective opinion from the following: "{question}"'
        f'Use the current date if needed: {datetime.now().strftime("%B %d, %Y")}.\n'
        f'You must respond with a list of strings in the following format: ["query 1", "query 2", "query 3"].'
    )


def generate_report_prompt(question: str, research_summary: str = "") -> str:
    """
    The function `generate_report_prompt` generates a prompt for writing a detailed report on a given
    question or topic, with optional research summary.

    Args:
      question (str): The question or topic that the report should focus on. This is a required
    parameter and should be a string.
      research_summary (str): The research summary is a brief summary of the research that has already
    been conducted on the given question or topic. It provides a starting point for the report and helps
    the writer understand the existing knowledge and findings related to the question.

    Returns:
      The function `generate_report_prompt` returns a string prompt that instructs the user to generate
    a detailed report on a given question or topic.
    """
    prompt = f"""Answer the following
        question or topic: "{question}" in a detailed report --
        The report should focus on the answer to the question, should be well structured, informative,
        in depth, with facts and numbers if available, a minimum of 1,200 words and with markdown syntax and apa format.
        You MUST determine your own concrete and valid opinion based on the given information. Do NOT deter to general and meaningless conclusions.
        Write all used source urls at the end of the report in apa format.
        Assume that the current date is {datetime.now().strftime('%B %d, %Y')}
    """

    if research_summary:
        prompt = f'"""{research_summary}""" Using the above information,' + prompt

    return prompt


def generate_resource_report_prompt(question: str, research_summary: str = "") -> str:
    """
    The function `generate_resource_report_prompt` generates a prompt for creating a bibliography
    recommendation report based on a research question or topic.

    Args:
      question (str): The research question or topic for which you want to generate a bibliography
    recommendation report.
      research_summary (str): The `research_summary` parameter is an optional string that represents a
    summary of the research that has already been conducted. It can be used to provide context or
    background information for generating the resource report. If no research summary is provided, the
    prompt will not include this information.

    Returns:
      The function `generate_resource_report_prompt` returns a string that represents a prompt for
    generating a bibliography recommendation report.
    """
    prompt = f"""Generate a bibliography recommendation report for the following
        question or topic: "{question}". The report should provide a detailed analysis of each recommended resource,
        explaining how each source can contribute to finding answers to the research question.
        Focus on the relevance, reliability, and significance of each source.
        Ensure that the report is well-structured, informative, in-depth, and follows Markdown syntax.
        Include relevant facts, figures, and numbers whenever available.
        The report should have a minimum length of 1,200 words.
    """

    if research_summary:
        prompt = f'"""{research_summary}""" Based on the above information,' + prompt

    return prompt


def generate_outline_report_prompt(question: str, research_summary: str = "") -> str:
    """
    The function `generate_outline_report_prompt` generates a prompt for creating an outline for a
    research report in Markdown syntax.

    Args:
      question (str): The question or topic for which you want to generate an outline for a research
    report in Markdown syntax.
      research_summary (str): The `research_summary` parameter is an optional string that represents a
    summary or background information related to the research question or topic. It can be used to
    provide additional context for generating the outline.

    Returns:
      a string that serves as a prompt for generating an outline for a research report.
    """
    prompt = f"""Generate an outline for a research report in Markdown syntax
            for the following question or topic: "{question}". The outline should provide a well-structured framework
            for the research report, including the main sections, subsections, and key points to be covered.
            The research report should be detailed, informative, in-depth, and a minimum of 1,200 words.
            Use appropriate Markdown syntax to format the outline and ensure readability."""

    if research_summary:
        prompt = f'"""{research_summary}""" Using the above information,' + prompt

    return prompt


# DOCUMENTS REPORT GENERATION PROMPT
def generate_document_report_prompt(question, research_summary):
    """Generates the report prompt for the given question and research summary.
    Args: question (str): The question to generate the report prompt for
            research_summary (str): The research summary to generate the report prompt for
    Returns: str: The report prompt for the given question and research summary
    """

    return (
        f'"""{research_summary}""" Using the above information, answer the following'
        f' question or topic: "{question}" in a detailed report --'
        " The report should focus on the answer to the question, should be well structured, informative,"
        " in depth, with facts and numbers if available, a minimum of 1,200 words and with markdown syntax and apa format.\n "
        "You MUST determine your own concrete and valid opinion based on the given information. Do NOT deter to general and meaningless conclusions.\n"
        f"Write all used source document names (along with their extensions) at the end of the report to form a references section in apa format.\n "
        f"Assume that the current date is {datetime.now().strftime('%B %d, %Y')}"
    )


def generate_document_resource_report_prompt(question, research_summary):
    """Generates the resource report prompt for the given question and research summary.

    Args:
        question (str): The question to generate the resource report prompt for.
        research_summary (str): The research summary to generate the resource report prompt for.

    Returns:
        str: The resource report prompt for the given question and research summary.
    """
    return (
        f'"""{research_summary}""" Based on the above information, generate a bibliography recommendation report for the following'
        f' question or topic: "{question}". The report should provide a detailed analysis of each recommended resource,'
        " explaining how each source can contribute to finding answers to the research question."
        " Focus on the relevance, reliability, and significance of each source."
        " Ensure that the report is well-structured, informative, in-depth, and follows Markdown syntax."
        " Include relevant facts, figures, and numbers whenever available."
        " The report should have a minimum length of 1,200 words."
    )


def generate_document_outline_report_prompt(
    question: str, research_summary: str = ""
) -> str:
    """Generates the outline report prompt for the given question and research summary.
    Args: question (str): The question to generate the outline report prompt for
            research_summary (str): The research summary to generate the outline report prompt for
    Returns: str: The outline report prompt for the given question and research summary
    """

    if research_summary:
        prompt = (
            f'"""{research_summary}""" Using the above information, generate an outline for a research report in Markdown syntax'
            f' for the following question or topic: "{question}". The outline should provide a well-structured framework'
            " for the research report, including the main sections, subsections, and key points to be covered."
            " The research report should be detailed, informative, in-depth, and a minimum of 1,200 words."
            " Use appropriate Markdown syntax to format the outline and ensure readability."
        )
    else:
        prompt = f"""Generate an outline for a research report in Markdown syntax
            for the following question or topic: "{question}". The outline should provide a well-structured framework
            for the research report, including the main sections, subsections, and key points to be covered.
            The research report should be detailed, informative, in-depth, and a minimum of 1,200 words.
            Use appropriate Markdown syntax to format the outline and ensure readability."""

    return prompt


# Other Prompts


def generate_concepts_prompt(question, research_summary) -> str:
    """Generates the concepts prompt for the given question.
    Args: question (str): The question to generate the concepts prompt for
            research_summary (str): The research summary to generate the concepts prompt for
    Returns: str: The concepts prompt for the given question
    """

    return (
        f'"""{research_summary}""" Using the above information, generate a list of 5 main concepts to learn for a research report'
        f' on the following question or topic: "{question}". The outline should provide a well-structured framework'
        'You must respond with a list of strings in the following format: ["concepts 1", "concepts 2", "concepts 3", "concepts 4, concepts 5"]'
    )


def generate_lesson_prompt(concept) -> str:
    """
    Generates the lesson prompt for the given question.
    Args:
        concept (str): The concept to generate the lesson prompt for.
    Returns:
        str: The lesson prompt for the given concept.
    """

    prompt = (
        f"generate a comprehensive lesson about {concept} in Markdown syntax. This should include the definition"
        f"of {concept}, its historical background and development, its applications or uses in different"
        f"fields, and notable events or facts related to {concept}."
    )

    return prompt


def get_report_by_type(report_type, source):
    """
    The function `get_report_by_type` returns a specific report prompt based on the report type and
    source.

    Args:
      report_type: The report_type parameter is a string that specifies the type of report to generate.
    It can have one of the following values: "research_report", "resource_report", or "outline_report".
      source: The source parameter is a string that indicates where the report is coming from. It can
    have two possible values: "external" or any other value.

    Returns:
      the appropriate report prompt based on the report type and source.
    """
    if source == "external":
        report_type_mapping = {
            "research_report": generate_report_prompt,
            "resource_report": generate_resource_report_prompt,
            "outline_report": generate_outline_report_prompt,
        }
    else:
        report_type_mapping = {
            "research_report": generate_document_report_prompt,
            "resource_report": generate_document_resource_report_prompt,
            "outline_report": generate_document_outline_report_prompt,
        }
    return report_type_mapping[report_type]


def auto_agent_instructions() -> str:
    return """
        This task involves researching a given topic, regardless of its complexity or the availability of a definitive answer. The research is conducted by a specific agent, defined by its type and role, with each agent requiring distinct instructions.
        Agent
        The agent is determined by the field of the topic and the specific name of the agent that could be utilized to research the topic provided. Agents are categorized by their area of expertise, and each agent type is associated with a corresponding emoji.

        examples:
        task: "should I invest in apple stocks?"
        response: 
        {
            "agent": "💰 Finance Agent",
            "agent_role_prompt: "You are a seasoned finance analyst AI assistant. Your primary goal is to compose comprehensive, astute, impartial, and methodically arranged financial reports based on provided data and trends."
        }
        task: "could reselling sneakers become profitable?"
        response: 
        { 
            "agent":  "📈 Business Analyst Agent",
            "agent_role_prompt": "You are an experienced AI business analyst assistant. Your main objective is to produce comprehensive, insightful, impartial, and systematically structured business reports based on provided business data, market trends, and strategic analysis."
        }
        task: "what are the most interesting sites in Tel Aviv?"
        response:
        {
            "agent:  "🌍 Travel Agent",
            "agent_role_prompt": "You are a world-travelled AI tour guide assistant. Your main purpose is to draft engaging, insightful, unbiased, and well-structured travel reports on given locations, including history, attractions, and cultural insights."
        }
    """


################################################################################################

# DETAILED REPORT PROMPTS


def generate_subtopic_report_prompt(
    main_topic: str, subtopics: list, current_subtopic: str, research_summary: str = ""
) -> str:
    """
    The function `generate_subtopic_report_prompt` generates a prompt for creating a detailed report on
    a subtopic under a main topic.

    Args:
      main_topic (str): The main topic of the report. It is a string that represents the main topic
    under which the subtopic report will be generated.
      subtopics (list): The `subtopics` parameter is a list of strings that represents the subtopics
    related to the main topic. Each string in the list represents a specific subtopic.
      current_subtopic (str): The current subtopic under the main topic.
      research_summary (str): The `research_summary` parameter is an optional string that contains a
    summary of the research conducted on the main topic. It provides a brief overview of the main
    findings and key points related to the main topic. If no research summary is provided, the prompt
    will be generated without including the research summary section.

    Returns:
      a string prompt for generating a subtopic report.
    """
    if research_summary:
        prompt = (
            f'"""{research_summary}""" Using the above latest information,'
            f"""construct a detailed report on the subtopic: {current_subtopic} under the main topic: {main_topic}.
            - The report should focus on the answer to the question, should be well structured, informative,
            in-depth, with facts and numbers if available, a minimum of 1,200 words and with markdown syntax.
            - As this report will be part of a bigger report, you must ONLY include the main body divided into suitable subtopics,
            without any introduction, conclusion, or reference section.
            - Include hyperlinked urls to relevant sources wherever possible in the text.
            - All related numerical values (if any) should be bold.
            - Also avoid including any details from these other subtopics: {[subtopic for subtopic in subtopics[1:] if subtopic!=current_subtopic]}
            - Ensure that you use smaller Markdown headers (e.g., H2 or H3) to structure your content and avoid using the largest Markdown header (H1).
            The H1 header will be used for the heading of the larger report later on.
            - Do NOT include any details, urls or references where data is unavailable.
            - Do NOT include any conclusion or summary section! - Do NOT include a conclusion or summary!
            Assume that the current date is {datetime.now().strftime('%B %d, %Y')} if required."""
        )
    else:
        prompt = f"""Construct a detailed report on the subtopic: {current_subtopic} under the main topic: {main_topic}.
            - The report should focus on the answer to the question, should be well structured, informative,
            in-depth, with facts and numbers if available, a minimum of 1,200 words and with markdown syntax.
            - As this report will be part of a bigger report, you must ONLY include the main body divided into suitable subtopics,
            without any introduction, conclusion, or reference section.
            - Include hyperlinked urls to relevant sources wherever possible in the text.
            - All related numerical values (if any) should be bold.
            - Also avoid including any details from these other subtopics: {[subtopic for subtopic in subtopics[1:] if subtopic!=current_subtopic]}
            - Ensure that you use smaller Markdown headers (e.g., H2 or H3) to structure your content and avoid using the largest Markdown header (H1).
            The H1 header will be used for the heading of the larger report later on.
            - Do NOT include any details, urls or references where data is unavailable.
            - Do NOT include any conclusion or summary section! - Do NOT include a conclusion or summary!
            Assume that the current date is {datetime.now().strftime('%B %d, %Y')} if required.
        """

    return prompt


def generate_report_introduction(question: str, research_summary: str = "") -> str:
    """
    The function `generate_report_introduction` generates a prompt for preparing a detailed report
    introduction on a given topic, with an optional research summary.

    Args:
      question (str): The main question or topic for the report. This should be a string.
      research_summary (str): The research summary is a brief overview of the findings or key points
    from your research on the topic. It provides context and background information that can be used to
    support the introduction of your report.

    Returns:
      The function `generate_report_introduction` returns a string that contains a prompt for preparing
    a detailed report introduction on a given topic.
    """
    prompt = f"""Prepare a detailed report introduction on the topic -- {question}.
        - The introduction should be succinct, well-structured, informative with markdown syntax.
        - As this introduction will be part of a larger report, do NOT include any other sections, which are generally present in a report.
        - The introduction should be preceded by an H1 heading with a suitable topic for the entire report.
        Assume that the current date is {datetime.now().strftime('%B %d, %Y')} if required.
    """

    if research_summary:
        prompt = (
            f'"""{research_summary}""" Using the above latest information,' + prompt
        )

    return prompt


def generate_report_conclusion(question: str, research_summary: str = "") -> str:
    """
    The function `generate_report_conclusion` generates a prompt for generating a detailed report
    conclusion in APA format.

    Args:
      question (str): The main question or topic of the report. This should be a string that describes
    the focus of the report. For example, "What are the effects of climate change on biodiversity?"
      research_summary (str): The research summary is a brief overview of the main findings and key
    points from the research conducted on the given topic. It provides a summary of the research
    process, methodology, and results.

    Returns:
      The function `generate_report_conclusion` returns a string prompt that provides instructions for
    generating a detailed report conclusion. The prompt includes information about the topic of the
    report, the required format, and any additional instructions. If a research summary is provided, it
    is included in the prompt.
    """
    prompt = f"""Generate a detailed report conclusion,
        on the topic -- {question}.
        - The conclusion should be succinct, well-structured, informative with markdown syntax following APA format.
        - Do NOT defer to general and meaningless conclusions.
        - Since the conclusion will be part of a larger report, do not generate any other sections that are generally present in reports.
        - Use a 'Conclusion' H2 header.
        - If there are urls present, they MUST be hyperlinked.
        Assume that the current date is {datetime.now().strftime('%B %d, %Y')} if required.
        """
    if research_summary:
        prompt = f'"""{research_summary}""" Using the above information,' + prompt

    return prompt
