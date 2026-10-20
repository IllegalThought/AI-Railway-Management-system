import type { Analytics, BenchmarkResult } from "./api";

export const engineLabel = (engine: string) => engine === "cp_sat" ? "OR-Tools CP-SAT" : engine === "csp" ? "Custom CSP" : "FCFS";

export function mapBenchmarkChart(results: BenchmarkResult[]) {
  return results.map((item) => ({
    engine: engineLabel(item.engine),
    delay: item.total_delay_minutes,
    averageDelay: item.average_delay_minutes,
    executionMs: Number(item.execution_time_ms.toFixed(3)),
    status: item.solver_status,
  }));
}

export function mapTrendChart(trends: Analytics["operational_trends"]) {
  return trends.map((item) => ({
    plan: `v${item.plan_version}`,
    delay: item.total_delay_minutes,
    averageDelay: item.average_delay_minutes,
    executionMs: item.execution_time_ms === null ? null : Number(item.execution_time_ms.toFixed(3)),
  }));
}
