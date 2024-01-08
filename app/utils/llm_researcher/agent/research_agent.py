# Description: Research assistant class that handles the research process for a given question.

# libraries
import asyncio
import json
import os
import re
from typing import Union
import time
import markdown
from bson import ObjectId
from ..actions import retrieve_context_from_documents
from ..actions.tables import extract_tables
from ..actions.web_search import serp_web_search
from ..agent.functions import *
from ..config import Config
from ..context.compression import ContextCompressor
from ..memory import Memory
from ..processing.text import (
    create_chat_completion,
    read_txt_files,
    remove_roman_numerals,
    save_markdown,
    write_md_to_pdf,
    write_md_to_word,
    write_to_file,
)

from app.config import Config as GlobalConfig
from app.utils.files_and_folders import get_report_directory
from app.utils.production import Production

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
        subtopics=[]
    ):
        # Stores the user question (task)
        self.query = query

        # Agent type and role of agent
        self.agent = None
        self.role = None

        # Type of report
        self.report_type = report_type

        # Set to store unique urls
        self.visited_urls = set()

        # Store user_id
        self.user_id = user_id

        # Stores the entire research summary
        self.context = []

        # Stores markdown format of any table if found
        self.tables = []

        # Source of report: external(web) or my_documents
        self.source = source

        # Format of expected report eg: pdf, word, ppt etc.
        self.format = format

        # Directory path of saved report
        self.dir_path = get_report_directory(user_id, self.query, self.source)
        print("📡 dir_path (report directory) : ", self.dir_path)

        self.websocket = websocket

        # For simple retrieval of embeddings for contextual compression
        self.memory = Memory()

        # Refernce to report config
        self.cfg = Config()
        
        
        # Only relevant for DETAILED REPORTS
        
        # Stores the main query of the detailed report
        self.parent_query = parent_query
        
        # Stores all the subtopics
        self.subtopics = subtopics

    async def conduct_research(
        self,
        max_docs: int = 15,
        score_threshold: float = 1.2
    ):
        try:
            report = ""
            print(f"🔎 Running research for '{self.query}'...")

            # Generate Agent for current task
            self.agent, self.role = await choose_agent(self.query, self.cfg)
            await stream_output("logs", self.agent, self.websocket)

            if self.source == "external":
                self.context = await self.get_context_by_search(self.query)

            else:
                self.context = retrieve_context_from_documents(
                    self.user_id, self.query, max_docs, score_threshold
                )

            # Write Research Report
            if len("".join(self.context)) > 10:
                await stream_output(
                    "logs",
                    f"✍️ Writing {self.report_type} for research task: {self.query}...",
                    self.websocket,
                )

                if self.report_type == "custom_report":
                    self.role = self.cfg.agent_role if self.cfg.agent_role else self.role
                elif self.report_type == "subtopic_report":
                    report = await generate_report(
                        query=self.query,
                        context=self.context,
                        agent_role_prompt=self.role,
                        report_type=self.report_type,
                        websocket=self.websocket,
                        cfg=self.cfg,
                        all_subtopics=self.subtopics,
                        main_topic=self.parent_query
                    )
                else:
                    report = await generate_report(
                        query=self.query,
                        context=self.context,
                        agent_role_prompt=self.role,
                        report_type=self.report_type,
                        websocket=self.websocket,
                        cfg=self.cfg
                    )
                
                time.sleep(2)

            return report
        
        except Exception as e:
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
                    f"Failed to gather content for for : {sub_query}",
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
        # Get Urls
        search_results = json.loads(
            serp_web_search(sub_query, self.cfg.max_search_results_per_query)
        )
        new_search_urls = await self.get_new_urls(
            [url.get("link") for url in search_results]
        )

        # Extract tables
        await self.extract_tables(new_search_urls)

        # Scrape Urls
        await stream_output(
            "logs", f"🤔Researching for relevant information...\n", self.websocket
        )
        scraped_content_results = scrape_urls(new_search_urls, self.cfg)
        return scraped_content_results

    async def get_new_urls(self, url_set_input):
        """Gets the new urls from the given url set.
        Args: url_set_input (set[str]): The url set to get the new urls from
        Returns: list[str]: The new urls from the given url set
        """

        new_urls = []
        for url in url_set_input:
            if url not in self.visited_urls:
                await stream_output("logs", f"✅ Adding source url to research: {url}\n")

                self.visited_urls.add(url)
                new_urls.append(url)

        return new_urls

    async def call_agent(self, prompt, stream=False, websocket=None):
        """
        The function `call_agent` takes a prompt and returns a completion generated by a chatbot model.

        :param prompt: The `prompt` parameter is a string that represents the user's input or query. It
        is the content that the user wants to send to the chatbot agent for processing and generating a
        response
        :param stream: The `stream` parameter is a boolean value that determines whether the response
        from the agent should be streamed or not. If `stream` is set to `True`, the response will be
        streamed as it becomes available. If `stream` is set to `False`, the response will be returned
        as a, defaults to False (optional)
        :param websocket: The `websocket` parameter is an optional argument that represents a WebSocket
        connection. It allows for real-time communication between the client and server. If provided,
        the `call_agent` function can use the WebSocket connection to send and receive messages
        asynchronously
        :return: The `call_agent` function returns the `answer` variable, which is the result of calling
        the `create_chat_completion` function.
        """
        messages = [
            {"role": "system", "content": self.role},
            {
                "role": "user",
                "content": prompt,
            },
        ]
        answer = create_chat_completion(
            model=self.cfg.smart_llm_model, messages=messages, stream=stream
        )
        return answer

    async def save_report(self, markdown_report):
        print("ℹ️ Adding source urls to report!") 
        
        markdown_report = add_source_urls(markdown_report, self.visited_urls)
        
        print("💾 Saving report!")
        # Save report mardown for future use
        report_markdown_path = await save_markdown(
            self.report_type, self.dir_path, markdown_report
        )
        
        print("💾 Saved markdown!")
        if self.format == "word":
            print("💾 Saving report document!")
            path = await write_md_to_word(
                self.report_type, self.dir_path, markdown_report, self.tables
            )
        # elif self.format == "ppt":
        #     path = await write_md_to_ppt(self.report_type, self.dir_path, markdown_report)
        else:
            print("💾 Saving report pdf!")
            path = await write_md_to_pdf(
                self.report_type, self.dir_path, markdown_report, self.tables
            )

        return path

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
        html_content = markdown.markdown(report)

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
        topic_introduction = await self.call_agent(
            topic_introduction_prompt, stream=websocket is not None, websocket=websocket
        )

        # Construct Report Conclusion from main topic research
        topic_conclusion_prompt = prompts.generate_report_conclusion(
            self.query, self.context
        )
        topic_conclusion = await self.call_agent(
            topic_conclusion_prompt, stream=websocket is not None, websocket=websocket
        )

        return topic_introduction, topic_conclusion

    ########################################################################################

    # TABLES

    def read_tables(self):
        if GlobalConfig.GCP_PROD_ENV:
            return read_txt_files(self.dir_path, tables=True) or ""
        else:
            if os.path.isdir(self.dir_path):
                return read_txt_files(self.dir_path, tables=True)
            else:
                return ""

    def save_tables(self):
        tables_path = os.path.join(self.dir_path, "tables.txt")

        # save tables
        if GlobalConfig.GCP_PROD_ENV:
            user_bucket = Production.get_users_bucket()
            blob = user_bucket.blob(tables_path)
            blob.upload_from_string(str(self.tables))
        else:
            os.makedirs(os.path.dirname(tables_path), exist_ok=True)
            write_to_file(tables_path, str(self.tables))

    async def extract_tables(self, urls: list = []):
        # Else extract tables from the urls and save them
        existing_tables = self.read_tables()
        if len(existing_tables):
            self.tables = eval(existing_tables)
            print("💎 Found EXISTING table/s")
        elif len(urls):
            # Extract all tables from search urls
            for url in urls:
                new_table = extract_tables(url)
                if len(new_table):
                    new_tables = {"tables": new_table, "url": url}
                    print(f"💎 Found table/s from {url}")
                    self.tables.append(new_tables)

            # If any tables at all are found then store them
            if len(self.tables):
                print("📝 Saving extracted tables")
                self.save_tables()

    ########################################################################################
