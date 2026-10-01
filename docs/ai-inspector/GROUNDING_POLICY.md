# AI Inspector — Grounding Policy & Evidence Citation

## Authoritative Grounding Rules

The MachIntel AI Inspector is strictly governed by the following analytical grounding principles:

### 1. Evidence-Grounded Synthesis
- Every factual claim regarding machine condition, remaining operational lifespan, risk classification, or optical surface defect must cite one or more actual `evidence_id` values retrieved during the investigation.
- If data is absent, stale, or ambiguous, the AI Inspector must explicitly state that evidence is unavailable. It must **never** fabricate synthetic metrics, timestamps, or observations.

### 2. Distinguish Observed vs. Derived Data
- The Inspector explicitly separates raw observed telemetry (e.g. sensor vibration, temperatures) from model-derived inferences (e.g. linear regression RUL estimates, PatchCore anomaly scores).
- Model-derived metrics are stated alongside their model identifier and policy version (e.g. `cmapss-rul-linear-v1.0.0`, `risk-policy-v1.0.0`).

### 3. No Uncalibrated Probabilities or Guaranteed Failures
- The Inspector strictly uses non-absolute analytical terminology:
  - **Acceptable**: "The latest estimated RUL is 34.5 cycles at observation cycle 192", "Risk assessment is ELEVATED under risk-policy-v1.0.0", "Anomaly score of 3.42 exceeds process threshold 2.8155".
  - **Prohibited**: "The machine will fail in 34 cycles", "There is a 94.7% chance of catastrophic breakdown", "Visual defect caused the turbofan damage".
- Unless a calibrated probabilistic model is actively running and persisted in evidence, confidence numbers must **never** be invented.

### 4. Cross-Domain Separation Enforcement
- NASA C-MAPSS FD001 is a gas turbine turbofan degradation dataset.
- MVTec AD metal_nut is an optical surface texture benchmark dataset.
- There exists no common physical machine, physical timeline, or causal coupling between them.
- Any user question asking whether an optical defect caused engine degradation must be unequivocally rejected with a formal explanation of domain isolation.

---

## Hallucinated Citation Stripping Mechanism

The `InvestigationOrchestrator` implements an automated post-generation sanitizer:

```python
# Extract all evidence_ids actually returned by registered tool executions
valid_evidence_ids = orchestrator.collect_tool_evidence_ids()

# Validate citations returned by provider
grounded_citations = []
hallucinated_citations = []

for citation in response.evidence:
    if citation.evidence_id in valid_evidence_ids:
        grounded_citations.append(citation)
    else:
        hallucinated_citations.append(citation)

# Overwrite with strictly validated citations
response.evidence = grounded_citations

if hallucinated_citations:
    response.limitations.append(
        f"Stripped {len(hallucinated_citations)} unverified citation(s) not returned by tool executions."
    )
```

This prevents the LLM from synthesizing plausible-looking UUIDs or referencing records that were not verified in the active session.
