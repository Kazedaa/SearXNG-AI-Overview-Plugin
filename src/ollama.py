"""Ollama client: streaming chat and embeddings via http.client (zero external dependencies)."""

import http.client
import json
import logging
import ssl
from typing import Generator
from urllib.parse import urlparse

from .config import Config

logger = logging.getLogger(__name__)

STREAM_TIMEOUT_SEC = 60


def _get_connection(url: str, timeout: int = STREAM_TIMEOUT_SEC):
    """Create an HTTP(S) connection from a full URL and return (connection, path)."""
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path + ("?" + parsed.query if parsed.query else "")

    if parsed.scheme == "https":
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ctx)
    else:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)

    return conn, path


def stream_chat(config: Config, messages: list[dict]) -> Generator[str, None, None]:
    """Stream chat completion tokens from Ollama.

    POST to {base_url}/api/chat with stream: true.
    Parses NDJSON lines and yields content tokens.
    Handles <think>...</think> reasoning blocks transparently.
    """
    url = f"{config.ollama_base_url}/api/chat"
    conn = None

    try:
        conn, path = _get_connection(url)
        payload = json.dumps({
            "model": config.chat_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "num_ctx": 8192,
            },
        })
        headers = {"Content-Type": "application/json"}
        conn.request("POST", path, body=payload.encode("utf-8"), headers=headers)
        res = conn.getresponse()

        if res.status != 200:
            body = res.read(2048).decode("utf-8", errors="replace")[:500]
            logger.error("AI Overview: Ollama chat API %d: %s", res.status, body)
            yield "\n⚠️ Could not connect to the AI model. Is Ollama running?\n"
            return

        # Read NDJSON line by line
        in_thinking_state = False
        while True:
            line_bytes = res.readline()
            if not line_bytes:
                break

            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Ollama native API format: {"message": {"content": "token", "thinking": "token"}, "done": false}
            message = obj.get("message")
            if isinstance(message, dict):
                content = message.get("content", "")
                thinking = message.get("thinking", "")

                if thinking:
                    if not in_thinking_state:
                        yield "<think>\n"
                        in_thinking_state = True
                    yield thinking

                if content:
                    if in_thinking_state:
                        yield "\n</think>\n\n"
                        in_thinking_state = False
                    yield content

            if obj.get("done", False):
                if in_thinking_state:
                    yield "\n</think>\n\n"
                break

    except ConnectionRefusedError:
        logger.error("AI Overview: Ollama connection refused at %s", config.ollama_base_url)
        yield "\n⚠️ Cannot reach Ollama. Make sure it's running.\n"
    except TimeoutError:
        logger.error("AI Overview: Ollama request timed out")
        yield "\n⚠️ Request timed out. The model may be loading.\n"
    except Exception as e:
        logger.error("AI Overview: Ollama stream error: %s", e)
        yield "\n⚠️ An error occurred while generating the response.\n"
    finally:
        if conn:
            conn.close()


def get_embeddings(config: Config, texts: list[str]) -> list[list[float]]:
    """Get embeddings for a list of texts from Ollama.

    POST to {base_url}/api/embed with input: [texts].
    Returns list of embedding vectors, or empty list on failure.
    """
    url = f"{config.ollama_base_url}/api/embed"
    conn = None

    try:
        conn, path = _get_connection(url, timeout=30)
        payload = json.dumps({
            "model": config.embed_model,
            "input": texts,
        })
        headers = {"Content-Type": "application/json"}
        conn.request("POST", path, body=payload.encode("utf-8"), headers=headers)
        res = conn.getresponse()

        if res.status != 200:
            body = res.read(2048).decode("utf-8", errors="replace")[:500]
            logger.error("AI Overview: Ollama embed API %d: %s", res.status, body)
            return []

        data = json.loads(res.read().decode("utf-8"))
        embeddings = data.get("embeddings", [])
        return embeddings

    except Exception as e:
        logger.error("AI Overview: Ollama embed error: %s", e)
        return []
    finally:
        if conn:
            conn.close()
