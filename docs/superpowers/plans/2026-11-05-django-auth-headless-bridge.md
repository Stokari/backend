# Django-Auth-Headless & Stokari Backend Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bridge the `django-auth-headless` OAuth handoff flow into Stokari's domain model, resolving settings, user model mismatches, migrations, and token issuance so that Google authentication produces a full Stokari `AuthSession` (JWT + Lease).

**Architecture:**
The application uses `django-auth-headless` (linked locally from `feature/cross-domain-token-auth`) to handle the browser Google OAuth authorization code handshake. When the frontend exchanges the one-time `OAuthHandoffCode` at `POST /api/auth/exchange`, a custom bridge view redeems the code, resolves the Google `sub` to a persistent `apps.identity.models.User`, and invokes Stokari's `create_user_session()` domain service to return a signed 15-minute JWT access token, 30-day rotating refresh token, and 7-day cryptographic `OfflineLease`.

**Tech Stack:** Python 3.14, Django 6.1.2, uv, django-auth-headless, django-allauth, PyJWT, psycopg 3.

**Spec:** `backend/docs/implementation_plan.md` (VS-04), `backend/documentation/Stokari_API_Data_Contract_v0_1.md` (E-02..E-06), and `/home/abelmekonen/Desktop/Projects/django-auth-headless/docs/architecture.md`.

## Global Constraints

- Never commit secrets, passwords, or live OAuth credentials to Git.
- Python 3.14 and uv locked dependencies; all commands executed via `uv run`.
- Composite primary keys on tenant models must be respected (`apps/shops`, `apps/identity`).
- Access tokens must be signed HS256 JWTs carrying `userId`, `email`, `shopId`, `membershipId`, `role`, and `deviceId`.
- Refresh tokens must be hashed SHA-256 with token family reuse tracking.
- Do not push git commits to any remote repository.

## Review Focus

1. Redeeming a handoff code with invalid or missing `deviceId` returns an RFC 9457 validation error.
2. An authorization code cannot be replayed; second attempt returns 400 Bad Request.
3. User logging in with multiple active memberships without specifying `membershipId` receives 409 Conflict with `MEMBERSHIP_SELECTION_REQUIRED`.
4. Deactivated attendant attempting exchange receives 403 Forbidden with `drainToken`.
5. `GET /api/me` succeeds when presented with Stokari's Bearer JWT access token and returns user and tenant context.

---

### Task 1: Link Local `django-auth-headless` & Configure Django Settings

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/config/settings.py`
- Modify: `backend/.env`
- Modify: `backend/.env.example`

- [ ] **Step 1.1: Add local path source in `backend/pyproject.toml`**
  Add `django-auth-headless = { path = "/home/abelmekonen/Desktop/Projects/django-auth-headless", editable = true }` under `[tool.uv.sources]`.
- [ ] **Step 1.2: Run `uv sync`**
  Verify that the local package from `/home/abelmekonen/Desktop/Projects/django-auth-headless` is resolved and installed into `.venv`.
- [ ] **Step 1.3: Update `backend/config/settings.py`**
  - Set `DJANGO_AUTH_MODE = os.getenv("DJANGO_AUTH_MODE", "cross-domain")`
  - Set `DJANGO_AUTH_FRONTEND_URL = os.getenv("DJANGO_FRONTEND_URL", "http://localhost:5173").rstrip("/")`
  - Set `DJANGO_ACCESS_TOKEN_LIFETIME_SECONDS = int(os.getenv("DJANGO_ACCESS_TOKEN_LIFETIME_SECONDS", "3600"))`
  - Set `CORS_ALLOW_CREDENTIALS = True`
  - Set `CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]`
  - Set `SOCIALACCOUNT_ADAPTER = "django_auth_headless.adapters.AuthenticationSocialAccountAdapter"`
- [ ] **Step 1.4: Update `.env` and `.env.example`**
  Add `DJANGO_FRONTEND_URL`, `DJANGO_AUTH_MODE`, `DJANGO_CORS_ALLOWED_ORIGINS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_AUTH_PROVIDERS=google`.
- [ ] **Step 1.5: Verify Django configuration**
  Run `uv run python manage.py check` to confirm settings are valid.

---

### Task 2: Apply Database Migrations & Run OAuth Setup

**Files:**
- Modify: Database tables via migrations

- [ ] **Step 2.1: Run database migrations**
  Execute `uv run python manage.py migrate` to apply migrations for `sites`, `socialaccount`, `account`, `django_auth_headless`, `identity`, and `shops`.
- [ ] **Step 2.2: Verify migration state**
  Run `uv run python manage.py showmigrations` to ensure 0 unapplied migrations remain.
- [ ] **Step 2.3: Verify site configuration helper**
  Ensure Site with ID 1 exists (`Site.objects.get_or_create(id=1, defaults={"domain": "localhost:8000", "name": "Stokari Local"})`).

---

### Task 3: Implement the Stokari Exchange Bridge Endpoint

**Files:**
- Create: `backend/apps/identity/exchange.py`
- Modify: `backend/apps/identity/serializers.py`
- Modify: `backend/apps/identity/views.py`
- Modify: `backend/config/urls.py`

- [ ] **Step 3.1: Define Exchange Request Serializer in `apps/identity/serializers.py`**
  Define `ExchangeAuthCodeRequestSerializer` validating `code` (string), `deviceId` (UUID), and optional `membershipId` (UUID).
- [ ] **Step 3.2: Implement bridge service logic in `apps/identity/exchange.py`**
  - Redeem `OAuthHandoffCode` using `OAuthHandoffCode.redeem(code)`. Return 400 if invalid or expired.
  - Look up `SocialAccount` for the user (`provider="google"`). Extract `uid` (`google_sub`), `email`, and name.
  - Get or create `apps.identity.models.User(google_sub=uid, defaults={"email": email, "name": name})`.
  - Invoke `apps.identity.services.create_user_session(user, device_id=deviceId, membership_id=membershipId)`.
  - Return the resulting `AuthSession` dictionary.
- [ ] **Step 3.3: Implement `ExchangeAuthCodeView` in `apps/identity/views.py`**
  - Subclass DRF `APIView` with `AllowAny` permissions and `@extend_schema` documentation.
  - Handle `AccountDeactivatedError` -> HTTP 403 Forbidden with `code="ACCOUNT_DEACTIVATED"` and `drainToken`.
  - Handle `MembershipSelectionRequiredError` -> HTTP 409 Conflict with `code="MEMBERSHIP_SELECTION_REQUIRED"` and choices.
- [ ] **Step 3.4: Route `/api/auth/exchange` to `ExchangeAuthCodeView`**
  In `config/urls.py`, route `path("api/auth/exchange", ExchangeAuthCodeView.as_view(), name="exchange_code")` before `django_auth_headless.urls` so Stokari's session-issuing exchange handler takes precedence.

---

### Task 4: Enhance `GET /api/me` for Stokari JWT Authentication

**Files:**
- Modify: `backend/apps/identity/views.py`
- Modify: `backend/config/urls.py`

- [ ] **Step 4.1: Implement `CurrentUserView` in `apps/identity/views.py`**
  - Use `StokariJWTAuthentication` as authentication class and `IsAuthenticated` permission.
  - Read `request.user` (`apps.identity.models.User`), `request.shop_id`, `request.membership_id`, `request.role`, `request.device_id`.
  - Return structured JSON matching API contract:
    ```json
    {
      "status": 200,
      "data": {
        "user": {
          "id": str(user.id),
          "email": user.email,
          "name": user.name
        },
        "session": {
          "shopId": getattr(request, "shop_id", None),
          "membershipId": getattr(request, "membership_id", None),
          "role": getattr(request, "role", None),
          "deviceId": getattr(request, "device_id", None)
        }
      }
    }
    ```
- [ ] **Step 4.2: Route `api/me` in `config/urls.py`**
  Wire `path("api/me", CurrentUserView.as_view(), name="current_user")` before `django_auth_headless.urls`.

---

### Task 5: Comprehensive Automated Tests & Verification

**Files:**
- Create: `backend/apps/identity/__tests__/test_auth_bridge.py`
- Modify: `backend/scripts/export_contract.py`

- [ ] **Step 5.1: Write failing tests in `test_auth_bridge.py`**
  - Test valid code redemption produces `AuthSession` with JWT access token and offline lease.
  - Test double redemption of same code returns 400 Bad Request.
  - Test missing `deviceId` returns 400 Bad Request.
  - Test multiple memberships without selection returns 409 `MEMBERSHIP_SELECTION_REQUIRED`.
  - Test deactivated user code exchange returns 403 `ACCOUNT_DEACTIVATED` with `drainToken`.
  - Test `GET /api/me` with Stokari Bearer token returns 200 with user and session context.
- [ ] **Step 5.2: Run tests and ensure all pass**
  Run `uv run --extra dev python -m pytest apps/identity/` and `uv run --extra dev python -m pytest`.
- [ ] **Step 5.3: Regenerate OpenAPI contract**
  Run `uv run python scripts/export_contract.py` to synchronize `contract/openapi.json`.
- [ ] **Step 5.4: Verify system hygiene**
  Run `uv run ruff check .` and `uv run python manage.py check`.
