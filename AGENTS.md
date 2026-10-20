# Stokari Backend Engineering Rules

This repository contains the backend REST API for Stokari, built with Python 3.14, Django 6.1, Django REST Framework (DRF), PostgreSQL, and `uv`.

All agents and contributors must follow these instructions and engineering standards.

---

## 1. Toolchain & Environment

- **Environment & Dependency Manager:** `uv`
- **Install locked dependencies:** `uv sync --locked`
- **Linting & Formatting:** `ruff`
- **Development Server:** `uv run python manage.py runserver`

Never use `pip`, `poetry`, or bare `python` commands directly. Always prefix commands with `uv run`.

---

## 2. Review & Quality Verification Checklist

Before considering any backend change complete, you MUST execute:

```bash
# 1. Check code formatting and linting
uv run ruff check .
uv run ruff format --check .

# 2. Django system checks
uv run python manage.py check

# 3. Verify no missing migrations (verification only)
uv run python manage.py makemigrations --check --dry-run

# 4. Run test suite
uv run python manage.py test
```

Never claim checks passed without actually running them.

> [!WARNING]
> `makemigrations --check --dry-run` is a verification gate. Do NOT automatically run `migrate` against an unspecified or shared database without explicit user instructions. Require review before executing destructive database operations.

---

## 3. Git Workflow & Conventions

### Branch Strategy
- `main`: Production branch. Direct pushes are disabled.
- `dev`: Active integration branch.
- Feature branches branch from `dev` and merge back into `dev` via Pull Request.

### Branch Naming Conventions
Branch names must match: `<type>/<short-description-in-kebab-case>`
Allowed types: `feat/`, `feature/`, `fix/`, `bugfix/`, `chore/`, `refactor/`, `docs/`, `test/`.
*(Exceptions: `main` and `dev`)*

### Commit Message Conventions
Follow Conventional Commits: `<type>(<optional-scope>): <description>`
Examples:
- `feat(inventory): add low stock alert threshold`
- `fix(auth): handle expired token error gracefully`
- `chore(deps): update python dependencies`

---

## 4. Architectural Rules & Precedence

### Precedence Rule
When a general engineering skill, repository rule, domain skill, and existing code conflict:
1. **Explicit SRS/Domain requirements and approved architecture decisions govern.**
2. If an instruction conflicts with technical correctness, concurrency safety, or data integrity, the agent must **stop and explain the conflict** rather than silently choosing whichever instruction was read last.
3. Database constraints and transactional invariants take precedence over convenience abstractions.

### Core Architecture Standards
- **DRF Serializers:** Run `is_valid(raise_exception=True)` before `save()`. Distinguish `initial_data` from `validated_data`. No side-effecting mutations inside serializer validation.
- **Tenant Scoping:** Scope data to the authenticated user's store across all data-access paths: `get_queryset()` for viewsets, explicit store parameters for domain services.
- **Stock Ledger Invariant:** Any inventory mutation MUST generate an immutable `StockMovement` audit ledger entry within the same database transaction. Never mutate stock balances directly without a ledger record.
- **Transactions & Concurrency:** Multi-table mutations must run inside `transaction.atomic()`. Use `select_for_update().order_by('id')` with deterministic ordering when locking rows to mutate balances.
- **OpenAPI Documentation:** All public endpoints and custom view actions must include OpenAPI schemas via `drf-spectacular` (`@extend_schema`).

---

## 5. Custom Domain Skills

- Consult [.agents/skills/django-rest-framework-engineering/SKILL.md](.agents/skills/django-rest-framework-engineering/SKILL.md) for DRF patterns, serializer lifecycles, and query optimization.
- Consult [.agents/skills/stokari-backend-domain/SKILL.md](.agents/skills/stokari-backend-domain/SKILL.md) for inventory domain rules, race-safe idempotency, the movement ledger, and canonical sync contracts.
