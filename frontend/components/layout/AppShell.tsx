"use client";

import React from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  return (
    <ProtectedRoute>
      <div className="app-container">
        <Sidebar />
        <div className="main-content">
          <TopBar />
          <main className="page-body">{children}</main>
        </div>
      </div>
    </ProtectedRoute>
  );
};
