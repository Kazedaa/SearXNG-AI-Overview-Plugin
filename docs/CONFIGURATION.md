# Configuration Reference

The plugin is configured entirely through environment variables. No config files to edit inside the plugin.

Set these in your `docker-compose.yml` under `environment:`, or in a `.env` file.

## Ollama Connection

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API base URL. Use `http://host.docker.internal:11434` when running SearXNG in Docker with Ollama on the host. |
| `OLLAMA_CHAT_MODEL` | `llama3.2` | The LLM model for generating AI overviews. Must be pulled in Ollama first. |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model for semantic re-ranking. Only used when `AI_RERANKING=true`. |

### Model Recommendations

| Model | Size | Speed | Quality | Use Case |
|---|---|---|---|---|
| `qwen3:1.7b` | ~1 GB | Fast | Good | Weak hardware, quick answers |
| `llama3.2` | ~2.5 GB | Medium | Great | **Recommended default** |
| `qwen3:8b` | ~5 GB | Slower | Excellent | Powerful GPU, best quality |
| `llama3.2` | ~2 GB | Medium | Great | Alternative to Qwen |
| `mistral` | ~4 GB | Medium | Great | Another solid alternative |

## Generation Settings

| Variable | Default | Range | Description |
|---|---|---|---|
| `AI_MAX_TOKENS` | `2048` | 100–8192 | Maximum number of tokens in the AI response. Higher = longer answers but slower. |
| `AI_TEMPERATURE` | `0.2` | 0.0–2.0 | Controls randomness. `0.0` = deterministic, `0.2` = focused (recommended), `1.0` = creative. |

## Context Window

These control how much search result data the AI sees.

| Variable | Default | Range | Description |
|---|---|---|---|
| `AI_CONTEXT_DEEP` | `10` | 0–20 | Number of top results included with **full text**. More = better grounding but slower/more tokens. |
| `AI_CONTEXT_SHALLOW` | `10` | 0–30 | Additional results included as **headlines only**. Gives broader awareness cheaply. |

**Examples:**

```bash
# Minimal context (fastest, lowest quality)
AI_CONTEXT_DEEP=2
AI_CONTEXT_SHALLOW=3

# Default (good balance)
AI_CONTEXT_DEEP=5
AI_CONTEXT_SHALLOW=10

# Maximum context (slowest, highest quality)
AI_CONTEXT_DEEP=10
AI_CONTEXT_SHALLOW=20
```

## Behavior

| Variable | Default | Description |
|---|---|---|
| `AI_TABS` | `general,science,it,news` | Comma-separated SearXNG tabs where AI Overview is active. Set to `general` to only show on the main tab. |
| `AI_RATE_LIMIT` | `10` | Max requests per minute per IP address (1–120). |
| `AI_RERANKING` | `false` | Enable semantic re-ranking using embeddings. Requires `nomic-embed-text` model. Adds ~1-2s latency but improves answer relevance. |
| `AI_INTERACTIVE` | `true` | Enable follow-up questions, copy button, and regenerate button. |
| `AI_QUESTION_MARK_ONLY` | `false` | Only show AI overview for queries containing `?`. Reduces unnecessary AI calls. |

## Docker Compose Example

```yaml
services:
  searxng:
    image: docker.io/searxng/searxng:latest
    container_name: searxng
    restart: unless-stopped
    ports:
      - "8888:8080"
    volumes:
      - ./searxng:/etc/searxng:rw
      - ./src:/usr/local/searxng/searx/plugins/ai_overview:ro
    environment:
      - OLLAMA_URL=http://host.docker.internal:11434
      - OLLAMA_CHAT_MODEL=llama3.2
      - OLLAMA_EMBED_MODEL=nomic-embed-text
      - AI_CONTEXT_DEEP=10
      - AI_CONTEXT_SHALLOW=10
      - AI_RERANKING=false
    extra_hosts:
      - "host.docker.internal:host-gateway"
```
