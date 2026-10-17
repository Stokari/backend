# Stokari Backend

The backend REST API for **Stokari**, an inventory and user management system, built with Python 3.14, Django 6.1, and Django REST Framework.

---

## Tech Stack

- **Runtime & Language:** [Python 3.14](https://www.python.org/)
- **Package & Environment Manager:** [uv](https://docs.astral.sh/uv/)
- **Web Framework:** [Django 6.1](https://docs.djangoproject.com/en/6.1/)
- **API Toolkit:** [Django REST Framework (DRF)](https://www.django-rest-framework.org/)
- **API Documentation:** [drf-spectacular](https://drf-spectacular.readthedocs.io/) (OpenAPI 3.0, Swagger UI, ReDoc)
- **Database:** [PostgreSQL](https://www.postgresql.org/) with [psycopg3](https://www.psycopg.org/psycopg3/)
- **Code Quality & Linter:** [Ruff](https://docs.astral.sh/ruff/) and [pre-commit](https://pre-commit.com/)
- **CI/CD:** GitHub Actions

---

## Getting Started

### Prerequisites

- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (recommended version >= 0.4.0)
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **PostgreSQL** running locally or via Docker:
  ```bash
  docker run --name stokari-postgres -e POSTGRES_DB=stokari -e POSTGRES_USER=stokari_user -e POSTGRES_PASSWORD=secret -p 5432:5432 -d postgres:16
  ```

---

### Quick Setup (Automated)

Run the automated developer setup script:

```bash
./scripts/setup-dev.sh
```

This script automatically:
1. Verifies `uv` is installed.
2. Configures Git hooks (`git config core.hooksPath .githooks`).
3. Creates `.env` from `.env.example` (if missing).
4. Installs locked dependencies via `uv sync --locked`.
5. Runs Django system checks.

---

### Manual Setup

1. **Clone the repository and enter the directory:**
   ```bash
   git clone git@github.com:Stokari/backend.git
   cd backend
   ```

2. **Configure Git hooks:**
   ```bash
   git config core.hooksPath .githooks
   chmod +x .githooks/* scripts/*.sh
   ```

3. **Install locked dependencies:**
   ```bash
   uv sync --locked
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to match your local database credentials:
   ```dotenv
   SECRET_KEY=your-local-secret-key
   DEBUG=True
   DATABASE_URL=postgresql://stokari_user:secret@localhost:5432/stokari
   ALLOWED_HOSTS=localhost,127.0.0.1
   CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```

5. **Run database migrations:**
   ```bash
   uv run python manage.py migrate
   ```

6. **Create a superuser:**
   ```bash
   uv run python manage.py createsuperuser
   ```

7. **Start the development server:**
   ```bash
   uv run python manage.py runserver
   ```
   The API server will run at `http://127.0.0.1:8000/`.

---

## API Documentation

Once the server is running, interactive API documentation is available at:

- **Swagger UI:** [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **ReDoc:** [http://127.0.0.1:8000/api/redoc/](http://127.0.0.1:8000/api/redoc/)
- **OpenAPI 3.0 Schema (YAML/JSON):** [http://127.0.0.1:8000/api/schema/](http://127.0.0.1:8000/api/schema/)

---

## Quality & Testing

Run code quality and test commands before committing:

```bash
# Lint with Ruff
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Check code formatting
uv run ruff format --check .

# Format code
uv run ruff format .

# Django system checks
uv run python manage.py check

# Check for missing migrations
uv run python manage.py makemigrations --check --dry-run

# Run test suite
uv run python manage.py test
```

---

## Git & Contribution Workflow

### Branch Strategy

- **`main`**: Production-ready code. Direct pushes are disabled.
- **`dev`**: Active integration branch.
- **Working branches**: Must branch from `dev` and merge back into `dev` via Pull Request.

### Branch Naming Conventions

Branches must adhere to the pattern:
`<type>/<short-description-in-kebab-case>`

Allowed types:
- `feat/`, `feature/`: New features
- `fix/`, `bugfix/`: Bug fixes
- `chore/`: Tooling, dependencies, or configuration changes
- `refactor/`: Code changes without functional differences
- `docs/`: Documentation updates
- `test/`: Adding or updating tests

*Exceptions: `main` and `dev`.*

### Commit Message Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) standard:
```text
<type>(<optional scope>): <description>
```
Examples:
- `feat(inventory): add low stock alert threshold`
- `fix(auth): handle expired token error gracefully`
- `chore(deps): update python dependencies`

### Git Hooks Summary

- **`pre-commit`**: Formats and lints staged Python files, runs Django system and migration checks.
- **`commit-msg`**: Validates that commit messages follow Conventional Commits.
- **`pre-push`**: Enforces branch naming rules before pushing to remote.
- **`post-merge`**: Automatically syncs dependencies (`uv sync --locked`) on `git pull` or `git merge`.
