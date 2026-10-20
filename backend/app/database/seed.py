from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SimulationSession
from app.services.scenarios import restore_scenario


DEFAULT_DEMO_SESSION_KEY = "default-demo"
DEFAULT_DEMO_PUBLIC_ID = "00000000-0000-4000-8000-000000000001"


@dataclass(frozen=True)
class SeedResult:
    session_id: int
    created: bool


def seed_demo_data(database: Session) -> SeedResult:
    """Create the baseline synthetic dataset once and return its session."""

    existing = database.scalar(
        select(SimulationSession).where(
            SimulationSession.session_key == DEFAULT_DEMO_SESSION_KEY
        )
    )
    if existing is not None:
        return SeedResult(session_id=existing.id, created=False)

    demo = SimulationSession(
        public_id=DEFAULT_DEMO_PUBLIC_ID,
        name="Normal traffic demo",
        session_key=DEFAULT_DEMO_SESSION_KEY,
        scenario_key="normal-traffic",
    )
    database.add(demo)
    database.flush()
    restore_scenario(database, demo, "normal-traffic", commit=False)
    database.commit()
    database.refresh(demo)
    return SeedResult(session_id=demo.id, created=True)

