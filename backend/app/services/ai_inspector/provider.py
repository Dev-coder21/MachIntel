from abc import ABC, abstractmethod
import json
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.ai_inspector.grounding_policy import (
    CROSS_DOMAIN_REJECTION_EXPLANATION,
    SYSTEM_GROUNDING_PROMPT,
    UNAVAILABLE_PROVIDER_EXPLANATION,
)


class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    async def generate_response(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generates a structured investigation response containing:
        - answer: str
        - evidence_citations: list of dicts (evidence_id, domain, type, explanation, etc.)
        - limitations: list of str
        - status: str (COMPLETED, PROVIDER_UNAVAILABLE, FAILED)
        """
        pass


class UnavailableProvider(BaseLLMProvider):
    """Fallback provider when no external LLM credentials or testing mock are configured."""

    @property
    def provider_name(self) -> str:
        return "none"

    @property
    def model_name(self) -> str:
        return "none"

    def is_available(self) -> bool:
        return False

    async def generate_response(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "status": "PROVIDER_UNAVAILABLE",
            "answer": "AI Inspector provider is unavailable. Configure AI_INSPECTOR_API_KEY in backend environment to enable natural language synthesis.",
            "evidence_citations": [],
            "limitations": [UNAVAILABLE_PROVIDER_EXPLANATION],
        }


class DeterministicTestProvider(BaseLLMProvider):
    """
    Deterministic test provider for comprehensive CI/CD and offline verification.
    Interprets retrieved tool results rigorously, grounds answers in real evidence IDs,
    enforces prompt-injection rejection, and strictly isolates evidence domains.
    """

    @property
    def provider_name(self) -> str:
        return "deterministic-test"

    @property
    def model_name(self) -> str:
        return "machintel-grounded-v1"

    def is_available(self) -> bool:
        return True

    async def generate_response(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        q_lower = question.lower()

        # 1. Prompt-Injection / Security Defenses
        if any(
            bad in q_lower
            for bad in [
                "ignore previous",
                "ignore all instructions",
                "reveal",
                "password",
                "secret_key",
                "api_key",
                "drop table",
                "delete from",
                "system prompt",
                "read .env",
            ]
        ):
            return {
                "status": "COMPLETED",
                "answer": (
                    "Security Notice: The requested operation or query pattern was refused. "
                    "The AI Inspector operates exclusively in read-only investigation mode over "
                    "persisted evidence and ignores instructions that attempt to alter policy, "
                    "access credentials, or perform system mutations."
                ),
                "evidence_citations": [],
                "limitations": [
                    "Prompt-injection attempt neutralized; system policy remains dominant.",
                    "No system credentials or hidden instructions can be exposed.",
                ],
            }

        # 2. Cross-Domain Causal Query Detection
        has_turbofan = any(w in q_lower for w in ["machine", "turbofan", "rul", "engine"])
        has_inspection = any(w in q_lower for w in ["defect", "nut", "metal_nut", "surface", "visual"])
        if has_turbofan and has_inspection and ("cause" in q_lower or "relationship" in q_lower or "due to" in q_lower):
            return {
                "status": "COMPLETED",
                "answer": (
                    f"Domain Separation Alert: {CROSS_DOMAIN_REJECTION_EXPLANATION} "
                    "MachIntel does not infer or establish physical causality between these datasets."
                ),
                "evidence_citations": [],
                "limitations": [
                    "NASA C-MAPSS and MVTec AD are completely independent evidence domains.",
                    "No cross-domain causal inferences are permitted.",
                ],
            }

        # 3. Grounded Synthesis from Tool Results
        citations: List[Dict[str, Any]] = []
        answer_parts: List[str] = []
        limitations: List[str] = [
            "Estimations reflect persisted model and policy configurations without live autonomous overrides.",
            "RUL point predictions are deterministic baselines without probabilistic calibration intervals.",
        ]

        for tr in tool_results:
            tool_name = tr.get("tool_name")
            output = tr.get("output", {})
            if not isinstance(output, dict):
                continue

            # Machine Health Summary Tool
            if tool_name == "get_machine_health_summary" and output.get("found"):
                mid = output.get("machine_id")
                cycle = output.get("observation_cycle")
                rul = output.get("predicted_rul")
                hi = output.get("health_index")
                state = output.get("operational_state")
                risk = output.get("risk_state")
                reasons = output.get("reason_codes", [])
                policy = output.get("risk_policy_version")

                answer_parts.append(
                    f"Machine {mid} at observation cycle {cycle} is evaluated in {risk} risk state "
                    f"(operational condition: {state}) under policy {policy or 'risk-policy-v1.0.0'}. "
                    f"The prognostic model estimates an RUL of {rul:.2f} cycles with normalized Health Index of {hi:.3f}. "
                    f"Active reason codes: {', '.join(reasons) if reasons else 'NONE'}."
                )

                for ev in output.get("evidence_citations", []):
                    citations.append({
                        "evidence_id": ev.get("evidence_id"),
                        "domain": ev.get("domain", "MACHINE_HEALTH"),
                        "type": ev.get("type", "RISK_ASSESSMENT"),
                        "source": "NASA C-MAPSS FD001",
                        "observation_cycle": ev.get("cycle"),
                        "quality_state": ev.get("quality_state", "VERIFIED"),
                        "explanation": f"Grounded prognostic assessment for {mid} at cycle {cycle}.",
                        "value_summary": f"RUL: {rul:.1f} cycles | HI: {hi:.3f} | State: {risk}",
                    })

            # Machine Alerts Tool
            elif tool_name == "get_machine_alerts" and output.get("alerts"):
                alerts = output.get("alerts", [])
                mid = output.get("machine_id")
                open_alerts = [a for a in alerts if a.get("status") == "OPEN"]
                answer_parts.append(
                    f"Machine {mid} has {len(open_alerts)} open alert(s) (total recorded: {len(alerts)}). "
                    f"Latest alert: '{alerts[0].get('title')}' with severity {alerts[0].get('severity')}."
                )

            # Machine Risk Tool
            elif tool_name == "get_machine_risk" and output.get("current_risk_state"):
                mid = output.get("machine_id")
                state = output.get("current_risk_state")
                reasons = output.get("latest_reason_codes", [])
                transitions = output.get("recent_transitions", [])
                trans_msg = (
                    f" Recent transition: from {transitions[0].get('from_state')} to {transitions[0].get('to_state')}."
                    if transitions else ""
                )
                answer_parts.append(
                    f"Current risk state for {mid} is {state} with reasons: {', '.join(reasons)}.{trans_msg}"
                )

            # Inspection Results Tool
            elif tool_name == "get_inspection_result" and output.get("found"):
                score = output.get("image_level_score")
                thresh = output.get("threshold_applied")
                decision = output.get("decision")
                defect = output.get("defect_class")
                is_gt = output.get("is_ground_truth_defect")
                ev_id = output.get("evidence_id")

                answer_parts.append(
                    f"Optical visual inspection result is classified as {decision} with PatchCore anomaly score "
                    f"of {score:.4f} against calibrated threshold of {thresh:.4f} (defect category: {defect}). "
                    f"Ground truth verification: {'Defective' if is_gt else 'Normal'}."
                )
                if ev_id:
                    citations.append({
                        "evidence_id": ev_id,
                        "domain": "VISUAL_INSPECTION",
                        "type": "INSPECTION_RESULT",
                        "source": "MVTec AD metal_nut",
                        "observation_cycle": None,
                        "quality_state": output.get("evidence_quality", "VERIFIED"),
                        "explanation": f"PatchCore WideResNet-50-2 anomaly detection result for {defect}.",
                        "value_summary": f"Score: {score:.4f} | Threshold: {thresh:.4f} | Decision: {decision}",
                    })

            # Maintenance Work Orders Tool
            elif tool_name == "get_maintenance_work_orders" and output.get("work_orders"):
                wos = output.get("work_orders", [])
                answer_parts.append(
                    f"Retrieved {len(wos)} maintenance work order(s). "
                    f"Latest order: '{wos[0].get('title')}' with priority {wos[0].get('priority')} and status {wos[0].get('status')}."
                )

            # Search Evidence Tool
            elif tool_name == "search_evidence" and output.get("evidence_records"):
                records = output.get("evidence_records", [])
                for r in records[:3]:
                    citations.append({
                        "evidence_id": r.get("evidence_id"),
                        "domain": r.get("domain"),
                        "type": r.get("evidence_type"),
                        "source": r.get("source"),
                        "observation_cycle": r.get("observation_cycle"),
                        "quality_state": r.get("quality_state"),
                        "explanation": r.get("explanation"),
                        "value_summary": f"Source Ref: {r.get('source_reference')}",
                    })

        final_answer = " ".join(answer_parts) if answer_parts else (
            "Investigation complete. Relevant operational evidence was queried; no anomalous findings "
            "or active alerts were observed for the specified parameters."
        )

        return {
            "status": "COMPLETED",
            "answer": final_answer,
            "evidence_citations": citations,
            "limitations": limitations,
        }


class OpenAICompatibleProvider(BaseLLMProvider):
    """Integration for OpenAI or OpenAI-compatible endpoints."""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None, timeout: int = 30):
        self._api_key = api_key
        self._model = model
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "openai-compatible"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def generate_response(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = (
            f"User Question: {question}\n\n"
            f"Context: {json.dumps(context or {})}\n\n"
            f"Tool Execution Results:\n{json.dumps(tool_results, indent=2)}\n\n"
            "Format your response as valid JSON matching schema:\n"
            "{\n"
            '  "answer": "string",\n'
            '  "evidence_citations": [{"evidence_id": "string", "domain": "string", "type": "string", "explanation": "string"}],\n'
            '  "limitations": ["string"]\n'
            "}"
        )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_GROUNDING_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post(f"{self._base_url}/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return {
                    "status": "COMPLETED",
                    "answer": parsed.get("answer", ""),
                    "evidence_citations": parsed.get("evidence_citations", []),
                    "limitations": parsed.get("limitations", []),
                }
        except Exception as exc:
            logger.error(f"OpenAI provider invocation failed: {exc}")
            return {
                "status": "FAILED",
                "answer": f"Investigation generation failed due to provider error: {str(exc)}",
                "evidence_citations": [],
                "limitations": ["Provider API call failed; tool evidence remains available."],
            }


class AnthropicProvider(BaseLLMProvider):
    """Integration for Anthropic Claude endpoints."""

    def __init__(self, api_key: str, model: str, timeout: int = 30):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def generate_response(
        self,
        question: str,
        context: Optional[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = (
            f"User Question: {question}\n\n"
            f"Context: {json.dumps(context or {})}\n\n"
            f"Tool Execution Results:\n{json.dumps(tool_results, indent=2)}\n\n"
            "Format your response as valid JSON matching schema:\n"
            "{\n"
            '  "answer": "string",\n'
            '  "evidence_citations": [{"evidence_id": "string", "domain": "string", "type": "string", "explanation": "string"}],\n'
            '  "limitations": ["string"]\n'
            "}"
        )

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self._model,
            "max_tokens": 1024,
            "system": SYSTEM_GROUNDING_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                content = data["content"][0]["text"]
                # Parse JSON block
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                else:
                    parsed = json.loads(content)
                return {
                    "status": "COMPLETED",
                    "answer": parsed.get("answer", ""),
                    "evidence_citations": parsed.get("evidence_citations", []),
                    "limitations": parsed.get("limitations", []),
                }
        except Exception as exc:
            logger.error(f"Anthropic provider invocation failed: {exc}")
            return {
                "status": "FAILED",
                "answer": f"Investigation generation failed due to provider error: {str(exc)}",
                "evidence_citations": [],
                "limitations": ["Provider API call failed; tool evidence remains available."],
            }


def get_llm_provider() -> BaseLLMProvider:
    """Factory creating the configured LLM provider from settings."""
    provider_type = (settings.AI_INSPECTOR_PROVIDER or "mock").strip().lower()

    if provider_type in ["mock", "deterministic", "test"]:
        return DeterministicTestProvider()

    if provider_type == "openai" or provider_type == "openai-compatible":
        if not settings.AI_INSPECTOR_API_KEY:
            logger.warning("AI_INSPECTOR_API_KEY missing for OpenAI provider. Falling back to UnavailableProvider.")
            return UnavailableProvider()
        return OpenAICompatibleProvider(
            api_key=settings.AI_INSPECTOR_API_KEY,
            model=settings.AI_INSPECTOR_MODEL or "gpt-4o",
            base_url=settings.AI_INSPECTOR_BASE_URL,
            timeout=settings.AI_INSPECTOR_TIMEOUT_SECONDS,
        )

    if provider_type == "anthropic":
        if not settings.AI_INSPECTOR_API_KEY:
            logger.warning("AI_INSPECTOR_API_KEY missing for Anthropic provider. Falling back to UnavailableProvider.")
            return UnavailableProvider()
        return AnthropicProvider(
            api_key=settings.AI_INSPECTOR_API_KEY,
            model=settings.AI_INSPECTOR_MODEL or "claude-3-5-sonnet-20241022",
            timeout=settings.AI_INSPECTOR_TIMEOUT_SECONDS,
        )

    return UnavailableProvider()
