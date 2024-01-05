# Description: Research assistant class that handles the research process for a given question.

# libraries
import asyncio
import json
import os
import re
import string
from typing import Union

import markdown
from bson import ObjectId

from app.config import Config as GlobalConfig
from app.utils.files_and_folders import get_report_directory
from app.utils.production import Production
from llm_researcher.agent.functions import *
from llm_researcher.memory import Memory
from llm_researcher.actions import retrieve_context_from_documents
from llm_researcher.actions.tables import extract_tables
from llm_researcher.actions.web_scraper import async_browse
from llm_researcher.actions.web_search import serp_web_search, web_search
from llm_researcher.config import Config
from llm_researcher.processing.text import (
    create_chat_completion,
    create_message,
    read_txt_files,
    remove_roman_numerals,
    save_markdown,
    write_md_to_pdf,
    write_md_to_word,
    write_to_file,
)
from . import prompts

class ResearchAgent:
    def __init__(
        self,
        user_id: Union[str, ObjectId],
        question: str,
        agent: str,
        agent_role_prompt: str,
        source: str,
        format: str,
        websocket=None,
    ):
        """Initializes the research assistant with the given question.
        Args: question (str): The question to research
        Returns: None
        """

        # Stores the user question (task)
        self.question = question
        self.agent = agent
        self.agent_role_prompt = (
            agent_role_prompt
            if agent_role_prompt
            else prompts.generate_agent_role_prompt(agent)
        )
        self.visited_urls = set()
        self.user_id = user_id
        
        # Stores the entire research summary
        self.research_summary = ""
        # Stores markdown format of any table if found
        # self.report_type = report_type
        self.context = []
        
        self.tables = []
        # Source of report: external(web) or my_documents
        self.source = source
        # Format of expected report eg: pdf, word, ppt etc.
        self.format = format
        # Directory path of saved report
        self.dir_path = get_report_directory(user_id, question, self.source)
        print("📡 dir_path (report directory) : ", self.dir_path)

        self.websocket = websocket
        self.role = None
        self.memory = Memory()
        self.cfg = Config()
        
    
    async def conduct_research(
        self, num_queries: int = 3, max_docs: int = 15, score_threshold: float = 1.2
    ):
        """
        The function conducts research by reading text files, creating search queries, running search
        summaries, and returning the research summary.

        Args:
          num_queries: The `num_queries` parameter is an optional parameter that specifies the number of
        search queries to create if the research summary is empty. If the research summary is not empty,
        the `num_queries` parameter is ignored. Defaults to 3

        Returns:
          the research summary, which is a string containing the results of conducting research.
        """
        if self.source == "external":
            if GlobalConfig.GCP_PROD_ENV:
                self.research_summary = read_txt_files(self.dir_path) or ""
            else:
                self.research_summary = (
                    read_txt_files(self.dir_path)
                    if os.path.isdir(self.dir_path)
                    else ""
                )
            await self.extract_tables()

            if not self.research_summary:
                
                self.research_summary = await self.get_context_by_search(self.query)
                
                # search_queries = await self.create_search_queries(num_queries)
                # for query in search_queries:
                #     research_result = await self.run_search_summary(query)
                #     self.research_summary += f"{research_result}\n\n"

            await self.stream_output(
                f"Total research words: {len(self.research_summary.split(' '))}"
            )

        else:
            self.research_summary = retrieve_context_from_documents(
                self.user_id, self.question, max_docs, score_threshold
            )

        return self.research_summary
    
    async def get_context_by_search(self, query):
        """
           Generates the context for the research task by searching the query and scraping the results
        Returns:
            context: List of context
        """
        context = []
        # Generate Sub-Queries including original query
        sub_queries = await get_sub_queries(query) + [query]
        await stream_output("logs",
                            f"🧠 I will conduct my research based on the following queries: {sub_queries}...",
                            self.websocket)

        # Run Sub-Queries
        for sub_query in sub_queries:
            await stream_output("logs", f"\n🔎 Running research for '{sub_query}'...", self.websocket)
            scraped_sites = await self.scrape_sites_by_query(sub_query)
            content = await self.get_similar_content_by_query(sub_query, scraped_sites)
            await stream_output("logs", f"📃 {content}", self.websocket)
            context.append(content)

        return context

    async def stream_output(self, output):
        if not self.websocket:
            return print(output)
        await self.websocket.send_json({"type": "logs", "output": output})

    async def summarize(self, text, topic):
        """Summarizes the given text for the given topic.
        Args: text (str): The text to summarize
                topic (str): The topic to summarize the text for
        Returns: str: The summarized text
        """

        messages = [create_message(text, topic)]
        await self.stream_output(f"📝 Summarizing text for query: {text}")

        return create_chat_completion(
            model=self.cfg.fast_llm_model,
            messages=messages,
        )

    async def get_new_urls(self, url_set_input):
        """Gets the new urls from the given url set.
        Args: url_set_input (set[str]): The url set to get the new urls from
        Returns: list[str]: The new urls from the given url set
        """

        new_urls = []
        for url in url_set_input:
            if url not in self.visited_urls:
                await self.stream_output(f"✅ Adding source url to research: {url}\n")

                self.visited_urls.add(url)
                new_urls.append(url)

        return new_urls

    async def call_agent(self, prompt, stream=False, websocket=None):
        messages = [
            {"role": "system", "content": self.agent_role_prompt},
            {
                "role": "user",
                "content": prompt,
            },
        ]
        answer = create_chat_completion(
            model=self.cfg.smart_llm_model, messages=messages, stream=stream
        )
        return answer

    async def async_search(self, query):
        """Runs the async search for the given query.
        Args: query (str): The query to run the async search for
        Returns: list[str]: The async search for the given query
        """

        if GlobalConfig.REPORT_WEB_SCRAPER == "selenium":
            search_results = json.loads(web_search(query))
            new_search_urls = await self.get_new_urls(
                [url.get("href") for url in search_results]
            )
        else:
            search_results = json.loads(serp_web_search(query))
            new_search_urls = await self.get_new_urls(
                [url.get("link") for url in search_results]
            )

        await self.extract_tables(new_search_urls)

        await self.stream_output(
            f"🌐 Browsing the following sites for relevant information: {new_search_urls}..."
        )

        # Create a list to hold the coroutine objects
        tasks = [
            async_browse(url, query, self.websocket) for url in new_search_urls
        ]

        # # Gather the results as they become available
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        return responses

    async def run_search_summary(self, query):
        """
        The function runs a research query, saves the results to a file, and returns the results as a
        string.
        
        :param query: The `query` parameter is a string that represents the search query for which the
        research is being conducted
        :return: the `result` variable, which is a string containing the responses from the search.
        """
        
        await self.stream_output(f"🔎 Running research for '{query}'...")

        responses = await self.async_search(query)

        result = "\n".join(responses)
        summary_path = os.path.join(f"{self.dir_path}", f"research-{query}.txt")

        if len(result.strip()) != 0:
            if GlobalConfig.GCP_PROD_ENV:
                user_bucket = Production.get_users_bucket()
                blob = user_bucket.blob(summary_path)
                blob.upload_from_string(result)
            else:
                os.makedirs(os.path.dirname(summary_path), exist_ok=True)
                write_to_file(summary_path, result)

        return result

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

    async def write_report(self, report_type, source, websocket=None):
        report_type_func = prompts.get_report_by_type(report_type)
        await self.stream_output(
            f"✍️ Writing {report_type} for research task: {self.question}..."
        )

        answer = await self.call_agent(
            report_type_func(self.question, self.research_summary, source=self.source),
            stream=websocket is not None,
            websocket=websocket,
        )
        # if websocket is True than we are streaming gpt response, so we need to wait for the final response
        final_report = await answer if websocket else answer

        return final_report

    async def save_report(self, report_type, markdown_report):
        # Save report mardown for future use
        report_markdown_path = await save_markdown(
            report_type, self.dir_path, markdown_report
        )
        if self.format == "word":
            path = await write_md_to_word(
                report_type, self.dir_path, markdown_report, self.tables
            )
        # elif self.format == "ppt":
        #     path = await write_md_to_ppt(report_type, self.dir_path, markdown_report)
        else:
            path = await write_md_to_pdf(
                report_type, self.dir_path, markdown_report, self.tables
            )

        return path

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

    async def write_subtopic_report(
        self, report_type, main_topic, subtopics, current_subtopic, websocket=None
    ):
        prompt = prompts.generate_subtopic_report_prompt(
            main_topic, subtopics, current_subtopic, self.research_summary
        )
        await self.stream_output(
            f"✍️ Writing {report_type} for subtopic research task: {self.question}..."
        )

        answer = await self.call_agent(
            prompt, stream=websocket is not None, websocket=websocket
        )
        # if websocket is True than we are streaming gpt response, so we need to wait for the final response
        final_report = await answer if websocket else answer

        return final_report

    async def write_introduction_conclusion(self, websocket=None):
        # Construct Report Introduction from main topic research
        topic_introduction_prompt = prompts.generate_report_introduction(
            self.question, self.research_summary
        )
        topic_introduction = await self.call_agent(
            topic_introduction_prompt, stream=websocket is not None, websocket=websocket
        )

        # Construct Report Conclusion from main topic research
        topic_conclusion_prompt = prompts.generate_report_conclusion(
            self.question, self.research_summary
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