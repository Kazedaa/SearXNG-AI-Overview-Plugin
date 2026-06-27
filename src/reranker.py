"""Semantic re-ranking of search results using Ollama embeddings."""

import logging
import math

from .config import Config
from .ollama import get_embeddings

logger = logging.getLogger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))

    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0

    return dot_product / (norm_v1 * norm_v2)


def rerank(
    query: str, parsed_results: list[dict], config: Config, top_k: int
) -> list[dict]:
    """Re-rank results based on semantic similarity to the query.

    Args:
        query: The user's search query.
        parsed_results: List of result dicts from context.parse_results.
        config: Plugin configuration.
        top_k: Number of top results to return.

    Returns:
        A new list of parsed_results ordered by relevance.
    """
    if not parsed_results:
        return []

    # Separate search results from infoboxes/answers (which we don't rerank)
    results_to_rerank = [r for r in parsed_results if r["type"] == "result"]
    other_results = [r for r in parsed_results if r["type"] != "result"]

    if not results_to_rerank:
        return parsed_results

    # Prepare texts for embedding
    # Format: "Title. Content snippet..."
    texts_to_embed = [query]
    for r in results_to_rerank:
        text = f"{r.get('title', '')}. {r.get('content', '')}".strip()
        texts_to_embed.append(text[:1000])  # Truncate to reasonable length

    # Call Ollama for embeddings
    logger.info("AI Overview: Fetching embeddings for re-ranking (%d items)", len(texts_to_embed))
    embeddings = get_embeddings(config, texts_to_embed)

    # Fallback if embeddings fail
    if not embeddings or len(embeddings) != len(texts_to_embed):
        logger.warning("AI Overview: Embedding generation failed, falling back to original order.")
        return other_results + results_to_rerank[:top_k]

    query_embedding = embeddings[0]
    result_embeddings = embeddings[1:]

    # Compute similarity and sort
    scored_results = []
    for i, r in enumerate(results_to_rerank):
        score = cosine_similarity(query_embedding, result_embeddings[i])
        scored_results.append((score, r))

    # Sort descending by score
    scored_results.sort(key=lambda x: x[0], reverse=True)

    # Extract the top_k results
    top_results = [r for score, r in scored_results[:top_k]]

    return other_results + top_results
