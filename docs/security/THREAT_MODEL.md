# MachIntel Threat Model

## 1. Scope & System Boundaries
MachIntel operates as a read-mostly multimodal analytical platform providing decision support for predictive maintenance and visual inspection. Actuator control, automated equipment shutdown, and SCADA control are strictly outside system capabilities.

---

## 2. Threat Analysis Matrix

### Threat 1: Unauthorized Access / Credential Compromise
- **Attack Surface**: `/api/v1/auth/login`, JWT Bearer authorization header, `/api/v1/*`.
- **Mitigation**: bcrypt-hashed passwords (`cost=12`), signed HS256 JWTs with explicit expiration, subject verification, inactive account lockouts, environment-validated secret key.
- **Verification**: `test_auth.py`, `test_hardening_security.py` (`test_auth_invalid_token_rejected`, `test_auth_expired_token_rejected`, `test_auth_inactive_user_token_rejected`).
- **Remaining Limitation**: Revocation of active JWTs before expiration requires short expiration periods or blacklist cache.

### Threat 2: IDOR / BOLA (Insecure Direct Object References)
- **Attack Surface**: Machine URLs (`/api/v1/machines/{id}`), alerts, maintenance work orders.
- **Mitigation**: Multi-tier RBAC (`VIEWER`, `OPERATOR`, `ADMIN`). Viewers are blocked from mutating predictions, risk evaluations, alert lifecycle, and work orders. All mutations bind the actor ID from the validated session.
- **Verification**: `test_rbac.py`, `test_maintenance.py::test_viewer_cannot_mutate_work_orders`, `test_hardening_security.py`.
- **Remaining Limitation**: Multi-tenant asset partitioning is not implemented in M11; all authorized users within an installation share the asset inventory.

### Threat 3: SQL Injection
- **Attack Surface**: Query filters, path parameters, machine search, inspection analytics filters.
- **Mitigation**: Exclusively parameterized queries via SQLAlchemy 2.0 ORM and Core constructs. No raw string formatting (`f"SELECT..."`) in repository or query layers.
- **Verification**: `test_hardening_security.py::test_sql_injection_machine_id_handled_safely`.
- **Remaining Limitation**: Complex analytical ad-hoc query builders must adhere strictly to SQLAlchemy expressions.

### Threat 4: Path Traversal (Arbitrary File Access)
- **Attack Surface**: Artifact streaming endpoints (`/inspections/results/{id}/heatmap`, `/overlay`, `/original`, `/mask`).
- **Mitigation**: `_validate_safe_path()` checks resolved canonical path (`Path.resolve()`) against explicit allowed root directories (`storage/inspections`, `data/raw/mvtec_ad`).
- **Verification**: `test_cv.py`, `test_hardening_security.py::test_path_traversal_blocked_in_inspection_artifacts`.
- **Remaining Limitation**: Storage directory permissions must be restricted at the OS level so the backend process cannot traverse parent directories even if symlinks exist.

### Threat 5: Stored & Reflected Cross-Site Scripting (XSS)
- **Attack Surface**: Frontend markdown rendering of AI Inspector responses, alert titles, maintenance comments.
- **Mitigation**: Next.js React JSX auto-escaping, safe markdown AST rendering with HTML disabled, `X-Content-Type-Options: nosniff`, `Content-Security-Policy`.
- **Verification**: Frontend vitest suites, automated header verification.
- **Remaining Limitation**: LLM output formatting must never use `dangerouslySetInnerHTML`.

### Threat 6: Secret Leakage in Logs or API Responses
- **Attack Surface**: Production JSON logs, unhandled exception tracebacks, `/api/v1/health` metadata.
- **Mitigation**: Structured JSON logging filters sensitive keys (`password`, `access_token`, `authorization`). Exception handlers strip tracebacks and DB strings in production. `Settings` rejects default secrets in production.
- **Verification**: `test_production_config_rejects_insecure_default_secret`, `test_health_readiness_probe`.
- **Remaining Limitation**: Developers must not print raw dicts containing credentials to `stdout`.

### Threat 7: Prompt Injection & Adversarial Jailbreaking
- **Attack Surface**: `/api/v1/ai-inspector/chat` (user inquiry messages).
- **Mitigation**: Hardened system prompt with strict read-only mandate, refusal instructions for SQL/system-state/code-generation prompts, tool-result provenance grounding.
- **Verification**: `test_ai_inspector.py::test_prompt_injection_resistance`.
- **Remaining Limitation**: LLM behavior is probabilistic; guardrails rely on combined prompt enforcement, parameter validation, and tool-layer constraints.

### Threat 8: AI Tool Abuse & State Mutation Attempts
- **Attack Surface**: AI Inspector tool execution engine (`ToolRegistry`).
- **Mitigation**: All 15 registered tools are strictly read-only getters. Mutation functions are deliberately absent from the registry. No `eval()`, `exec()`, or shell subcommands.
- **Verification**: `test_ai_inspector.py::test_all_tools_are_read_only`, `test_no_mutation_tools_in_registry`.
- **Remaining Limitation**: Rate of tool calls per investigation is clamped to `AI_INSPECTOR_MAX_TOOL_CALLS` (5).

### Threat 9: Excessive Resource Consumption / Denial of Service
- **Attack Surface**: Heavy analytics endpoints (`compare_machines`, feature preview, telemetry trends).
- **Mitigation**: Query-level bounds: `len(machine_ids) <= 10`, `max_points <= 1000`, `window <= 100`, `start_cycle <= end_cycle <= 1000`. Fast indexed DB queries.
- **Verification**: `test_resource_abuse_compare_machines_bounded`, `test_resource_abuse_feature_preview_cycles_validated`.
- **Remaining Limitation**: Upstream reverse proxy rate limiting (e.g. Nginx `limit_req`) is required for production perimeter protection.

### Threat 10: Malicious / Unverified Evidence Content
- **Attack Surface**: Evidence bundle creation and cross-referencing.
- **Mitigation**: Evidence provenance verification: hashes and entity IDs must resolve to authentic `RiskAssessment` or `InspectionResult` records.
- **Verification**: `test_evidence.py::test_evidence_provenance_verification`.
- **Remaining Limitation**: Offline tampering of stored source images on disk would invalidate sha256 checksums.

### Threat 11: Cross-Domain Causal Contamination
- **Attack Surface**: AI Inspector synthesis correlating turbofan engine sensor data with metal nut visual defect images.
- **Mitigation**: Strict domain separation: NASA C-MAPSS and MVTec AD are isolated domains without shared entities or timestamps. AI Inspector tools reject cross-domain queries.
- **Verification**: `test_ai_inspector.py::test_cross_domain_isolation`.
- **Remaining Limitation**: If a real combined multimodal machine is added in future milestones, a formal schema relationship must be authored.

### Threat 12: Database Corruption / Inconsistent Transactions
- **Attack Surface**: Failed multi-step mutations (e.g., Risk assessment + Alert emission + Work order).
- **Mitigation**: Explicit transaction boundaries. Database dependencies execute `db.rollback()` upon any uncaught exception.
- **Verification**: `test_risk_and_alerts.py`, `test_maintenance.py`.
- **Remaining Limitation**: Relies on ACID transaction guarantees provided by PostgreSQL 16.

### Threat 13: Dependency Vulnerabilities
- **Attack Surface**: Python packages (`requirements.txt`), Node modules (`package.json`).
- **Mitigation**: `pip check` validation, `npm audit` monitoring, locked dependency versions, minimal attack surface without unnecessary packages.
- **Verification**: Automated build and test suites.
- **Remaining Limitation**: Periodic security scans and scheduled patch cycles must be sustained during operations.
