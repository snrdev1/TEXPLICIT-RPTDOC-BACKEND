from __future__ import annotations
from app.utils.common import Common

import json
import sys
from duckduckgo_search import DDGS

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
            
        print(f"Web search results for query {query} : {results} ", file=sys.stdout)
        sys.stdout.flush()

        total_added = 0
        for i in results:
            print(i,file=sys.stdout)
            sys.stdout.flush()
            search_results.append(i)
            total_added += 1
            if total_added >= num_results:
                break
            
        
        # for j in results:
        #     search_results.append(j)
        #     total_added += 1
        #     if total_added >= num_results:
        #         break

        return json.dumps(search_results, ensure_ascii=False, indent=4)

    except Exception as e:
        Common.exception_details("web_search", e)
        return json.dumps([])
