from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.core.risk_policy import (
    AlertSeverity,
    AlertStatus,
    DEFAULT_RISK_POLICY,
    RiskPolicyConfig,
    RiskState,
)
from backend.app.models.alert import Alert
from backend.app.models.audit import AuditLog
from backend.app.models.machine import Machine
from backend.app.models.risk import RiskAssessment
from backend.app.models.user import User


class AlertService:
    """
    Manages deterministic alert generation, deduplication, lifecycle transitions,
    and audit trail logging.
    """

    def __init__(self, db: Session, policy: RiskPolicyConfig = DEFAULT_RISK_POLICY):
        self.db = db
        self.policy = policy

    def process_risk_assessment(
        self,
        assessment: RiskAssessment,
        machine: Machine,
    ) -> Optional[Alert]:
        """
        Evaluates a RiskAssessment against alert generation and deduplication policy.
        Returns newly created Alert if triggered, or None if deduplicated / NORMAL state.
        """
        risk_state_enum = RiskState(assessment.risk_state)
        severity = self.policy.severity_mapping.get(risk_state_enum)

        # NORMAL produces no alert
        if severity is None or risk_state_enum == RiskState.NORMAL:
            return None

        # Build deterministic deduplication key
        dedup_key = f"{machine.id}:{assessment.risk_state}:{self.policy.policy_version}"

        # Deduplication check: Is there an existing OPEN or ACKNOWLEDGED alert with the same key?
        if self.policy.deduplicate_active_alerts:
            existing_active_alert = self.db.execute(
                select(Alert).where(
                    Alert.deduplication_key == dedup_key,
                    Alert.status.in_([AlertStatus.OPEN.value, AlertStatus.ACKNOWLEDGED.value]),
                )
            ).scalar_one_or_none()

            if existing_active_alert:
                return None  # Suppress duplicate alert generation

        # Build titles and descriptions
        if severity == AlertSeverity.CRITICAL:
            title = f"CRITICAL: Low RUL on {machine.machine_id}"
            description = (
                f"Asset {machine.machine_id} estimated RUL has dropped to {assessment.predicted_rul:.1f} cycles "
                f"(Health Index: {assessment.health_index:.3f}), entering CRITICAL analytical risk state."
            )
        elif severity == AlertSeverity.WARNING:
            title = f"ELEVATED: Degradation Trend on {machine.machine_id}"
            description = (
                f"Asset {machine.machine_id} estimated RUL is {assessment.predicted_rul:.1f} cycles "
                f"(Health Index: {assessment.health_index:.3f}), entering ELEVATED analytical risk state."
            )
        else:
            title = f"WATCH: Incipient Degradation on {machine.machine_id}"
            description = (
                f"Asset {machine.machine_id} estimated RUL is {assessment.predicted_rul:.1f} cycles "
                f"(Health Index: {assessment.health_index:.3f}), entering WATCH analytical risk state."
            )

        alert = Alert(
            machine_id=machine.id,
            risk_assessment_id=assessment.id,
            severity=severity.value,
            status=AlertStatus.OPEN.value,
            title=title,
            description=description,
            reason_codes=assessment.reason_codes,
            deduplication_key=dedup_key,
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def acknowledge_alert(self, alert_id: uuid.UUID, actor: User, comment: Optional[str] = None) -> Alert:
        """Transitions an alert from OPEN to ACKNOWLEDGED."""
        alert = self.db.get(Alert, alert_id)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

        if alert.status == AlertStatus.RESOLVED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot acknowledge an already resolved alert.",
            )

        now = datetime.now(timezone.utc)
        alert.status = AlertStatus.ACKNOWLEDGED.value
        alert.acknowledged_at = now
        alert.acknowledged_by_id = actor.id

        # Write audit log
        audit = AuditLog(
            actor_id=actor.id,
            action="ALERT_ACKNOWLEDGED",
            target_type="alert",
            target_id=str(alert.id),
            details={"comment": comment, "machine_id": str(alert.machine_id), "severity": alert.severity},
            created_at=now,
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def resolve_alert(self, alert_id: uuid.UUID, actor: User, comment: Optional[str] = None) -> Alert:
        """Transitions an alert to RESOLVED."""
        alert = self.db.get(Alert, alert_id)
        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

        now = datetime.now(timezone.utc)
        alert.status = AlertStatus.RESOLVED.value
        alert.resolved_at = now
        alert.resolved_by_id = actor.id

        # Write audit log
        audit = AuditLog(
            actor_id=actor.id,
            action="ALERT_RESOLVED",
            target_type="alert",
            target_id=str(alert.id),
            details={"comment": comment, "machine_id": str(alert.machine_id), "severity": alert.severity},
            created_at=now,
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def list_alerts(
        self,
        status_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        machine_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Alert], int]:
        """Returns bounded paginated list of alerts with optional status, severity, and machine filters."""
        stmt = select(Alert)

        if status_filter:
            stmt = stmt.where(Alert.status == status_filter)
        if severity_filter:
            stmt = stmt.where(Alert.severity == severity_filter)
        if machine_id:
            try:
                m_uuid = uuid.UUID(machine_id)
                stmt = stmt.where((Alert.machine_id == m_uuid) | (Alert.machine.has(Machine.machine_id == machine_id)))
            except (ValueError, AttributeError):
                stmt = stmt.where(Alert.machine.has(Machine.machine_id == machine_id))

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        paginated = (
            stmt.order_by(Alert.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(paginated).scalars().all())
        return items, total

    def get_alert_summary(self) -> Dict[str, Any]:
        """Aggregates alert counts for Dashboard and Alert Console."""
        total = self.db.scalar(select(func.count(Alert.id))) or 0
        open_cnt = self.db.scalar(select(func.count(Alert.id)).where(Alert.status == AlertStatus.OPEN.value)) or 0
        ack_cnt = self.db.scalar(select(func.count(Alert.id)).where(Alert.status == AlertStatus.ACKNOWLEDGED.value)) or 0
        res_cnt = self.db.scalar(select(func.count(Alert.id)).where(Alert.status == AlertStatus.RESOLVED.value)) or 0

        crit_open = self.db.scalar(
            select(func.count(Alert.id)).where(
                Alert.status == AlertStatus.OPEN.value,
                Alert.severity == AlertSeverity.CRITICAL.value,
            )
        ) or 0
        warn_open = self.db.scalar(
            select(func.count(Alert.id)).where(
                Alert.status == AlertStatus.OPEN.value,
                Alert.severity == AlertSeverity.WARNING.value,
            )
        ) or 0
        info_open = self.db.scalar(
            select(func.count(Alert.id)).where(
                Alert.status == AlertStatus.OPEN.value,
                Alert.severity == AlertSeverity.INFO.value,
            )
        ) or 0

        by_severity = {
            "CRITICAL": self.db.scalar(select(func.count(Alert.id)).where(Alert.severity == "CRITICAL")) or 0,
            "WARNING": self.db.scalar(select(func.count(Alert.id)).where(Alert.severity == "WARNING")) or 0,
            "INFO": self.db.scalar(select(func.count(Alert.id)).where(Alert.severity == "INFO")) or 0,
        }

        by_status = {
            "OPEN": open_cnt,
            "ACKNOWLEDGED": ack_cnt,
            "RESOLVED": res_cnt,
        }

        return {
            "total_alerts": total,
            "open_alerts": open_cnt,
            "acknowledged_alerts": ack_cnt,
            "resolved_alerts": res_cnt,
            "critical_open_alerts": crit_open,
            "warning_open_alerts": warn_open,
            "info_open_alerts": info_open,
            "by_severity": by_severity,
            "by_status": by_status,
        }
