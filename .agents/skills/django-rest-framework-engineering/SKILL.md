---
name: django-rest-framework-engineering
description: Enforces Django REST Framework conventions for Stokari backend. Use when building or modifying serializers, viewsets, API views, permissions, ORM queries, database transactions, or API tests.
---

# Django REST Framework Engineering

## Overview

This skill guides engineering judgment when building REST APIs for the Stokari backend using Python 3.14, Django 6.1, Django REST Framework (DRF), PostgreSQL, and `drf-spectacular`.

Rather than copying prescriptive templates, apply these engineering principles, decision frameworks, and failure analysis to derive clean, secure, and robust implementations.

---

## Precedence Rule

When instructions, skills, or existing code conflict:
1. **Explicit SRS/Domain requirements and approved architecture decisions govern.**
2. If an instruction conflicts with technical correctness, concurrency safety, or data integrity, **stop and explain the conflict** before proceeding.
3. Database constraints, atomic transaction guarantees, and tenant isolation take precedence over convenience abstractions.

---

## Layer 1 — Invariants (Non-Negotiable System Guarantees)

Every DRF endpoint and serializer in Stokari must strictly satisfy these core invariants:

### 1. The Validation-Persistence Lifecycle Invariant
*Untrusted input must be validated before persistence. Authorization-sensitive fields must be derived from trusted server-side context, never from client-supplied values.*
- Always invoke `serializer.is_valid(raise_exception=True)` before `serializer.save()`.
- Never read raw `initial_data` in business logic; use `validated_data`.
- Authorization-sensitive fields (such as `store`, `created_by`, or tenant boundaries) must be passed via `serializer.save(**kwargs)` from `request.user` or verified session state, never from unvetted request payloads.

### 2. Multi-Tenant Scoping Invariant
*Data must be filtered and scoped by tenant/store across every data-access path, not just on list endpoints.*
- Base querysets in viewsets must be scoped to the authenticated user's store in `get_queryset()`.
- Service functions, background workers, and detail endpoints must explicitly enforce `store_id` boundaries.

### 3. Side-Effect Free Validation Invariant
*Serializer validation methods (`validate_<field>`, `validate`) must be read-only and side-effect free.*
- Never execute database writes (`save()`, `delete()`, or mutations) inside serializer validation.
- Do not rely on validation-time checks to protect against race conditions; rely on database constraints and row locking during persistence.

---

## Layer 2 — Decision Frameworks

Use these frameworks to determine the right architectural approach:

### 1. Responsibility & Layering Decision

Before writing code, reason through where logic belongs:
- **Serializer:** Translating HTTP input to typed data, field validation, and model hydration (`create`/`update`). Keep serializers focused on data transformations.
- **View / ViewSet:** HTTP coordination: parsing request, checking authentication and permissions, determining response status codes, and scoping base querysets.
- **Domain Service Function:** Multi-model workflows, business calculations, or operations requiring atomic transactions and ledger entries. Extract a service function when complexity, reuse, or testability justifies it—not blindly for trivial single-model CRUD.
- **Model / Database:** Enforcing structural invariants, unique constraints, foreign keys, and indexes directly at the database engine level.

### 2. Read vs Write Serializer Decision

Ask: *Do the input payload and output representation differ meaningfully in fields, nesting, or permissions?*
- If yes: Use separate, focused serializers (e.g. `ProductCreateSerializer` with strict required fields vs. `ProductDetailSerializer` with computed fields and nested relations).
- If no: A single `ModelSerializer` is sufficient. Avoid boolean flags and conditional branches inside a single bloated serializer.

### 3. ORM Query Optimization Decision

Ask: *Which related records will be accessed when serializing the response or executing logic?*
- **`select_related()`:** For single-valued relationships (`ForeignKey`, `OneToOne`) that will be serialized.
- **`prefetch_related()`:** For multi-valued relationships (`ManyToManyField`, reverse foreign keys) that will be iterated over.
- Do NOT apply prefetching to relationships that are not rendered in the response.

---

## Layer 3 — Failure Modes & Verification

Anticipate these common API vulnerabilities and design against them:

### Failure Mode 1: Mass-Assignment / Tenant Boundary Bypass
- **The Bug:** Client submits `{"name": "Item", "store_id": "other-store-uuid"}`. The serializer blindly saves `store_id` from client input.
- **The Defense:** Exclude `store` from serializer write fields. Inject `store=request.user.active_store` explicitly in `serializer.save()`.

### Failure Mode 2: The Validation-Time Race Condition
- **The Bug:** A serializer checks `if product.current_stock >= requested_qty:` during validation. Two simultaneous requests pass validation because stock was available at that millisecond, causing stock to be oversold.
- **The Defense:** Never trust validation-time checks for concurrency-sensitive invariants. Use database-level row locking (`select_for_update().order_by('id')`) within a transaction when persisting the mutation.

### Failure Mode 3: Raw Traceback Leakage
- **The Bug:** An unhandled database or system exception in a view returns a 500 HTML debug page or raw exception text in production.
- **The Defense:** Use DRF's custom exception handler to convert unhandled exceptions into structured, generic error responses with correlation IDs.

### Required Automated Test Verifications
For every new or modified API endpoint, write automated tests verifying:
1. **Tenant Isolation:** A user from Store A receives 403 or 404 when attempting to view, edit, or delete a record belonging to Store B.
2. **Validation Rejection:** Submitting malformed, missing, or invalid fields returns HTTP 400 with descriptive error keys.
3. **Authentication Defense:** Unauthenticated requests return HTTP 401.
4. **Transaction Integrity:** When a downstream error occurs during a multi-model mutation, verify that all database changes roll back completely.

---

## Layer 4 — Minimal Reference Contrasts

### Unsafe Client Field vs Safe Server Context Injection

```python
# UNSAFE: Trusts client-supplied store_id
def create(self, validated_data):
    return Product.objects.create(**validated_data)  # Client can inject another store's ID!


# SAFE: Derives authorization-sensitive fields from verified request context
def perform_create(self, serializer):
    serializer.save(store=self.request.user.active_store, created_by=self.request.user)
```

### Read-Only Validation vs Database Locking

```python
# VALID: Read-only check in validation for user feedback
def validate_sku(self, value):
    store = self.context["request"].user.active_store
    if ProductVariant.objects.filter(store=store, sku=value).exists():
        raise serializers.ValidationError("This SKU is already in use in your store.")
    return value


# NOTE: The database MUST also have a UniqueConstraint(fields=['store', 'sku'])
# because the validation check alone does not prevent concurrent duplicate inserts!
```
