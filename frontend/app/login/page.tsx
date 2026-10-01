"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ApiClientError } from "@/lib/api-client";
import { Layers, Lock, ShieldCheck, User } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usernameOrEmail.trim() || !password.trim()) {
      setError("Please provide username/email and password");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await login({
        username_or_email: usernameOrEmail,
        password: password,
      });
      router.push("/");
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to connect to authentication service. Ensure backend is running.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        backgroundColor: "var(--bg-app)",
        padding: 20,
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 420,
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)",
          padding: 36,
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--bg-app)",
              border: "1px solid var(--accent-cyan)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 14px auto",
              boxShadow: "0 0 14px var(--accent-cyan-glow)",
            }}
          >
            <Layers size={24} color="var(--accent-cyan)" />
          </div>
          <h2
            style={{
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: "0.08em",
              fontFamily: "var(--font-mono)",
              color: "var(--text-primary)",
              marginBottom: 4,
            }}
          >
            MACHINTEL
          </h2>
          <p
            style={{
              fontSize: 12,
              color: "var(--text-muted)",
              letterSpacing: "0.04em",
              fontFamily: "var(--font-mono)",
            }}
          >
            INDUSTRIAL COMMAND CENTER LOGIN
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: "10px 14px",
              backgroundColor: "var(--risk-critical-bg)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              borderRadius: "var(--radius-sm)",
              color: "var(--risk-critical)",
              fontSize: 12,
              marginBottom: 20,
              lineHeight: 1.4,
            }}
          >
            {error}
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div>
            <label
              style={{
                display: "block",
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                marginBottom: 6,
              }}
            >
              Username or Email
            </label>
            <div style={{ position: "relative" }}>
              <span
                style={{
                  position: "absolute",
                  left: 12,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--text-muted)",
                }}
              >
                <User size={15} />
              </span>
              <input
                type="text"
                value={usernameOrEmail}
                onChange={(e) => setUsernameOrEmail(e.target.value)}
                placeholder="admin or user@domain.com"
                required
                style={{
                  width: "100%",
                  padding: "10px 12px 10px 36px",
                  backgroundColor: "var(--bg-input)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                  fontSize: 13,
                  outline: "none",
                  transition: "border-color 0.15s ease",
                }}
                onFocus={(e) => (e.target.style.borderColor = "var(--accent-cyan)")}
                onBlur={(e) => (e.target.style.borderColor = "var(--border-default)")}
              />
            </div>
          </div>

          <div>
            <label
              style={{
                display: "block",
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                marginBottom: 6,
              }}
            >
              Password
            </label>
            <div style={{ position: "relative" }}>
              <span
                style={{
                  position: "absolute",
                  left: 12,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--text-muted)",
                }}
              >
                <Lock size={15} />
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                style={{
                  width: "100%",
                  padding: "10px 12px 10px 36px",
                  backgroundColor: "var(--bg-input)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                  fontSize: 13,
                  outline: "none",
                  transition: "border-color 0.15s ease",
                }}
                onFocus={(e) => (e.target.style.borderColor = "var(--accent-cyan)")}
                onBlur={(e) => (e.target.style.borderColor = "var(--border-default)")}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              marginTop: 6,
              padding: "11px 16px",
              backgroundColor: "var(--accent-cyan)",
              color: "#05070A",
              border: "none",
              borderRadius: "var(--radius-sm)",
              fontSize: 12,
              fontWeight: 700,
              fontFamily: "var(--font-mono)",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              cursor: isSubmitting ? "not-allowed" : "pointer",
              opacity: isSubmitting ? 0.7 : 1,
              transition: "all 0.15s ease",
            }}
          >
            <ShieldCheck size={16} />
            {isSubmitting ? "AUTHENTICATING..." : "SIGN IN TO PLATFORM"}
          </button>
        </form>

        {/* Local Development Credentials Note */}
        <div
          style={{
            marginTop: 24,
            paddingTop: 18,
            borderTop: "1px solid var(--border-subtle)",
            fontSize: 11,
            color: "var(--text-muted)",
            lineHeight: 1.5,
          }}
        >
          <div style={{ fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
            Local Development Account:
          </div>
          <div>Run <code className="mono-readout" style={{ color: "var(--accent-cyan)" }}>python3 backend/scripts/create_first_admin.py</code> to initialize local credentials.</div>
        </div>
      </div>
    </div>
  );
}
