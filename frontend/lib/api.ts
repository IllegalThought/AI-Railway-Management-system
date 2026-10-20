export type HealthResponse = {
  status: "ok";
  service: string;
  version: string;
  environment: string;
  database: "available";
  message: string;
};

export type TrainStatus = "scheduled" | "delayed" | "cancelled";

export type Train = {
  id: number;
  identifier: string;
  priority: number;
  arrival_minute: number;
  departure_minute: number;
  minimum_dwell_minutes: number;
  length_meters: number;
  required_platform_type: string | null;
  compatible_platform_codes: string[];
  service_status: TrainStatus;
  delay_minutes: number;
  origin_node_code?: string | null;
  destination_node_code?: string | null;
  created_at: string;
  updated_at: string;
};

export type TrainInput = Omit<Train, "id" | "created_at" | "updated_at">;

export type Platform = {
  id: number;
  code: string;
  platform_type: string;
  length_meters: number;
  clearance_minutes: number;
  is_available: boolean;
  unavailable_reason: string | null;
  compatible_train_count: number;
  created_at: string;
  updated_at: string;
};

export type Scenario = {
  key: string;
  name: string;
  description: string;
  train_count: number;
  platform_count: number;
};

export type Overview = {
  scenario_key: string;
  scenario_name: string;
  train_count: number;
  scheduled_train_count: number;
  delayed_train_count: number;
  platform_count: number;
  available_platform_count: number;
  unavailable_platform_count: number;
  active_incident_count: number;
  upcoming_trains: Array<Pick<Train, "id" | "identifier" | "arrival_minute" | "departure_minute" | "service_status" | "delay_minutes">>;
  active_incidents: Array<{ id: number; title: string; severity: string; status: string; resource_code: string | null; reported_minute: number }>;
  recent_activity: Array<{ id: number; message: string; event_type: string; event_minute: number; resource_code: string | null; created_at: string }>;
};

export type SchedulingEngine = "csp" | "fcfs" | "cp_sat";
export type SolverStatus = "FEASIBLE" | "OPTIMAL" | "INFEASIBLE" | "UNKNOWN" | "SEARCH_LIMIT";
export type ScheduleAssignment = {
  id: number; train_id: number; train_identifier: string; platform_id: number; platform_code: string;
  priority: number; planned_arrival_minute: number; planned_departure_minute: number;
  occupancy_start_minute: number; occupancy_end_minute: number; delay_minutes: number; reassigned: boolean;
};
export type SchedulePlan = {
  id: number; name: string; version: number; lifecycle_status: "draft" | "ready" | "applied" | "invalid" | "archived";
  solver_status: SolverStatus; engine: SchedulingEngine; horizon_start_minute: number; horizon_end_minute: number;
  maximum_delay_minutes: number; objective_value: number | null; is_validated: boolean; is_stale: boolean;
  execution_time_ms: number | null;
  route_reservations_provisional: boolean; explanation: string; assignments: ScheduleAssignment[];
  platforms: Array<{ id: number; code: string; platform_type: string; length_meters: number; clearance_minutes: number; is_available: boolean }>;
  created_at: string; updated_at: string;
};
export type ScheduleValidation = { plan: SchedulePlan; valid: boolean; issues: Array<{ code: string; message: string; train_id: number | null; platform_id: number | null }>; message: string };

export type NetworkNode = { code: string; name: string; node_type: string; x: number; y: number; blocked: boolean };
export type NetworkEdge = { code: string; from_node: string; to_node: string; traversal_minutes: number; capacity: number; resource_group: string | null; blocked: boolean };
export type RouteReservation = { resource_code: string; resource_type: string; edge_code: string | null; start_minute: number; end_minute: number; sequence: number };
export type NetworkMovement = { train_id: number; train_identifier: string; platform_code: string; origin_node_code: string | null; destination_node_code: string | null; path: string[]; indicator: "RED" | "YELLOW" | "GREEN"; decision: "MovementAllowed" | "MovementBlocked"; explanation: string; reservations: RouteReservation[] };
export type NetworkMonitor = { plan_id: number | null; plan_version: number | null; route_validation_complete: boolean; nodes: NetworkNode[]; edges: NetworkEdge[]; movements: NetworkMovement[]; blocked_resources: string[]; message: string };

export type LiveTrainState = { train_id: number; train_identifier: string; status: string; position: string; platform_code: string; progress_percent: number; movement_permission: string; signal: "RED" | "YELLOW" | "GREEN" };
export type SimulationState = {
  current_minute: number; run_status: "paused" | "running"; speed: 1 | 2 | 5; revision: number;
  active_plan_id: number | null; active_plan_version: number | null; trains: LiveTrainState[];
  platforms: Array<{ platform_code: string; train_identifier: string | null; occupied: boolean }>;
  active_reservations: Array<{ train_identifier: string; resource_code: string; resource_type: string; start_minute: number; end_minute: number }>;
  events: Array<{ id: number; event_type: string; event_minute: number; message: string; resource_code: string | null }>;
  message: string;
};
export type IncidentType = "train_arrival_delay" | "train_departure_delay" | "platform_closure" | "track_blockage" | "junction_closure" | "new_train_request";
export type Incident = { id: number; incident_type: IncidentType; affected_resource: string; start_minute: number; duration_minutes: number; severity: "low" | "medium" | "high" | "critical"; status: "open" | "monitoring" | "resolved"; description: string; title: string; affected_train_ids: number[]; created_at: string };
export type ReplanResult = { base_plan: SchedulePlan; revised_plan: SchedulePlan; valid: boolean; infeasible_reason: string | null; preserved_train_ids: number[]; affected_train_ids: number[]; changes: Array<{ train_identifier: string; before: ScheduleAssignment | null; after: ScheduleAssignment | null; change: string; reason: string }>; message: string };

export type BenchmarkResult = {
  benchmark_id: string; scenario_identifier: string; engine: SchedulingEngine; solver_status: SolverStatus;
  execution_time_ms: number; total_delay_minutes: number; average_delay_minutes: number; maximum_delay_minutes: number;
  processed_train_count: number; objective_value: number | null; optimality_proven: boolean; explanation: string; created_at: string;
};
export type Analytics = {
  scenario_identifier: string;
  metrics: { plan_id: number | null; plan_version: number | null; total_arrival_delay_minutes: number; average_delay_minutes: number; maximum_delay_minutes: number; train_processing_count: number; active_conflicts: number; schedule_feasible: boolean; solver_execution_time_ms: number | null; rescheduling_impact: { base_plan_version: number | null; current_plan_version: number | null; changed_train_count: number; reassigned_train_count: number; delay_delta_minutes: number } };
  platform_utilization: Array<{ platform_code: string; occupied_minutes: number; utilization_percent: number; train_count: number }>;
  delay_distribution: Array<{ label: string; train_count: number }>;
  operational_trends: Array<{ plan_version: number; engine: SchedulingEngine; total_delay_minutes: number; average_delay_minutes: number; execution_time_ms: number | null; created_at: string }>;
  latest_benchmark: BenchmarkResult[];
  platform_decisions: Array<{ train_identifier: string; assigned_platform: string; accepted_reasons: string[]; rejected_platforms: Array<{ platform_code: string; reasons: string[] }>; route_decision: string | null; route_explanation: string | null }>;
  decision_insights: Array<{ category: string; title: string; summary: string; evidence: string[] }>;
  message: string;
};

export type ValidationDetail = { field: string | null; message: string; type?: string };

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number, public readonly code?: string, public readonly details: ValidationDetail[] = []) {
    super(message);
    this.name = "ApiError";
  }
}

export type ApiFailurePresentation = { title: string; message: string };

export function describeApiFailure(error: unknown, endpoint: "analytics" | "operations" = "operations"): ApiFailurePresentation {
  if (!(error instanceof ApiError)) return { title: "Request failed", message: endpoint === "analytics" ? "Analytics could not be loaded." : "Operational data could not be loaded." };
  if (error.code === "API_NOT_CONFIGURED") return { title: "Backend not configured", message: error.message };
  if (error.code === "API_CONFIGURATION_ERROR") return { title: "Backend configuration error", message: error.message };
  if (error.code === "BACKEND_UNREACHABLE") return { title: "Backend unreachable", message: error.message };
  if (error.code === "DATABASE_ERROR") return { title: "Database operation failed", message: "The backend is online, but its database could not complete this request." };
  if (error.code === "INVALID_SESSION") return { title: "Invalid workspace session", message: "The saved workspace identifier is no longer valid. Clear it or restore a valid workspace session, then refresh." };
  if (endpoint === "analytics") return { title: "Analytics endpoint failed", message: error.message };
  return { title: "Operational request failed", message: error.message };
}

const workspaceStorageKey = "railops-session-id";
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
let transientWorkspaceSessionId = "";

export function getApiBaseUrl() {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "").trim().replace(/\/$/, "");
}

function validateApiBaseUrl(baseUrl: string): string | null {
  if (!baseUrl) return "Backend API is not configured.";
  let parsed: URL;
  try { parsed = new URL(baseUrl); }
  catch { return "NEXT_PUBLIC_API_BASE_URL must be a valid HTTP(S) origin."; }
  if (!(["http:", "https:"] as string[]).includes(parsed.protocol) || parsed.pathname !== "/" || parsed.search || parsed.hash) {
    return "NEXT_PUBLIC_API_BASE_URL must contain only an HTTP(S) origin without a path, query, or fragment.";
  }
  const localHost = parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1" || parsed.hostname === "[::1]";
  if (process.env.NODE_ENV === "production" && parsed.protocol !== "https:" && !localHost) {
    return "Production backend requests require an HTTPS API origin.";
  }
  return null;
}

export function getWorkspaceSessionId() {
  if (typeof window === "undefined") return "";
  try {
    const existing = window.localStorage.getItem(workspaceStorageKey);
    if (existing && uuidPattern.test(existing)) return existing;
    const sessionId = window.crypto.randomUUID();
    window.localStorage.setItem(workspaceStorageKey, sessionId);
    return sessionId;
  } catch {
    if (!transientWorkspaceSessionId) transientWorkspaceSessionId = window.crypto.randomUUID();
    return transientWorkspaceSessionId;
  }
}

async function apiRequest<T>(path: string, init: RequestInit = {}, scoped = true): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const configurationIssue = validateApiBaseUrl(baseUrl);
  if (configurationIssue) {
    throw new ApiError(
      configurationIssue,
      undefined,
      baseUrl ? "API_CONFIGURATION_ERROR" : "API_NOT_CONFIGURED",
    );
  }
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  if (scoped) headers.set("X-RailOps-Session", getWorkspaceSessionId());
  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, { ...init, headers, cache: "no-store" });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("Backend API could not be reached.", undefined, "BACKEND_UNREACHABLE");
  }
  if (!response.ok) {
    let payload: { error?: { message?: string; code?: string; details?: ValidationDetail[] } } = {};
    try { payload = await response.json(); } catch { /* The status fallback remains actionable. */ }
    throw new ApiError(payload.error?.message ?? `Request failed with status ${response.status}.`, response.status, payload.error?.code, payload.error?.details ?? []);
  }
  return response.json() as Promise<T>;
}

export function getHealth(signal?: AbortSignal) {
  return apiRequest<HealthResponse>("/api/health", { signal }, false);
}

export function getTrains(signal?: AbortSignal) { return apiRequest<Train[]>("/api/trains", { signal }); }
export function getTrain(id: number, signal?: AbortSignal) { return apiRequest<Train>(`/api/trains/${id}`, { signal }); }
export function createTrain(data: TrainInput) { return apiRequest<{ train: Train; schedule_validation_required: boolean }>("/api/trains", { method: "POST", body: JSON.stringify(data) }); }
export function updateTrain(id: number, data: Partial<TrainInput>) { return apiRequest<{ train: Train; schedule_validation_required: boolean }>(`/api/trains/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }
export function deleteTrain(id: number) { return apiRequest<{ message: string; deleted_id: number; schedule_validation_required: boolean }>(`/api/trains/${id}`, { method: "DELETE" }); }

export function getPlatforms(signal?: AbortSignal) { return apiRequest<Platform[]>("/api/platforms", { signal }); }
export function updatePlatform(id: number, data: Partial<Pick<Platform, "code" | "platform_type" | "length_meters" | "clearance_minutes" | "is_available" | "unavailable_reason">>) { return apiRequest<{ platform: Platform; schedule_validation_required: boolean }>(`/api/platforms/${id}`, { method: "PATCH", body: JSON.stringify(data) }); }

export function getScenarios(signal?: AbortSignal) { return apiRequest<Scenario[]>("/api/scenarios", { signal }, false); }
export function restoreScenario(key: string) { return apiRequest<{ scenario: Scenario; message: string }>(`/api/scenarios/${key}/restore`, { method: "POST" }); }
export function getOverview(signal?: AbortSignal) { return apiRequest<Overview>("/api/overview", { signal }); }

export function getCurrentSchedule(signal?: AbortSignal) { return apiRequest<SchedulePlan | null>("/api/schedules/current", { signal }); }
export function generateSchedule(engine: SchedulingEngine) { return apiRequest<SchedulePlan>("/api/schedules/generate", { method: "POST", body: JSON.stringify({ engine, maximum_delay_minutes: 30 }) }); }
export function validateSchedule(plan: Pick<SchedulePlan, "id" | "version">) { return apiRequest<ScheduleValidation>("/api/schedules/validate", { method: "POST", body: JSON.stringify({ plan_id: plan.id, version: plan.version }) }); }
export function applySchedule(plan: Pick<SchedulePlan, "id" | "version">) { return apiRequest<{ plan: SchedulePlan; message: string }>("/api/schedules/apply", { method: "POST", body: JSON.stringify({ plan_id: plan.id, version: plan.version }) }); }
export function getNetworkMonitor(signal?: AbortSignal) { return apiRequest<NetworkMonitor>("/api/network/monitor", { signal }); }
export function getSimulationState(signal?: AbortSignal) { return apiRequest<SimulationState>("/api/simulation/state", { signal }); }
export function controlSimulation(action: "start" | "pause" | "step" | "reset", expectedRevision: number, speed?: 1 | 2 | 5) { return apiRequest<SimulationState>("/api/simulation/control", { method: "POST", body: JSON.stringify({ action, expected_revision: expectedRevision, ...(speed ? { speed } : {}) }) }); }
export function getIncidents(signal?: AbortSignal) { return apiRequest<Incident[]>("/api/incidents", { signal }); }
export function createIncident(data: { incident_type: IncidentType; affected_resource: string; start_minute: number; duration_minutes: number; severity: Incident["severity"]; description: string; new_train?: TrainInput }) { return apiRequest<Incident>("/api/incidents", { method: "POST", body: JSON.stringify(data) }); }
export function updateIncidentStatus(id: number, status: Incident["status"]) { return apiRequest<Incident>(`/api/incidents/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }); }
export function replanIncident(data: { incident_id: number; base_plan_id: number; base_plan_version: number; expected_simulation_revision: number }) { return apiRequest<ReplanResult>("/api/incidents/replan", { method: "POST", body: JSON.stringify(data) }); }
export function getAnalytics(signal?: AbortSignal) { return apiRequest<Analytics>("/api/analytics", { signal }); }
export function runBenchmark() { return apiRequest<{ benchmark_id: string; scenario_identifier: string; results: BenchmarkResult[] }>("/api/analytics/benchmarks", { method: "POST", body: JSON.stringify({ maximum_delay_minutes: 30 }) }); }
