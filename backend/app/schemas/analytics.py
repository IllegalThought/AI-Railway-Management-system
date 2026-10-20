from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel


class BenchmarkRequest(ApiModel):
    maximum_delay_minutes: int = Field(default=30, ge=0, le=240)
    search_limit: int = Field(default=100_000, ge=1, le=500_000)
    time_limit_seconds: float = Field(default=10, gt=0, le=15)


class BenchmarkResultResponse(ApiModel):
    benchmark_id: str
    scenario_identifier: str
    engine: str
    solver_status: str
    execution_time_ms: float
    total_delay_minutes: int
    average_delay_minutes: float
    maximum_delay_minutes: int
    processed_train_count: int
    objective_value: int | None
    optimality_proven: bool
    explanation: str
    created_at: datetime


class BenchmarkResponse(ApiModel):
    benchmark_id: str
    scenario_identifier: str
    results: list[BenchmarkResultResponse]


class PlatformUtilizationMetric(ApiModel):
    platform_code: str
    occupied_minutes: int
    utilization_percent: float
    train_count: int


class DelayDistributionBucket(ApiModel):
    label: str
    train_count: int


class OperationalTrendPoint(ApiModel):
    plan_version: int
    engine: str
    total_delay_minutes: int
    average_delay_minutes: float
    execution_time_ms: float | None
    created_at: datetime


class ReplanningImpact(ApiModel):
    base_plan_version: int | None
    current_plan_version: int | None
    changed_train_count: int
    reassigned_train_count: int
    delay_delta_minutes: int


class OperationalMetrics(ApiModel):
    plan_id: int | None
    plan_version: int | None
    total_arrival_delay_minutes: int
    average_delay_minutes: float
    maximum_delay_minutes: int
    train_processing_count: int
    active_conflicts: int
    schedule_feasible: bool
    solver_execution_time_ms: float | None
    rescheduling_impact: ReplanningImpact


class RejectedPlatform(ApiModel):
    platform_code: str
    reasons: list[str]


class PlatformDecisionInsight(ApiModel):
    train_identifier: str
    assigned_platform: str
    accepted_reasons: list[str]
    rejected_platforms: list[RejectedPlatform]
    route_decision: str | None
    route_explanation: str | None


class DecisionInsight(ApiModel):
    category: str
    title: str
    summary: str
    evidence: list[str]


class AnalyticsResponse(ApiModel):
    scenario_identifier: str
    metrics: OperationalMetrics
    platform_utilization: list[PlatformUtilizationMetric]
    delay_distribution: list[DelayDistributionBucket]
    operational_trends: list[OperationalTrendPoint]
    latest_benchmark: list[BenchmarkResultResponse]
    platform_decisions: list[PlatformDecisionInsight]
    decision_insights: list[DecisionInsight]
    message: str
