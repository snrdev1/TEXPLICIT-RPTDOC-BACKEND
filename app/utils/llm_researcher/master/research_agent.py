# Description: Research assistant class that handles the research process for a given question.

import asyncio
import os
import time
from functools import lru_cache
from typing import List, Union

from bson import ObjectId

from app.config import Config as GlobalConfig
from app.utils.common import Common
from app.utils.files_and_folders import get_report_directory
from app.utils.formatter import get_formatted_report_type
from app.utils.production import Production
from app.utils.socket import emit_report_status
from app.utils.timer import timeout_handler

from ..config import Config
from ..context.compression import ContextCompressor
from ..master.functions import *
from ..memory import Memory
from ..scraper import *
from ..utils.llm import construct_subtopics
from ..utils.text import save_markdown, write_md_to_pdf, write_md_to_word
from . import prompts


class ResearchAgent:
    def __init__(
        self,
        user_id: Union[str, ObjectId],
        query: str,
        source: str,
        format: str,
        report_type: str = Enumerator.ReportType.ResearchReport.value,
        websocket=None,
        parent_query="",
        subtopics=[],
        report_generation_id="",
        input_urls: List[str] = [],
        visited_urls: set = set(),
        restrict_search: bool = False,
        agent: str = "",
        role: str = ""
    ):
        # Stores the user question (task)
        self.query = query

        # Agent type and role of agent
        self.agent = agent
        self.role = role

        # Reference to report config
        self.cfg = Config()

        # Type of report
        self.report_type = report_type

        # Type of search to perform : restricted or mixed
        self.restrict_search = restrict_search
        
        # List of input urls to research on
        self.input_urls = input_urls

        # Set to store unique urls
        self.visited_urls = visited_urls

        # Store user_id
        self.user_id = user_id

        # Stores the entire research summary
        self.context = []

        # Get research retriever
        self.retriever = get_retriever(self.cfg.retriever)

        # Get the url scraper
        self.scraper = self.cfg.scraper

        # Source of report: external(web) or my_documents
        self.source = source

        # Format of expected report eg: pdf, word, ppt etc.
        self.format = format

        # Directory path of saved report
        self.dir_path = get_report_directory(user_id, self.query, self.source)

        # Table extractor object
        self.tables_extractor = TableExtractor(self.dir_path)

        self.websocket = websocket

        # For simple retrieval of embeddings for contextual compression
        self.memory = Memory()

        # Only relevant for DETAILED REPORTS

        # Stores the main query of the detailed report
        self.parent_query = parent_query

        # Stores all the subtopics
        self.subtopics = subtopics

        # Stores the report generation id
        self.report_generation_id = report_generation_id
        
        # To record the error logs while generating the report
        self.error_log = []

    async def conduct_research(
        self,
        max_docs: int = 15,
        score_threshold: float = 1.2,
        existing_headers: list = [],
        write_report: bool = True
    ):
        try:
            report = ""
            print(f"🔎 Running research for '{self.query}'...")
            emit_report_status(
                self.user_id,
                self.report_generation_id,
                f"🔎 Running research for '{self.query}'..."
            )

            # Generate Agent for current task if necessary
            if not (self.agent and self.role):
                self.agent, self.role = await choose_agent(self.query, self.cfg)
                emit_report_status(
                    self.user_id,
                    self.report_generation_id,
                    self.agent
                )
                await stream_output(
                    "logs",
                    self.agent,
                    self.websocket
                )

            if self.source == "external":
                emit_report_status(
                    self.user_id,
                    self.report_generation_id,
                    "📂 Retrieving context from external search..."
                )

                context = await self.get_context_by_search(self.query)
                self.context.extend(context)

            else:
                emit_report_status(
                    self.user_id,
                    self.report_generation_id,
                    "📂 Retrieving context from documents..."
                )

                context, self.visited_urls = retrieve_context_from_documents(
                    self.user_id, self.query, max_docs, score_threshold
                )
                self.context.extend(context)

            if write_report:
                report = await self.write_report(existing_headers)

            return report

        except Exception as e:
            Common.exception_details("ResearchAgent.conduct_research", e)
            self.error_log.append(e)
            return report

    async def write_report(self, existing_headers: list = []):
        try:
            report = ""

            # Write Report
            emit_report_status(
                self.user_id,
                self.report_generation_id,
                f"✍️ Writing {get_formatted_report_type(self.report_type)} for research task: {self.query}..."
            )
            await stream_output(
                "logs",
                f"✍️ Writing {self.report_type} for research task: {self.query}...",
                self.websocket,
            )

            if self.report_type == "custom_report":
                self.role = (
                    self.cfg.agent_role if self.cfg.agent_role else self.role
                )
            elif self.report_type == "subtopic_report":
                report = await generate_report(
                    query=self.query,
                    context=self.context,
                    agent_role_prompt=self.role,
                    report_type=self.report_type,
                    websocket=self.websocket,
                    cfg=self.cfg,
                    main_topic=self.parent_query,
                    existing_headers=existing_headers
                )
            else:
                report = await generate_report(
                    query=self.query,
                    context=self.context,
                    agent_role_prompt=self.role,
                    report_type=self.report_type,
                    websocket=self.websocket,
                    cfg=self.cfg,
                )

            time.sleep(2)

            return report

        except Exception as e:
            Common.exception_details("ResearchAgent.conduct_research", e)
            self.error_log.append(e)
            return report

    async def get_context_by_search(self, query):
        """ Generates the context for the research task by searching the query and scraping the results
        Returns: context: List of context
        """
        context = []

        # Determine sub-queries based on report type
        sub_queries = [query]
        if self.report_type != "subtopic_report":
            sub_queries.extend(await get_sub_queries(query, self.role, self.cfg))
        else:
            sub_queries = [f"{self.parent_query} - {query}"]

        await stream_output(
            "logs",
            f"🧠 I will conduct my research based on the following queries: {', '.join(sub_queries)}...",
            self.websocket
        )

        # Cache scraped sites if custom URLs are provided and search type is restricted
        scraped_sites = None
        if self.restrict_search:
            scraped_sites = await self.scrape_sites_by_query()

        async def process_sub_query(sub_query):
            nonlocal scraped_sites
            emit_report_status(
                self.user_id,
                self.report_generation_id,
                f"🔎 Running research for '{sub_query}'..."
            )
            await stream_output(
                "logs",
                f"\n🔎 Running research for '{sub_query}'...",
                self.websocket
            )

            # Perform scraping if data not already cached
            if not scraped_sites:
                scraped_sites = await self.scrape_sites_by_query(sub_query)

            # Handle scraping failures
            if not scraped_sites:
                await stream_output(
                    "logs",
                    f"Failed to gather content for: {sub_query}",
                    self.websocket
                )
                return None

            # Get similar content by query from scraped sites
            content = await self.get_similar_content_by_query(sub_query, scraped_sites)

            # Handle content retrieval failures
            if content:
                await stream_output(
                    "logs",
                    f"📃 {content}",
                    self.websocket
                )
                return content
            else:
                await stream_output(
                    "logs",
                    f"Failed to gather content for: {sub_query}",
                    self.websocket
                )
                return None

        # Use asyncio.gather for concurrent execution of sub-queries
        tasks = [process_sub_query(sub_query) for sub_query in sub_queries]
        results = await asyncio.gather(*tasks)
        context.extend(filter(None, results))  # Filter out None results

        return context

    async def get_similar_content_by_query(self, query, pages):
        """
        This Python async function retrieves relevant content based on a query by summarizing raw data
        and running tasks using a ContextCompressor.

        Args:
          query: The `query` parameter is the search query based on which relevant content will be
        retrieved.
          pages: The `pages` parameter in the `get_similar_content_by_query` function is a list of
        documents or content that you want to search for relevant content based on the provided query.
        It is used by the `ContextCompressor` to compress the context and find similar content based on
        the query.

        Returns:
          The `get_similar_content_by_query` function returns the context compressor's result of getting
        relevant content based on the provided query, with a maximum of 8 results.
        """
        await stream_output(
            "logs",
            f"📃 Getting relevant content based on query: {query}...",
            self.websocket,
        )
        # Summarize Raw Data
        context_compressor = ContextCompressor(
            documents=pages,
            embeddings=self.memory.get_embeddings()
        )
        # Run Tasks
        return context_compressor.get_context(query, max_results=8)

    async def scrape_sites_by_query(self, sub_query: str = ""):
        try:
            # Assign the new_search_urls to the input urls
            # As per the working of the get_new_urls function,
            # if this function is called a second time it will return a blank array
            # as the input_urls will already be marked visited under the 
            # visited_urls set
            new_search_urls = await self.get_new_urls(self.input_urls)
            
            # If search is not restricted then further scraping and searching is required
            if not self.restrict_search:
                # Get Urls
                retriever = self.retriever(sub_query)
                search_results = retriever.search(
                    max_results=self.cfg.max_search_results_per_query
                )

                # If no search results are found then return empty contents
                if not search_results:
                    emit_report_status(
                        self.user_id,
                        self.report_generation_id,
                        f"🚩 Failed to get search results for : {sub_query}"
                    )
                    return ""

                # Retrieve new search urls that are encountered from web search
                new_search_urls.extend(
                    await self.get_new_urls(
                        [url.get("href") or url.get("link")
                        or "" for url in search_results]
                    )
                )

            # Extract tables from gathered urls
            emit_report_status(
                self.user_id,
                self.report_generation_id,
                "📊 Trying to extract tables..."
            )
            await self.extract_tables(new_search_urls)

            # Scrape Urls
            emit_report_status(
                self.user_id,
                self.report_generation_id,
                f"🤔Researching for relevant information..."
            )
            await stream_output(
                "logs",
                f"🤔Researching for relevant information...\n",
                self.websocket
            )
            scraped_content_results = scrape_urls(new_search_urls, self.cfg)
            return scraped_content_results

        except Exception as e:
            Common.exception_details("scrape_sites_by_query", e)
            emit_report_status(
                self.user_id,
                self.report_generation_id,
                "🚩 Failed to get search results..."
            )
            self.error_log.append("🚩 Failed to get search results...")
            return ""

    async def get_new_urls(self, url_set_input):
        """Gets the new urls from the given url set.
        Args: url_set_input (set[str]): The url set to get the new urls from
        Returns: list[str]: The new urls from the given url set
        """

        new_urls = []
        for url in url_set_input:
            if url not in self.visited_urls:
                emit_report_status(
                    self.user_id,
                    self.report_generation_id,
                    f"✅ Adding source url to research: {url}..."
                )
                await stream_output(
                    "logs",
                    f"✅ Adding source url to research: {url}\n"
                )

                self.visited_urls.add(url)
                new_urls.append(url)

        return new_urls

    async def save_report(self, markdown_report):
        """
        This Python async function saves a report in markdown format, converts it to either Word or PDF
        format based on user preference, and saves tables to Excel.

        Args:
          markdown_report: The `save_report` method you provided is an asynchronous function that saves
        a report in different formats based on the specified format ("word" or "pdf"). Here's a
        breakdown of the steps it performs:

        Returns:
          The `save_report` method returns two values: `encoded_file_path` and `encoded_table_path`.
        """

        emit_report_status(
            self.user_id,
            self.report_generation_id,
            "💾 Saving report..."
        )
        await stream_output(
            "logs",
            f"💾 Saving report...\n"
        )

        # Get the complete file path based reports folder, type of report
        file_path = os.path.join(self.dir_path, self.report_type)

        # Ensure that this file path exists
        os.makedirs(file_path, exist_ok=True)

        updated_markdown_report = add_source_urls(
            markdown_report,
            self.visited_urls,
            self.report_type,
            self.source
        )

        # Save report markdown for future use
        _ = await save_markdown(file_path, updated_markdown_report)
        print("💾 Saved markdown!")

        if self.format == "word":
            emit_report_status(
                self.user_id,
                self.report_generation_id,
                f"💾 Saving report document format...\n"
            )
            await stream_output(
                "logs",
                f"💾 Saving report document format...\n"
            )
            encoded_file_path = await write_md_to_word(
                file_path,
                updated_markdown_report
            )
        else:
            emit_report_status(
                self.user_id,
                self.report_generation_id,
                f"💾 Saving report pdf format...\n"
            )
            await stream_output(
                "logs",
                f"💾 Saving report pdf format...\n"
            )
            encoded_file_path = await write_md_to_pdf(
                file_path,
                updated_markdown_report
            )

        await stream_output(
            "logs",
            f"💾 Saving tables to excel...\n"
        )
        encoded_table_path = await self.tables_extractor.save_tables_to_excel()

        return encoded_file_path, encoded_table_path

    async def get_report_markdown(self, report_type):
        """
        This async function generates a markdown report based on the specified report type.

        Args:
          report_type: The `report_type` parameter in the `get_report_markdown` function is used to
        specify the type of report for which you want to generate the markdown. It could be a string
        indicating the type of report such as "summary", "detailed", "monthly", "yearly", etc.
        """
        if GlobalConfig.GCP_PROD_ENV:
            markdown_report_path = f"{self.dir_path}/{report_type}.md"
            user_bucket = Production.get_users_bucket()
            blob = user_bucket.blob(markdown_report_path)
            if blob.exists():
                markdown_content = blob.download_as_text()
                return markdown_content
        else:
            if os.path.isdir(self.dir_path):
                markdown_report_path = os.path.join(
                    self.dir_path, f"{report_type}.md")
                if os.path.exists(markdown_report_path):
                    # Initialize an empty string to store the content
                    markdown_content = ""

                    # Open and read the Markdown file
                    with open(
                        markdown_report_path, "r", encoding="cp437", errors="ignore"
                    ) as file:
                        markdown_content = file.read()

                    # Now, 'markdown_content' contains the content of the Markdown file
                    return markdown_content

        return None

    async def check_existing_report(self, report_type):
        """
        The function `check_existing_report` checks if a report of a given type already exists in a
        directory or a Google Cloud Storage bucket.

        Args:
          report_type: The `report_type` parameter is a string that represents the type of report being
        checked. It is used to construct the file name of the report.

        Returns:
          the report path if the report exists, otherwise it returns None.
        """
        if GlobalConfig.GCP_PROD_ENV:
            report_path = f"{self.dir_path}/{report_type}.{self.format}"
            user_bucket = Production.get_users_bucket()
            blob = user_bucket.blob(report_path)
            if blob.exists():
                return report_path
        else:
            if os.path.isdir(self.dir_path):
                report_path = os.path.join(
                    self.dir_path, f"{report_type}.{self.format}"
                )
                if os.path.exists(report_path):
                    return report_path

        return None

    ########################################################################################

    # DETAILED REPORT

    async def get_subtopics(self):
        subtopics = await construct_subtopics(
            task=self.query,
            data=self.context,
            source=self.source,
            # This is a list of user provided subtopics
            subtopics=self.subtopics
        )

        return subtopics

    async def write_introduction_conclusion(self, websocket=None):
        # Construct Report Introduction from main topic research
        topic_introduction_prompt = prompts.generate_report_introduction(
            self.query, self.context
        )
        topic_introduction = await create_chat_completion(
            model=self.cfg.smart_llm_model,
            messages=[
                {"role": "system", "content": f"{self.role}"},
                {"role": "user", "content": topic_introduction_prompt},
            ],
            temperature=0,
            llm_provider=self.cfg.llm_provider,
            # stream=True,
            websocket=websocket,
            max_tokens=self.cfg.smart_token_limit,
        )

        # Construct Report Conclusion from main topic research
        topic_conclusion_prompt = prompts.generate_report_conclusion(
            self.query, self.context
        )
        topic_conclusion = await create_chat_completion(
            model=self.cfg.smart_llm_model,
            messages=[
                {"role": "system", "content": f"{self.role}"},
                {"role": "user", "content": topic_conclusion_prompt},
            ],
            temperature=0,
            llm_provider=self.cfg.llm_provider,
            # stream=True,
            websocket=websocket,
            max_tokens=self.cfg.smart_token_limit,
        )

        return topic_introduction, topic_conclusion

    ########################################################################################

    # TABLES

    async def extract_tables(self, urls: list = []):
        # Else extract tables from the urls and save them
        existing_tables = self.tables_extractor.read_tables()
        if len(existing_tables):
            self.tables_extractor.tables = eval(existing_tables)
            await stream_output(
                "logs",
                f"💎 Found {len(self.tables_extractor.tables)} EXISTING table/s\n,"
            )
        elif len(urls):
            # Extract all tables from search urls
            for url in urls:
                await stream_output(
                    "logs",
                    f"🌐 Looking for tables to extract from {url}...\n",
                    self.websocket,
                )

                tables = timeout_handler(
                    [], 10, self.tables_extractor.extract_tables, url)
                if len(tables):
                    new_tables = {"tables": tables, "url": url}
                    print(f"💎 Found table/s from {url}")
                    self.tables_extractor.tables.append(new_tables)

            # If any tables at all are found then store them
            if len(self.tables_extractor.tables):
                print("📝 Saving extracted tables")
                self.tables_extractor.save_tables()

    ########################################################################################
