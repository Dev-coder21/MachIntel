"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { User } from "@/types/auth";
import { Shield, Users } from "lucide-react";

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const data = await apiClient.get<User[]>("/admin/users");
        setUsers(data);
      } catch (err: unknown) {
        if (err instanceof ApiClientError) {
          setError(err.message);
        } else {
          setError("Failed to fetch user directory. Verify administrative privileges.");
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchUsers();
  }, []);

  return (
    <AppShell>
      <PageHeader
        title="System Administration & Access Control"
        subtitle="Manage user permissions, Role-Based Access Control (RBAC), and model registry governance."
        breadcrumbs={[{ label: "Governance" }, { label: "System Admin" }]}
        badge={<StatusBadge status="ADMIN" label="RESTRICTED AREA" />}
      />

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* User Management Section */}
        <div className="tech-card">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 16,
              paddingBottom: 12,
              borderBottom: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Users size={18} color="var(--accent-cyan)" />
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
                Active System Users
              </span>
            </div>
            <span
              className="mono-readout"
              style={{ fontSize: 11, color: "var(--text-muted)" }}
            >
              TOTAL: {users.length}
            </span>
          </div>

          {isLoading ? (
            <LoadingSkeleton count={3} height={36} />
          ) : error ? (
            <ErrorState
              title="Access Denied or Query Failure"
              message={error}
              code="ADMIN_RESTRICTION"
            />
          ) : users.length === 0 ? (
            <div style={{ padding: "20px 0", color: "var(--text-secondary)", fontSize: 13 }}>
              No registered users returned.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr
                    style={{
                      borderBottom: "1px solid var(--border-default)",
                      textAlign: "left",
                      color: "var(--text-muted)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    <th style={{ padding: "8px 12px" }}>USERNAME</th>
                    <th style={{ padding: "8px 12px" }}>EMAIL</th>
                    <th style={{ padding: "8px 12px" }}>ROLE</th>
                    <th style={{ padding: "8px 12px" }}>STATUS</th>
                    <th style={{ padding: "8px 12px" }}>CREATED AT</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr
                      key={u.id}
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        transition: "background-color 0.1s ease",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--bg-surface-hover)")}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                    >
                      <td style={{ padding: "10px 12px", fontWeight: 600, color: "var(--text-primary)" }}>
                        {u.username}
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>
                        {u.email}
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <StatusBadge status={u.role} />
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <StatusBadge
                          status={u.is_active ? "ACTIVE" : "INACTIVE"}
                          label={u.is_active ? "ACTIVE" : "DISABLED"}
                        />
                      </td>
                      <td
                        className="mono-readout"
                        style={{ padding: "10px 12px", color: "var(--text-muted)", fontSize: 11 }}
                      >
                        {new Date(u.created_at).toISOString().replace("T", " ").substring(0, 19)} UTC
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
