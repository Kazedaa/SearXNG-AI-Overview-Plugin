# Architecture

A module-by-module walkthrough of how the AI Overview plugin works.

## High-Level Flow

1. User searches in SearXNG → SearXNG fetches results from engines
2. `post_search()` is called → classify intent → parse results → optionally re-rank → assemble context → inject HTML
3. Injected JS calls `/ai-stream` → validate token → build prompt → stream from Ollama → render markdown

## How SearXNG Plugins Work

Plugins are Python packages in `searx/plugins/` with a class inheriting from `Plugin`. They define:
- `__init__(plg_cfg)` — Load config, read assets
- `init(app)` — Register Flask routes
- `post_search(request, search)` — Inject answers via `search.result_container.answers.add()`

Enabled in `settings.yml` under `plugins:`.

## Module Reference

### `__init__.py` — Plugin Entry Point
Thin orchestrator. Reads assets at init (not per-request). Runs the pipeline: classify → parse → rerank → assemble → inject HTML.

### `config.py` — Configuration  
`@dataclass` with `from_env()`. Parses env vars with type coercion and range clamping.

### `context.py` — Result Parsing
- `parse_results()` — Normalizes MainResult and LegacyResult types into uniform dicts
- `assemble_context()` — Builds structured text: KNOWLEDGE GRAPH → DEEP SOURCES → SHALLOW SOURCES

### `intent.py` — Query Classification
Returns `navigational` (skip AI), `informational` (use AI), or `ambiguous` (use AI).

### `reranker.py` — Semantic Re-ranking
Embeds query + results via Ollama, computes cosine similarity, sorts by relevance. Pure Python (no numpy).

### `prompt.py` — Prompt Assembly
Builds messages list with system prompt (role, date, language) and user prompt with XML sections.

### `ollama.py` — Ollama Client
Uses `http.client` (stdlib). `stream_chat()` yields tokens from NDJSON. `get_embeddings()` returns vectors. User-friendly error messages.

### `security.py` — Token & Rate Limiting
HMAC tokens: `{timestamp}.{hmac}` covering `{ts}:{query}`. Rate limiter: sliding 60s window per IP.

### `routes.py` — Flask Endpoints
- `POST /ai-stream` — Main streaming endpoint
- `POST /ai-followup` — Follow-up conversations

### `assets/` — Frontend
- `overview.html` — HTML shell with skeleton, answer area, source cards, follow-up form
- `overview.css` — Uses SearXNG CSS variables for theme integration
- `overview.js` — Streaming, markdown rendering, citations, source cards, follow-ups

## Data Flow

```
Query → intent.classify() → parse_results() → rerank() → assemble_context()
      → generate_token() → inject HTML+JS
      
Browser JS → POST /ai-stream → validate_token() → build_prompt()
           → stream_chat() → render markdown + citations
```
