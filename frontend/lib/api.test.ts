import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getHealth } from "./api";

describe("typed API client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("reports a missing backend origin", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    await expect(getHealth()).rejects.toEqual(new ApiError("Backend API is not configured."));
  });

  it("loads and validates backend health", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test/");
    const payload = {
      status: "ok",
      service: "RailOps AI API",
      version: "0.1.0",
      environment: "test",
      database: "available",
      message: "RailOps AI API is operational.",
    };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getHealth()).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/api/health",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("rejects an invalid health contract", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    await expect(getHealth()).rejects.toThrow("unexpected health response");
  });
});
