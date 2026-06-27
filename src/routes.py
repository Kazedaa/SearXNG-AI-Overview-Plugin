"""Flask routes for AI Overview streaming endpoint."""

import logging

from flask import Response, abort, request

from .config import Config
from .ollama import stream_chat
from .prompt import build_prompt
from .security import validate_token

logger = logging.getLogger(__name__)


def _handle_stream_request(config: Config, secret: str, is_followup: bool):
    """Shared handler for /ai-stream and /ai-followup."""
    data = request.json or {}

    token = data.get("tk", "")
    query = data.get("q", "").strip()
    lang = data.get("lang", "all")
    context_text = data.get("context", "")
    prev_answer = (data.get("prev_answer") or "")[-4000:]

    # For follow-ups, the token was generated using the original query
    token_query = data.get("orig_q", query) if is_followup else query

    # Validate token
    if not validate_token(token, token_query, secret):
        abort(403)

    if not query:
        return Response("Missing query", status=400)

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
        },
    )


def register_routes(app, config: Config, secret: str):
    """Register the streaming routes on the Flask app."""
    
    @app.route("/ai-stream", methods=["POST"])
    def handle_ai_stream():
        return _handle_stream_request(config, secret, is_followup=False)

    @app.route("/ai-followup", methods=["POST"])
    def handle_ai_followup():
        return _handle_stream_request(config, secret, is_followup=True)

    return True
