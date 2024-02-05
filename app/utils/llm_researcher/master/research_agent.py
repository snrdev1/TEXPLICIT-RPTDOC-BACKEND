# Description: Research assistant class that handles the research process for a given question.

import os
import re
import time
from typing import Union

import mistune
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
from ..utils.text import (remove_roman_numerals, save_markdown,
                          write_md_to_pdf, write_md_to_word)
from . import prompts


class ResearchAgent:
    def __init__(
        self,
        user_id: Union[str, ObjectId],
        query: str,
        source: str,
        format: str,
        report_type: str = "research_report",
        websocket=None,
        parent_query="",
        subtopics=[],
        report_generation_id=""
    ):
        # Stores the user question (task)
        self.query = query

        # Agent type and role of agent
        self.agent = None
        self.role = None

        # Refernce to report config
        self.cfg = Config()

        # Type of report
        self.report_type = report_type

        # Set to store unique urls
        self.visited_urls = set()

        # Store user_id
        self.user_id = user_id

        # Stores the entire research summary
        self.context = []

        # Get research retriever
        self.retriever = get_retriever(self.cfg.retriever)

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

    async def conduct_research(self, max_docs: int = 15, score_threshold: float = 1.2):
        try:
            report = ""
            print(f"🔎 Running research for '{self.query}'...")
            emit_report_status(self.user_id, self.report_generation_id, f"🔎 Running research for '{self.query}'...")

            # Generate Agent for current task
            self.agent, self.role = await choose_agent(self.query, self.cfg)
            emit_report_status(self.user_id, self.report_generation_id, self.agent)
            await stream_output("logs", self.agent, self.websocket)

            if self.source == "external":
                emit_report_status(self.user_id, self.report_generation_id,  "📂 Retrieving context from external search...")

                self.context = await self.get_context_by_search(self.query)

            else:
                emit_report_status(self.user_id, self.report_generation_id,  "📂 Retrieving context from documents...")

                self.context, self.visited_urls = retrieve_context_from_documents(
                    self.user_id, self.query, max_docs, score_threshold
                )

            # Write Research Report
            if len("".join(self.context)) > 50:
                emit_report_status(self.user_id, self.report_generation_id,  f"✍️ Writing {get_formatted_report_type(self.report_type)} for research task: {self.query}...")
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
                        all_subtopics=self.subtopics,
                        main_topic=self.parent_query,
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
            return report

    async def get_context_by_search(self, query):
        """
           Generates the context for the research task by searching the query and scraping the results
        Returns:
            context: List of context
        """
        context = []

        # Generate Sub-Queries including original query (if report type is not subtopic_report)
        sub_queries = []
        if self.report_type == "subtopic_report":
            sub_queries = [f"{self.parent_query} - {query}"]
        else:
            sub_queries = await get_sub_queries(query, self.role, self.cfg) + [query]

        await stream_output(
            "logs",
            f"🧠 I will conduct my research based on the following queries: {sub_queries}...",
            self.websocket,
        )

        # Run Sub-Queries
        for sub_query in sub_queries:
            emit_report_status(self.user_id, self.report_generation_id,  f"🔎 Running research for '{sub_query}'...")
            await stream_output(
                "logs", f"\n🔎 Running research for '{sub_query}'...", self.websocket
            )
            scraped_sites = await self.scrape_sites_by_query(sub_query)

            content = await self.get_similar_content_by_query(sub_query, scraped_sites)
            if content:
                await stream_output("logs", f"📃 {content}", self.websocket)
            else:
                await stream_output(
                    "logs",
                    f"Failed to gather content for : {sub_query}",
                    self.websocket,
                )
            context.append(content)

        return context

    async def get_similar_content_by_query(self, query, pages):
        """
        The function `get_similar_content_by_query` retrieves relevant content based on a given query by
        summarizing raw data and returning the context with a maximum of 8 results.

        :param query: The query parameter is the search query or keyword that you want to use to find
        similar content. It is the input that will be used to retrieve relevant content based on the
        query
        :param pages: The "pages" parameter is a list of documents or pages that you want to find
        similar content for. Each document or page should be represented as a string
        :return: the relevant content based on the given query. The content is obtained by compressing
        the raw data using a ContextCompressor object and then getting the context for the query with a
        maximum of 8 results.
        """
        await stream_output(
            "logs",
            f"📃 Getting relevant content based on query: {query}...",
            self.websocket,
        )
        # Summarize Raw Data
        context_compressor = ContextCompressor(
            documents=pages, embeddings=self.memory.get_embeddings()
        )
        # Run Tasks
        return context_compressor.get_context(query, max_results=8)

    async def scrape_sites_by_query(self, sub_query):
        """
        Runs a sub-query
        Args:
            sub_query:

        Returns:
            Summary
        """
        try:
            # Get Urls
            retriever = self.retriever(sub_query)
            search_results = retriever.search(
                max_results=self.cfg.max_search_results_per_query
            )

            new_search_urls = await self.get_new_urls(
                [url.get("href") or url.get("link") or "" for url in search_results]
            )

            # Extract tables
            emit_report_status(self.user_id, self.report_generation_id, "📊 Trying to extracting tables...")
            await self.extract_tables(new_search_urls)

            # Scrape Urls
            emit_report_status(self.user_id, self.report_generation_id,  f"🤔Researching for relevant information...")
            await stream_output(
                "logs", f"🤔Researching for relevant information...\n", self.websocket
            )
            scraped_content_results = scrape_urls(new_search_urls, self.cfg)
            return scraped_content_results

        except Exception as e:
            Common.exception_details("scrape_sites_by_query", e)

    async def get_new_urls(self, url_set_input):
        """Gets the new urls from the given url set.
        Args: url_set_input (set[str]): The url set to get the new urls from
        Returns: list[str]: The new urls from the given url set
        """

        new_urls = []
        for url in url_set_input:
            if url not in self.visited_urls:
                emit_report_status(self.user_id, self.report_generation_id,  f"✅ Adding source url to research: {url}...")
                await stream_output("logs", f"✅ Adding source url to research: {url}\n")

                self.visited_urls.add(url)
                new_urls.append(url)

        return new_urls

    async def save_report(self, markdown_report):
        emit_report_status(self.user_id, self.report_generation_id, "💾 Saving report...")
        await stream_output("logs", f"💾 Saving report...\n")

        updated_markdown_report = add_source_urls(markdown_report, self.visited_urls, self.report_type, self.source)

        # Save report mardown for future use
        _ = await save_markdown(
            self.report_type, self.dir_path, updated_markdown_report
        )
        print("💾 Saved markdown!")

        if self.format == "word":
            emit_report_status(self.user_id, self.report_generation_id, f"💾 Saving report document format...\n")
            await stream_output("logs", f"💾 Saving report document format...\n")
            path = await write_md_to_word(
                self.report_type,
                self.dir_path,
                updated_markdown_report,
                self.tables_extractor,
            )
        else:
            emit_report_status(self.user_id, self.report_generation_id, f"💾 Saving report pdf format...\n")
            await stream_output("logs", f"💾 Saving report pdf format...\n")
            path = await write_md_to_pdf(
                self.report_type,
                self.dir_path,
                updated_markdown_report,
                self.tables_extractor,
            )

        return path

    async def get_report_markdown(self, report_type):
        if GlobalConfig.GCP_PROD_ENV:
            markdown_report_path = f"{self.dir_path}/{report_type}.md"
            user_bucket = Production.get_users_bucket()
            blob = user_bucket.blob(markdown_report_path)
            if blob.exists():
                markdown_content = blob.download_as_text()
                return markdown_content
        else:
            if os.path.isdir(self.dir_path):
                markdown_report_path = os.path.join(self.dir_path, f"{report_type}.md")
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

    def extract_subtopics(self, report, search, source):
        # Convert the Markdown to HTML
        html_content = mistune.html(report)

        # Use regular expressions to extract only the heading names and remove index and HTML tags
        h2_headings = re.findall(r"<h2[^>]*>(.*?)<\/h2>", html_content)

        subtopics = []
        # Print the extracted h2 headings without the index and HTML tags
        for heading in h2_headings:
            clean_heading = remove_roman_numerals(heading).split(".")[-1].strip()
            subtopics.append(
                {"task": clean_heading, "websearch": search, "source": source}
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
                if url.endswith(".pdf"):
                    continue

                await stream_output(
                    "logs",
                    f"🌐 Looking for tables to extract from {url}...\n",
                    self.websocket,
                )

                new_table = timeout_handler([], 5, self.tables_extractor.extract_tables, url)
                if len(new_table):
                    new_tables = {"tables": new_table, "url": url}
                    print(f"💎 Found table/s from {url}")
                    self.tables_extractor.tables.append(new_tables)

            # If any tables at all are found then store them
            if len(self.tables_extractor.tables):
                print("📝 Saving extracted tables")
                self.tables_extractor.save_tables()

    ########################################################################################
