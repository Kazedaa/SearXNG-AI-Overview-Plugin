"""Parse search results into structured context for the LLM."""

import logging
from urllib.parse import urlparse

from .config import Config

logger = logging.getLogger(__name__)


def parse_results(raw_results: list, raw_infoboxes: list, raw_answers) -> list[dict]:
    """Normalize SearXNG results into a uniform list of dicts.

    Handles both MainResult (attribute-access) and LegacyResult (dict-access) types.
    Also extracts infobox and direct answer data.

    Returns:
        list of dicts with keys: type, title, content, url, publishedDate, attributes
    """
    results = []

    # Process infoboxes (knowledge graph data)
    for ib in raw_infoboxes[:2]:
        name = ""
        content = ""
        attributes = []

        if isinstance(ib, dict):
            name = ib.get("infobox", "") or ib.get("title", "") or ib.get("name", "")
            content = str(ib.get("content", ""))[:2000]
            attributes = ib.get("attributes", [])
        else:
            name = getattr(ib, "infobox", "") or getattr(ib, "title", "") or getattr(ib, "name", "")
            content = str(getattr(ib, "content", ""))[:2000]
            attributes = getattr(ib, "attributes", [])

        if name:
            results.append({
                "type": "infobox",
                "title": name,
                "content": content,
                "url": "",
                "publishedDate": "",
                "attributes": attributes,
            })

    # Process direct answers (skip HTML answers — those are from other plugins)
    for a in list(raw_answers)[:2]:
        ans_text = ""
        if hasattr(a, "answer") and isinstance(getattr(a, "answer", None), str):
            ans_text = a.answer
        elif isinstance(a, dict) and a.get("answer"):
            ans_text = str(a["answer"])

        if ans_text and not ans_text.strip().startswith("<"):
            results.append({
                "type": "answer",
                "title": "",
                "content": ans_text[:500],
                "url": "",
                "publishedDate": "",
                "attributes": [],
            })

    # Process search results
    for r in raw_results:
        if hasattr(r, "title"):
            # MainResult — attribute access
            results.append({
                "type": "result",
                "title": getattr(r, "title", ""),
                "content": getattr(r, "content", ""),
                "url": getattr(r, "url", ""),
                "publishedDate": getattr(r, "publishedDate", ""),
                "attributes": [],
            })
        else:
            # LegacyResult — dict access
            results.append({
                "type": "result",
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "url": r.get("url", ""),
                "publishedDate": r.get("publishedDate", ""),
                "attributes": [],
            })

    return results


def assemble_context(results: list[dict], config: Config) -> tuple[str, list[str]]:
    """Build a structured context string from parsed results.

    Returns:
        (context_string, urls_list) — the context for the LLM and ordered source URLs.
    """
    context_parts = []
    urls = []

    # --- Knowledge Graph section (infoboxes + direct answers) ---
    kg_lines = []
    for r in results:
        if r["type"] == "infobox":
            parts = [f"INFOBOX [{r['title']}]:"]
            if r["content"]:
                parts.append(r["content"].replace("\n", " ").strip())
            for attr in r.get("attributes", []):
                label = attr.get("label", "")
                value = attr.get("value", "")
                if label and value:
                    parts.append(f"  {label}: {value}")
            kg_lines.append("\n".join(parts) if len(parts) > 2 else " ".join(parts))

        elif r["type"] == "answer":
            kg_lines.append(f"ANSWER: {r['content'][:300]}")

    if kg_lines:
        context_parts.append("KNOWLEDGE GRAPH:\n" + "\n".join(kg_lines))

    # --- Deep Sources (full title + content) ---
    search_results = [r for r in results if r["type"] == "result"]
    deep_lines = []
    for i, r in enumerate(search_results[: config.context_deep_count]):
        url = r.get("url", "")
        urls.append(url)
        domain = urlparse(url).netloc.replace("www.", "") if url else "unknown"
        date_str = f" ({r['publishedDate']})" if r.get("publishedDate") else ""
        title = r.get("title", "").replace("\n", " ").strip()
        content = str(r.get("content", "")).replace("\n", " ").strip()[:800]
        idx = i + 1
        deep_lines.append(f"[{idx}] {domain}{date_str}: {title}: {content}")

    if deep_lines:
        context_parts.append("DEEP SOURCES:\n" + "\n".join(deep_lines))

    # --- Shallow Sources (title only) ---
    if config.context_shallow_count > 0:
        start = config.context_deep_count
        end = start + config.context_shallow_count
        shallow_lines = []
        for i, r in enumerate(search_results[start:end]):
            url = r.get("url", "")
            urls.append(url)
            domain = urlparse(url).netloc.replace("www.", "") if url else "unknown"
            title = r.get("title", "").replace("\n", " ").strip()[:60]
            idx = i + 1 + start
            shallow_lines.append(f"[{idx}] {domain}: {title}")

        if shallow_lines:
            context_parts.append("SHALLOW SOURCES (headlines):\n" + "\n".join(shallow_lines))

    return "\n\n".join(context_parts), urls
