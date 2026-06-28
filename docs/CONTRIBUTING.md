# Contributing

Thanks for your interest in contributing! This document covers how to set up a development environment and the conventions we follow.

## Development Setup

### Prerequisites
- Python 3.11+
- Ollama running locally with `gemma3:4b` pulled
- Docker (for integration testing)

### Clone and Install

```bash
git clone https://github.com/Kazedaa/SearXNG-AI-Overview-Plugin.git
cd SearXNG-AI-Overview-Plugin
pip install -r requirements.txt
```

### Project Structure

```
src/                  # The plugin package — this gets mounted into SearXNG
├── __init__.py       # Plugin class (SXNGPlugin)
├── config.py         # Env var configuration
├── context.py        # Search result → LLM context
├── intent.py         # Query intent classification
├── ollama.py         # Ollama HTTP client
├── prompt.py         # Prompt assembly
├── reranker.py       # Semantic re-ranking
├── routes.py         # Flask endpoints
├── security.py       # HMAC tokens + rate limiting
├── store.py          # Server-side context caching
└── assets/           # Frontend (HTML/CSS/JS)
```

## Code Conventions

### Python
- Python 3.11+ type hints (use `list[str]` not `List[str]`)
- Docstrings on all public functions (Google style)
- `logging` module for all debug/error output — never `print()`
- Zero external dependencies in `src/` — stdlib only (except `markupsafe` and `flask` which come from SearXNG)

### JavaScript
- No build tools, no bundler — vanilla JS only
- All DOM manipulation via safe APIs (`textContent`, `createElement`) — never raw `innerHTML` with user data
- Feature detection, no browser-specific hacks

### CSS
- Use SearXNG CSS variables (`--color-result-link`, `--color-base-font`, etc.) for theme compatibility
- No hard-coded colors except for the error state
- Mobile-responsive by default

## Testing Changes

### Quick Test with Docker

The fastest way to test changes:

```bash
# Start SearXNG with the plugin mounted
docker compose up -d

# Watch logs
docker compose logs -f searxng

# After making changes to src/, restart:
docker compose restart searxng
```

### Running Tests

```bash
PYTHONPATH=. pytest tests/ -v
```

## Adding a New Feature

1. **Open an issue** describing what you want to add and why
2. **Fork the repo** and create a feature branch
3. **Make changes** in `src/` following the conventions above
4. **Test** with Docker Compose
5. **Submit a PR** with a clear description

### Common Extension Points

- **Add a new LLM provider:** Modify `ollama.py` or create a new client module
- **Change the prompt:** Edit `prompt.py` — the rules list is easy to modify
- **Add a new UI feature:** Edit `assets/overview.js` and `assets/overview.css`
- **Change intent classification:** Edit `intent.py` — add patterns to the regex lists
- **Add config options:** Add a field to `Config` in `config.py` and wire it into `from_env()`

## Commit Messages

Use clear, descriptive commit messages:
- `fix: prevent XSS in source card rendering`
- `feat: add copy-to-clipboard button`
- `docs: update setup guide for Docker`
- `refactor: extract markdown parser into separate function`
