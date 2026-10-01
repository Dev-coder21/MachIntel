# MachIntel Security Architecture & Governance

## Overview
MachIntel is an enterprise-grade multimodal artificial intelligence platform for predictive maintenance (NASA C-MAPSS turbofan health) and industrial visual inspection (MVTec AD anomaly localization).

Because MachIntel assists human operators in mission-critical industrial decision support, security, integrity, provenance, and domain boundaries are central architectural requirements.

## Security Documentation Structure

1. **[THREAT_MODEL.md](file:///Users/devtrivedi/Desktop/MachIntel/docs/security/THREAT_MODEL.md)**:
   Formal STRIDE-aligned threat model analyzing 13 distinct industrial threat surfaces, including prompt injection, AI tool abuse, IDOR/BOLA, cross-domain contamination, and resource starvation.

2. **[SECURITY_CONTROLS.md](file:///Users/devtrivedi/Desktop/MachIntel/docs/security/SECURITY_CONTROLS.md)**:
   Catalog of active architectural security controls across Authentication, Authorization (RBAC), Input Sanitization, Path Traversal Defense, AI Guardrails, and Cryptographic Hygiene.

3. **[INCIDENT_RESPONSE.md](file:///Users/devtrivedi/Desktop/MachIntel/docs/security/INCIDENT_RESPONSE.md)**:
   Operational incident handling runbook covering compromise detection, token revocation, audit log extraction, and post-incident forensic analysis.

4. **[HARDENING_BASELINE.md](file:///Users/devtrivedi/Desktop/MachIntel/docs/operations/HARDENING_BASELINE.md)**:
   Verification matrix documenting control status, verification methodology, and operational limitations for production-like readiness.
