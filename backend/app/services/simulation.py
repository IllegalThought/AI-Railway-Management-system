"""Persisted deterministic simulation clock and live state projection."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.base import utc_now
from app.models import Incident, OperationalEvent, Platform, RouteMovement, SchedulingPlan, SimulationState, TrainAssignment
from app.models.enums import EventType, IncidentStatus, PlanStatus, SimulationRunStatus
from app.schemas.simulation import SimulationAction
from app.services.exceptions import InvalidOperationError


def get_or_create_state(database: Session, session_id: int) -> SimulationState:
    state = database.scalar(select(SimulationState).where(SimulationState.session_id == session_id))
    if state is None:
        state = SimulationState(session_id=session_id)
        database.add(state)
        database.flush()
    return state


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def materialize_clock(database: Session, state: SimulationState) -> None:
    if state.run_status != SimulationRunStatus.RUNNING:
        return
    now = utc_now()
    if state.last_tick_at is None:
        state.last_tick_at = now
        return
    elapsed_seconds = max(0, int((now - _aware(state.last_tick_at)).total_seconds()))
    if elapsed_seconds:
        state.current_minute += elapsed_seconds * state.speed
        state.last_tick_at = now
        state.revision += 1
        database.commit()


def control(database: Session, session_id: int, action: SimulationAction, expected_revision: int, speed: int | None) -> SimulationState:
    state = get_or_create_state(database, session_id)
    materialize_clock(database, state)
    if state.revision != expected_revision:
        raise InvalidOperationError("The simulation state changed. Refresh the live state before issuing another control command.")
    now = utc_now()
    event_type: EventType
    message: str
    if speed is not None:
        state.speed = speed
    if action == SimulationAction.START:
        plan = database.scalar(select(SchedulingPlan).where(SchedulingPlan.session_id == session_id, SchedulingPlan.status == PlanStatus.APPLIED).order_by(SchedulingPlan.version.desc()))
        if plan is None or not plan.is_validated or not plan.route_validated:
            raise InvalidOperationError("Apply a validated schedule before starting the simulation.")
        state.active_plan_id = plan.id
        if state.current_minute == 0:
            state.current_minute = plan.horizon_start_minute
        state.run_status = SimulationRunStatus.RUNNING
        state.last_tick_at = now
        event_type, message = EventType.SIMULATION_STARTED, f"Simulation started at {state.speed}x speed."
    elif action == SimulationAction.PAUSE:
        state.run_status = SimulationRunStatus.PAUSED
        state.last_tick_at = None
        event_type, message = EventType.SIMULATION_PAUSED, "Simulation paused."
    elif action == SimulationAction.STEP:
        if state.run_status == SimulationRunStatus.RUNNING:
            raise InvalidOperationError("Pause the simulation before stepping forward.")
        state.current_minute += state.speed
        event_type, message = EventType.SIMULATION_STEPPED, f"Simulation stepped forward {state.speed} minute(s)."
    else:
        plan = database.scalar(select(SchedulingPlan).where(SchedulingPlan.session_id == session_id, SchedulingPlan.status == PlanStatus.APPLIED).order_by(SchedulingPlan.version.desc()))
        state.current_minute = plan.horizon_start_minute if plan else 0
        state.active_plan_id = plan.id if plan else None
        state.run_status = SimulationRunStatus.PAUSED
        state.last_tick_at = None
        event_type, message = EventType.SIMULATION_RESET, "Simulation reset to the active plan start."
    state.revision += 1
    database.add(OperationalEvent(session_id=session_id, event_type=event_type, event_minute=state.current_minute, message=message))
    database.commit()
    database.refresh(state)
    return state


def _active_plan(database: Session, state: SimulationState) -> SchedulingPlan | None:
    if state.active_plan_id is None:
        return None
    return database.scalar(
        select(SchedulingPlan).where(SchedulingPlan.id == state.active_plan_id).options(
            selectinload(SchedulingPlan.assignments).selectinload(TrainAssignment.train),
            selectinload(SchedulingPlan.assignments).selectinload(TrainAssignment.platform),
            selectinload(SchedulingPlan.assignments).selectinload(TrainAssignment.route).selectinload(RouteMovement.reservations),
        )
    )


def project_state(database: Session, session_id: int) -> dict:
    state = get_or_create_state(database, session_id)
    materialize_clock(database, state)
    plan = _active_plan(database, state)
    current = state.current_minute
    train_states: list[dict] = []
    active_reservations: list[dict] = []
    occupied: dict[str, str] = {}
    blocked_now = set(database.scalars(select(Incident.resource_code).where(Incident.session_id == session_id, Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.MONITORING]), Incident.start_minute <= current, Incident.start_minute + Incident.duration_minutes > current, Incident.resource_code.is_not(None))).all())
    if plan:
        for assignment in sorted(plan.assignments, key=lambda item: item.train.identifier):
            movement = assignment.route
            reservations = sorted(movement.reservations, key=lambda item: (item.start_minute, item.sequence)) if movement else []
            active = next((item for item in reservations if item.start_minute <= current < item.end_minute), None)
            first = reservations[0].start_minute if reservations else assignment.occupancy_start_minute
            last = reservations[-1].end_minute if reservations else assignment.occupancy_end_minute
            if current < first:
                status, position = "scheduled", assignment.train.origin_node_code or "Entry pending"
            elif current < assignment.occupancy_start_minute:
                status, position = "approaching", active.edge_code if active and active.edge_code else active.resource_code if active else "Approach held"
            elif current < assignment.occupancy_end_minute:
                status, position = "at_platform", assignment.platform.code
                occupied[assignment.platform.code] = assignment.train.identifier
            elif current < last:
                status, position = "departing", active.edge_code if active and active.edge_code else active.resource_code if active else "Departure held"
            else:
                status, position = "completed", assignment.train.destination_node_code or "Exited"
            span = max(1, last - first)
            progress = min(100, max(0, round((current - first) * 100 / span)))
            indicator = movement.indicator if movement else "YELLOW"
            decision = movement.decision if movement else "MovementBlocked"
            if assignment.platform.code in blocked_now or (active and (active.resource_code in blocked_now or active.edge_code in blocked_now)):
                indicator, decision = "RED", "MovementBlocked"
            train_states.append({"train_id": assignment.train_id, "train_identifier": assignment.train.identifier, "status": status, "position": position, "platform_code": assignment.platform.code, "progress_percent": progress, "movement_permission": decision, "signal": indicator})
            if active:
                active_reservations.append({"train_identifier": assignment.train.identifier, "resource_code": active.resource_code, "resource_type": active.resource_type, "start_minute": active.start_minute, "end_minute": active.end_minute})
    platforms = list(database.scalars(select(Platform).where(Platform.session_id == session_id).order_by(Platform.code)).all())
    events = list(database.scalars(select(OperationalEvent).where(OperationalEvent.session_id == session_id, OperationalEvent.event_minute <= current).order_by(OperationalEvent.event_minute.desc(), OperationalEvent.id.desc()).limit(30)).all())
    return {"state": state, "plan": plan, "trains": train_states, "platforms": [{"platform_code": item.code, "train_identifier": occupied.get(item.code), "occupied": item.code in occupied} for item in platforms], "reservations": active_reservations, "events": events}
