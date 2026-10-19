from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Platform,
    SimulationSession,
    TrackEdge,
    TrackNode,
    Train,
    TrainPlatformCompatibility,
)


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
        name="RailOps AI Demonstration",
        session_key=DEFAULT_DEMO_SESSION_KEY,
    )
    platform_1 = Platform(
        session=demo,
        code="P1",
        platform_type="passenger",
        length_meters=350,
        clearance_minutes=3,
    )
    platform_2 = Platform(
        session=demo,
        code="P2",
        platform_type="passenger",
        length_meters=280,
        clearance_minutes=3,
    )
    entry = TrackNode(session=demo, code="N-ENTRY", name="West Entry", node_type="junction")
    station = TrackNode(session=demo, code="N-STATION", name="Central Station", node_type="station")
    edge = TrackEdge(
        session=demo,
        code="T-WEST-01",
        from_node=entry,
        to_node=station,
        traversal_minutes=5,
        capacity=1,
        resource_group="west-approach",
    )
    train = Train(
        session=demo,
        identifier="RA-101",
        priority=3,
        arrival_minute=480,
        departure_minute=495,
        minimum_dwell_minutes=10,
        length_meters=220,
        required_platform_type="passenger",
    )
    train.compatible_platforms = [
        TrainPlatformCompatibility(platform=platform_1),
        TrainPlatformCompatibility(platform=platform_2),
    ]
    database.add_all([demo, platform_1, platform_2, entry, station, edge, train])
    database.commit()
    database.refresh(demo)
    return SeedResult(session_id=demo.id, created=True)

