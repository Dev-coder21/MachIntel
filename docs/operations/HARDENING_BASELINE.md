# MachIntel Hardening Baseline & Operational Compliance

## Control 1: Authentication & Token Security
- **CONTROL**: Stateless JWT Bearer authentication with cryptographic signing and subject verification.
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_hardening_security.py` passes `test_auth_missing_token_rejected`, `test_auth_invalid_token_rejected`, `test_auth_expired_token_rejected`, and `test_auth_inactive_user_token_rejected`.
- **LIMITATION**: Token revocation prior to natural expiration requires account deactivation or secret rotation.

## Control 2: Role-Based Access Control (RBAC)
- **CONTROL**: Explicit role enforcement (`VIEWER`, `OPERATOR`, `ADMIN`). Viewer accounts are restricted to read-only operations and forbidden from mutating predictions, risk evaluations, alerts, and maintenance work orders.
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_hardening_security.py` passes `test_rbac_viewer_blocked_from_prediction_mutation`, `test_rbac_viewer_blocked_from_risk_evaluation`, `test_rbac_viewer_blocked_from_alert_acknowledgement`, and `test_rbac_viewer_blocked_from_work_order_creation`.
- **LIMITATION**: Single tenant authorization model; assets are shared across authenticated organization users.

## Control 3: API Input Validation & Query Bounding
- **CONTROL**: Strict Pydantic schema validation and bounded query parameters (`len(machine_ids) <= 10`, `start_cycle <= end_cycle <= 1000`).
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_hardening_security.py` passes `test_resource_abuse_compare_machines_bounded` and `test_resource_abuse_feature_preview_cycles_validated`.
- **LIMITATION**: Application-level limits protect individual endpoints but do not replace perimeter network DDoS protection.

## Control 4: SQL Injection Prevention
- **CONTROL**: 100% parameterized queries via SQLAlchemy 2.0 ORM and Core. Zero raw SQL string interpolation.
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_hardening_security.py` passes `test_sql_injection_machine_id_handled_safely`.
- **LIMITATION**: Developers must continue adhering to ORM query constructs for future migrations and endpoints.

## Control 5: File & Artifact Security (Path Traversal Protection)
- **CONTROL**: Canonical path resolution via `Path.resolve()` validated against whitelisted roots (`storage/inspections`, `data/raw/mvtec_ad`).
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_hardening_security.py` passes `test_path_traversal_blocked_in_inspection_artifacts`.
- **LIMITATION**: Requires host filesystem permissions to prevent backend process traversal outside its run directory.

## Control 6: CORS & HTTP Security Headers
- **CONTROL**: Explicit origin whitelist (no wildcard with credentials). Injected headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy`, and `Permissions-Policy`.
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_hardening_security.py` passes `test_security_headers_present` and `test_production_config_rejects_wildcard_cors`.
- **LIMITATION**: CSP allows local images and inline styles required by Next.js and Tailwind rendering.

## Control 7: Request Correlation & Structured Logging
- **CONTROL**: `X-Request-ID` generated or propagated per request, injected into contextvars, structured JSON logs, and response headers. Secrets and credentials redacted from logs.
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_hardening_security.py` passes `test_request_correlation_id_generated` and `test_request_correlation_id_propagated`.
- **LIMITATION**: Developers must not bypass standard logging by printing secrets directly to `stdout`.

## Control 8: Database Transaction Reliability
- **CONTROL**: Explicit session management with automatic `db.rollback()` on exception; clean pool teardown on shutdown.
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_risk_and_alerts.py`, `test_maintenance.py`, and `get_db()` rollback exception handlers.
- **LIMITATION**: Relies on ACID transaction engine of PostgreSQL 16.

## Control 9: Alembic Migration Chain Integrity
- **CONTROL**: Single deterministic migration chain (8 revisions) from initial schema through AI Inspector to `e2f3a4b5c6d7`.
- **STATUS**: VERIFIED
- **VERIFICATION**: `alembic current` confirms single head revision without branching or drift.
- **LIMITATION**: Migration rollbacks must be planned and tested prior to applying disruptive schema modifications.

## Control 10: Environment & Secret Hygiene
- **CONTROL**: All credentials loaded from `.env` (gitignored). In production, `Settings` validator blocks insecure default keys and `DEBUG=True`.
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_hardening_security.py` passes `test_production_config_rejects_insecure_default_secret` and `test_production_config_rejects_debug_mode`.
- **LIMITATION**: Host environment security is responsible for safeguarding filesystem `.env` file permissions.

## Control 11: Dependency Security Audit
- **CONTROL**: Backend Python dependencies validated via `pip check` (0 broken requirements). Frontend evaluated via `npm audit`.
- **STATUS**: VERIFIED
- **VERIFICATION**: `pip check` reports no broken requirements; frontend production build passes.
- **LIMITATION**: Upstream Next.js transitive dev-dependency advisories documented; major non-breaking upgrades deferred to scheduled maintenance.

## Control 12: AI Inspector Guardrails & Domain Separation
- **CONTROL**: Strictly read-only tool registry (15 tools). Prompt injection defenses, citation provenance validation, strict decoupling between C-MAPSS and MVTec AD domains.
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_ai_inspector.py` (all tests passing) and `test_no_mutation_tools_in_registry`.
- **LIMITATION**: External cloud LLM calls depend on external provider latency and availability when not using mock provider.

## Control 13: Frontend Security & XSS Mitigation
- **CONTROL**: Next.js React JSX auto-escaping, safe markdown AST rendering with HTML disabled, no `dangerouslySetInnerHTML`.
- **STATUS**: VERIFIED
- **VERIFICATION**: Frontend vitest suite (51/51 tests passing) and TypeScript compilation (0 errors).
- **LIMITATION**: Client-side token storage in `localStorage` requires modern browser XSS defenses.

## Control 14: Health & Diagnostics Probes
- **CONTROL**: Distinct probes: `/api/v1/health/liveness` (process running) and `/api/v1/health/readiness` (PostgreSQL connectivity verified without heavy ML inference). Error details sanitized in production.
- **STATUS**: VERIFIED
- **VERIFICATION**: `test_hardening_security.py` passes `test_health_liveness_probe` and `test_health_readiness_probe`.
- **LIMITATION**: AI Inspector provider readiness is decoupled from core database readiness to prevent cascading false negatives.

## Control 15: Data Safety & Backup Strategy
- **CONTROL**: Documented asset classification, backup cadence, and recovery runbooks in `docs/operations/DATA_SAFETY.md`.
- **STATUS**: VERIFIED
- **VERIFICATION**: Verified documentation of logical dumps, storage tar archives, and key vaulting.
- **LIMITATION**: Automated off-host replication requires host-level infrastructure outside local scope.

## Known Remaining Risks
1. **Host-Level Compromise**: Local SQLite or PostgreSQL on a compromised host cannot resist root-level file access.
2. **Reverse Proxy Perimeter**: Production deployments require Nginx or Envoy for TLS termination, rate-limiting, and request body size caps.
3. **External LLM Latency**: When configured with cloud LLM providers, external network timeouts can affect AI Inspector turnaround time.
