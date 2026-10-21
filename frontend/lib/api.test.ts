import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, applySchedule, createTrain, describeApiFailure, generateSchedule, getHealth, getTrains, validateSchedule } from "./api";

describe("typed API client", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("reports a missing backend origin", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    await expect(getHealth()).rejects.toEqual(new ApiError("Backend API is not configured.", undefined, "API_NOT_CONFIGURED"));
  });

  it("rejects malformed and insecure production API origins", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test/v1");
    await expect(getHealth()).rejects.toMatchObject({ code: "API_CONFIGURATION_ERROR" });

    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.example.test");
    vi.stubEnv("NODE_ENV", "production");
    await expect(getHealth()).rejects.toEqual(
      new ApiError("Production backend requests require an HTTPS API origin.", undefined, "API_CONFIGURATION_ERROR"),
    );
  });

  it("loads and validates backend health", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test/");
    const payload = {
      status: "ok",
      service: "RailOps AI API",
      version: "0.9.0",
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
    await expect(getHealth()).resolves.toEqual({});
  });

  it("adds the isolated workspace header to operational requests", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test");
    const storage = new Map<string, string>();
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => storage.set(key, value),
      },
      crypto: { randomUUID: () => "00000000-0000-4000-8000-000000000099" },
    });
    const fetchMock = vi.fn().mockImplementation(async () => new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await getTrains();
    const request = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(request.headers).get("X-RailOps-Session")).toBe("00000000-0000-4000-8000-000000000099");
  });

  it("retains the same workspace session across requests", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test");
    const storage = new Map<string, string>();
    vi.stubGlobal("window", {
      localStorage: { getItem: (key: string) => storage.get(key) ?? null, setItem: (key: string, value: string) => storage.set(key, value) },
      crypto: { randomUUID: () => "00000000-0000-4000-8000-000000000088" },
    });
    const fetchMock = vi.fn().mockImplementation(async () => new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await getTrains();
    await getTrains();

    expect(fetchMock.mock.calls.map((call) => new Headers((call[1] as RequestInit).headers).get("X-RailOps-Session"))).toEqual([
      "00000000-0000-4000-8000-000000000088",
      "00000000-0000-4000-8000-000000000088",
    ]);
  });

  it("repairs a malformed stored workspace identifier", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test");
    const storage = new Map<string, string>([["railops-session-id", "invalid-session"]]);
    vi.stubGlobal("window", {
      localStorage: { getItem: (key: string) => storage.get(key) ?? null, setItem: (key: string, value: string) => storage.set(key, value) },
      crypto: { randomUUID: () => "00000000-0000-4000-8000-000000000077" },
    });
    const fetchMock = vi.fn().mockResolvedValue(new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await getTrains();

    expect(storage.get("railops-session-id")).toBe("00000000-0000-4000-8000-000000000077");
    expect(new Headers((fetchMock.mock.calls[0][1] as RequestInit).headers).get("X-RailOps-Session")).toBe("00000000-0000-4000-8000-000000000077");
  });

  it("exposes backend field validation details", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test");
    vi.stubGlobal("window", { localStorage: { getItem: () => "00000000-0000-4000-8000-000000000099" }, crypto });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "VALIDATION_ERROR", message: "Request validation failed.", details: [{ field: "priority", message: "Invalid priority." }] } }), { status: 422 })));
    const error = await getTrains().catch((caught) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).details[0].field).toBe("priority");
  });

  it("distinguishes database, session, endpoint, and connectivity failures", () => {
    expect(describeApiFailure(new ApiError("Database failed", 503, "DATABASE_ERROR")).title).toBe("Database operation failed");
    expect(describeApiFailure(new ApiError("Bad session", 400, "INVALID_SESSION")).title).toBe("Invalid workspace session");
    expect(describeApiFailure(new ApiError("Offline", undefined, "BACKEND_UNREACHABLE")).title).toBe("Backend unreachable");
    expect(describeApiFailure(new ApiError("Endpoint failed", 500, "INTERNAL_ERROR")).title).toBe("Operational request failed");
  });

  it("sends train mutations to the persistent API", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test");
    vi.stubGlobal("window", { localStorage: { getItem: () => "00000000-0000-4000-8000-000000000099" }, crypto });
    const train = { identifier: "RA-901", priority: 3, arrival_minute: 480, departure_minute: 495, minimum_dwell_minutes: 10, length_meters: 220, required_platform_type: "passenger", compatible_platform_codes: ["P1"], service_status: "scheduled" as const, delay_minutes: 0 };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ train: { ...train, id: 21, created_at: "2026-10-20T00:00:00Z", updated_at: "2026-10-20T00:00:00Z" }, schedule_validation_required: false }), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    await createTrain(train);
    expect(fetchMock.mock.calls[0][0]).toBe("https://api.example.test/api/trains");
    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ method: "POST", body: JSON.stringify(train) }));
  });

  it("uses persisted plan identifiers for the scheduling lifecycle", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test");
    vi.stubGlobal("window", { localStorage: { getItem: () => "00000000-0000-4000-8000-000000000099" }, crypto });
    const fetchMock = vi.fn().mockImplementation(async () => new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await generateSchedule("cp_sat");
    await validateSchedule({ id: 12, version: 4 });
    await applySchedule({ id: 12, version: 4 });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "https://api.example.test/api/schedules/generate",
      "https://api.example.test/api/schedules/validate",
      "https://api.example.test/api/schedules/apply",
    ]);
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: "POST", body: JSON.stringify({ plan_id: 12, version: 4 }) }));
    expect(fetchMock.mock.calls[2][1]).toEqual(expect.objectContaining({ method: "POST", body: JSON.stringify({ plan_id: 12, version: 4 }) }));
  });
});
