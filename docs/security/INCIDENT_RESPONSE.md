# MachIntel Incident Response Runbook

## 1. Objective & Triage Workflow
This runbook provides actionable procedures for responding to security incidents in a MachIntel deployment.

```
+---------------+     +---------------+     +---------------+     +---------------+
| 1. Detection  | --> | 2. Triage &   | --> | 3. Contain-   | --> | 4. Recovery & |
| & Alerting    |     | Identification|     |    ment       |     |    Post-Mortem|
+---------------+     +---------------+     +---------------+     +---------------+
```

---

## 2. Incident Classification & Severity

| Severity Level | Examples | Initial Response SLA |
| :--- | :--- | :--- |
| **SEV-1 (Critical)** | Compromised Admin credentials; unauthorized access to host filesystem; arbitrary code execution attempt | < 15 minutes |
| **SEV-2 (High)** | BOLA/IDOR exploitation attempt; repeated authentication brute-force; token spoofing | < 1 hour |
| **SEV-3 (Medium)** | Blocked path traversal attempt; excessive resource consumption query; rejected prompt injection | < 4 hours |
| **SEV-4 (Low)** | Misconfigured CORS origin attempt; malformed client payload | Next business day |

---

## 3. Immediate Containment Actions

### A. Revoke or Inactivate Compromised User Account
To immediately lock an account and invalidate all issued JWTs (enforced via DB-level `is_active=False` check in `_resolve_user_from_token`):
```sql
UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE username = 'compromised_username';
```

### B. Rotate Secret Key (Global Token Invalidation)
If `SECRET_KEY` is suspected of compromise:
1. Generate a new cryptographic random 32+ character key:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. Update `SECRET_KEY` in `.env`.
3. Restart backend service to immediately invalidate all outstanding JWTs.

### C. Extract Correlated Incident Logs
MachIntel structured logs record `request_id` across every request step:
```bash
# Filter logs by request correlation ID or user identifier
grep '"request_id": "REDACTED-REQUEST-UUID"' /var/log/machintel/backend.log
```

---

## 4. Post-Incident Forensic Audit
1. Audit Alembic migration state (`alembic current`).
2. Verify integrity of inspection storage directory:
   ```bash
   find storage/inspections/ -type f -exec sha256sum {} + > /tmp/current_hashes.txt
   ```
3. Document root cause, timeline, affected assets, and preventive remediation steps in an incident post-mortem.
