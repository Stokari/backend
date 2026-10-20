# VS-02 Task List: Contract-First Architecture & Kernel Primitives

## Phase 1: Backend Kernel & Persistence

- [x] **Task 2.1** `common/kernel` — Result, DomainError, Typed IDs, Clock, EventBus
  - Files: `backend/common/kernel/{types,result,errors,bus,clock}.py`
  - Test: `uv run python -m pytest backend/common/kernel/ -v`
  - Size: M (5 files)

- [x] **Task 2.2** `common/http` — RFC 9457, Request-ID, Throttles, StrictIntegerField, Pagination
  - Files: `backend/common/http/{errors,middleware,serializers,pagination}.py`
  - Test: `uv run python -m pytest backend/common/http/ -v`
  - Size: M (4 files)

- [x] **Task 2.3** `common/persistence` — TransactionManager, ShopScopedRepository, Outbox
  - Files: `backend/common/persistence/{manager,repository,outbox}.py`
  - Test: `uv run python -m pytest backend/common/persistence/ -v`
  - Size: M (3 files)

## Checkpoint: Kernel & Persistence
- [x] All kernel/persistence tests pass
- [x] `uv run ruff check .` clean
- [x] `uv run python manage.py check` clean

## Phase 2: Permissions Contract & Export

- [x] **Task 2.4** `apps/shops/domain/permissions.py` → `contract/fixtures/permissions.json`
  - Files: `backend/apps/shops/domain/permissions.py`, `contract/fixtures/permissions.json`, `backend/scripts/export_permissions.py`
  - Test: `uv run python backend/scripts/export_permissions.py`
  - Size: S (3 files)

- [x] **Task 2.5** Contract Bundle Workflow — `export_contract.py`, `contract-release.yml`, `contract.lock`, `pnpm contract:sync`
  - Files: `backend/scripts/export_contract.py`, `web/scripts/sync_contract.sh`, `.github/workflows/contract-release.yml`
  - Test: `uv run python backend/scripts/export_contract.py` → verify `web/src/contract/`
  - Size: L (3 files + workflow)

## Checkpoint: Contract Sync Loop
- [x] `contract/openapi.json` generated
- [x] `web/src/contract/` types generated
- [x] `pnpm contract:sync` runs without errors

## Phase 3: Shared Fixtures & Web Contract Tests

- [x] **Task 2.6** Shared Fixtures — money-vectors, quantity-vectors, payload-hash-vectors, permissions, error-codes, sample-operations
  - Files: `contract/fixtures/*.json`
  - Test: JSON validity + referenced by tests
  - Size: M (6+ files)

- [x] **Task 2.7** Web Contract Tests — Zod validation + vector parity
  - Files: `web/src/contract/__tests__/contract-validation.test.ts`
  - Test: `vp test run web/src/contract/__tests__/contract-validation.test.ts`
  - Size: M (1 test file + fixtures)

## Phase 4: CI Gate

- [x] **Task 2.8** OpenAPI Diff in CI
  - Files: `.github/workflows/contract-diff.yml`
  - Test: PR with schema change → CI fails
  - Size: S (1 workflow file)

## Checkpoint: Complete VS-02
- [x] All 8 tasks verified
- [x] `uv run ruff check .` clean
- [x] `uv run python manage.py check` clean
- [x] `uv run python manage.py test` passes
- [x] `vp check` clean
- [x] `vp test` passes
- [x] `vp build` succeeds
