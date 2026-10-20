---
name: stokari-backend-domain
description: Enforces Stokari inventory, catalog, stock ledger, and synchronization domain rules. Use when designing or implementing inventory models, stock movements, auditing, idempotency, or backend sync endpoints.
---

# Stokari Backend Domain Engineering

## Overview

This skill guides engineering reasoning for Stokari's business domain: inventory management, auditable stock movements, store-level multi-tenancy, and distributed synchronization.

The goal is not to copy fixed code snippets, but to apply rigorous engineering judgment so that every implementation preserves Stokari's core invariants under real-world conditions (concurrency, network partitions, and hardware failures).

---

## Precedence Rule

When instructions, skills, or existing code conflict:
1. **Explicit SRS/Domain requirements and approved architecture decisions govern.**
2. If an instruction conflicts with technical correctness, concurrency safety, or data integrity, **stop and explain the conflict** before proceeding.
3. Database constraints, atomic transaction guarantees, and tenant isolation take precedence over convenience abstractions.

---

## Layer 1 — Invariants (Non-Negotiable System Guarantees)

Every domain implementation in Stokari must strictly satisfy these four invariants:

### 1. The Stock Ledger Invariant
*Every committed inventory mutation MUST have an accompanying, immutable `StockMovement` ledger entry created in the exact same database transaction.*
- Stock balance is a materialized balance backed by a continuous audit trail.
- Stock balances must never change through arbitrary updates (`current_stock = 10` or raw `F()` updates) without a corresponding ledger record.
- Every ledger record must capture: `product_variant`, `store`, signed `quantity_delta`, `balance_after`, `movement_type`, `reference_id`, and `created_by`.

### 2. Multi-Tenant Store Isolation Invariant
*Data belonging to Store A must never be accessible, modifiable, or observable by Store B.*
- All catalog items, stock records, audit movements, and sync logs must be strictly scoped to `store_id`.
- Scoping must be enforced at every layer: database queries, service functions, and API endpoints.

### 3. Effectively-Once Idempotency Invariant
*Re-submitting the same client operation ID must produce the exact business effect of a single execution, returning the consistent historical result without re-executing mutations.*
- Idempotency is enforced by the database engine (unique constraints), not by application-level memory checks.
- Retries must never duplicate sales, double-decrement stock, or create duplicate payment entries.

### 4. Explicit Conflict Review Invariant
*When offline operations violate business rules (e.g. concurrent sales overselling physical stock), the system must preserve the transaction data and flag it for human owner review (`NEEDS_REVIEW`).*
- Never silently discard collected sales.
- Never silently force arbitrary policies (such as unapproved negative stock) without explicit owner governance.

---

## Layer 2 — Decision Frameworks

When designing or implementing a domain feature, reason through these decision frameworks:

### 1. Concurrency & Locking Strategy

Before mutating any inventory or financial record, ask:
1. **Could multiple clients or background workers touch this record simultaneously?**
   - If yes: Determine the coordination mechanism.
2. **Do we need row locks or database arithmetic?**
   - **Use `select_for_update()`:** When you must inspect the current balance (e.g. checking whether stock is available) before deciding whether to deduct or transition to conflict review.
   - **Order locks deterministically:** If an operation touches multiple items (e.g., a multi-line sale), you MUST acquire locks in a deterministic order (e.g. `.order_by('id')`) at the SQL level. Sorting IDs in Python memory is insufficient; the database query itself must guarantee lock acquisition sequence to prevent deadlocks.
   - **Use atomic database arithmetic (`F()` expressions):** Only for blind counter increments where availability checks are not needed, and ONLY when the corresponding ledger entry is created in the same atomic block.

### 2. Sync Operation Classification & Transaction Boundaries

When processing operations from offline clients:
1. **Identify the transaction boundary:**
   - Wrap the overall sync batch in `transaction.atomic()`.
   - Isolate each operation inside a savepoint (`transaction.savepoint()`) so an error in one operation does not abort the entire batch.
2. **Classify the outcome:**
   - **`SUCCESS`:** Invariants satisfied, stock deducted, ledger movement created, cached response persisted.
   - **`DUPLICATE`:** Operation was previously processed; return cached response immediately without executing domain logic.
   - **`NEEDS_REVIEW`:** Business invariant cannot be satisfied (e.g. insufficient stock due to concurrent offline sales). Retain transaction record, flag for review, and commit savepoint so the conflict is visible on the management dashboard.
   - **`ERROR` (Validation):** Payload is malformed or unprocessable. Savepoint rolled back, client alerted with safe error code.
3. **Handle transient vs permanent failures:**
   - Only cache outcomes for completed business evaluations (`SUCCESS`, `DUPLICATE`, `NEEDS_REVIEW`, and domain validation rejections). Do not permanently cache transient server crashes or database disconnection errors.

### 3. Domain Logic Placement

Decide where logic belongs based on cohesion and testability:
- **Model / Manager:** Invariants inherent to a single model (e.g. generating SKU, checking variant active state).
- **Domain Service Function:** Multi-model workflows (e.g. `process_sale()`, `reconcile_inventory_count()`, `record_stock_transfer()`) requiring explicit transaction management, ledger generation, and notifications.
- **Serializer:** Parsing, type conversion, and validating incoming shapes. Serializers delegate to domain services; they do not orchestrate multi-model transactions.

---

## Layer 3 — Failure Modes & Verification

Anticipate these subtle failure modes and design defenses against them:

### Failure Mode 1: The Duplicate-Sync Race (Check-then-Act)
```
Request A (Device 1 retry)          Request B (Device 1 concurrent)
─────────────────────────          ───────────────────────────────
1. Checks operation log (None)     1. Checks operation log (None)
2. Decrements stock                2. Decrements stock (DOUBLE DEDUCTION!)
3. Creates Sale & Ledger           3. Creates Sale & Ledger
4. Inserts operation log           4. DB Unique Constraint Error / Crash
```
- **Root Cause:** Relying on `filter(operation_id=...).first()` before inserting. A race window exists between the check and the insert.
- **Defense:** Enforce a database constraint `UniqueConstraint(fields=['store', 'operation_id'])`. Catch `IntegrityError` on the insert attempt, roll back the savepoint, and read the response committed by the competing request.

### Failure Mode 2: Multi-Item Deadlocks
- **Scenario:** Sale 1 purchases Item A then Item B. Sale 2 purchases Item B then Item A.
- **Root Cause:** Non-deterministic lock acquisition across concurrent transactions causes PostgreSQL to abort one with a deadlock exception.
- **Defense:** Always enforce `.order_by('id')` on queries using `select_for_update()`.

### Failure Mode 3: Data & Traceback Leakage
- **Scenario:** An unhandled exception occurs during sync (e.g. DB connection dropped or foreign key violation). Returning `str(e)` in the API response leaks database table names, constraint details, and internal stack traces to the client.
- **Defense:** Log full exceptions server-side with a correlation ID (`logger.exception("Sync error %s", correlation_id)`). Return only structured, client-safe error codes (`INTERNAL_ERROR`, correlation ID).

### Required Automated Test Verifications
Before declaring any domain implementation complete, write automated tests verifying:
1. **Sequential Idempotency:** Submitting operation `X` twice in sequence creates exactly 1 sale, 1 stock movement, and returns identical responses.
2. **Concurrent Idempotency:** Firing operation `X` concurrently from multiple threads/connections results in exactly 1 successful execution and 1 duplicate acknowledgment, with zero duplicate movements.
3. **Transaction Rollback:** Intentionally raising an exception after stock deduction proves that both the balance change and ledger movement roll back completely.
4. **Tenant Isolation:** Attempting to process an operation using Store B's product variant inside Store A raises an authorization or not-found error.

---

## Layer 4 — Minimal Reference Contrasts

Use these small snippets to contrast unsafe vs safe patterns:

### Safe Idempotency Pattern vs Unsafe Check-then-Act

```python
# UNSAFE: Vulnerable to race conditions under concurrent delivery
if not SyncOperationLog.objects.filter(store=store, operation_id=op_id).exists():
    execute_sale(...)
    SyncOperationLog.objects.create(store=store, operation_id=op_id)

# SAFE: Database constraint guarantees single execution, savepoint isolates batch
sid = transaction.savepoint()
try:
    # 1. Check existing cache
    log = SyncOperationLog.objects.filter(store=store, operation_id=op_id).first()
    if log:
        return {"status": "DUPLICATE", "data": log.response_payload}

    # 2. Execute domain logic
    result = execute_sale(store, payload)

    # 3. Commit idempotency record (DB unique constraint on (store, operation_id))
    SyncOperationLog.objects.create(store=store, operation_id=op_id, response_payload=result)
    transaction.savepoint_commit(sid)
    return {"status": "SUCCESS", "data": result}

except IntegrityError:
    # Concurrent request inserted first; rollback savepoint and read winner's result
    transaction.savepoint_rollback(sid)
    log = SyncOperationLog.objects.get(store=store, operation_id=op_id)
    return {"status": "DUPLICATE", "data": log.response_payload}
```

### Deterministic Lock Acquisition

```python
# SAFE: Order locks deterministically at the DB query level
locked_variants = list(
    ProductVariant.objects.select_for_update()
    .filter(id__in=requested_variant_ids, store_id=store_id)
    .order_by("id")
)
```
