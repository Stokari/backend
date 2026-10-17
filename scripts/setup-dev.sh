#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

echo "=== Stokari Backend Developer Setup ==="

# 1. Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: 'uv' is not installed." >&2
    echo "Install uv via: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

# 2. Configure Git hooks
echo "Configuring Git hooks directory to .githooks..."
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh 2>/dev/null || true

# 3. Create .env from .env.example if missing
if [[ ! -f ".env" ]]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "NOTE: Review .env and set your local DATABASE_URL and SECRET_KEY."
else
    echo ".env file already exists."
fi

# 4. Synchronize dependencies
echo "Installing locked Python dependencies with uv..."
uv sync --locked

# 5. Run Django system check
echo "Running Django system check..."
uv run python manage.py check

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. Start PostgreSQL (e.g. via Docker or system service)"
echo "  2. Run migrations:  uv run python manage.py migrate"
echo "  3. Start dev server: uv run python manage.py runserver"
echo "  4. View API docs:   http://localhost:8000/api/docs/"
