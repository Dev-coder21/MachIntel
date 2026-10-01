"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Cpu,
  Eye,
  FileCheck,
  GitBranch,
  Layers,
  LogOut,
  Search,
  Shield,
  User as UserIcon,
  Wrench,
  Zap,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<{ username: string; role: string } | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("user");
      if (stored) {
        const u = JSON.parse(stored);
        if (u && u.username) {
          setCurrentUser({ username: u.username, role: u.role || "OPERATOR" });
        }
      }
    } catch {
      // Ignore
    }
  }, []);

  const handleLogout = () => {
    try {
      apiClient.logout();
    } catch {
      // Ignore
    }
    localStorage.removeItem("user");
    localStorage.removeItem("token");
    setCurrentUser(null);
    router.push("/login");
  };

  const navigationSections: NavSection[] = [
    {
      title: "COMMAND",
      items: [
        { name: "Command Center", href: "/", icon: Activity },
        { name: "Machine Fleet", href: "/machines", icon: Cpu },
        { name: "Alert Console", href: "/alerts", icon: AlertTriangle },
        { name: "Maintenance Orders", href: "/maintenance", icon: Wrench },
      ],
    },
    {
      title: "INTELLIGENCE",
      items: [
        { name: "Prognostics & RUL", href: "/predictions", icon: Zap },
        { name: "Visual Inspection", href: "/inspections", icon: Eye },
        { name: "Inspection Analytics", href: "/analytics", icon: BarChart3 },
        { name: "Evidence Intelligence", href: "/evidence", icon: FileCheck },
        { name: "AI Inspector", href: "/ai-inspector", icon: Search },
      ],
    },
    {
      title: "GOVERNANCE",
      items: [
        { name: "Model Lifecycle", href: "/admin/models", icon: GitBranch },
        { name: "Worker Jobs", href: "/admin/jobs", icon: Layers },
        { name: "System Admin", href: "/admin", icon: Shield },
      ],
    },
  ];

  return (
    <aside
      aria-label="Sidebar Navigation"
      style={{
        width: 240,
        backgroundColor: "var(--bg-sidebar)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        minHeight: "100vh",
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: "20px 18px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            backgroundColor: "var(--bg-app)",
            border: "1px solid var(--accent-cyan)",
            borderRadius: "var(--radius-sm)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 10px var(--accent-cyan-glow)",
          }}
        >
          <Layers size={18} color="var(--accent-cyan)" />
        </div>
        <div>
          <div
            style={{
              fontSize: 14,
              fontWeight: 700,
              letterSpacing: "0.08em",
              color: "var(--text-primary)",
              fontFamily: "var(--font-mono)",
            }}
          >
            MACHINTEL
          </div>
          <div
            style={{
              fontSize: 10,
              color: "var(--text-muted)",
              letterSpacing: "0.05em",
              fontFamily: "var(--font-mono)",
            }}
          >
            COMMAND CENTER
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <div
        style={{
          flex: 1,
          padding: "16px 10px",
          display: "flex",
          flexDirection: "column",
          gap: 20,
          overflowY: "auto",
        }}
      >
        {navigationSections.map((section) => (
          <div key={section.title}>
            <div
              style={{
                fontSize: 10,
                fontWeight: 600,
                color: "var(--text-muted)",
                letterSpacing: "0.08em",
                padding: "0 8px 6px 8px",
                fontFamily: "var(--font-mono)",
              }}
            >
              {section.title}
            </div>
            <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "8px 10px",
                      borderRadius: "var(--radius-sm)",
                      fontSize: 12,
                      fontWeight: isActive ? 600 : 400,
                      color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                      backgroundColor: isActive
                        ? "var(--bg-surface-active)"
                        : "transparent",
                      borderLeft: isActive
                        ? "2px solid var(--accent-cyan)"
                        : "2px solid transparent",
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor =
                          "var(--bg-surface-hover)";
                        e.currentTarget.style.color = "var(--text-primary)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = "transparent";
                        e.currentTarget.style.color = "var(--text-secondary)";
                      }
                    }}
                  >
                    <Icon
                      size={16}
                      color={isActive ? "var(--accent-cyan)" : "var(--text-muted)"}
                    />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Operator Session Info */}
      {currentUser && (
        <div
          style={{
            padding: "10px 14px",
            borderTop: "1px solid var(--border-subtle)",
            backgroundColor: "rgba(0, 0, 0, 0.2)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
            <div
              style={{
                width: 24,
                height: 24,
                borderRadius: 4,
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <UserIcon size={13} color="var(--accent-cyan)" />
            </div>
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {currentUser.username}
              </div>
              <div
                style={{
                  fontSize: 9,
                  fontFamily: "var(--font-mono)",
                  color: currentUser.role === "ADMIN" ? "var(--accent-cyan)" : "var(--text-muted)",
                }}
              >
                {currentUser.role}
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Log Out"
            style={{
              padding: 4,
              borderRadius: 4,
              color: "var(--text-muted)",
              transition: "color 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "var(--risk-critical)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "var(--text-muted)";
            }}
          >
            <LogOut size={14} />
          </button>
        </div>
      )}

      {/* Footer Version & Daemon Info */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: "1px solid var(--border-subtle)",
          backgroundColor: "var(--bg-app)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span
            className="mono-readout"
            style={{ fontSize: 10, color: "var(--text-muted)" }}
          >
            LOCAL PRODUCTION • v0.1.0
          </span>
          <span
            className="mono-readout"
            style={{ fontSize: 9, color: "var(--risk-normal)", display: "flex", alignItems: "center", gap: 4 }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "var(--risk-normal)" }} />
            DAEMON ONLINE
          </span>
        </div>
        <span
          className="mono-readout"
          style={{
            fontSize: 9,
            padding: "2px 6px",
            borderRadius: 3,
            backgroundColor: "rgba(0, 229, 255, 0.1)",
            color: "var(--accent-cyan)",
            border: "1px solid rgba(0, 229, 255, 0.2)",
          }}
        >
          POSTGRES
        </span>
      </div>
    </aside>
  );
};
