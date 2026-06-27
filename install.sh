#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# SearXNG AI Overview Plugin — Installation Script
#
# This script sets up everything you need to run SearXNG with the AI Overview
# plugin on your local machine. It assumes you're starting from scratch.
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - Ollama installed (https://ollama.com)
#
# Usage:
#   chmod +x install.sh && ./install.sh
# ==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠️  $1${NC}"; }
error()   { echo -e "${RED}❌ $1${NC}"; exit 1; }

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     SearXNG AI Overview Plugin — Setup              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Check prerequisites ──────────────────────────────────────────────

info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Install it from https://docs.docker.com/get-docker/"
fi

# Check for Docker Compose (v2 plugin or standalone)
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    error "Docker Compose is not installed. Install it from https://docs.docker.com/compose/install/"
fi

success "Docker and Docker Compose found"

# ── Step 2: Check / Install Ollama ───────────────────────────────────────────

if command -v ollama &> /dev/null; then
    success "Ollama is already installed"
else
    warn "Ollama is not installed."
    echo ""
    read -rp "  Would you like to install Ollama now? [Y/n] " install_ollama
    if [[ "${install_ollama:-Y}" =~ ^[Yy]$ ]]; then
        info "Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        success "Ollama installed"
    else
        warn "Skipping Ollama installation."
        warn "You'll need Ollama running before using the plugin."
        echo "  Install manually: https://ollama.com"
    fi
fi

# ── Step 2b: Configure Ollama for Docker access (Linux) ─────────────────────

if command -v ollama &> /dev/null && [[ "$(uname)" == "Linux" ]]; then
    # Check if Ollama is listening on 127.0.0.1 only
    if ss -tlnp 2>/dev/null | grep ":11434" | grep -q "127.0.0.1"; then
        warn "Ollama is listening on 127.0.0.1 only — Docker containers can't reach it."
        echo ""
        echo "  To fix this, Ollama needs to listen on 0.0.0.0 (all interfaces)."
        read -rp "  Apply this fix now? [Y/n] " fix_ollama
        if [[ "${fix_ollama:-Y}" =~ ^[Yy]$ ]]; then
            if systemctl is-active ollama &> /dev/null; then
                # Ollama runs as a systemd service — create a persistent override
                info "Ollama is a systemd service. Creating persistent config..."
                sudo mkdir -p /etc/systemd/system/ollama.service.d
                sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null << 'OLLAMA_EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
OLLAMA_EOF
                sudo systemctl daemon-reload
                sudo systemctl restart ollama
                sleep 2
                success "Ollama is now listening on all interfaces (persistent)"
            else
                # Ollama runs as a user process — restart it with OLLAMA_HOST set
                info "Restarting Ollama with OLLAMA_HOST=0.0.0.0:11434..."
                pkill -f "ollama serve" 2>/dev/null || true
                sleep 1
                OLLAMA_HOST=0.0.0.0:11434 nohup ollama serve > /dev/null 2>&1 &
                sleep 2
                success "Ollama restarted on all interfaces"
                warn "This is a session-only fix. To make it permanent, add to your shell profile:"
                echo "    export OLLAMA_HOST=0.0.0.0:11434"
            fi
        else
            warn "Skipped. You may need to set OLLAMA_HOST=0.0.0.0:11434 manually."
            echo "  See docs/SETUP.md#troubleshooting for details."
        fi
    fi
fi

# ── Step 3: Pull required AI models ─────────────────────────────────────────

if command -v ollama &> /dev/null; then
    echo ""
    info "Pulling AI models (this may take a few minutes on first run)..."
    echo ""

    # Chat model
    if ollama list 2>/dev/null | grep -q "llama3.2"; then
        success "Chat model (llama3.2) already downloaded"
    else
        info "Downloading chat model: llama3.2 (~2.0 GB)..."
        ollama pull llama3.2 || warn "Failed to pull llama3.2. You can do this manually later."
    fi

    # Embedding model (optional, for re-ranking)
    if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
        success "Embedding model (nomic-embed-text) already downloaded"
    else
        info "Downloading embedding model: nomic-embed-text (~340 MB)..."
        echo "  (Optional — used for semantic re-ranking of search results)"
        ollama pull nomic-embed-text || warn "Failed to pull nomic-embed-text. Re-ranking will be disabled."
    fi
fi

# ── Step 4: Create SearXNG configuration ────────────────────────────────────

echo ""
info "Setting up SearXNG configuration..."

SEARXNG_DIR="./searxng"

mkdir -p "$SEARXNG_DIR"

if [ ! -f "$SEARXNG_DIR/settings.yml" ]; then
    info "Creating SearXNG settings.yml..."
    cat > "$SEARXNG_DIR/settings.yml" << 'SETTINGS_EOF'
# SearXNG Configuration
# Full reference: https://docs.searxng.org/admin/settings/index.html

use_default_settings: true

server:
  # Generate a unique secret key for your instance
  secret_key: "changeme-generate-a-real-secret"
  # Set to false if you want to restrict to localhost
  bind_address: "0.0.0.0"
  port: 8080

search:
  # Enable JSON format (needed for API access)
  formats:
    - html
    - json

# Enable the AI Overview plugin
plugins:
  searx.plugins.ai_overview.SXNGPlugin:
    active: true
SETTINGS_EOF

    # Generate a random secret key
    SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || head -c 64 /dev/urandom | od -An -tx1 | tr -d ' \n')
    sed -i "s/changeme-generate-a-real-secret/$SECRET_KEY/" "$SEARXNG_DIR/settings.yml"

    success "Created $SEARXNG_DIR/settings.yml with a unique secret key"
else
    success "$SEARXNG_DIR/settings.yml already exists"
    # Check if plugin is enabled
    if ! grep -q "ai_overview" "$SEARXNG_DIR/settings.yml"; then
        warn "The AI Overview plugin may not be enabled in your settings.yml"
        echo "  Add the following to your settings.yml under 'plugins:':"
        echo ""
        echo "  plugins:"
        echo "    searx.plugins.ai_overview.SXNGPlugin:"
        echo "      active: true"
        echo ""
    fi
fi

# ── Step 5: Start services ──────────────────────────────────────────────────

echo ""
info "Starting SearXNG with Docker Compose..."

# Make sure Ollama is running
if command -v ollama &> /dev/null; then
    if ! pgrep -x "ollama" > /dev/null 2>&1; then
        info "Starting Ollama service..."
        ollama serve &> /dev/null &
        sleep 2
        success "Ollama service started"
    else
        success "Ollama is already running"
    fi
fi

# Start Docker containers
$COMPOSE_CMD up -d

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     🎉 Setup Complete!                              ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  SearXNG is running at: http://localhost:8888        ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  Try searching for something like:                   ║${NC}"
echo -e "${GREEN}║    'How does photosynthesis work?'                   ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}║  To stop:   ${COMPOSE_CMD} down                     ║${NC}"
echo -e "${GREEN}║  To restart: ${COMPOSE_CMD} restart                  ║${NC}"
echo -e "${GREEN}║                                                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "For configuration options, see: docs/CONFIGURATION.md"
echo "For troubleshooting, see: docs/SETUP.md#troubleshooting"
echo ""
