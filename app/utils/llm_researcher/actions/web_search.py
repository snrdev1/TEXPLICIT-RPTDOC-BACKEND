from __future__ import annotations
from app.utils.common import Common
from serpapi import GoogleSearch
import json
import sys
from duckduckgo_search import DDGS
from app.config import Config

ddgs = DDGS()

def web_search(query: str, num_results: int = 4) -> str:
    try:
        """Useful for general internet search queries."""
        
        print("Searching with query {0}...".format(query))
        
        search_results = []
        # If there is no query then return empty list
        if not query:
            return json.dumps(search_results)

        results = ddgs.text(query)
        # If there are no search results then return empty list
        if not results:
            return json.dumps(search_results)
            
        # print(f"Web search results for query {query} : {results} ", file=sys.stdout)
        sys.stdout.flush()

        total_added = 0
        for i in results:
            print(i,file=sys.stdout)
            sys.stdout.flush()
            search_results.append(i)
            total_added += 1
            if total_added >= num_results:
                break

        return json.dumps(search_results, ensure_ascii=False, indent=4)

    except Exception as e:
        Common.exception_details("web_search.web_search", e)
        return json.dumps([])
    
def serp_web_search(query: str, num_results: int = 4) -> str:
    try:
        """Useful for general internet search queries."""
        
        print("Searching with query {0}...".format(query))
        
        search_results = []
        # If there is no query then return empty list
        if not query:
            return json.dumps(search_results)

        params = {
        "engine": "duckduckgo",
        "q": query,
        "api_key": Config.SERPAPI_KEY
        }

        search = GoogleSearch(params)
        results = search.get_dict().get("organic_results", [])        # If there are no search results then return empty list
        if not results:
            print("🚩 Serp API failed to get search results!")
            return json.dumps(search_results)
            
        # print(f"Web search results for query {query} : {results} ", file=sys.stdout)
        sys.stdout.flush()

        total_added = 0
        for i in results:
            # print(i, file=sys.stdout)
            sys.stdout.flush()
            search_results.append(i)
            total_added += 1
            if total_added >= num_results:
                break
         
        return json.dumps(search_results, ensure_ascii=False, indent=4)

    except Exception as e:
        Common.exception_details("web_search.serp_web_search", e)
        return json.dumps([])
