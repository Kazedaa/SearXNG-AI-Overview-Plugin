"""Query intent classification for AI Overview."""

import re


def classify(query: str) -> str:
    """Classify the intent of a search query.

    Returns:
        "navigational": The user is looking for a specific website (skip AI).
        "informational": The user is asking a question or seeking knowledge.
        "ambiguous": Unclear intent, usually short keywords.
    """
    query = query.strip().lower()

    # Empty query
    if not query:
        return "ambiguous"

    # 1. Navigational Intent
    # Patterns indicating the user wants a specific domain or file
    nav_patterns = [
        r"^https?://",  # URLs
        r"\.[a-z]{2,4}(/.*)?$",  # Domain names (e.g., example.com, example.co.uk)
        r"^(site:|filetype:|inurl:|intitle:)",  # Search operators
    ]
    for pattern in nav_patterns:
        if re.search(pattern, query):
            return "navigational"

    # Single word queries for major brands/sites are almost always navigational
    # e.g., "youtube", "facebook", "twitter", "reddit"
    if " " not in query and len(query) > 3:
        known_navigational = {
            "youtube", "facebook", "twitter", "reddit", "instagram",
            "linkedin", "netflix", "amazon", "gmail", "yahoo",
            "pinterest", "tumblr", "wikipedia", "github", "stackoverflow"
        }
        if query in known_navigational:
            return "navigational"

    # 2. Informational Intent
    # Questions, comparisons, tutorials
    info_patterns = [
        r"^(how|what|why|when|where|who|which)\b",  # Question words
        r"\?$",  # Ends in question mark
        r"\b(vs|versus)\b",  # Comparisons
        r"^(define|meaning|explain|describe)\b",  # Explanations
        r"^(tutorial|guide|steps to)\b",  # How-tos
    ]
    for pattern in info_patterns:
        if re.search(pattern, query):
            return "informational"

    # 3. Ambiguous Intent
    # If it's a very short query (1-2 words) without question marks, it's ambiguous
    word_count = len(query.split())
    if word_count <= 2:
        return "ambiguous"

    # Default to informational for longer phrases
    return "informational"
