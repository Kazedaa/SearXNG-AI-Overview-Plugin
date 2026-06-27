"""Flask routes for AI Overview streaming endpoint."""

import json
import logging

from flask import Response, abort, request

from .config import Config
from .ollama import stream_chat
from .prompt import build_prompt
from .security import validate_token, RateLimiter

logger = logging.getLogger(__name__)


def register_routes(app, config: Config, secret: str):
    """Register the /ai-stream route on the Flask app."""
    
    limiter = RateLimiter(rpm=config.rate_limit_rpm)

    @app.route("/ai-stream", methods=["POST"])
    def handle_ai_stream():
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if not limiter.check(ip):
            return Response("Rate limit exceeded", status=429)
            
        data = request.json or {}

        token = data.get("tk", "")
        query = data.get("q", "").strip()
        lang = data.get("lang", "all")
        context_text = data.get("context", "")
        prev_answer = (data.get("prev_answer") or "")[-4000:]

        # Validate token
        if not validate_token(token, query, secret):
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

    @app.route("/ai-followup", methods=["POST"])
    def handle_ai_followup():
        """Handle conversational follow-up queries."""
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if not limiter.check(ip):
            return Response("Rate limit exceeded", status=429)
            
        data = request.json or {}
        token = data.get("tk", "")
        # The follow-up query
        query = data.get("q", "").strip()
        orig_q = data.get("orig_q", query)
        lang = data.get("lang", "all")
        context_text = data.get("context", "")
        prev_answer = (data.get("prev_answer") or "")[-4000:]

        if not validate_token(token, orig_q, secret):
            abort(403)

        if not query:
            return Response("Missing query", status=400)

        # Build prompt using the history
        messages = build_prompt(
            query=query,
            context=context_text,
            config=config,
            lang=lang,
            prev_answer=prev_answer if prev_answer else None,
        )

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

    return True
