"""Operational analytics and evidence-backed decision explanations."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai.scheduling import Candidate, SolverStatus, build_domains, solve_cp_sat, solve_csp, solve_fcfs
from app.models import Incident, Platform, RouteMovement, SchedulingPlan, SimulationSession, SimulationState, SolverBenchmark, TrainAssignment
from app.models.enums import IncidentStatus, PlanStatus
from app.schemas.analytics import BenchmarkRequest
from app.services import schedules
from app.services.exceptions import InvalidOperationError


def scenario_identifier(simulation_session: SimulationSession) -> str:
    return f"{simulation_session.scenario_key}:{simulation_session.public_id}"


def _plan_options():
    return (
        selectinload(SchedulingPlan.assignments).selectinload(TrainAssignment.train),
        selectinload(SchedulingPlan.assignments).selectinload(TrainAssignment.platform),
        selectinload(SchedulingPlan.assignments).selectinload(TrainAssignment.route).selectinload(RouteMovement.reservations),
    )


def operational_plan(database: Session, session_id: int) -> SchedulingPlan | None:
    state = database.scalar(select(SimulationState).where(SimulationState.session_id == session_id))
    if state and state.active_plan_id:
        plan = database.scalar(select(SchedulingPlan).where(SchedulingPlan.id == state.active_plan_id, SchedulingPlan.session_id == session_id).options(*_plan_options()))
        if plan:
            return plan
    return database.scalar(select(SchedulingPlan).where(SchedulingPlan.session_id == session_id, SchedulingPlan.status != PlanStatus.ARCHIVED).order_by(SchedulingPlan.version.desc()).options(*_plan_options()))


def _timed(call: Callable[[], object]) -> tuple[object, float]:
    started = perf_counter()
    result = call()
    return result, (perf_counter() - started) * 1000


def run_benchmark(database: Session, simulation_session: SimulationSession, request: BenchmarkRequest) -> list[SolverBenchmark]:
    trains, platforms = schedules.load_resources(database, simulation_session.id)
    if not trains:
        raise InvalidOperationError("No active trains are available for an algorithm benchmark.")
    start = min(item.arrival_minute for item in trains)
    end = max(item.departure_minute + request.maximum_delay_minutes for item in trains) + max((item.clearance_minutes for item in platforms), default=0)
    train_problems, platform_problems = schedules._problems(trains, platforms)
    domains = build_domains(train_problems, platform_problems, horizon_start=start, horizon_end=end, maximum_delay=request.maximum_delay_minutes)
    preferred = schedules._preferred_platforms(database, simulation_session.id)
    solvers = (
        ("fcfs", lambda: solve_fcfs(train_problems, platform_problems, domains, preferred)),
        ("csp", lambda: solve_csp(train_problems, platform_problems, domains, preferred, node_limit=request.search_limit)),
        ("cp_sat", lambda: solve_cp_sat(train_problems, platform_problems, domains, preferred, time_limit_seconds=request.time_limit_seconds)),
    )
    benchmark_id = str(uuid.uuid4())
    identifier = scenario_identifier(simulation_session)
    records: list[SolverBenchmark] = []
    for engine, solver in solvers:
        result, elapsed = _timed(solver)
        delays = [item.delay for item in result.assignments.values()]
        record = SolverBenchmark(
            session_id=simulation_session.id,
            benchmark_id=benchmark_id,
            scenario_identifier=identifier,
            engine=engine,
            solver_status=result.status.value,
            execution_time_ms=elapsed,
            total_delay_minutes=sum(delays),
            maximum_delay_minutes=max(delays, default=0),
            processed_train_count=len(result.assignments),
            objective_value=result.objective,
            explanation=result.explanation,
        )
        database.add(record)
        records.append(record)
    database.commit()
    for record in records:
        database.refresh(record)
    return records


def latest_benchmark(database: Session, session_id: int) -> list[SolverBenchmark]:
    benchmark_id = database.scalar(select(SolverBenchmark.benchmark_id).where(SolverBenchmark.session_id == session_id).order_by(SolverBenchmark.created_at.desc(), SolverBenchmark.id.desc()).limit(1))
    if benchmark_id is None:
        return []
    return list(database.scalars(select(SolverBenchmark).where(SolverBenchmark.session_id == session_id, SolverBenchmark.benchmark_id == benchmark_id).order_by(SolverBenchmark.id)).all())


def replanning_impact(database: Session, plan: SchedulingPlan | None) -> dict:
    empty = {"base_plan_version": None, "current_plan_version": plan.version if plan else None, "changed_train_count": 0, "reassigned_train_count": 0, "delay_delta_minutes": 0}
    if plan is None:
        return empty
    prior = database.scalar(select(SchedulingPlan).where(SchedulingPlan.session_id == plan.session_id, SchedulingPlan.version < plan.version).order_by(SchedulingPlan.version.desc()).options(*_plan_options()))
    if prior is None:
        return empty
    before = {item.train_id: item for item in prior.assignments}
    after = {item.train_id: item for item in plan.assignments}
    changed = 0
    reassigned = 0
    for train_id in set(before) | set(after):
        old, new = before.get(train_id), after.get(train_id)
        if old is None or new is None or (old.platform_id, old.occupancy_start_minute, old.occupancy_end_minute) != (new.platform_id, new.occupancy_start_minute, new.occupancy_end_minute):
            changed += 1
        if old and new and old.platform_id != new.platform_id:
            reassigned += 1
    return {"base_plan_version": prior.version, "current_plan_version": plan.version, "changed_train_count": changed, "reassigned_train_count": reassigned, "delay_delta_minutes": sum(item.delay_minutes for item in after.values()) - sum(item.delay_minutes for item in before.values())}


def metric_snapshot(database: Session, session_id: int, plan: SchedulingPlan | None) -> dict:
    assignments = plan.assignments if plan else []
    delays = [item.delay_minutes for item in assignments]
    state = database.scalar(select(SimulationState).where(SimulationState.session_id == session_id))
    current_minute = state.current_minute if state else 0
    active_incidents = database.scalar(select(func.count()).select_from(Incident).where(Incident.session_id == session_id, Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.MONITORING]))) or 0
    red_movements = sum(1 for item in assignments if item.route and item.route.indicator == "RED")
    feasible = bool(plan and plan.solver_status in {SolverStatus.FEASIBLE.value, SolverStatus.OPTIMAL.value} and plan.is_validated and plan.route_validated)
    return {
        "plan_id": plan.id if plan else None,
        "plan_version": plan.version if plan else None,
        "total_arrival_delay_minutes": sum(delays),
        "average_delay_minutes": round(sum(delays) / len(delays), 2) if delays else 0,
        "maximum_delay_minutes": max(delays, default=0),
        "train_processing_count": sum(item.occupancy_end_minute <= current_minute for item in assignments),
        "active_conflicts": active_incidents + red_movements,
        "schedule_feasible": feasible,
        "solver_execution_time_ms": plan.execution_time_ms if plan else None,
        "rescheduling_impact": replanning_impact(database, plan),
    }


def platform_utilization(plan: SchedulingPlan | None, platforms: list[Platform]) -> list[dict]:
    horizon = (plan.horizon_end_minute - plan.horizon_start_minute) if plan else 0
    return [
        {
            "platform_code": platform.code,
            "occupied_minutes": sum(item.occupancy_end_minute - item.occupancy_start_minute for item in (plan.assignments if plan else []) if item.platform_id == platform.id),
            "utilization_percent": round(100 * sum(item.occupancy_end_minute - item.occupancy_start_minute for item in (plan.assignments if plan else []) if item.platform_id == platform.id) / horizon, 2) if horizon else 0,
            "train_count": sum(item.platform_id == platform.id for item in (plan.assignments if plan else [])),
        }
        for platform in platforms
    ]


def delay_distribution(plan: SchedulingPlan | None) -> list[dict]:
    delays = [item.delay_minutes for item in plan.assignments] if plan else []
    buckets = (("On time", lambda value: value == 0), ("1–5 min", lambda value: 1 <= value <= 5), ("6–10 min", lambda value: 6 <= value <= 10), ("11–20 min", lambda value: 11 <= value <= 20), ("21+ min", lambda value: value >= 21))
    return [{"label": label, "train_count": sum(predicate(value) for value in delays)} for label, predicate in buckets]


def operational_trends(database: Session, session_id: int) -> list[dict]:
    plans = list(database.scalars(select(SchedulingPlan).where(SchedulingPlan.session_id == session_id).order_by(SchedulingPlan.version.desc()).limit(12).options(selectinload(SchedulingPlan.assignments))).unique().all())
    result = []
    for plan in reversed(plans):
        total = sum(item.delay_minutes for item in plan.assignments)
        result.append({"plan_version": plan.version, "engine": plan.engine, "total_delay_minutes": total, "average_delay_minutes": round(total / len(plan.assignments), 2) if plan.assignments else 0, "execution_time_ms": plan.execution_time_ms, "created_at": plan.created_at})
    return result


def platform_decisions(plan: SchedulingPlan | None, platforms: list[Platform]) -> list[dict]:
    if plan is None:
        return []
    platform_map = {item.id: item for item in platforms}
    candidate_map = {item.train_id: Candidate(item.platform_id, item.occupancy_start_minute, item.occupancy_end_minute, item.delay_minutes) for item in plan.assignments}
    results = []
    for assignment in sorted(plan.assignments, key=lambda item: item.train.identifier):
        train = assignment.train
        compatible_ids = {link.platform_id for link in train.compatible_platforms}
        accepted = [
            f"The persisted solver outcome selected {assignment.platform.code}.",
            f"The compatibility mapping {'permits' if assignment.platform_id in compatible_ids else 'does not currently permit'} this train-platform pair.",
            f"Its {assignment.platform.length_meters} m length accommodates the {train.length_meters} m train.",
            f"The platform is {'currently available' if assignment.platform.is_available else 'currently unavailable and requires replanning'}.",
            f"The {assignment.occupancy_start_minute}–{assignment.occupancy_end_minute} interval {'passed independent validation' if plan.is_validated else 'has not passed current independent validation'} against the {plan.maximum_delay_minutes}-minute delay limit.",
        ]
        rejected = []
        for platform in platforms:
            if platform.id == assignment.platform_id:
                continue
            reasons = []
            if not platform.is_available:
                reasons.append(platform.unavailable_reason or "The platform is unavailable.")
            if platform.id not in compatible_ids:
                reasons.append("The train-platform compatibility mapping does not allow this platform.")
            if train.required_platform_type and train.required_platform_type != platform.platform_type:
                reasons.append(f"The platform type is {platform.platform_type}, not {train.required_platform_type}.")
            if train.length_meters > platform.length_meters:
                reasons.append(f"The {platform.length_meters} m platform is shorter than the {train.length_meters} m train.")
            proposed = Candidate(platform.id, assignment.occupancy_start_minute, assignment.occupancy_end_minute, assignment.delay_minutes)
            if any(
                other.train_id != train.id
                and candidate_map[other.train_id].platform_id == platform.id
                and proposed.start < candidate_map[other.train_id].end + platform.clearance_minutes
                and candidate_map[other.train_id].start < proposed.end + platform.clearance_minutes
                for other in plan.assignments
            ):
                reasons.append("The assigned interval conflicts with another train, including platform clearance.")
            if not reasons:
                reasons.append("This platform remained constraint-feasible, but the solver selected the persisted alternative under its deterministic ordering or objective.")
            rejected.append({"platform_code": platform.code, "reasons": reasons})
        route = assignment.route
        results.append({"train_identifier": train.identifier, "assigned_platform": assignment.platform.code, "accepted_reasons": accepted, "rejected_platforms": rejected, "route_decision": route.decision if route else None, "route_explanation": route.explanation if route else None})
    return results


def decision_insights(database: Session, session_id: int, plan: SchedulingPlan | None, metrics: dict) -> list[dict]:
    if plan is None:
        return []
    insights = [{"category": "solver", "title": f"{plan.engine.upper()} schedule outcome", "summary": plan.explanation, "evidence": [f"Solver status: {plan.solver_status}", f"Platform validation: {'passed' if plan.is_validated else 'not passed'}", f"Route reservations: {'validated' if plan.route_validated else 'not validated'}"]}]
    route_count = sum(len(item.route.reservations) for item in plan.assignments if item.route)
    allowed = sum(item.route is not None and item.route.decision == "MovementAllowed" for item in plan.assignments)
    insights.append({"category": "routing", "title": "Route reservation and knowledge-base outcome", "summary": f"{allowed} movement decisions are allowed after evaluating platform facts, route availability, and blocked-resource predicates.", "evidence": [f"{route_count} track and switch reservations persisted", f"{metrics['active_conflicts']} active incident or route conflict signals"]})
    impact = metrics["rescheduling_impact"]
    if impact["base_plan_version"] is not None:
        incident = database.scalar(select(Incident).where(Incident.session_id == session_id).order_by(Incident.created_at.desc(), Incident.id.desc()).limit(1)) if plan.name.startswith("Incident replan") else None
        reason = f" after {incident.title}" if incident else " after the latest planning change"
        insights.append({"category": "replanning", "title": "Latest plan change", "summary": f"Plan v{impact['current_plan_version']} changed {impact['changed_train_count']} train allocation(s){reason}.", "evidence": [f"{impact['reassigned_train_count']} train(s) changed platform", f"Total delay changed by {impact['delay_delta_minutes']:+d} minutes", "Committed movements remain fixed during incident replanning"]})
    return insights
