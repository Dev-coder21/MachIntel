"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { AuthResponse, LoginCredentials, User } from "@/types/auth";
import { apiClient, ApiClientError } from "@/lib/api-client";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<AuthResponse>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = apiClient.getToken();
      if (storedToken) {
        setToken(storedToken);
        try {
          const profile = await apiClient.getMe();
          setUser(profile);
        } catch (err) {
          console.warn("Session check failed or expired:", err);
          apiClient.setToken(null);
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (credentials: LoginCredentials): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      const response = await apiClient.login(credentials);
      setToken(response.access_token);
      setUser(response.user);
      return response;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    apiClient.logout();
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const profile = await apiClient.getMe();
      setUser(profile);
    } catch {
      logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user && !!token,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
