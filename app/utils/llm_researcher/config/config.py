"""Configuration class to store the state of bools for different scripts access."""

import openai
from colorama import Fore

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
        self.fast_llm_model = ApplicationConfig.REPORT_FAST_LLM_MODEL
        self.smart_llm_model = ApplicationConfig.REPORT_SMART_LLM_MODEL
        self.fast_token_limit = ApplicationConfig.REPORT_FAST_TOKEN_LIMIT
        self.smart_token_limit = ApplicationConfig.REPORT_SMART_TOKEN_LIMIT
        self.browse_chunk_max_length = ApplicationConfig.REPORT_BROWSE_CHUNK_MAX_LENGTH
        self.summary_token_limit = ApplicationConfig.REPORT_SUMMARY_TOKEN_LIMIT
        self.openai_api_key = ApplicationConfig.OPENAI_API_KEY
        self.temperature = ApplicationConfig.REPORT_TEMPERATURE
        self.user_agent = ApplicationConfig.REPORT_USER_AGENT
        self.memory_backend = ApplicationConfig.REPORT_MEMORY_BACKEND

        # Initialize the OpenAI API client
        openai.api_key = self.openai_api_key

    def set_fast_llm_model(self, value: str) -> None:
        """Set the fast LLM model value."""
        self.fast_llm_model = value

    def set_smart_llm_model(self, value: str) -> None:
        """Set the smart LLM model value."""
        self.smart_llm_model = value

    def set_fast_token_limit(self, value: int) -> None:
        """Set the fast token limit value."""
        self.fast_token_limit = value

    def set_smart_token_limit(self, value: int) -> None:
        """Set the smart token limit value."""
        self.smart_token_limit = value

    def set_browse_chunk_max_length(self, value: int) -> None:
        """Set the browse_website command chunk max length value."""
        self.browse_chunk_max_length = value

    def set_openai_api_key(self, value: str) -> None:
        """Set the OpenAI API key value."""
        self.openai_api_key = value

    def set_debug_mode(self, value: bool) -> None:
        """Set the debug mode value."""
        self.debug_mode = value


def check_openai_api_key() -> None:
    """Check if the OpenAI API key is set in config.py or as an environment variable."""
    cfg = Config()
    if not cfg.openai_api_key:
        print(
            Fore.RED
            + "Please set your OpenAI API key in .env or as an environment variable."
        )
        print("You can get your key from https://platform.openai.com/account/api-keys")
        exit(1)
