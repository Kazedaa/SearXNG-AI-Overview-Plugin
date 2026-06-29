# SearXNG AI Overview Plugin

![SearXNG AI Overview Plugin](assets/banner.png)

A fully local, AI Overview plugin for [SearXNG](https://github.com/searxng/searxng). Powered by [Ollama](https://ollama.com).

When you search, the plugin takes your search results, feeds them to a local LLM as context (RAG), and streams back a concise, well-cited AI-generated answer — right above your normal search results. No API keys. No cloud. Everything runs on your machine.

## ✨ Features

- **100% Local** — Zero API keys, zero cloud dependencies, zero data leaves your machine
- **RAG Architecture** — Uses your actual search results as grounded context to minimize hallucinations
- **Semantic Re-ranking** — Optionally re-ranks results by relevance using `nomic-embed-text` embeddings before feeding them to the LLM.
- **Smart Intent Detection** — Automatically skips AI for navigational queries (e.g., `youtube.com`) to save resources
- **Conversational Follow-ups** — Ask follow-up questions without leaving the search page
- **Streaming Markdown** — Real-time token-by-token rendering with inline citations `[1]`, `[2]` linking back to sources

## 🌐 Exposing to the Internet (Security)

This plugin has been **security-hardened** and is safe to use on internet-facing SearXNG instances. It implements several defensive layers to protect your GPU and data:

* **HMAC Token Validation:** The streaming endpoint is protected by cryptographically signed, short-lived tokens (5-minute expiry). This prevents attackers from directly querying your LLM backend.
* **Server-Side Context Caching:** Extracted web text is temporarily cached in the backend memory rather than embedded in the HTML page source, preventing search context leakage to scrapers.
* **IP-Based Rate Limiting:** A sliding-window rate limiter prevents Denial of Service (DoS) attacks from hogging your GPU resources.
* **Prompt Injection Mitigations:** The system prompt aggressively instructs the LLM to ignore override attempts or prompt-leaking queries.
* **Payload Constraints:** Strict truncation limits on queries prevent resource exhaustion attacks via massive payloads.

**Caveats & Requirements for Public Hosting:**
1. **Rotate Your Secret Key:** You MUST change the default `secret_key` in your `searxng/settings.yml` to a secure random string (e.g., `openssl rand -hex 32`).
2. **Protect Ollama:** Do not expose Ollama's port (11434) to the internet. Only SearXNG (port 8080) should be public.
3. **Hardware Limits:** Local LLMs process requests sequentially by default. If multiple users search simultaneously, Ollama will queue the requests, which can increase latency. For high-traffic servers, you will need multiple GPUs and Ollama concurrency configured.

## Quick Start

### Prerequisites

| Requirement | Why |
|---|---|
| [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/install/) | Runs SearXNG in a container |
| [Ollama](https://ollama.com) | Runs the AI models locally |

### One-Command Setup

```bash
git clone https://github.com/Kazedaa/SearXNG-AI-Overview-Plugin.git
cd SearXNG-AI-Overview-Plugin
chmod +x install.sh && ./install.sh
```

The install script will:
1. Check that Docker and Ollama are installed
2. Pull the required AI models (`gemma3:4b` + `nomic-embed-text`)
3. Generate a SearXNG configuration with the plugin enabled
4. Start everything with Docker Compose

Once complete, open **http://localhost:8888** and try a search like *"How does photosynthesis work?"*

### Manual Setup

If you prefer to set things up yourself, see [docs/SETUP.md](docs/SETUP.md) for a detailed step-by-step guide.

## ⚙️ Configuration

The plugin is configured entirely through environment variables. Set them in your `docker-compose.yml` or a `.env` file.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_CHAT_MODEL` | `gemma3:4b` | LLM for generating answers |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model for re-ranking |
| `AI_MAX_TOKENS` | `2048` | Max response length |
| `AI_TEMPERATURE` | `0.2` | Generation temperature (lower = more accurate) |
| `AI_CONTEXT_DEEP` | `10` | Results with full text as context |
| `AI_CONTEXT_SHALLOW` | `10` | Additional results as headlines |
| `AI_RERANKING` | `false` | Enable semantic re-ranking |
| `AI_RATE_LIMIT` | `10` | Max requests/minute per IP |

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for the full reference with all options.

## 📁 Project Structure

```
├── src/                    # Plugin package (mounted into SearXNG container)
│   ├── __init__.py         # SXNGPlugin class — orchestrates everything
│   ├── config.py           # Environment variable parsing + validation
│   ├── ollama.py           # Ollama HTTP client (streaming chat + embeddings)
│   ├── context.py          # Search results → structured LLM context
│   ├── reranker.py         # Cosine similarity re-ranking via embeddings
│   ├── intent.py           # Query intent classification (skip navigational)
│   ├── prompt.py           # System prompt + prompt assembly
│   ├── security.py         # HMAC token generation + rate limiting
│   ├── store.py            # Server-side context caching (prevents HTML leaks)
│   ├── routes.py           # Flask routes: /ai-stream, /ai-followup
│   └── assets/
│       ├── overview.html   # HTML template injected into SearXNG
│       ├── overview.css    # Styles (uses SearXNG CSS variables)
│       └── overview.js     # Client-side streaming + markdown rendering
├── docs/                   # Detailed documentation
│   ├── SETUP.md            # Full setup guide for beginners
│   ├── ARCHITECTURE.md     # Code walkthrough for developers
│   ├── CONTRIBUTING.md     # Contribution guidelines
│   └── CONFIGURATION.md    # Full config reference
├── docker-compose.yml      # Production Docker setup
├── install.sh              # Automated installation script
├── .env.example            # All environment variables documented
└── requirements.txt        # Python dependencies (for development)
```

## 🛠️ Development

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for how to set up a development environment and contribute.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a module-by-module code walkthrough.

If you find this project useful please consider giving it a 🌟. It helps a LOT.

Thank You XD