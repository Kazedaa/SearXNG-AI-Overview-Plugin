"""AI Overview — SearXNG Plugin

Adds a streaming AI-generated answer above search results using a local Ollama instance.
"""

import hashlib
import json
import logging
import pathlib

from markupsafe import Markup

from .config import Config
from .context import assemble_context, parse_results
from .intent import classify
from .reranker import rerank
from .routes import register_routes
from .security import generate_token
from .store import context_store

from searx.plugins import Plugin, PluginInfo
from searx.result_types import EngineResults
from searx import settings
from flask_babel import gettext

logger = logging.getLogger(__name__)

ASSETS_DIR = pathlib.Path(__file__).parent / "assets"


def _safe_json(value) -> str:
    """JSON-encode a value with XSS-safe escaping for inline <script> tags."""
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class SXNGPlugin(Plugin):
    id = "ai_overview"

    def __init__(self, plg_cfg=None):
        if plg_cfg is not None:
            super().__init__(plg_cfg)

        if PluginInfo is not None:
            self.info = PluginInfo(
                id=self.id,
                name=gettext("AI Overview Plugin"),
                description=gettext("Streaming AI search answers using a local Ollama instance."),
                preference_section="general",
            )

        # Load config
        self.config = Config.from_env()

        # Derive secret from SearXNG server secret
        server_secret = ""
        if isinstance(settings, dict):
            server_secret = settings.get("server", {}).get("secret_key", "")
        elif hasattr(settings, "get"):
            server_secret = settings.get("server", {}).get("secret_key", "")
        self.secret = hashlib.sha256(f"ai_overview_{server_secret}".encode()).hexdigest()

        # Load assets from disk at init time
        self._css = (ASSETS_DIR / "overview.css").read_text()
        self._js = (ASSETS_DIR / "overview.js").read_text()
        self._html_template = (ASSETS_DIR / "overview.html").read_text()

        logger.info(
            "AI Overview: Loaded (model=%s, url=%s)",
            self.config.chat_model,
            self.config.ollama_base_url,
        )

    def init(self, app):
        """Register Flask routes."""
        register_routes(app, self.config, self.secret)
        return True

    def post_search(self, request, search):
        """Inject AI overview HTML into search results."""
        results = EngineResults()

        try:
            # Gate checks
            if request and request.form.get("format", "html") != "html":
                return results

            if self.config.question_mark_required and "?" not in search.search_query.query:
                return results

            current_tabs = set(search.search_query.categories) or {"general"}
            allowed = set(self.config.allowed_tabs)

            if search.search_query.pageno > 1 or not allowed.intersection(current_tabs):
                return results

            # Intent classification — skip AI for navigational queries
            query = search.search_query.query.strip()
            if classify(query) == "navigational":
                logger.debug("AI Overview: Skipping navigational query '%s'", query)
                return results

            # Parse results
            raw_results = search.result_container.get_ordered_results()
            raw_infoboxes = getattr(search.result_container, "infoboxes", [])
            raw_answers = getattr(search.result_container, "answers", set())

            parsed = parse_results(raw_results, raw_infoboxes, raw_answers)

            # Fast path check — if we already have a great answer, skip the AI
            fast_answer = ""
            for r in parsed:
                if r["type"] == "answer":
                    fast_answer = r["content"]
                    break
                elif r["type"] == "infobox" and r.get("content"):
                    fast_answer = f"**{r['title']}**\n\n{r['content']}"
                    break

            # Semantic re-ranking (only if we don't have a fast answer and it's enabled)
            if self.config.reranking_enabled and not fast_answer:
                top_k = self.config.context_deep_count + self.config.context_shallow_count
                parsed = rerank(query, parsed, self.config, top_k)

            context_str, urls = assemble_context(parsed, self.config)

            # Generate token
            lang = search.search_query.lang
            token = generate_token(query, self.secret)

            # Store the full search context server-side so we don't leak it in the HTML source
            context_store.put(token, context_str, urls)

            # Build JS config object — context is now stored securely on the server
            js_config = {
                "query": query,
                "lang": lang,
                "urls": urls,
                "token": token,
                "fastAnswer": fast_answer,
                "scriptRoot": (request.script_root if request else "").rstrip("/"),
            }

            # Substitute config into JS
            js_code = self._js.replace("__AI_CONFIG__", _safe_json(js_config))

            # Build final HTML
            html = self._html_template.format(css=self._css, js=js_code)

            search.result_container.answers.add(
                results.types.Answer(answer=Markup(html))
            )

        except Exception as e:
            logger.error("AI Overview: %s", e, exc_info=True)

        return results
