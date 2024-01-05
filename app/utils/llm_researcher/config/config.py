"""Configuration class to store the state of bools for different scripts access."""

import openai
from app.config import Config as ApplicationConfig


class Config:
    """
    Configuration class to store the state of bools for different scripts access.
    """

    def __init__(self) -> None:
        """Initialize the Config class"""
        self.debug_mode = ApplicationConfig.REPORT_DEBUG_MODE
        self.allow_downloads = ApplicationConfig.REPORT_ALLOW_DOWNLOADS
        self.selenium_web_browser = ApplicationConfig.REPORT_WEB_BROWSER
        self.llm_provider = ApplicationConfig.REPORT_LLM_PROVIDER
        self.fast_llm_model = ApplicationConfig.FAST_LLM_MODEL
        self.smart_llm_model = ApplicationConfig.SMART_LLM_MODEL
        self.fast_token_limit = ApplicationConfig.REPORT_FAST_TOKEN_LIMIT
        self.smart_token_limit = ApplicationConfig.REPORT_SMART_TOKEN_LIMIT
        self.browse_chunk_max_length = ApplicationConfig.REPORT_BROWSE_CHUNK_MAX_LENGTH
        self.summary_token_limit = ApplicationConfig.REPORT_SUMMARY_TOKEN_LIMIT
        self.openai_api_key = ApplicationConfig.OPENAI_API_KEY
        self.temperature = ApplicationConfig.REPORT_TEMPERATURE
        self.user_agent = ApplicationConfig.REPORT_USER_AGENT
        self.memory_backend = ApplicationConfig.REPORT_MEMORY_BACKEND
        self.max_search_results_per_query = ApplicationConfig.REPORT_MAX_SEARCH_RESULTS_PER_QUERY
        self.max_iterations = ApplicationConfig.REPORT_MAX_ITERATIONS
        self.report_format = ApplicationConfig.REPORT_FORMAT
        self.total_words = ApplicationConfig.REPORT_TOTAL_WORDS 
        self.agent_role =  ApplicationConfig.REPORT_AGENT_ROLE

        # Initialize the OpenAI API client
        openai.api_key = self.openai_api_key
