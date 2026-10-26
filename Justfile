set shell := ["bash", "-cu"]

default:
    @just --list

# Lint and test
check: lint test

lint:
    uv run ruff check .

format:
    uv run ruff format .

test:
    uv run pytest -q

# Enable the git hooks that block credentials from commits and pushes
hooks:
    git config core.hooksPath .githooks

# Scan every tracked file for credentials and private files
secrets:
    python3 scripts/check_secrets.py --all

# --- gateway service (systemd user unit) ---
up:
    systemctl --user start museai.service

down:
    systemctl --user stop museai.service

restart:
    systemctl --user restart museai.service

status:
    systemctl --user status museai.service --no-pager

logs:
    journalctl --user -u museai.service -f

# Foreground run using ~/.config/museai/env
run:
    set -a && source ~/.config/museai/env && set +a && uv run --no-sync python -m museai

# Register the MCP bridge with Claude Code (user scope)
mcp-install:
    claude mcp remove --scope user museai 2>/dev/null || true
    claude mcp add --scope user museai -e MUSE2API_API_KEY=$${MUSE2API_API_KEY:-sk-museai-local-key} -- uv run {{justfile_directory()}}/scripts/muse_mcp.py
