// Mock localStorage for Vitest jsdom environment
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

import { vi } from "vitest";

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: {
      id: "u-mock-1",
      email: "admin@machintel.io",
      full_name: "Admin Operator",
      role: "ADMIN",
      is_active: true,
    },
    token: "mock-valid-jwt-token",
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));
