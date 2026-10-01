# AI Inspector — Architecture & Orchestration

## High-Level Topology

```
Authorized User (JWT: VIEWER / OPERATOR / ADMIN)
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ FastAPI Router (/api/v1/ai-inspector)                  │
│ • Validates Pydantic Request (InvestigationCreateRequest)│
│ • Enforces RBAC Dependencies (current_active_user)     │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ Investigation Orchestrator                            │
│ • Context Validation & Normalization                   │
│ • Safe Nested Transaction (`db.begin_nested()`)       │
│ • Bounded Execution Guard (max 5 tool calls)           │
│ • Provider Execution & Fallback Handler                │
│ • Strict Citation Verification vs. Tool Results        │
│ • Audit Trail Persistence (`AIInvestigation` entity)   │
└───────────────────────┬────────────────────────────────┘
                        │
       ┌────────────────┴────────────────┐
       ▼                                 ▼
┌─────────────────────────┐   ┌──────────────────────────┐
│ LLM Provider Engine     │   │ Controlled Tool Registry │
│ • Provider Abstraction  │   │ • 15 Typed Tools         │
│ • Grounding System Prompt│   │ • Strict Read-Only Policy│
│ • Prompt Injection Shield│   │ • Input Sanitizers       │
│ • Deterministic Fallback│   │ • Domain Isolation Guard │
└─────────────────────────┘   └─────────────┬────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────┐
                              │ Existing Domain Services │
                              │ • Machine / Prediction   │
                              │ • Risk / Alert Engine    │
                              │ • Visual Inspection      │
                              │ • Evidence Intelligence  │
                              │ • Maintenance Workflow   │
                              └─────────────┬────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────┐
                              │ PostgreSQL 16 Store      │
                              │ • Authoritative Evidence │
                              │ • Zero Shadow Data       │
                              └──────────────────────────┘
```

---

## Bounded Execution & Guardrails

The `InvestigationOrchestrator` implements strict deterministic bounds to eliminate runaway tool loops, latency spikes, or denial-of-service risks:

1. **Max Tool Calls**: Capped at `AI_INSPECTOR_MAX_TOOL_CALLS = 5`. If the LLM generates a plan requesting more than 5 tools, the list is truncated and a limitation notice is recorded.
2. **Execution Timeout**: Capped at `AI_INSPECTOR_TIMEOUT_SECONDS = 30`. Long-running operations are terminated gracefully.
3. **Transaction Isolation**: Each tool call runs inside a SQLAlchemy savepoint (`with self.db.begin_nested():`). If any tool raises a handled domain error or validation failure, the outer database transaction remains uncorrupted.
4. **Data Truncation**: Collection tools enforce strict upper limits (e.g. `limit <= 50`, `history_limit <= 20`) to prevent LLM context exhaustion and memory bloat.

---

## Response Lifecycle

1. **Request Ingestion**: User submits question with optional contextual filters (`machine_id`, `inspection_run_id`, `domain`).
2. **Tool Selection / Query Planning**: The provider inspects the query and available tool definitions to formulate an execution plan.
3. **Controlled Tool Execution**: Orchestrator validates tool arguments against parameter sanitizers (regex UUID check, alphanumeric machine ID check, SQL pattern rejection) and invokes the internal service.
4. **Grounded Synthesis**: Tool results are structured into JSON evidence payloads and passed to the LLM alongside the `SYSTEM_GROUNDING_PROMPT`.
5. **Post-Processing Citation Verification**:
   - The orchestrator collects all valid `evidence_id` values returned by the tools during execution.
   - Any citation in the LLM response whose `evidence_id` was not returned by a tool call is flagged as hallucinated and stripped from the response.
   - If citations are stripped, a formal limitation warning is appended to the response.
6. **Audit Emission**: The complete question, trace, duration, citations, and structured findings are saved to the `ai_investigations` table in PostgreSQL.
