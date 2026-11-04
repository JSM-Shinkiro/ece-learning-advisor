"""Precompute a real Gemini index when an API key is configured."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from src.catalog import ROOT, build_evidence, load_catalog
from src.providers import EmbeddingCache, GeminiProvider


def main():
    load_dotenv(ROOT/".env")
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY in .env or your environment before building the index.")
    provider = GeminiProvider(
        key, embedding_model=os.getenv("EMBEDDING_MODEL","gemini-embedding-2"),
        generation_model=os.getenv("GENERATION_MODEL","gemini-3.5-flash-lite"),
        dimensions=int(os.getenv("EMBEDDING_DIMENSION","768")),
    )
    try:
        catalog = load_catalog()
        vectors, state, manifest = EmbeddingCache(ROOT/".cache/embeddings").get(catalog,build_evidence(catalog),provider)
        print("Index:", vectors.shape, "cache:", state, "model:", manifest["model"])
    finally:
        provider.close()


if __name__ == "__main__":
    main()
