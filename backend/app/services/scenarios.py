from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import (
    Incident,
    OperationalEvent,
    Platform,
    RouteMovement,
    RouteReservation,
    SchedulingPlan,
    SimulationSession,
    SimulationState,
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
    IncidentType,
    SimulationRunStatus,
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
        delete(RouteReservation).where(
            RouteReservation.movement_id.in_(
                database.query(RouteMovement.id)
                .join(TrainAssignment)
                .join(SchedulingPlan)
                .filter(SchedulingPlan.session_id == session_id)
            )
        )
    )
    database.execute(
        delete(RouteMovement).where(
            RouteMovement.assignment_id.in_(
                database.query(TrainAssignment.id)
                .join(SchedulingPlan)
                .filter(SchedulingPlan.session_id == session_id)
            )
        )
    )
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
    state = database.query(SimulationState).filter(SimulationState.session_id == session_id).one_or_none()
    if state is None:
        state = SimulationState(session_id=session_id)
        database.add(state)
    else:
        state.current_minute = 0
        state.run_status = SimulationRunStatus.PAUSED
        state.speed = 1
        state.active_plan_id = None
        state.last_tick_at = None
        state.revision += 1
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
            origin_node_code="ENTRY-W",
            destination_node_code="EXIT-E",
        )
        compatible = [platform for platform in platforms if platform.length_meters >= train.length_meters]
        train.compatible_platforms = [
            TrainPlatformCompatibility(platform=platform) for platform in compatible
        ]
        trains.append(train)
    return trains


def _add_network(database: Session, simulation_session: SimulationSession) -> None:
    definitions = (
        ("ENTRY-W", "West Entry", "entry", 40, 210),
        ("J-W", "West Junction", "junction", 180, 210),
        ("SW-W", "West Switch", "switch", 300, 210),
        ("P1", "Platform 1", "platform", 470, 70),
        ("P2", "Platform 2", "platform", 470, 140),
        ("P3", "Platform 3", "platform", 470, 210),
        ("P4", "Platform 4", "platform", 470, 280),
        ("P5", "Platform 5", "platform", 470, 350),
        ("SW-E", "East Switch", "switch", 650, 210),
        ("J-E", "East Junction", "junction", 770, 210),
        ("EXIT-E", "East Exit", "exit", 910, 210),
        ("ENTRY-E", "East Entry", "entry", 910, 300),
        ("EXIT-W", "West Exit", "exit", 40, 300),
        ("BYPASS-N", "North Bypass", "junction", 470, 15),
    )
    nodes = {
        code: TrackNode(session=simulation_session, code=code, name=name, node_type=node_type, x=x, y=y)
        for code, name, node_type, x, y in definitions
    }
    database.add_all(nodes.values())
    edges: list[tuple[str, str, str, int, str]] = [
        ("T-WEST-01", "ENTRY-W", "J-W", 2, "WEST-THROAT"),
        ("T-WEST-02", "J-W", "SW-W", 2, "WEST-THROAT"),
        ("T-EAST-IN-01", "ENTRY-E", "J-E", 2, "EAST-THROAT"),
        ("T-EAST-IN-02", "J-E", "SW-E", 2, "EAST-THROAT"),
        ("T-EAST-OUT-01", "SW-E", "J-E", 2, "EAST-THROAT"),
        ("T-EAST-OUT-02", "J-E", "EXIT-E", 2, "EAST-THROAT"),
        ("T-WEST-OUT-01", "SW-W", "J-W", 2, "WEST-THROAT"),
        ("T-WEST-OUT-02", "J-W", "EXIT-W", 2, "WEST-THROAT"),
        ("T-W-BYPASS", "J-W", "BYPASS-N", 4, "NORTH-BYPASS"),
        ("T-BYPASS-E", "BYPASS-N", "SW-E", 4, "NORTH-BYPASS"),
        ("T-E-BYPASS", "J-E", "BYPASS-N", 4, "NORTH-BYPASS"),
        ("T-BYPASS-W", "BYPASS-N", "SW-W", 4, "NORTH-BYPASS"),
    ]
    for platform_number in range(1, 6):
        platform_code = f"P{platform_number}"
        minutes = 2
        edges.extend(
            [
                (f"T-W-{platform_code}", "SW-W", platform_code, minutes, f"BERTH-{platform_code}"),
                (f"T-{platform_code}-E", platform_code, "SW-E", minutes, f"BERTH-{platform_code}"),
                (f"T-E-{platform_code}", "SW-E", platform_code, minutes, f"BERTH-{platform_code}"),
                (f"T-{platform_code}-W", platform_code, "SW-W", minutes, f"BERTH-{platform_code}"),
            ]
        )
    database.add_all(
        [
            TrackEdge(session=simulation_session, code=code, from_node=nodes[start], to_node=nodes[end], traversal_minutes=minutes, capacity=1, resource_group=group)
            for code, start, end, minutes, group in edges
        ]
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
                incident_type=IncidentType.PLATFORM_CLOSURE,
                start_minute=350,
                duration_minutes=120,
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
                incident_type=IncidentType.TRACK_BLOCKAGE,
                start_minute=340,
                duration_minutes=120,
            )
        )
