"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LogOut, User as UserIcon } from "lucide-react";

export const TopBar: React.FC = () => {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [utcTime, setUtcTime] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(
        now.toISOString().replace("T", " ").substring(0, 19) + " UTC"
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header
      style={{
        height: 52,
        backgroundColor: "var(--bg-surface)",
        borderBottom: "1px solid var(--border-subtle)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 24px",
      }}
    >
      {/* System Telemetry & Heartbeat */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              backgroundColor: "var(--risk-normal)",
              display: "inline-block",
            }}
          />
          <span
            className="mono-readout"
            style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 500 }}
          >
            LOCAL BACKEND ONLINE
          </span>
        </div>

        <span
          className="tech-badge"
          style={{
            background: "var(--bg-app)",
            color: "var(--text-muted)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          ENV: LOCAL_DOCKER
        </span>
      </div>

      {/* Clock & User Profile Controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        <span
          className="mono-readout"
          style={{
            fontSize: 11,
            color: "var(--text-secondary)",
            letterSpacing: "0.02em",
          }}
        >
          {utcTime || "SYNCING CLOCK..."}
        </span>

        <div
          style={{
            height: 20,
            width: 1,
            backgroundColor: "var(--border-default)",
          }}
        />

        {user ? (
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--bg-app)",
                  border: "1px solid var(--border-default)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <UserIcon size={14} color="var(--text-secondary)" />
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: "var(--text-primary)",
                    lineHeight: 1.2,
                  }}
                >
                  {user.username}
                </span>
              </div>
            </div>

            <StatusBadge status={user.role} />

            <button
              onClick={handleLogout}
              title="Sign Out of MachIntel"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 28,
                height: 28,
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-app)",
                border: "1px solid var(--border-default)",
                color: "var(--text-muted)",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "var(--risk-critical)";
                e.currentTarget.style.borderColor = "var(--risk-critical)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "var(--text-muted)";
                e.currentTarget.style.borderColor = "var(--border-default)";
              }}
            >
              <LogOut size={13} />
            </button>
          </div>
        ) : (
          <button
            onClick={() => router.push("/login")}
            style={{
              padding: "5px 12px",
              backgroundColor: "transparent",
              color: "var(--accent-cyan)",
              border: "1px solid var(--accent-cyan)",
              borderRadius: "var(--radius-sm)",
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              textTransform: "uppercase",
            }}
          >
            SIGN IN
          </button>
        )}
      </div>
    </header>
  );
};
