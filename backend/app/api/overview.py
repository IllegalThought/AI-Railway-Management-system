from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.dependencies import ActiveSession, DatabaseSession
from app.models import Incident, OperationalEvent, Platform, Train
from app.models.enums import IncidentStatus, TrainStatus
from app.schemas.operations import ActivitySummary, IncidentSummary, OverviewResponse
from app.services.scenarios import get_scenario


router = APIRouter(prefix="/overview", tags=["Operations"])


@router.get("", response_model=OverviewResponse, summary="Get operational overview")
def get_overview(database: DatabaseSession, simulation_session: ActiveSession) -> OverviewResponse:
    session_id = simulation_session.id
    train_count = database.scalar(select(func.count()).select_from(Train).where(Train.session_id == session_id)) or 0
    scheduled_count = database.scalar(select(func.count()).select_from(Train).where(Train.session_id == session_id, Train.service_status == TrainStatus.SCHEDULED)) or 0
    delayed_count = database.scalar(select(func.count()).select_from(Train).where(Train.session_id == session_id, Train.service_status == TrainStatus.DELAYED)) or 0
    platform_count = database.scalar(select(func.count()).select_from(Platform).where(Platform.session_id == session_id)) or 0
    available_count = database.scalar(select(func.count()).select_from(Platform).where(Platform.session_id == session_id, Platform.is_available.is_(True))) or 0
    active_incident_count = database.scalar(select(func.count()).select_from(Incident).where(Incident.session_id == session_id, Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.MONITORING]))) or 0
    incidents = database.scalars(select(Incident).where(Incident.session_id == session_id, Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.MONITORING])).order_by(Incident.reported_minute.desc()).limit(5)).all()
    upcoming = database.scalars(select(Train).where(Train.session_id == session_id, Train.service_status != TrainStatus.CANCELLED).order_by(Train.arrival_minute, Train.identifier).limit(5)).all()
    events = database.scalars(select(OperationalEvent).where(OperationalEvent.session_id == session_id).order_by(OperationalEvent.created_at.desc(), OperationalEvent.id.desc()).limit(5)).all()
    scenario = get_scenario(simulation_session.scenario_key)
    return OverviewResponse(
        scenario_key=scenario.key,
        scenario_name=scenario.name,
        train_count=train_count,
        scheduled_train_count=scheduled_count,
        delayed_train_count=delayed_count,
        platform_count=platform_count,
        available_platform_count=available_count,
        unavailable_platform_count=platform_count - available_count,
        active_incident_count=active_incident_count,
        upcoming_trains=[{"id": item.id, "identifier": item.identifier, "arrival_minute": item.arrival_minute, "departure_minute": item.departure_minute, "service_status": item.service_status.value, "delay_minutes": item.delay_minutes} for item in upcoming],
        active_incidents=[IncidentSummary.model_validate(item) for item in incidents],
        recent_activity=[ActivitySummary.model_validate(item) for item in events],
    )
