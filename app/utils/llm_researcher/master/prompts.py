from datetime import datetime


def generate_search_queries_prompt(question: str, max_iterations: int = 3) -> str:
    return (
        f'Write {max_iterations} google search queries to search online that form an objective opinion from the following: "{question}"'
        f'Use the current date if needed: {datetime.now().strftime("%B %d, %Y")}.\n'
        f'You must respond with a list of strings in the following format: ["query 1", "query 2", "query 3"].'
    )


def generate_report_prompt(
    question, context, report_format="apa", total_words=1000, source="external"
):
    """Generates the report prompt for the given question and research summary.
    Args: question (str): The question to generate the report prompt for
            research_summary (str): The research summary to generate the report prompt for
    Returns: str: The report prompt for the given question and research summary
    """

    current_source = "documents"
    source_hyperlinks = ""
    source_url = ""
    if source == "external":
        current_source = "urls"
        
        source_hyperlinks = """
        Additionally, you MUST include hyperlinks to the relevant URLs wherever they are referenced in the report : 
        
        eg:    
            # Report Header
            
            This is a sample text. ([url website](url))
        """
        
        source_url = "(Each url in hyperlinked form : [url website](url))"

    return (
        f'Information: """{context}"""\n\n'
        f"Using the above information, answer the following"
        f' query or task: "{question}" in a detailed report --'
        " The report should focus on the answer to the query, should be well structured, informative,"
        f" in depth and comprehensive, with facts and numbers if available and a minimum of {total_words} words.\n"
        "You should strive to write the report as long as you can using all relevant and necessary information provided.\n"
        "You must write the report with markdown syntax.\n "
        f"Use an unbiased and journalistic tone. \n"
        "You MUST determine your own concrete and valid opinion based on the given information. Do NOT deter to general and meaningless conclusions.\n"
        "All related numerical values (if any) should be bold.\n"
        f"You MUST write all used source {current_source}{source_url} at the end of the report as references, and make sure to not add duplicated sources, but only one reference for each."
        f"{source_hyperlinks}"
        f"You MUST write the report in {report_format} format.\n "
        f"Cite search results using inline notations. Only cite the most \
            relevant results that answer the query accurately. Place these citations at the end \
            of the sentence or paragraph that reference them.\n"
        f"Please do your best, this is very important to my career. "
        f"Assume that the current date is {datetime.now().strftime('%B %d, %Y')}"
    )


def generate_resource_report_prompt(
    question, context, report_format="apa", total_words=1000, source="external"
):
    """Generates the resource report prompt for the given question and research summary.

    Args:
        question (str): The question to generate the resource report prompt for.
        context (str): The research summary to generate the resource report prompt for.

    Returns:
        str: The resource report prompt for the given question and research summary.
    """

    current_source = "urls" if source == "external" else "documents"

    return (
        f'"""{context}"""\n\nBased on the above information, generate a bibliography recommendation report for the following'
        f' question or topic: "{question}". The report should provide a detailed analysis of each recommended resource,'
        " explaining how each source can contribute to finding answers to the research question.\n"
        "Focus on the relevance, reliability, and significance of each source.\n"
        "Ensure that the report is well-structured, informative, in-depth, and follows Markdown syntax.\n"
        "Include relevant facts, figures, and numbers whenever available.\n"
        "The report should have a minimum length of 700 words.\n"
        f"You MUST include all relevant source {current_source}."
    )


def generate_custom_report_prompt(
    query_prompt, context, report_format="apa", total_words=1000, source="external"
):
    return f'"{context}"\n\n{query_prompt}'


def generate_outline_report_prompt(
    question, context, report_format="apa", total_words=1000, source="external"
):
    """Generates the outline report prompt for the given question and research summary.
    Args: question (str): The question to generate the outline report prompt for
            research_summary (str): The research summary to generate the outline report prompt for
    Returns: str: The outline report prompt for the given question and research summary
    """

    return (
        f'"""{context}""" Using the above information, generate an outline for a research report in Markdown syntax'
        f' for the following question or topic: "{question}". The outline should provide a well-structured framework'
        " for the research report, including the main sections, subsections, and key points to be covered."
        " The research report should be detailed, informative, in-depth, and a minimum of 1,200 words."
        " Use appropriate Markdown syntax to format the outline and ensure readability."
    )


def get_report_by_type(report_type):
    report_type_mapping = {
        "research_report": generate_report_prompt,
        "resource_report": generate_resource_report_prompt,
        "outline_report": generate_outline_report_prompt,
        "custom_report": generate_custom_report_prompt,
        "subtopic_report": generate_subtopic_report_prompt,
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


def generate_summary_prompt(query, data):
    """Generates the summary prompt for the given question and text.
    Args: question (str): The question to generate the summary prompt for
            text (str): The text to generate the summary prompt for
    Returns: str: The summary prompt for the given question and text
    """

    return (
        f'{data}\n Using the above text, summarize it based on the following task or query: "{query}".\n If the '
        f"query cannot be answered using the text, YOU MUST summarize the text in short.\n Include all factual "
        f"information such as numbers, stats, quotes, etc if available. "
    )


################################################################################################

# DETAILED REPORT PROMPTS


def generate_subtopic_report_prompt(
    current_subtopic,
    subtopics,
    main_topic,
    context,
    report_format="apa",
    total_words=1000,
    source="external",
) -> str:
    source_hyperlinks = ""
    if source == "external":
        source_hyperlinks = """
        You MUST include hyperlinks to the relevant URLs wherever they are referenced in the report : 
        
        eg:    
            # Report Header
            
            This is a sample text. ([url website](url))
        """
    
    prompt = (
        f'"""{context}""" Using the above latest information,'
        f"""construct a detailed report on the subtopic: {current_subtopic} under the main topic: {main_topic}.
        - The report should focus on the answer to the question, should be well structured, informative,
        in-depth, with facts and numbers if available, a minimum of {total_words} words and with markdown syntax.
        - As this report will be part of a bigger report, you must ONLY include the main body divided into suitable subtopics,
        without any introduction, conclusion, or reference section.
        {source_hyperlinks}
        - All related numerical values (if any) should be bold.
        - Also avoid including any details from these other subtopics: {[subtopic for subtopic in subtopics[1:] if subtopic!=current_subtopic]}
        - Ensure that you use smaller Markdown headers (e.g., H2 or H3) to structure your content and avoid using the largest Markdown header (H1).
        The H1 header will be used for the heading of the larger report later on.
        - Do NOT include any details, urls or references where data is unavailable.
        - Do NOT include any conclusion or summary section! - Do NOT include a conclusion or summary!
        Assume that the current date is {datetime.now().strftime('%B %d, %Y')} if required."""
    )

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
