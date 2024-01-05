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
        model=self.cfg.smart_llm_model,
        messages=[
            {"role": "system", "content": f"{agent_role_prompt}"},
            {"role": "user", "content": generate_search_queries_prompt(query, max_iterations=max_research_iterations)}],
        temperature=0,
        llm_provider=cfg.llm_provider
    )
    sub_queries = json.loads(response)
    return sub_queries