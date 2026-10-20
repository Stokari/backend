# VS-02 Implementation Plan: Contract-First Architecture & Kernel Primitives

## Overview
Implement the 8 tasks of VS-02 (Tasks #3–#10) establishing kernel primitives, HTTP infrastructure, persistence layer, permissions contract, automated contract sync, shared test fixtures, web contract tests, and OpenAPI diff CI gate.

## Architecture Decisions
- **Backend-first contract generation**: Django drf-spectacular generates OpenAPI → Python script exports → TypeScript types generated in web
- **Shared fixtures in `contract/fixtures/`**: Committed canonical vectors for cross-language validation
- **Zero-dependency kernel**: `common/kernel` has no Django/DRF dependencies
- **Shop-scoped everything**: All repositories automatically scope by `shop_id` via composite PK

---

## Phase 1: Backend Kernel & Persistence (Tasks #3, #4, #5)

### Task 2.1: `common/kernel` — Result, DomainError, Typed IDs, Clock, EventBus
**Files:** `backend/common/kernel/{types,result,errors,bus,clock}.py`
**Acceptance:**
- [ ] `Result[T, E]` monad with `ok()`, `err()`, `unwrap()`, `map()`, `and_then()`
- [ ] `DomainError` base + subclasses (`NotFound`, `Conflict`, `Validation`, `Unauthorized`, `Forbidden`)
- [ ] Typed IDs: `ShopId`, `OpId`, `ProductId`, `StockChangeId`, `MembershipId` as `NewType`
- [ ] `Clock` protocol + `SystemClock` implementation
- [ ] Simple in-memory `EventBus` for domain events
- [ ] 100% unit test coverage
**Verification:** `uv run python -m pytest backend/common/kernel/ -v`

### Task 2.2: `common/http` — RFC 9457, Request-ID, Throttles, StrictIntegerField, Pagination
**Files:** `backend/common/http/{errors,middleware,serializers,pagination}.py`
**Acceptance:**
- [ ] `ProblemDetailException` mapping to RFC 9457 response
- [ ] Request-ID middleware (generates/propagates `X-Request-ID`)
- [ ] `StrictIntegerField` rejects floats in money/quantity
- [ ] Cursor pagination base classes
- [ ] DRF exception handler integration
**Verification:** `uv run python -m pytest backend/common/http/ -v`

### Task 2.3: `common/persistence` — TransactionManager, ShopScopedRepository, Outbox
**Files:** `backend/common/persistence/{manager,repository,outbox}.py`
**Acceptance:**
- [ ] `TransactionManager.atomic(shop_id)` → `select_for_update` with deterministic ordering
- [ ] `ShopScopedRepository` base: `get_queryset()` auto-filters `shop_id`
- [ ] `DomainEventOutbox` table + `append_event()` for sync pipeline
- [ ] Multi-tenant mock tests verifying isolation
**Verification:** `uv run python -m pytest backend/common/persistence/ -v`

---

## Checkpoint: Kernel & Persistence
- [ ] All kernel/persistence tests pass
- [ ] `uv run ruff check .` clean
- [ ] `uv run python manage.py check` clean

---

## Phase 2: Permissions Contract & Export (Tasks #6, #7)

### Task 2.4: `apps/shops/domain/permissions.py` → `contract/fixtures/permissions.json`
**Files:** `backend/apps/shops/domain/permissions.py`, `contract/fixtures/permissions.json`
**Acceptance:**
- [ ] Role-Permission matrix: `OWNER` vs `ATTENDANT` across all operations
- [ ] Export script generates `permissions.json` fixture
- [ ] Fixture includes: `create_shop`, `close_shop`, `invite_staff`, `deactivate_staff`, `manage_products`, `receive_stock`, `adjust_stock`, `view_reports`, `manage_settings`, `sync_push`, `sync_pull`, `resolve_conflicts`
**Verification:** `uv run python backend/scripts/export_permissions.py` produces valid JSON

### Task 2.5: Contract Bundle Workflow — `export_contract.py`, `contract-release.yml`, `contract.lock`, `pnpm contract:sync`
**Files:** `backend/scripts/export_contract.py`, `web/scripts/sync_contract.sh`, `.github/workflows/contract-release.yml`
**Acceptance:**
- [ ] `export_contract.py`: Runs `drf-spectacular` → writes `contract/openapi.json`
- [ ] Generates TypeScript types to `web/src/contract/` via `openapi-typescript`
- [ ] `contract.lock` records schema hash
- [ ] GitHub Action `contract-release.yml` runs on backend changes
- [ ] `pnpm contract:sync` in web pulls types + runs validation
**Verification:** Run `uv run python backend/scripts/export_contract.py` → check `web/src/contract/` updated

---

## Checkpoint: Contract Sync Loop
- [ ] `contract/openapi.json` generated
- [ ] `web/src/contract/` types generated
- [ ] `pnpm contract:sync` runs without errors

---

## Phase 3: Shared Fixtures & Web Contract Tests (Tasks #8, #9)

### Task 2.6: Shared Fixtures — `money-vectors.json`, `quantity-vectors.json`, `payload-hash-vectors.json`, `permissions.json`, `error-codes.json`, `sample-operations/*.json`
**Files:** `contract/fixtures/*.json`
**Acceptance:**
- [ ] `money-vectors.json`: santim parsing/formatting/rounding cases
- [ ] `quantity-vectors.json`: milli-unit parsing/formatting/bounds
- [ ] `payload-hash-vectors.json`: RFC 8785 canonical JSON → SHA-256 → base64url
- [ ] `permissions.json`: from Task 2.4
- [ ] `error-codes.json`: RFC 9457 error codes + custom domain codes
- [ ] `sample-operations/*.json`: CreateProduct, ReceiveStock, Sale, AdjustStock, SyncPush, SyncPull
**Verification:** All fixtures valid JSON, referenced by both backend and frontend tests

### Task 2.7: Web Contract Tests — Zod validation + vector parity
**Files:** `web/src/contract/__tests__/contract-validation.test.ts`
**Acceptance:**
- [ ] Vitest suite loads all sample operations
- [ ] Each operation validated against generated Zod schemas
- [ ] Money/quantity vectors produce identical results in TS vs Python
- [ ] Payload hashes match across languages
**Verification:** `vp test run web/src/contract/__tests__/contract-validation.test.ts`

---

## Phase 4: CI Gate (Task #10)

### Task 2.8: OpenAPI Diff in CI
**Files:** `.github/workflows/contract-diff.yml`
**Acceptance:**
- [ ] Workflow runs on PR to `dev`/`main`
- [ ] Compares `contract/openapi.json` vs regenerated from current code
- [ ] Fails if drift detected (exit code 1)
- [ ] Action comment on PR with diff summary
**Verification:** Create test PR with intentional schema change → CI fails

---

## Checkpoint: Complete VS-02
- [ ] All 8 tasks verified
- [ ] `uv run ruff check .` clean
- [ ] `uv run python manage.py check` clean
- [ ] `uv run python manage.py test` passes
- [ ] `vp check` clean
- [ ] `vp test` passes
- [ ] `vp build` succeeds

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| drf-spectacular doesn't capture all custom fields | High | Add `@extend_schema_field` annotations early |
| TypeScript type generation misses nullable fields | Medium | Add `nullable: true` in serializers; test with sample ops |
| Composite PK scoping not enforced in repository base | High | Write multi-tenant test with 2 shops, assert isolation |
| Contract sync race in CI | Low | Use `contract.lock` hash comparison |

---

## Open Questions
- [ ] Should `common/kernel` be a separate pip package? (Defer: keep in-repo for now)
- [ ] Where does `contract/` directory live? (Current: repo root, accessible from both backend/web)
- [ ] Python 3.14 `NewType` vs `typing.NewType`? (Use `typing.NewType` for compatibility)
