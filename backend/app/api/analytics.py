from fastapi import APIRouter, status

from app.api.dependencies import ActiveSession, DatabaseSession
from app.schemas.analytics import AnalyticsResponse, BenchmarkRequest, BenchmarkResponse, BenchmarkResultResponse
from app.services import analytics, schedules


router = APIRouter(prefix="/analytics", tags=["Performance analytics"])


def benchmark_response(records) -> BenchmarkResponse:
    return BenchmarkResponse(
        benchmark_id=records[0].benchmark_id,
        scenario_identifier=records[0].scenario_identifier,
        results=[BenchmarkResultResponse(
            benchmark_id=item.benchmark_id,
            scenario_identifier=item.scenario_identifier,
            engine=item.engine,
            solver_status=item.solver_status,
            execution_time_ms=round(item.execution_time_ms, 3),
            total_delay_minutes=item.total_delay_minutes,
            average_delay_minutes=round(item.total_delay_minutes / item.processed_train_count, 2) if item.processed_train_count else 0,
            maximum_delay_minutes=item.maximum_delay_minutes,
            processed_train_count=item.processed_train_count,
            objective_value=item.objective_value,
            optimality_proven=item.solver_status == "OPTIMAL",
            explanation=item.explanation,
            created_at=item.created_at,
        ) for item in records],
    )


@router.get("", response_model=AnalyticsResponse)
def get_analytics(database: DatabaseSession, simulation_session: ActiveSession) -> AnalyticsResponse:
    plan = analytics.operational_plan(database, simulation_session.id)
    platforms = schedules.load_resources(database, simulation_session.id)[1]
    metrics = analytics.metric_snapshot(database, simulation_session.id, plan)
    benchmarks = analytics.latest_benchmark(database, simulation_session.id)
    return AnalyticsResponse(
        scenario_identifier=analytics.scenario_identifier(simulation_session),
        metrics=metrics,
        platform_utilization=analytics.platform_utilization(plan, platforms),
        delay_distribution=analytics.delay_distribution(plan),
        operational_trends=analytics.operational_trends(database, simulation_session.id),
        latest_benchmark=benchmark_response(benchmarks).results if benchmarks else [],
        platform_decisions=analytics.platform_decisions(plan, platforms),
        decision_insights=analytics.decision_insights(database, simulation_session.id, plan, metrics),
        message="Operational analytics are based on the current persisted station state." if plan else "Generate a schedule to populate operational analytics.",
    )


@router.post("/benchmarks", response_model=BenchmarkResponse, status_code=status.HTTP_201_CREATED)
def create_benchmark(data: BenchmarkRequest, database: DatabaseSession, simulation_session: ActiveSession) -> BenchmarkResponse:
    records = analytics.run_benchmark(database, simulation_session, data)
    return benchmark_response(records)
