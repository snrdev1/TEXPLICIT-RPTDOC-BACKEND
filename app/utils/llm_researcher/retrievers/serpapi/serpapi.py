# SerpApi Retriever

# libraries
import os
import json
from serpapi import GoogleSearch
from app.config import Config

class SerpApiSearch():
    """
    SerpApi Retriever
    """
    def __init__(self, query):
        """
        Initializes the SerpApiSearch object
        Args:
            query:
        """
        self.query = query
        self.api_key = self.get_api_key()

    def get_api_key(self):
        """
        Gets the SerpApi API key
        Returns:

        """
        try:
            api_key = Config.SERPAPI_KEY
        except:
            raise Exception("SerpApi API key not found. Please set the SERPAPI_KEY environment variable. "
                            "You can get a key at https://serpapi.com/")
        return api_key

    def search(self, max_results=5):
        """
        Searches the query
        Returns:

        """
        try:
            print(f"\n🧲 Calling SERPAPI...\n")

            print("Searching with query {0}...".format(self.query))
            """Useful for general internet search queries using SerpApi."""
                
            search_results = []
            # If there is no query then return empty list
            if not self.query:
                return json.dumps(search_results)

            params = {
                "engine": "duckduckgo",
                "q": self.query,
                "api_key": self.api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict().get("organic_results", [])        # If there are no search results then return empty list
            if not results:
                print("🚩 Serp API failed to get search results!")
                return json.loads(json.dumps(search_results))

            total_added = 0
            for i in results:
                search_results.append(i)
                total_added += 1
                if total_added >= max_results:
                    break
            
            return json.loads(json.dumps(search_results, ensure_ascii=False, indent=4))

        except Exception as e:
            return json.loads(json.dumps([]))

