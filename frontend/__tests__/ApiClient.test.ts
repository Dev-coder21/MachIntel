import { describe, it, expect, beforeEach } from "vitest";
import { apiClient, ApiClientError } from "@/lib/api-client";

describe("ApiClient", () => {
  beforeEach(() => {
    localStorage.clear();
    apiClient.setToken(null);
  });

  it("stores and retrieves token from localStorage", () => {
    expect(apiClient.getToken()).toBeNull();
    apiClient.setToken("mock-jwt-token-12345");
    expect(apiClient.getToken()).toBe("mock-jwt-token-12345");
    expect(localStorage.getItem("machintel_token")).toBe("mock-jwt-token-12345");
  });

  it("clears token on logout", async () => {
    apiClient.setToken("temp-token");
    await apiClient.logout();
    expect(apiClient.getToken()).toBeNull();
    expect(localStorage.getItem("machintel_token")).toBeNull();
  });

  it("creates proper ApiClientError instances", () => {
    const error = new ApiClientError("Forbidden", "PERMISSION_DENIED", 403, {
      role: "VIEWER",
    });
    expect(error.message).toBe("Forbidden");
    expect(error.code).toBe("PERMISSION_DENIED");
    expect(error.status).toBe(403);
    expect(error.details?.role).toBe("VIEWER");
  });
});
