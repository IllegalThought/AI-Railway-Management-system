import uuid
from datetime import timezone
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import utc_now
from app.database.session import get_db
from app.models import SimulationSession
from app.models.enums import SessionStatus
from app.services.exceptions import InvalidSessionError
from app.services.scenarios import restore_scenario


SESSION_HEADER = "X-RailOps-Session"


def get_active_session(
    database: Annotated[Session, Depends(get_db)],
    session_header: Annotated[str | None, Header(alias=SESSION_HEADER)] = None,
) -> SimulationSession:
    if not session_header:
        raise InvalidSessionError(
            f"The {SESSION_HEADER} header is required for isolated demo data."
        )
    try:
        session_id = str(uuid.UUID(session_header))
    except ValueError as exc:
        raise InvalidSessionError(
            f"The {SESSION_HEADER} header must contain a valid UUID."
        ) from exc

    simulation_session = database.scalar(
        select(SimulationSession).where(SimulationSession.public_id == session_id)
    )
    if simulation_session is not None:
        expires_at = simulation_session.expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if simulation_session.status != SessionStatus.ACTIVE:
            raise InvalidSessionError("This demo workspace is archived and is no longer active.")
        if expires_at is not None and expires_at <= utc_now():
            raise InvalidSessionError("This demo workspace has expired.")
        return simulation_session

    simulation_session = SimulationSession(
        public_id=session_id,
        name="Isolated demo workspace",
        scenario_key="normal-traffic",
    )
    database.add(simulation_session)
    try:
        database.flush()
        restore_scenario(database, simulation_session, "normal-traffic", commit=False)
        database.commit()
    except IntegrityError:
        database.rollback()
        simulation_session = database.scalar(
            select(SimulationSession).where(SimulationSession.public_id == session_id)
        )
        if simulation_session is None:
            raise
    database.refresh(simulation_session)
    return simulation_session


ActiveSession = Annotated[SimulationSession, Depends(get_active_session)]
DatabaseSession = Annotated[Session, Depends(get_db)]
