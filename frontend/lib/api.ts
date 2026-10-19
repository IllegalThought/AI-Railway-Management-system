export type HealthResponse = {
  status: "ok";
  service: string;
  version: string;
  environment: string;
  database: "available";
  message: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getApiBaseUrl() {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").trim().replace(/\/$/, "");
}

function isHealthResponse(value: unknown): value is HealthResponse {
  if (!value || typeof value !== "object") return false;
  const health = value as Record<string, unknown>;
  return (
    health.status === "ok" &&
    typeof health.service === "string" &&
    typeof health.version === "string" &&
    typeof health.environment === "string" &&
    health.database === "available" &&
    typeof health.message === "string"
  );
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    throw new ApiError("Backend API is not configured.");
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/health`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("Backend API could not be reached.");
  }

  if (!response.ok) {
    throw new ApiError("Backend health check failed.", response.status);
  }

  const payload: unknown = await response.json();
  if (!isHealthResponse(payload)) {
    throw new ApiError("Backend returned an unexpected health response.");
  }
  return payload;
}
