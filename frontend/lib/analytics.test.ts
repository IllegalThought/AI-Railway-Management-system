import { describe, expect, it } from "vitest";
import { mapBenchmarkChart, mapTrendChart } from "./analytics";

describe("analytics chart mapping", () => {
  it("maps benchmark values without inventing improvements", () => {
    expect(mapBenchmarkChart([{ benchmark_id: "b", scenario_identifier: "s", engine: "cp_sat", solver_status: "FEASIBLE", execution_time_ms: 1.23456, total_delay_minutes: 18, average_delay_minutes: 6, maximum_delay_minutes: 10, processed_train_count: 3, objective_value: 18, optimality_proven: false, explanation: "Measured", created_at: "2026-10-20T00:00:00Z" }])).toEqual([{ engine: "OR-Tools CP-SAT", delay: 18, averageDelay: 6, executionMs: 1.235, status: "FEASIBLE" }]);
  });

  it("keeps unavailable execution timing as null", () => {
    expect(mapTrendChart([{ plan_version: 2, engine: "csp", total_delay_minutes: 5, average_delay_minutes: 2.5, execution_time_ms: null, created_at: "2026-10-20T00:00:00Z" }])[0].executionMs).toBeNull();
  });
});
