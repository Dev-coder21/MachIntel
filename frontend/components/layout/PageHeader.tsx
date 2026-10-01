import React, { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  badge?: ReactNode;
  actions?: ReactNode;
  breadcrumbs?: { label: string; href?: string }[];
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  badge,
  actions,
  breadcrumbs,
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
        marginBottom: 24,
        paddingBottom: 16,
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      {breadcrumbs && breadcrumbs.length > 0 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 11,
            fontFamily: "var(--font-mono)",
            color: "var(--text-muted)",
          }}
        >
          {breadcrumbs.map((b, idx) => (
            <React.Fragment key={idx}>
              {idx > 0 && <span>/</span>}
              {b.href ? (
                <a href={b.href} style={{ color: "var(--text-secondary)" }}>
                  {b.label}
                </a>
              ) : (
                <span style={{ color: "var(--text-primary)" }}>{b.label}</span>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h1
            style={{
              fontSize: 20,
              fontWeight: 700,
              letterSpacing: "-0.01em",
              color: "var(--text-primary)",
            }}
          >
            {title}
          </h1>
          {badge}
        </div>

        {actions && (
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {actions}
          </div>
        )}
      </div>

      {subtitle && (
        <p
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
            maxWidth: 800,
            lineHeight: 1.5,
          }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
};
