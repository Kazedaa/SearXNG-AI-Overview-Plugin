# Setup Guide

This guide walks you through setting up SearXNG with the AI Overview plugin from scratch. If you've never used SearXNG or Ollama before, start here.

## Table of Contents

- [What You're Setting Up](#what-youre-setting-up)
- [Step 1: Install Docker](#step-1-install-docker)
- [Step 2: Install Ollama](#step-2-install-ollama)
- [Step 3: Pull AI Models](#step-3-pull-ai-models)
- [Step 4: Clone This Repository](#step-4-clone-this-repository)
- [Step 5: Configure SearXNG](#step-5-configure-searxng)
- [Step 6: Start Everything](#step-6-start-everything)
- [Step 7: Verify It Works](#step-7-verify-it-works)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)

---

## What You're Setting Up

```
┌─────────────────────────────────────────────┐
│              Your Machine                    │
│                                              │
│  ┌──────────────────┐   ┌────────────────┐  │
│  │   SearXNG         │   │    Ollama       │  │
│  │   (Docker)        │──▶│    (Native)     │  │
│  │                   │   │                 │  │
│  │  + AI Overview    │   │  gemma3:4b      │  │
│  │    Plugin         │   │  nomic-embed    │  │
│  └──────────────────┘   └────────────────┘  │
│         ▲                                    │
│         │ http://localhost:8888               │
│         │                                    │
│     Your Browser                             │
└─────────────────────────────────────────────┘
```

- **SearXNG** runs in a Docker container and serves the search UI
- **Ollama** runs natively on your machine and provides the AI models
- The **AI Overview Plugin** lives inside SearXNG and connects to Ollama

---

## Step 1: Install Docker

Docker runs SearXNG in an isolated container so you don't need to install Python, Flask, or any SearXNG dependencies on your system.

### Linux (Ubuntu/Debian)

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add your user to the docker group (so you don't need sudo)
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
docker compose version
```

### macOS

Download and install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/).

### Windows

Download and install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/). Make sure WSL 2 backend is enabled.

---

## Step 2: Install Ollama

Ollama runs AI models locally on your machine. It manages model downloads and provides a local API.

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### macOS / Windows

Download from [ollama.com](https://ollama.com) and run the installer.

### Verify

```bash
ollama --version
# Should print something like: ollama version 0.x.x
```

---

## Step 3: Pull AI Models

You need at least the **chat model**. The embedding model is optional (used for re-ranking).

```bash
# Required — the main AI model (~2.5 GB download)
ollama pull gemma3:4b

# Optional — for semantic re-ranking (~340 MB download)
ollama pull nomic-embed-text
```

> **Model choices:** `gemma3:4b` is recommended for a good balance of speed and quality. Change the model via the `OLLAMA_CHAT_MODEL` environment variable.

---

## Step 4: Clone This Repository

```bash
git clone https://github.com/Kazedaa/SearXNG-AI-Overview-Plugin.git
cd SearXNG-AI-Overview-Plugin
```

---

## Step 5: Configure SearXNG

The plugin needs a SearXNG `settings.yml` file. Create the config directory and file:

```bash
mkdir -p searxng
```

Create `searxng/settings.yml` with this content:

```yaml
use_default_settings: true

server:
  secret_key: "generate-a-random-string-here"
  bind_address: "0.0.0.0"
  port: 8080

search:
  formats:
    - html
    - json

plugins:
  searx.plugins.ai_overview.SXNGPlugin:
    active: true
```

> **Important:** Replace `"generate-a-random-string-here"` with an actual random string. You can generate one with: `openssl rand -hex 32`

### Environment Variables (Optional)

Copy the example environment file and customize:

```bash
cp .env.example .env
# Edit .env to change models, context sizes, etc.
```

Or set variables directly in `docker-compose.yml` under `environment:`.

---

## Step 6: Start Everything

### Make sure Ollama is running

```bash
# On Linux, Ollama may already be running as a service. Check with:
ollama list

# If it's not running:
ollama serve &
```

### Start SearXNG

```bash
docker compose up -d
```

This downloads the SearXNG Docker image (first run only) and starts it.

---

## Step 7: Verify It Works

1. Open **http://localhost:8888** in your browser
2. Search for something informational, like: *"How does photosynthesis work?"*
3. You should see an **✨ AI Overview** box above the search results
4. The answer should stream in with `[1]`, `[2]` citation links

### What to expect

- First search may be slow (model loading into memory)
- Subsequent searches should be faster (model stays loaded)
- Navigational queries like `youtube.com` will **not** show an AI overview (by design)

---

## Updating

To update to the latest version:

```bash
cd SearXNG-AI-Overview-Plugin
git pull
docker compose restart
```

---

## Troubleshooting

### "AI Overview doesn't appear"

1. **Check the plugin is enabled** in `searxng/settings.yml`:
   ```yaml
   plugins:
     searx.plugins.ai_overview.SXNGPlugin:
       active: true
   ```

2. **Check Docker logs** for errors:
   ```bash
   docker compose logs searxng | tail -50
   ```

3. **Check you're on the right tab** — AI Overview only activates on `general`, `science`, `it`, and `news` tabs by default.

4. **Try a question** — navigational queries like `youtube` are intentionally skipped. Try something like `"what is quantum computing?"`.

### "⚠️ Cannot reach Ollama"

The SearXNG container can't connect to Ollama on your host machine. This is the **most common issue on Linux**.

**Root cause:** Ollama defaults to listening on `127.0.0.1` (localhost only), which Docker containers cannot reach. It needs to listen on `0.0.0.0` (all interfaces).

**Fix (if Ollama is running as a regular process):**

```bash
# Stop the current Ollama process
pkill -f "ollama serve"

# Restart with OLLAMA_HOST set
OLLAMA_HOST=0.0.0.0:11434 ollama serve &

# To make this permanent, add to your ~/.bashrc or ~/.zshrc:
echo 'export OLLAMA_HOST=0.0.0.0:11434' >> ~/.bashrc
```

**Fix (if Ollama is a systemd service):**

```bash
# Create an override to set OLLAMA_HOST
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

# Reload and restart Ollama
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

> **Not sure which one you have?** Run `systemctl is-active ollama`. If it says "active", use the systemd fix. If it says "inactive" or "unknown", use the regular process fix.

**Verify the fix:**

```bash
# Ollama should now listen on 0.0.0.0
ss -tlnp | grep 11434
# Expected: LISTEN  0.0.0.0:11434

# Test from the Docker container
docker exec searxng wget -q -O- http://host.docker.internal:11434/api/tags
```

> **Note:** On macOS/Windows with Docker Desktop, `host.docker.internal` works out of the box. This fix is only needed on Linux.

### "⚠️ Request timed out"

The model is likely loading for the first time. This can take 10–30 seconds depending on your hardware. Try the search again.

If timeouts persist, check if your machine has enough RAM for the model:
- `gemma3:4b` needs ~3-4 GB RAM
- `qwen3:8b` needs ~5 GB RAM

### SearXNG container won't start

```bash
# Check logs
docker compose logs searxng

# Most common issue: settings.yml syntax error
# Validate your YAML: https://www.yamllint.com/
```

### How to change the AI model

Edit `docker-compose.yml`:
```yaml
environment:
  - OLLAMA_CHAT_MODEL=gemma3:4b  # or any model from ollama.com/library
```

Then pull the model and restart:
```bash
ollama pull gemma3:4b
docker compose restart
```
