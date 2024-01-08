import json
import asyncio
from ..utils.llm import *
from ..scraper import Scraper
from ..agent.prompts import *
import json


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
            stream=True,
            websocket=websocket,
            max_tokens=cfg.smart_token_limit,
        )

        return report
    except Exception as e:
        print(f"{Fore.RED}Error in generate_report: {e}{Style.RESET_ALL}")
        return ""
