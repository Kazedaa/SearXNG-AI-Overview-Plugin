"""Flask routes for AI Overview streaming endpoint."""

import logging

from flask import Response, abort, request

from .config import Config
from .ollama import stream_chat
from .prompt import build_prompt
from .security import validate_token, RateLimiter
from .store import context_store

logger = logging.getLogger(__name__)


def _handle_stream_request(config: Config, secret: str, limiter: RateLimiter, is_followup: bool):
    """Shared handler for /ai-stream and /ai-followup."""
    # Rate Limiting
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if not limiter.check(ip):
        return Response("Rate limit exceeded", status=429)

    data = request.json or {}
    token = data.get("tk", "")
    query = data.get("q", "").strip()[:500]  # Cap query length
    lang = data.get("lang", "all")
    prev_answer = (data.get("prev_answer") or "")[-4000:]

    if not token:
        abort(403)

    # Validate token
    token_query = data.get("orig_q", query)[:500] if is_followup else query
    if not validate_token(token, token_query, secret):
        abort(403)

    if not query:
        return Response("Missing query", status=400)

    # Retrieve context from server-side store
    store_entry = context_store.get(token)
    context_text = store_entry[0] if store_entry else ""

    # Build prompt
    messages = build_prompt(
        query=query,
        context=context_text,
        config=config,
        lang=lang,
        prev_answer=prev_answer if prev_answer else None,
    )

    # Stream response from Ollama
    def generate():
        for chunk in stream_chat(config, messages):
            yield chunk

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-store",
            "Connection": "keep-alive",
            "X-Content-Type-Options": "nosniff",
            "Access-Control-Allow-Origin": "*",
        },
    )


def register_routes(app, config: Config, secret: str):
    """Register the streaming routes on the Flask app."""
    limiter = RateLimiter(rpm=config.rate_limit_rpm)

    @app.route("/ai-stream", methods=["POST", "OPTIONS"])
    def handle_ai_stream():
        if request.method == "OPTIONS":
            return Response("", status=204, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type"})
        return _handle_stream_request(config, secret, limiter, is_followup=False)

    @app.route("/ai-followup", methods=["POST", "OPTIONS"])
    def handle_ai_followup():
        if request.method == "OPTIONS":
            return Response("", status=204, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type"})
        return _handle_stream_request(config, secret, limiter, is_followup=True)

    return True
