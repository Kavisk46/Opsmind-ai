def estimate_token_count(text: str) -> int:
    """A cheap word-count estimate, not a real tokenizer — consistent
    with this codebase's existing character-based (not token-based)
    chunking (see core/chunking.py). Shared by IngestionService (chunk
    token_count) and the retrieval engine (QueryService's query estimate,
    ContextService's context-budget accounting) so every part of the
    pipeline that needs "roughly how big is this text" agrees on the same
    definition, rather than each computing it slightly differently.
    """
    return len(text.split())
