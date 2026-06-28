"""Server-side context store for AI Overview.

Keeps search context server-side so it never appears in the HTML page source.
Entries auto-expire after a configurable TTL.
"""

import threading
import time


class ContextStore:
    """Thread-safe, TTL-based in-memory store for search context.

    Used to keep the assembled LLM context entirely on the server,
    preventing information leakage via page source inspection.
    """

    def __init__(self, ttl: int = 300, max_entries: int = 500):
        self.ttl = ttl
        self.max_entries = max_entries
        self._store: dict[str, tuple[str, list[str], float]] = {}
        self._lock = threading.Lock()

    def put(self, key: str, context: str, urls: list[str]) -> None:
        """Store context and URLs under the given key (typically the HMAC token)."""
        now = time.time()
        with self._lock:
            self._store[key] = (context, urls, now)
            # Periodic cleanup to prevent unbounded memory growth
            if len(self._store) > self.max_entries:
                cutoff = now - self.ttl
                self._store = {
                    k: v for k, v in self._store.items() if v[2] > cutoff
                }

    def get(self, key: str) -> tuple[str, list[str]] | None:
        """Retrieve context and URLs by key. Returns None if expired or missing."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            context, urls, ts = entry
            if time.time() - ts > self.ttl:
                del self._store[key]
                return None
            return context, urls


# Module-level singleton — shared between __init__.py and routes.py
context_store = ContextStore()
