from fastapi import APIRouter, status
from app.api.dependencies import ActiveSession, DatabaseSession
from app.api.schedules import plan_response
from app.models import Incident
from app.models.enums import IncidentStatus
from app.schemas.common import ApiModel, ErrorResponse
from app.schemas.simulation import AssignmentChange, IncidentCreate, IncidentResponse, ReplanRequest, ReplanResponse
from app.services import incidents
from app.services.exceptions import RecordNotFoundError


router = APIRouter(prefix="/incidents", tags=["Incident management"])


class IncidentStatusUpdate(ApiModel):
    status: IncidentStatus


def incident_response(database: DatabaseSession, incident: Incident) -> IncidentResponse:
    return IncidentResponse(
        id=incident.id,
        incident_type=incident.incident_type,
        affected_resource=incident.resource_code or "",
        start_minute=incident.start_minute,
        duration_minutes=incident.duration_minutes,
        severity=incident.severity,
        status=incident.status,
        description=incident.description,
        title=incident.title,
        affected_train_ids=incidents.affected_train_ids(database, incident),
        created_at=incident.created_at,
    )


@router.get("", response_model=list[IncidentResponse])
def list_all(database: DatabaseSession, simulation_session: ActiveSession) -> list[IncidentResponse]:
    return [incident_response(database, item) for item in incidents.list_incidents(database, simulation_session.id)]


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED, responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def create(data: IncidentCreate, database: DatabaseSession, simulation_session: ActiveSession) -> IncidentResponse:
    return incident_response(database, incidents.create_incident(database, simulation_session, data))


@router.patch("/{incident_id}", response_model=IncidentResponse, responses={404: {"model": ErrorResponse}})
def change_status(incident_id: int, data: IncidentStatusUpdate, database: DatabaseSession, simulation_session: ActiveSession) -> IncidentResponse:
    return incident_response(database, incidents.update_status(database, simulation_session.id, incident_id, data.status))


@router.post("/replan", response_model=ReplanResponse, responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def replan(data: ReplanRequest, database: DatabaseSession, simulation_session: ActiveSession) -> ReplanResponse:
    incident = next((item for item in incidents.list_incidents(database, simulation_session.id) if item.id == data.incident_id), None)
    if incident is None:
        raise RecordNotFoundError("Incident was not found in this demo workspace.")
    base, revised, preserved, affected, issues = incidents.replan(database, simulation_session, incident, data.base_plan_id, data.base_plan_version, data.expected_simulation_revision)
    before_response, after_response = plan_response(database, base), plan_response(database, revised)
    before = {item.train_id: item for item in before_response.assignments}
    after = {item.train_id: item for item in after_response.assignments}
    train_ids = sorted(set(before) | set(after), key=lambda train_id: (after.get(train_id) or before[train_id]).train_identifier)
    changes: list[AssignmentChange] = []
    for train_id in train_ids:
        old, new = before.get(train_id), after.get(train_id)
        if old is None:
            change = "Added"
            reason = f"The {incident.title.lower()} introduced this service into the replanning problem."
        elif new is None:
            change = "Unassigned"
            reason = f"No assignment satisfied the platform, timing, and route constraints after {incident.title.lower()}."
        elif (old.platform_id, old.occupancy_start_minute, old.occupancy_end_minute) == (new.platform_id, new.occupancy_start_minute, new.occupancy_end_minute):
            change = "Preserved" if train_id in preserved else "Unchanged"
            reason = "The movement had already started and was preserved as a non-revocable reservation." if train_id in preserved else "The existing allocation still satisfied all platform, delay, and route constraints."
        else:
            change = "Reallocated"
            reason = f"The allocation changed after {incident.title.lower()} so the revised plan could satisfy current availability, delay, and reservation constraints."
        changes.append(AssignmentChange(train_identifier=(new or old).train_identifier, before=old, after=new, change=change, reason=reason))
    valid = revised.is_validated and revised.route_validated
    reason = None if valid else (issues[0].message if issues else revised.explanation)
    return ReplanResponse(base_plan=before_response, revised_plan=after_response, valid=valid, infeasible_reason=reason, preserved_train_ids=preserved, affected_train_ids=affected, changes=changes, message="A validated revised plan is ready for operator review." if valid else "No valid revised plan could be produced; the active plan was left unchanged.")
