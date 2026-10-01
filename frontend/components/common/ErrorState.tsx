import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  code?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "System Operation Error",
  message,
  onRetry,
  code,
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "36px 20px",
        background: "var(--bg-surface)",
        border: "1px solid rgba(239, 68, 68, 0.3)",
        borderRadius: "var(--radius-md)",
        textAlign: "center",
        width: "100%",
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: "var(--radius-sm)",
          background: "var(--risk-critical-bg)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: 14,
        }}
      >
        <AlertTriangle size={24} color="var(--risk-critical)" />
      </div>

      {code && (
        <span
          className="tech-badge"
          style={{
            color: "var(--risk-critical)",
            background: "var(--risk-critical-bg)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            marginBottom: 8,
          }}
        >
          {code}
        </span>
      )}

      <h4
        style={{
          fontSize: 15,
          fontWeight: 600,
          color: "var(--text-primary)",
          marginBottom: 6,
        }}
      >
        {title}
      </h4>

      <p
        style={{
          fontSize: 13,
          color: "var(--text-secondary)",
          maxWidth: 420,
          lineHeight: 1.5,
          marginBottom: onRetry ? 18 : 0,
        }}
      >
        {message}
      </p>

      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 16px",
            background: "var(--bg-app)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            fontSize: 12,
            fontFamily: "var(--font-mono)",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "var(--text-primary)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "var(--border-default)";
          }}
        >
          <RefreshCw size={14} />
          Retry Operation
        </button>
      )}
    </div>
  );
};
