from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import (
    Incident,
    OperationalEvent,
    Platform,
    SchedulingPlan,
    SimulationSession,
    TrackEdge,
    TrackNode,
    Train,
    TrainAssignment,
    TrainPlatformCompatibility,
)
from app.models.enums import (
    EventType,
    IncidentSeverity,
    IncidentStatus,
    TrainStatus,
)
from app.services.exceptions import RecordNotFoundError


@dataclass(frozen=True)
class ScenarioDefinition:
    key: str
    name: str
    description: str
    train_count: int
    platform_count: int = 5


SCENARIOS = {
    item.key: item
    for item in (
        ScenarioDefinition(
            "normal-traffic",
            "Normal traffic",
            "A balanced service pattern with twenty scheduled trains and five available platforms.",
            20,
        ),
        ScenarioDefinition(
            "congested-station",
            "Congested station",
            "A compressed arrival pattern that creates sustained demand across all platforms.",
            28,
        ),
        ScenarioDefinition(
            "multiple-delayed-trains",
            "Multiple delayed trains",
            "Twenty services with several recorded delays of varying duration.",
            20,
        ),
        ScenarioDefinition(
            "platform-closure",
            "Platform closure",
            "Normal traffic with Platform P3 unavailable for infrastructure inspection.",
            20,
        ),
        ScenarioDefinition(
            "track-closure",
            "Track closure",
            "Normal traffic with the west approach closed and an active operational incident.",
            20,
        ),
    )
}


def list_scenarios() -> list[ScenarioDefinition]:
    return list(SCENARIOS.values())


def get_scenario(key: str) -> ScenarioDefinition:
    scenario = SCENARIOS.get(key)
    if scenario is None:
        raise RecordNotFoundError(f"Demo scenario '{key}' was not found.")
    return scenario


def restore_scenario(
    database: Session,
    simulation_session: SimulationSession,
    scenario_key: str,
    *,
    commit: bool = True,
) -> ScenarioDefinition:
    scenario = get_scenario(scenario_key)
    session_id = simulation_session.id

    database.execute(
        delete(TrainAssignment).where(
            TrainAssignment.plan_id.in_(
                database.query(SchedulingPlan.id).filter(SchedulingPlan.session_id == session_id)
            )
        )
    )
    database.execute(
        delete(TrainPlatformCompatibility).where(
            TrainPlatformCompatibility.train_id.in_(
                database.query(Train.id).filter(Train.session_id == session_id)
            )
        )
    )
    for model in (
        SchedulingPlan,
        OperationalEvent,
        Incident,
        TrackEdge,
        TrackNode,
        Train,
        Platform,
    ):
        database.execute(delete(model).where(model.session_id == session_id))

    platforms = _build_platforms(simulation_session, scenario_key)
    database.add_all(platforms)
    database.flush()

    trains = _build_trains(simulation_session, scenario, platforms)
    database.add_all(trains)
    _add_network(database, simulation_session)
    _add_scenario_incidents(database, simulation_session, scenario_key)

    simulation_session.scenario_key = scenario_key
    simulation_session.name = f"{scenario.name} demo"
    database.add(
        OperationalEvent(
            session=simulation_session,
            event_type=EventType.SCENARIO_RESTORED,
            event_minute=0,
            message=f"The {scenario.name} scenario was restored.",
        )
    )
    if commit:
        database.commit()
        database.refresh(simulation_session)
    return scenario


def _build_platforms(
    simulation_session: SimulationSession, scenario_key: str
) -> list[Platform]:
    lengths = (360, 320, 300, 280, 240)
    platforms = [
        Platform(
            session=simulation_session,
            code=f"P{index}",
            platform_type="passenger",
            length_meters=length,
            clearance_minutes=3 if index < 5 else 4,
        )
        for index, length in enumerate(lengths, start=1)
    ]
    if scenario_key == "platform-closure":
        platforms[2].is_available = False
        platforms[2].unavailable_reason = "Infrastructure inspection"
    return platforms


def _build_trains(
    simulation_session: SimulationSession,
    scenario: ScenarioDefinition,
    platforms: list[Platform],
) -> list[Train]:
    interval = 6 if scenario.key == "congested-station" else 18
    trains: list[Train] = []
    for index in range(1, scenario.train_count + 1):
        arrival = 360 + (index - 1) * interval
        dwell = 10 + (index % 3) * 2
        delayed = scenario.key == "multiple-delayed-trains" and index % 3 == 0
        delay_minutes = 5 + (index % 4) * 5 if delayed else 0
        train = Train(
            session=simulation_session,
            identifier=f"RA-{100 + index}",
            priority=((index - 1) % 5) + 1,
            arrival_minute=arrival,
            departure_minute=arrival + dwell + 4,
            minimum_dwell_minutes=dwell,
            length_meters=180 + (index % 5) * 20,
            required_platform_type="passenger",
            service_status=TrainStatus.DELAYED if delayed else TrainStatus.SCHEDULED,
            delay_minutes=delay_minutes,
        )
        compatible = [platform for platform in platforms if platform.length_meters >= train.length_meters]
        train.compatible_platforms = [
            TrainPlatformCompatibility(platform=platform) for platform in compatible
        ]
        trains.append(train)
    return trains


def _add_network(database: Session, simulation_session: SimulationSession) -> None:
    west = TrackNode(
        session=simulation_session,
        code="N-WEST",
        name="West Approach",
        node_type="junction",
    )
    station = TrackNode(
        session=simulation_session,
        code="N-CENTRAL",
        name="Central Station",
        node_type="station",
    )
    database.add(
        TrackEdge(
            session=simulation_session,
            code="T-WEST-01",
            from_node=west,
            to_node=station,
            traversal_minutes=5,
            capacity=1,
            resource_group="west-approach",
        )
    )


def _add_scenario_incidents(
    database: Session,
    simulation_session: SimulationSession,
    scenario_key: str,
) -> None:
    if scenario_key == "platform-closure":
        database.add(
            Incident(
                session=simulation_session,
                title="Platform P3 unavailable",
                description="Platform P3 is closed for a synthetic infrastructure inspection.",
                severity=IncidentSeverity.MEDIUM,
                status=IncidentStatus.OPEN,
                reported_minute=350,
                resource_code="P3",
            )
        )
    elif scenario_key == "track-closure":
        database.add(
            Incident(
                session=simulation_session,
                title="West approach track closure",
                description="Track T-WEST-01 is closed in this synthetic scenario.",
                severity=IncidentSeverity.HIGH,
                status=IncidentStatus.OPEN,
                reported_minute=340,
                resource_code="T-WEST-01",
            )
        )
