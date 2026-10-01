import React from "react";
import { RiskState } from "@/types/risk";
import { UserRole } from "@/types/auth";
import { AlertSeverity, AlertStatus } from "@/types/alert";

type BadgeType = RiskState | UserRole | AlertSeverity | AlertStatus | "ACTIVE" | "INACTIVE" | "ONLINE" | "OFFLINE";

interface StatusBadgeProps {
  status: BadgeType;
  label?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, className = "" }) => {
  const getBadgeStyles = () => {
    switch (status) {
      case "NORMAL":
      case "ACTIVE":
      case "ONLINE":
      case "RESOLVED":
        return {
          color: "var(--risk-normal)",
          backgroundColor: "var(--risk-normal-bg)",
          borderColor: "rgba(16, 185, 129, 0.3)",
          dotColor: "var(--risk-normal)",
        };
      case "WATCH":
      case "INFO":
        return {
          color: "var(--risk-watch)",
          backgroundColor: "var(--risk-watch-bg)",
          borderColor: "rgba(6, 182, 212, 0.3)",
          dotColor: "var(--risk-watch)",
        };
      case "ELEVATED":
      case "WARNING":
      case "OPEN":
        return {
          color: "var(--risk-elevated)",
          backgroundColor: "var(--risk-elevated-bg)",
          borderColor: "rgba(245, 158, 11, 0.3)",
          dotColor: "var(--risk-elevated)",
        };
      case "CRITICAL":
      case "INACTIVE":
      case "OFFLINE":
        return {
          color: "var(--risk-critical)",
          backgroundColor: "var(--risk-critical-bg)",
          borderColor: "rgba(239, 68, 68, 0.3)",
          dotColor: "var(--risk-critical)",
        };
      case "ACKNOWLEDGED":
      case "OPERATOR":
        return {
          color: "#A78BFA",
          backgroundColor: "rgba(167, 139, 250, 0.12)",
          borderColor: "rgba(167, 139, 250, 0.3)",
          dotColor: "#A78BFA",
        };
      case "ADMIN":
        return {
          color: "var(--accent-cyan)",
          backgroundColor: "var(--accent-cyan-glow)",
          borderColor: "rgba(0, 229, 255, 0.3)",
          dotColor: "var(--accent-cyan)",
        };
      case "VIEWER":
      default:
        return {
          color: "var(--text-secondary)",
          backgroundColor: "rgba(148, 163, 184, 0.12)",
          borderColor: "rgba(148, 163, 184, 0.3)",
          dotColor: "var(--text-secondary)",
        };
    }
  };

  const styles = getBadgeStyles();

  return (
    <span
      className={`tech-badge ${className}`}
      style={{
        color: styles.color,
        backgroundColor: styles.backgroundColor,
        border: `1px solid ${styles.borderColor}`,
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          backgroundColor: styles.dotColor,
          display: "inline-block",
        }}
      />
      {label || status}
    </span>
  );
};
