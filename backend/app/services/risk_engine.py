from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.core.risk_policy import (
    DEFAULT_RISK_POLICY,
    RiskPolicyConfig,
    RiskState,
)
from backend.app.models.machine import Machine
from backend.app.models.prediction import Prediction
from backend.app.models.risk import RiskAssessment, RiskTransition
from backend.app.schemas.evidence import EvidenceObject


class RiskEngine:
    """
    Deterministic, explainable risk assessment engine.
    Interprets empirical RUL predictions against explicit, versioned thresholds
    to generate auditable risk states, structured reason codes, and evidence records.
    """

    def __init__(self, db: Session, policy: RiskPolicyConfig = DEFAULT_RISK_POLICY):
        self.db = db
        self.policy = policy

    def evaluate_prediction(
        self,
        prediction: Prediction,
        machine: Machine,
        persist: bool = True,
    ) -> RiskAssessment:
        """
        Evaluates a prediction record deterministically and generates a RiskAssessment.
        Checks for prior historical predictions to detect rapid degradation trends.
        """
        hi = prediction.health_index
        rul = prediction.predicted_rul
        cycle = prediction.observation_cycle

        # 1. Deterministic State Determination
        if hi >= self.policy.threshold_normal_min:
            risk_state = RiskState.NORMAL
        elif hi >= self.policy.threshold_watch_min:
            risk_state = RiskState.WATCH
        elif hi >= self.policy.threshold_elevated_min:
            risk_state = RiskState.ELEVATED
        else:
            risk_state = RiskState.CRITICAL

        # 2. Structured Reason Codes Determination
        reason_codes: List[str] = []

        if risk_state == RiskState.NORMAL:
            reason_codes.append("HEALTH_INDEX_NORMAL")
        elif risk_state == RiskState.WATCH:
            reason_codes.append("HEALTH_INDEX_WATCH")
        elif risk_state == RiskState.ELEVATED:
            reason_codes.append("HEALTH_INDEX_ELEVATED")
        elif risk_state == RiskState.CRITICAL:
            reason_codes.append("HEALTH_INDEX_CRITICAL")

        # Threshold proximity reason codes
        if rul < 6.25:
            reason_codes.append("RUL_BELOW_CRITICAL_THRESHOLD")
        elif rul < self.policy.rul_elevated_cycles:
            reason_codes.append("RUL_BELOW_ELEVATED_THRESHOLD")
        elif rul < self.policy.rul_watch_cycles:
            reason_codes.append("RUL_BELOW_WATCH_THRESHOLD")

        # 3. Strictly backward-looking trend degradation check
        prior_pred_stmt = (
            select(Prediction)
            .where(
                Prediction.machine_id == machine.id,
                Prediction.observation_cycle < cycle,
            )
            .order_by(Prediction.observation_cycle.desc())
            .limit(1)
        )
        prior_pred = self.db.execute(prior_pred_stmt).scalar_one_or_none()

        if prior_pred:
            cycle_delta = cycle - prior_pred.observation_cycle
            rul_drop = prior_pred.predicted_rul - rul
            if 0 < cycle_delta <= self.policy.rapid_decline_max_cycles and rul_drop >= self.policy.rapid_decline_rul_delta:
                reason_codes.append("RAPID_RUL_DECLINE")

        # 4. Standardized Evidence Object Generation
        model_version_str = (
            prediction.model_version.model_id if prediction.model_version else "active"
        )
        dataset_str = (
            prediction.dataset.dataset_name if prediction.dataset else "NASA-C-MAPSS-FD001"
        )

        rul_evidence = EvidenceObject(
            machine_id=machine.machine_id,
            evidence_type="RUL_PREDICTION",
            source="NASA_CMAPSS_FD001_PREDICTION",
            source_reference=str(prediction.id),
            observation_cycle=cycle,
            observed_at=prediction.created_at,
            value=rul,
            unit="cycles",
            confidence=None,  # Not calibrated; strictly omitted
            provenance={
                "dataset": dataset_str,
                "model_version": model_version_str,
                "feature_version": prediction.feature_engineering_version,
            },
            model_version=model_version_str,
            feature_version=prediction.feature_engineering_version,
        )

        hi_evidence = EvidenceObject(
            machine_id=machine.machine_id,
            evidence_type="HEALTH_INDEX",
            source="DETERMINISTIC_HI_MAPPING",
            source_reference=str(prediction.id),
            observation_cycle=cycle,
            observed_at=prediction.created_at,
            value=round(hi, 4),
            unit="normalized [0,1]",
            confidence=None,
            provenance={
                "clamped_formula": "clamp(predicted_RUL / 125.0, 0, 1)",
                "policy_version": self.policy.policy_version,
            },
            model_version=model_version_str,
            feature_version=prediction.feature_engineering_version,
        )

        evidence_references = [
            rul_evidence.model_dump(mode="json"),
            hi_evidence.model_dump(mode="json"),
        ]

        # 5. Human-readable explainable text
        if risk_state == RiskState.NORMAL:
            detail_msg = "Operating within nominal parameter margins without significant high-pressure compressor degradation."
        elif risk_state == RiskState.WATCH:
            detail_msg = "Incipient sensor parameter drift observed across causal pressure and temperature channels."
        elif risk_state == RiskState.ELEVATED:
            detail_msg = "Substantial component degradation detected; remaining life approaching planned maintenance intervals."
        else:
            detail_msg = "Imminent end of operational cycle life threshold reached; urgent maintenance review indicated."

        explanation = (
            f"Analytical risk state: {risk_state.value}. "
            f"Estimated Remaining Useful Life: {rul:.1f} cycles (Health Index: {hi:.3f}). "
            f"Risk state derived from model output and configured policy '{self.policy.policy_version}'. "
            f"{detail_msg} "
            f"Analytical risk interpretation only; not a certified safety determination."
        )

        # 6. Create RiskAssessment Record
        assessment = RiskAssessment(
            machine_id=machine.id,
            prediction_id=prediction.id,
            risk_state=risk_state.value,
            health_index=round(hi, 4),
            predicted_rul=round(rul, 2),
            reason_codes=reason_codes,
            explanation=explanation,
            policy_version=self.policy.policy_version,
            evidence_references=evidence_references,
        )

        if persist:
            self.db.add(assessment)
            self.db.flush()

            # 7. Check for State Transition
            self._record_transition_if_changed(machine, assessment, cycle)
            self.db.commit()
            self.db.refresh(assessment)

        return assessment

    def _record_transition_if_changed(
        self,
        machine: Machine,
        current_assessment: RiskAssessment,
        current_cycle: int,
    ) -> Optional[RiskTransition]:
        """Records a RiskTransition if the state changed from the previous assessment."""
        prev_assessment = self.db.execute(
            select(RiskAssessment)
            .where(
                RiskAssessment.machine_id == machine.id,
                RiskAssessment.id != current_assessment.id,
            )
            .order_by(RiskAssessment.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if prev_assessment and prev_assessment.risk_state != current_assessment.risk_state:
            transition = RiskTransition(
                machine_id=machine.id,
                risk_assessment_id=current_assessment.id,
                from_state=prev_assessment.risk_state,
                to_state=current_assessment.risk_state,
                observation_cycle=current_cycle,
            )
            self.db.add(transition)
            return transition
        return None
