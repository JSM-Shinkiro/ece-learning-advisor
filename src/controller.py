"""One submitted provider request with a current-profile fallback."""
from pathlib import Path
from .providers import GeminiProvider, ProviderError
from .service import recommend


def run_advisor(catalog, profile, *, api_key="", use_ai=False, method="hybrid",
                embedding_model="gemini-embedding-2", generation_model="gemini-3.5-flash-lite",
                dimensions=768, cache_dir=Path(".cache/embeddings"), provider_factory=None):
    provider, issue = None, None
    if use_ai and api_key:
        try:
            provider = (provider_factory or GeminiProvider)(api_key, embedding_model=embedding_model,
                generation_model=generation_model, dimensions=dimensions)
        except (ProviderError, ImportError, ValueError):
            issue = "AI could not start. This updated plan uses the available source information."
    try:
        result = recommend(catalog, profile, provider=provider,
                           method=method if provider else "keyword", cache_dir=cache_dir)
        if issue:
            result.issues.append(issue)
        return result
    finally:
        if provider is not None:
            provider.close()
