import asyncio
import json

from ..master.prompts import *
from ..scraper import Scraper
from ..utils.llm import *


def get_retriever(retriever):
    """
    Gets the retriever
    Args:
        retriever: retriever name

    Returns:
        retriever: Retriever class

    """
    match retriever:
        case "tavily":
            from ..retrievers import TavilySearch

            retriever = TavilySearch
        case "tavily_news":
            from ..retrievers import TavilyNews

            retriever = TavilyNews
        case "google":
            from ..retrievers import GoogleSearch

            retriever = GoogleSearch
        case "searx":
            from ..retrievers import SearxSearch

            retriever = SearxSearch
        case "serpapi":
            from ..retrievers import SerpApiSearch

            retriever = SerpApiSearch
        case "googleSerp":
            from ..retrievers import SerperSearch

            retriever = SerperSearch
        case "duckduckgo":
            from ..retrievers import Duckduckgo

            retriever = Duckduckgo
        case "BingSearch":
            from ..retrievers import BingSearch

            retriever = BingSearch

        case _:
            raise Exception("Retriever not found.")

    return retriever


async def get_sub_queries(query, agent_role_prompt, cfg):
    """
    Gets the sub queries
    Args:
        query: original query
        agent_role_prompt: agent role prompt
        cfg: Config

    Returns:
        sub_queries: List of sub queries

    """

    max_research_iterations = cfg.max_iterations if cfg.max_iterations else 1

    response = await create_chat_completion(
        model=cfg.smart_llm_model,
        messages=[
            {"role": "system", "content": f"{agent_role_prompt}"},
            {
                "role": "user",
                "content": generate_search_queries_prompt(
                    query, max_iterations=max_research_iterations
                ),
            },
        ],
        temperature=0,
        llm_provider=cfg.llm_provider,
    )
    sub_queries = json.loads(response)
    return sub_queries


async def stream_output(type, output, websocket=None, logging=True):
    """
    Streams output to the websocket
    Args:
        type:
        output:

    Returns:
        None
    """
    if not websocket or logging:
        print(output)

    if websocket:
        await websocket.send_json({"type": type, "output": output})


def scrape_urls(urls, cfg=None):
    """
    Scrapes the urls
    Args:
        urls: List of urls
        cfg: Config (optional)

    Returns:
        text: str

    """
    content = []
    user_agent = (
        cfg.user_agent
        if cfg
        else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
    )
    try:
        content = Scraper(urls, user_agent).run()
    except Exception as e:
        print(f"{Fore.RED}Error in scrape_urls: {e}{Style.RESET_ALL}")
    return content


async def generate_report(
    query,
    context,
    agent_role_prompt,
    report_type,
    websocket,
    cfg,
    all_subtopics: list = [],
    main_topic: str = "",
):
    try:
        generate_prompt = get_report_by_type(report_type)

        if report_type == "subtopic_report":
            all_subtopic_tasks = [subtopic.get("task") for subtopic in all_subtopics]
            content = f"{generate_prompt(query, all_subtopic_tasks, main_topic, context, cfg.report_format, cfg.total_words)}"
        else:
            content = (
                f"{generate_prompt(query, context, cfg.report_format, cfg.total_words)}"
            )

        report = await create_chat_completion(
            model=cfg.smart_llm_model,
            messages=[
                {"role": "system", "content": f"{agent_role_prompt}"},
                {"role": "user", "content": content},
            ],
            temperature=0,
            llm_provider=cfg.llm_provider,
            # stream=True,
            websocket=websocket,
            max_tokens=cfg.smart_token_limit,
        )

        return report
    except Exception as e:
        print(f"{Fore.RED}Error in generate_report: {e}{Style.RESET_ALL}")
        return ""


def add_source_urls(report_markdown: str, visited_urls: set, report_type: str, source: str):
    """
    The function takes a markdown report, a set of visited URLs, a report type, and a source, and
    returns the report with added source URLs.
    
    :param report_markdown: A string containing the markdown content of the report
    :type report_markdown: str
    :param visited_urls: The `visited_urls` parameter is a set that contains the URLs of web pages that
    have already been visited. This is used to keep track of which URLs have already been processed to
    avoid duplicate entries in the report
    :type visited_urls: set
    :param report_type: The type of report being generated. It could be "summary", "detailed", or any
    other type you define
    :type report_type: str
    :param source: The `source` parameter is a string that represents the source of the report. It could
    be the name of a website, a document, or any other source from which the report was generated
    :type source: str
    """
    try:
        if report_type not in ["detailed_report", "complete_report"]:
            return report_markdown
        
        print("ℹ️ Adding source urls/documents to report!")

        url_markdown = "\n\n\n## References\n\n"

        if source == "external":
            url_markdown += "".join(f"- [{url}]({url})\n" for url in visited_urls)
        else:
            url_markdown += "".join(f"- {url}\n" for url in visited_urls)

        updated_markdown_report = report_markdown + url_markdown

        return updated_markdown_report

    except Exception as e:
        return report_markdown

