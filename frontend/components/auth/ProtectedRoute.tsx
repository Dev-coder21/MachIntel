"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          backgroundColor: "var(--bg-app)",
          gap: 16,
          padding: 24,
        }}
      >
        <div
          className="mono-readout"
          style={{ fontSize: 12, color: "var(--accent-cyan)", letterSpacing: "0.1em" }}
        >
          AUTHENTICATING SESSION...
        </div>
        <div style={{ width: 200 }}>
          <LoadingSkeleton height={3} count={1} />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
};
