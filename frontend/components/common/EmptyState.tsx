import React, { ReactNode } from "react";
import { AlertCircle, Database, Eye, Terminal } from "lucide-react";

interface EmptyStateProps {
  icon?: "database" | "alert" | "inspection" | "terminal";
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  metadataTag?: string;
  children?: ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = "database",
  title,
  description,
  actionText,
  onAction,
  metadataTag,
  children,
}) => {
  const renderIcon = () => {
    switch (icon) {
      case "alert":
        return <AlertCircle size={32} color="var(--accent-amber)" />;
      case "inspection":
        return <Eye size={32} color="var(--accent-cyan)" />;
      case "terminal":
        return <Terminal size={32} color="var(--text-code)" />;
      case "database":
      default:
        return <Database size={32} color="var(--accent-cyan)" />;
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        background: "var(--bg-surface)",
        border: "1px dashed var(--border-default)",
        borderRadius: "var(--radius-md)",
        textAlign: "center",
        width: "100%",
      }}
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: "var(--radius-sm)",
          background: "var(--bg-app)",
          border: "1px solid var(--border-default)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: 16,
        }}
      >
        {renderIcon()}
      </div>

      {metadataTag && (
        <span
          className="tech-badge"
          style={{
            color: "var(--text-muted)",
            background: "var(--bg-app)",
            border: "1px solid var(--border-subtle)",
            marginBottom: 12,
          }}
        >
          {metadataTag}
        </span>
      )}

      <h3
        style={{
          fontSize: 16,
          fontWeight: 600,
          color: "var(--text-primary)",
          marginBottom: 8,
          letterSpacing: "-0.01em",
        }}
      >
        {title}
      </h3>

      <p
        style={{
          fontSize: 13,
          color: "var(--text-secondary)",
          maxWidth: 480,
          lineHeight: 1.6,
          marginBottom: actionText || children ? 20 : 0,
        }}
      >
        {description}
      </p>

      {children}

      {actionText && onAction && (
        <button
          onClick={onAction}
          style={{
            padding: "8px 16px",
            background: "transparent",
            color: "var(--accent-cyan)",
            border: "1px solid var(--accent-cyan)",
            borderRadius: "var(--radius-sm)",
            fontSize: 12,
            fontWeight: 500,
            fontFamily: "var(--font-mono)",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--accent-cyan-glow)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
          }}
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
