# MachIntel Security Controls Catalog

## 1. Authentication Controls (AC)
- **AC-1 (Password Hashing)**: Passwords hashed using bcrypt with salt rounds = 12 (`passlib.context.CryptContext`). Plaintext passwords never stored.
- **AC-2 (JWT Token Signing)**: Stateless Bearer authentication via PyJWT. Signed with HMAC-SHA256 (`HS256`).
- **AC-3 (Token Expiration)**: Strict expiration check (`exp` claim). Expired tokens rejected with HTTP 401.
- **AC-4 (Subject Validation)**: User ID in `sub` claim validated against active DB user. Inactive accounts rejected.
- **AC-5 (Secret Strength)**: `Settings` model validator rejects default/short secret keys when `ENVIRONMENT=production`.

## 2. Authorization Controls (RBAC)
- **RBAC-1 (Role Hierarchy)**: Three operational roles: `VIEWER`, `OPERATOR`, `ADMIN`.
- **RBAC-2 (Viewer Restrictions)**: Read-only access to all machine telemetry, predictions, inspections, and work orders. Blocked from triggering ML inference, risk evaluations, alert lifecycle, and work orders.
- **RBAC-3 (Operator Capabilities)**: Permitted to trigger predictions, run inspections, acknowledge/resolve alerts, and manage work order lifecycle.
- **RBAC-4 (Admin Governance)**: User administration and system configuration.

## 3. API & Input Controls (IC)
- **IC-1 (Strict Pydantic Validation)**: All request payloads validated against strongly-typed Pydantic schemas.
- **IC-2 (Query Parameter Bounding)**: Machine comparison limited to 10 machines; pagination limits bounded (1..200); cycle ranges bounded (1..1000).
- **IC-3 (Parameterized Queries)**: Zero raw SQL; 100% SQLAlchemy ORM/Core parameterization.

## 4. File & Artifact Security (FC)
- **FC-1 (Path Normalization & Resolution)**: File paths resolved via `Path(p).resolve()`.
- **FC-2 (Allowed Root Confinement)**: Canonical path must reside within `ALLOWED_STORAGE_ROOTS` (`storage/inspections/`, `data/raw/mvtec_ad/`).
- **FC-3 (Safe Error Responses)**: Traversal attempts and nonexistent files return HTTP 404 or 403 without revealing filesystem paths.

## 5. HTTP & Transport Security (HC)
- **HC-1 (Explicit CORS)**: `allow_origins` bound to explicit origins (`settings.BACKEND_CORS_ORIGINS`). Wildcard origins with credentials forbidden in production.
- **HC-2 (Security Headers)**: Every response includes:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy: default-src 'self' ...`
  - `Permissions-Policy: geolocation=(), camera=(), microphone=()`

## 6. Observability & Logging Controls (OC)
- **OC-1 (Correlation ID)**: `X-Request-ID` attached to all requests and propagated through structured JSON logs and response headers.
- **OC-2 (Redaction of Sensitive Fields)**: Formatter strips authorization headers, password fields, and tokens from log output.
- **OC-3 (Error Sanitization)**: Internal tracebacks and database error strings masked in production environments.

## 7. AI Inspector Guardrails (AIC)
- **AIC-1 (Read-Only Tool Registry)**: Zero state mutation tools; zero code execution capabilities.
- **AIC-2 (Bounded Execution)**: Maximum 5 tool calls per investigation; 30-second timeout.
- **AIC-3 (Strict Domain Isolation)**: NASA C-MAPSS and MVTec AD data domains strictly decoupled.
- **AIC-4 (Evidence Provenance)**: Findings cite verified database records only.
