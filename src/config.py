"""Centralized configuration from environment variables with validation."""

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _parse_bool(value: str) -> bool:
    return value.lower().strip() in ("true", "1", "yes", "on")


def _parse_int(name: str, raw: str, default: int, min_val: int | None = None, max_val: int | None = None) -> int:
    try:
        val = int(raw)
    except (ValueError, TypeError):
        logger.warning("AI Overview: Invalid %s value '%s', using default %d", name, raw, default)
        return default
    if min_val is not None and val < min_val:
        logger.warning("AI Overview: %s=%d below minimum %d, clamping", name, val, min_val)
        val = min_val
    if max_val is not None and val > max_val:
        logger.warning("AI Overview: %s=%d above maximum %d, clamping", name, val, max_val)
        val = max_val
    return val


def _parse_float(name: str, raw: str, default: float, min_val: float = 0.0, max_val: float = 2.0) -> float:
    try:
        val = float(raw)
    except (ValueError, TypeError):
        logger.warning("AI Overview: Invalid %s value '%s', using default %.1f", name, raw, default)
        return default
    if val < min_val or val > max_val:
        logger.warning("AI Overview: %s=%.2f out of range [%.1f, %.1f], clamping", name, val, min_val, max_val)
        val = max(min_val, min(max_val, val))
    return val


@dataclass
class Config:
    """Plugin configuration loaded from environment variables."""

    ollama_base_url: str = "http://localhost:11434"
    chat_model: str = "llama3.2"
    embed_model: str = "nomic-embed-text"
    max_tokens: int = 2048
    temperature: float = 0.2
    context_deep_count: int = 10
    context_shallow_count: int = 10
    allowed_tabs: list[str] = field(default_factory=lambda: ["general", "science", "it", "news"])
    rate_limit_rpm: int = 10
    reranking_enabled: bool = True
    interactive: bool = True
    question_mark_required: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables with validation."""
        return cls(
            ollama_base_url=os.getenv("OLLAMA_URL", "http://localhost:11434").strip().rstrip("/"),
            chat_model=os.getenv("OLLAMA_CHAT_MODEL", "llama3.2").strip(),
            embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text").strip(),
            max_tokens=_parse_int("AI_MAX_TOKENS", os.getenv("AI_MAX_TOKENS", "2048"), 2048, min_val=100, max_val=8192),
            temperature=_parse_float("AI_TEMPERATURE", os.getenv("AI_TEMPERATURE", "0.2"), 0.2),
            context_deep_count=_parse_int("AI_CONTEXT_DEEP", os.getenv("AI_CONTEXT_DEEP", "10"), 10, min_val=0, max_val=20),
            context_shallow_count=_parse_int("AI_CONTEXT_SHALLOW", os.getenv("AI_CONTEXT_SHALLOW", "10"), 10, min_val=0, max_val=30),
            allowed_tabs=[t.strip() for t in os.getenv("AI_TABS", "general,science,it,news").split(",") if t.strip()],
            rate_limit_rpm=_parse_int("AI_RATE_LIMIT", os.getenv("AI_RATE_LIMIT", "10"), 10, min_val=1, max_val=120),
            reranking_enabled=_parse_bool(os.getenv("AI_RERANKING", "false")),
            interactive=_parse_bool(os.getenv("AI_INTERACTIVE", "true")),
            question_mark_required=_parse_bool(os.getenv("AI_QUESTION_MARK_ONLY", "false")),
        )
