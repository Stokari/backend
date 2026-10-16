#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

if [[ ! -f "uv.lock" || ! -f "pyproject.toml" ]]; then
    exit 0
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is not installed. Install uv, then run: uv sync --locked" >&2
    exit 1
fi

echo "Synchronizing project dependencies with uv.lock..."
uv sync --locked
echo "Dependencies are synchronized."
