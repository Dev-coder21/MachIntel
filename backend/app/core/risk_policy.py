from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RiskState(str, Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class RiskPolicyConfig:
    """
    Explicit, versioned deterministic risk and alert configuration policy.
    Thresholds and mapping rules are strictly defined without scattered magic numbers.
    """
    policy_version: str = "risk-policy-v1.0.0"

    # Health Index thresholds
    # HI >= 0.70 -> NORMAL
    # 0.40 <= HI < 0.70 -> WATCH
    # 0.15 <= HI < 0.40 -> ELEVATED
    # HI < 0.15 -> CRITICAL
    threshold_normal_min: float = 0.70
    threshold_watch_min: float = 0.40
    threshold_elevated_min: float = 0.15

    # Corresponding RUL nominal equivalent caps (125 * threshold)
    rul_watch_cycles: float = 50.0      # 125 * 0.40
    rul_elevated_cycles: float = 18.75  # 125 * 0.15

    # Trend degradation parameters (strictly historical backward-looking)
    rapid_decline_rul_delta: float = 25.0    # Drop of >= 25 cycles
    rapid_decline_max_cycles: int = 10       # Occurring within <= 10 observed cycles

    # Alert severity mappings
    severity_mapping: Dict[RiskState, Optional[AlertSeverity]] = field(
        default_factory=lambda: {
            RiskState.NORMAL: None,
            RiskState.WATCH: AlertSeverity.INFO,
            RiskState.ELEVATED: AlertSeverity.WARNING,
            RiskState.CRITICAL: AlertSeverity.CRITICAL,
        }
    )

    # Deduplication policy: deduplicate on machine_id + risk_state while an alert is OPEN or ACKNOWLEDGED
    deduplicate_active_alerts: bool = True


DEFAULT_RISK_POLICY = RiskPolicyConfig()
