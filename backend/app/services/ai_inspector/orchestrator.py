from datetime import datetime, timezone
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.errors import ValidationException
from backend.app.core.logging import logger
from backend.app.models.ai_investigation import AIInvestigation
from backend.app.models.audit import AuditLog
from backend.app.models.evidence import EvidenceRecord
from backend.app.models.inspection import InspectionRun
from backend.app.models.machine import Machine
from backend.app.models.user import User
from backend.app.schemas.ai_investigation import (
    AIInvestigationResponse,
    EvidenceCitation,
    InvestigationContext,
    InvestigationTrace,
    ToolCallRecord,
)
from backend.app.services.ai_inspector.provider import BaseLLMProvider, get_llm_provider
from backend.app.services.ai_inspector.tools import tool_registry


class InvestigationOrchestrator:
    """
    Coordinates evidence-grounded AI investigations through strictly controlled,
    read-only tools, validating citations, preserving domain separation, and persisting
    audit records.
    """

    def __init__(self, db: Session, provider: Optional[BaseLLMProvider] = None):
        self.db = db
        self.provider = provider or get_llm_provider()
        self.max_tool_calls = settings.AI_INSPECTOR_MAX_TOOL_CALLS

    def _extract_machine_id(self, question: str, context: Optional[InvestigationContext]) -> Optional[str]:
        if context and context.machine_id:
            return context.machine_id.strip()

        # Look for explicit TURBOFAN-ENG-XXX pattern
        m = re.search(r"\bTURBOFAN-ENG-\d+\b", question, re.IGNORECASE)
        if m:
            return m.group(0).upper()

        # Look for "machine <number>" or "unit <number>"
        m2 = re.search(r"\b(?:machine|unit)\s*#?\s*(\d+)\b", question, re.IGNORECASE)
        if m2:
            num = int(m2.group(1))
            return f"TURBOFAN-ENG-{num:03d}"

        return None

    def _plan_tools(self, question: str, context: Optional[InvestigationContext]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Determines the bounded sequence of read-only tools to execute based on query intent and context.
        """
        planned: List[Tuple[str, Dict[str, Any]]] = []
        q_lower = question.lower()
        machine_id = self._extract_machine_id(question, context)

        # 1. Machine Health Domain Tools
        if machine_id:
            planned.append(("get_machine_health_summary", {"machine_id": machine_id}))

            if any(w in q_lower for w in ["alert", "warning", "alarm"]):
                planned.append(("get_machine_alerts", {"machine_id": machine_id, "limit": 5}))

            if any(w in q_lower for w in ["risk", "why", "reason", "transition", "status"]):
                planned.append(("get_machine_risk", {"machine_id": machine_id, "history_limit": 5}))

            if any(w in q_lower for w in ["prediction", "rul", "trajectory", "history", "trend"]):
                planned.append(("get_machine_predictions", {"machine_id": machine_id, "limit": 5}))

            if any(w in q_lower for w in ["maintenance", "work order", "repair", "service"]):
                planned.append(("get_maintenance_work_orders", {"machine_id": machine_id, "limit": 5}))

        # 2. Visual Inspection Domain Tools
        run_id_val = str(context.inspection_run_id) if context and context.inspection_run_id else None
        res_id_val = str(context.inspection_result_id) if context and context.inspection_result_id else None

        if res_id_val:
            planned.append(("get_inspection_result", {"result_id": res_id_val}))
        elif run_id_val:
            planned.append(("get_inspection_run", {"run_id": run_id_val}))
            planned.append(("get_inspection_results", {"run_id": run_id_val, "limit": 10}))
        elif any(w in q_lower for w in ["inspection", "metal_nut", "defect", "patchcore", "anomaly", "surface"]):
            # Find latest run
            stmt = select(InspectionRun).order_by(InspectionRun.created_at.desc()).limit(1)
            latest_run = self.db.execute(stmt).scalar_one_or_none()
            if latest_run:
                planned.append(("get_inspection_run", {"run_id": str(latest_run.id)}))
                if any(w in q_lower for w in ["scratch", "bent", "color", "flip"]):
                    for d_class in ["scratch", "bent", "color", "flip"]:
                        if d_class in q_lower:
                            planned.append(("get_inspection_results", {"run_id": str(latest_run.id), "defect_class": d_class, "limit": 5}))
                            break
                else:
                    planned.append(("get_inspection_results", {"run_id": str(latest_run.id), "limit": 5}))
            else:
                planned.append(("get_inspection_runs", {"limit": 5}))

        # 3. General Maintenance Query (without explicit machine)
        if not machine_id and any(w in q_lower for w in ["maintenance", "work order", "open orders"]):
            planned.append(("get_maintenance_work_orders", {"limit": 10}))

        # 4. Fallback search_evidence if no targeted tool matched
        if not planned:
            domain_filter = context.domain if context and context.domain else None
            planned.append(("search_evidence", {"domain": domain_filter, "limit": 10}))

        return planned[: self.max_tool_calls]

    async def execute_investigation(
        self,
        question: str,
        current_user: User,
        context: Optional[InvestigationContext] = None,
    ) -> AIInvestigationResponse:
        """
        Executes an end-to-end investigation with bounded tool execution, citation verification,
        and audit logging.
        """
        investigation_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc)

        tool_plan = self._plan_tools(question, context)
        tool_records: List[ToolCallRecord] = []
        raw_tool_results: List[Dict[str, Any]] = []
        domains_consulted: Set[str] = set()
        available_evidence_ids: Set[str] = set()

        for tool_name, tool_args in tool_plan:
            tool_def = tool_registry.get(tool_name)
            if not tool_def:
                logger.warning(f"Requested tool '{tool_name}' not in registry. Skipping.")
                continue

            t0 = time.perf_counter()
            tool_status = "SUCCESS"
            output: Dict[str, Any] = {}
            evidence_ids_in_tool: List[str] = []

            try:
                # Execute tool safely inside nested savepoint
                with self.db.begin_nested():
                    output = tool_def.func(db=self.db, **tool_args)

                # Collect domain
                if tool_def.domain != "CROSS_DOMAIN":
                    domains_consulted.add(tool_def.domain)
                elif "domain" in tool_args and tool_args["domain"]:
                    domains_consulted.add(tool_args["domain"])

                # Harvest returned evidence IDs for validation
                if "evidence_id" in output and output["evidence_id"]:
                    evidence_ids_in_tool.append(str(output["evidence_id"]))
                if "evidence_citations" in output and isinstance(output["evidence_citations"], list):
                    for cit in output["evidence_citations"]:
                        if isinstance(cit, dict) and cit.get("evidence_id"):
                            evidence_ids_in_tool.append(str(cit["evidence_id"]))
                if "evidence_records" in output and isinstance(output["evidence_records"], list):
                    for rec in output["evidence_records"]:
                        if isinstance(rec, dict) and rec.get("evidence_id"):
                            evidence_ids_in_tool.append(str(rec["evidence_id"]))
                if "evidence_references" in output and isinstance(output["evidence_references"], list):
                    for ref in output["evidence_references"]:
                        if isinstance(ref, str):
                            evidence_ids_in_tool.append(ref)

            except Exception as exc:
                logger.error(f"Tool execution failed for '{tool_name}': {exc}")
                tool_status = "FAILED"
                output = {"error": str(exc)}

            duration_ms = (time.perf_counter() - t0) * 1000.0
            available_evidence_ids.update(evidence_ids_in_tool)

            tool_records.append(
                ToolCallRecord(
                    tool_name=tool_name,
                    arguments=tool_args,
                    status=tool_status,
                    duration_ms=round(duration_ms, 2),
                    evidence_ids_returned=evidence_ids_in_tool,
                )
            )

            raw_tool_results.append({
                "tool_name": tool_name,
                "arguments": tool_args,
                "status": tool_status,
                "output": output,
            })

        # Generate structured response from provider
        context_dict = context.model_dump(exclude_none=True) if context else {}
        provider_resp = await self.provider.generate_response(
            question=question,
            context=context_dict,
            tool_results=raw_tool_results,
        )

        resp_status = provider_resp.get("status", "COMPLETED")
        raw_citations = provider_resp.get("evidence_citations", [])
        validated_citations: List[EvidenceCitation] = []

        # Validate that cited evidence IDs were actually returned during the investigation
        for cit in raw_citations:
            eid = cit.get("evidence_id")
            if not eid:
                continue

            # Must exist either in tool output or verified in DB
            if eid in available_evidence_ids:
                validated_citations.append(
                    EvidenceCitation(
                        evidence_id=eid,
                        domain=cit.get("domain", "MACHINE_HEALTH"),
                        type=cit.get("type", "UNKNOWN"),
                        source=cit.get("source", "PERSISTED_DATABASE"),
                        observation_cycle=cit.get("observation_cycle"),
                        quality_state=cit.get("quality_state", "VERIFIED"),
                        explanation=cit.get("explanation"),
                        value_summary=cit.get("value_summary"),
                    )
                )
            else:
                # Verify in database before rejecting to handle valid cross-references
                try:
                    eid_uuid = uuid.UUID(eid)
                    db_rec = self.db.get(EvidenceRecord, eid_uuid)
                    if db_rec:
                        validated_citations.append(
                            EvidenceCitation(
                                evidence_id=str(db_rec.id),
                                domain=db_rec.domain,
                                type=db_rec.evidence_type,
                                source=db_rec.source,
                                observation_cycle=db_rec.observation_cycle,
                                quality_state=db_rec.quality_state,
                                explanation=cit.get("explanation") or db_rec.explanation,
                                value_summary=f"Record: {db_rec.entity_type} {db_rec.entity_id}",
                            )
                        )
                    else:
                        logger.warning(f"Stripped hallucinated evidence ID: {eid}")
                except Exception:
                    logger.warning(f"Stripped invalid evidence ID: {eid}")

        # Construct final structured response
        completed_at = datetime.now(timezone.utc)
        trace = InvestigationTrace(
            tool_calls=tool_records,
            domains_consulted=sorted(list(domains_consulted)),
            completed=True,
        )

        response = AIInvestigationResponse(
            id=investigation_id,
            question=question,
            status=resp_status,
            answer=provider_resp.get("answer", ""),
            evidence=validated_citations,
            limitations=provider_resp.get("limitations", []),
            investigation=trace,
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            created_at=started_at,
            completed_at=completed_at,
            error_message=provider_resp.get("error_message"),
        )

        # Persist Investigation to database
        db_investigation = AIInvestigation(
            id=investigation_id,
            user_id=current_user.id,
            question=question,
            context_data=context_dict if context_dict else None,
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            status=resp_status,
            tool_calls=[t.model_dump() for t in tool_records],
            domains_consulted=list(domains_consulted),
            evidence_ids_referenced=[c.evidence_id for c in validated_citations],
            structured_response=response.model_dump(mode="json"),
            error_message=response.error_message,
            started_at=started_at,
            completed_at=completed_at,
        )
        self.db.add(db_investigation)

        # Emit structured AuditLog entry
        audit = AuditLog(
            id=uuid.uuid4(),
            actor_id=current_user.id,
            action="AI_INVESTIGATION_COMPLETED" if resp_status == "COMPLETED" else f"AI_INVESTIGATION_{resp_status}",
            target_type="AI_INVESTIGATION",
            target_id=str(investigation_id),
            details={
                "question": question[:200],
                "tools_executed": [t.tool_name for t in tool_records],
                "evidence_count": len(validated_citations),
                "domains_consulted": list(domains_consulted),
                "provider": self.provider.provider_name,
            },
            created_at=completed_at,
        )
        self.db.add(audit)
        self.db.commit()

        return response
