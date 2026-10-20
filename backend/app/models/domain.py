from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, utc_now
from app.models.enums import (
    EventType,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    PlanStatus,
    SessionStatus,
    SimulationRunStatus,
    TrainStatus,
)


def new_public_id() -> str:
    return str(uuid.uuid4())


class SimulationSession(TimestampMixin, Base):
    __tablename__ = "simulation_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, default=new_public_id, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    session_key: Mapped[str | None] = mapped_column(String(120), unique=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, native_enum=False, length=20),
        default=SessionStatus.ACTIVE,
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scenario_key: Mapped[str] = mapped_column(
        String(60), default="normal-traffic", nullable=False
    )

    trains: Mapped[list[Train]] = relationship(back_populates="session", cascade="all, delete-orphan")
    platforms: Mapped[list[Platform]] = relationship(back_populates="session", cascade="all, delete-orphan")
    track_nodes: Mapped[list[TrackNode]] = relationship(back_populates="session", cascade="all, delete-orphan")
    track_edges: Mapped[list[TrackEdge]] = relationship(back_populates="session", cascade="all, delete-orphan")
    plans: Mapped[list[SchedulingPlan]] = relationship(back_populates="session", cascade="all, delete-orphan")
    incidents: Mapped[list[Incident]] = relationship(back_populates="session", cascade="all, delete-orphan")
    events: Mapped[list[OperationalEvent]] = relationship(back_populates="session", cascade="all, delete-orphan")
    simulation_state: Mapped[SimulationState | None] = relationship(back_populates="session", cascade="all, delete-orphan", uselist=False)


class Train(TimestampMixin, Base):
    __tablename__ = "trains"
    __table_args__ = (
        UniqueConstraint("session_id", "identifier", name="uq_train_session_identifier"),
        CheckConstraint("priority BETWEEN 1 AND 5", name="ck_train_priority"),
        CheckConstraint("arrival_minute >= 0", name="ck_train_arrival_nonnegative"),
        CheckConstraint("departure_minute > arrival_minute", name="ck_train_departure_after_arrival"),
        CheckConstraint("minimum_dwell_minutes > 0", name="ck_train_dwell_positive"),
        CheckConstraint("departure_minute - arrival_minute >= minimum_dwell_minutes", name="ck_train_dwell_fits"),
        CheckConstraint("length_meters > 0", name="ck_train_length_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    identifier: Mapped[str] = mapped_column(String(40), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    departure_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_dwell_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    length_meters: Mapped[int] = mapped_column(Integer, nullable=False)
    required_platform_type: Mapped[str | None] = mapped_column(String(40))
    service_status: Mapped[TrainStatus] = mapped_column(
        Enum(TrainStatus, native_enum=False, length=20),
        default=TrainStatus.SCHEDULED,
        nullable=False,
    )
    delay_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    origin_node_code: Mapped[str | None] = mapped_column(String(40))
    destination_node_code: Mapped[str | None] = mapped_column(String(40))

    session: Mapped[SimulationSession] = relationship(back_populates="trains")
    compatible_platforms: Mapped[list[TrainPlatformCompatibility]] = relationship(back_populates="train", cascade="all, delete-orphan")
    assignments: Mapped[list[TrainAssignment]] = relationship(back_populates="train")


class Platform(TimestampMixin, Base):
    __tablename__ = "platforms"
    __table_args__ = (
        UniqueConstraint("session_id", "code", name="uq_platform_session_code"),
        CheckConstraint("length_meters > 0", name="ck_platform_length_positive"),
        CheckConstraint("clearance_minutes >= 0", name="ck_platform_clearance_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    platform_type: Mapped[str] = mapped_column(String(40), nullable=False)
    length_meters: Mapped[int] = mapped_column(Integer, nullable=False)
    clearance_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_available: Mapped[bool] = mapped_column(default=True, nullable=False)
    unavailable_reason: Mapped[str | None] = mapped_column(String(200))

    session: Mapped[SimulationSession] = relationship(back_populates="platforms")
    compatible_trains: Mapped[list[TrainPlatformCompatibility]] = relationship(back_populates="platform", cascade="all, delete-orphan")
    assignments: Mapped[list[TrainAssignment]] = relationship(back_populates="platform")


class TrainPlatformCompatibility(Base):
    __tablename__ = "train_platform_compatibility"
    __table_args__ = (UniqueConstraint("train_id", "platform_id", name="uq_train_platform_compatibility"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.id", ondelete="CASCADE"), nullable=False)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False)

    train: Mapped[Train] = relationship(back_populates="compatible_platforms")
    platform: Mapped[Platform] = relationship(back_populates="compatible_trains")


class TrackNode(TimestampMixin, Base):
    __tablename__ = "track_nodes"
    __table_args__ = (UniqueConstraint("session_id", "code", name="uq_track_node_session_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    node_type: Mapped[str] = mapped_column(String(40), nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    session: Mapped[SimulationSession] = relationship(back_populates="track_nodes")
    outgoing_edges: Mapped[list[TrackEdge]] = relationship(foreign_keys="TrackEdge.from_node_id", back_populates="from_node")
    incoming_edges: Mapped[list[TrackEdge]] = relationship(foreign_keys="TrackEdge.to_node_id", back_populates="to_node")


class TrackEdge(TimestampMixin, Base):
    __tablename__ = "track_edges"
    __table_args__ = (
        UniqueConstraint("session_id", "code", name="uq_track_edge_session_code"),
        CheckConstraint("from_node_id <> to_node_id", name="ck_track_edge_distinct_nodes"),
        CheckConstraint("traversal_minutes > 0", name="ck_track_edge_traversal_positive"),
        CheckConstraint("capacity > 0", name="ck_track_edge_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    from_node_id: Mapped[int] = mapped_column(ForeignKey("track_nodes.id", ondelete="RESTRICT"), nullable=False)
    to_node_id: Mapped[int] = mapped_column(ForeignKey("track_nodes.id", ondelete="RESTRICT"), nullable=False)
    traversal_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    resource_group: Mapped[str | None] = mapped_column(String(80))

    session: Mapped[SimulationSession] = relationship(back_populates="track_edges")
    from_node: Mapped[TrackNode] = relationship(foreign_keys=[from_node_id], back_populates="outgoing_edges")
    to_node: Mapped[TrackNode] = relationship(foreign_keys=[to_node_id], back_populates="incoming_edges")


class SchedulingPlan(TimestampMixin, Base):
    __tablename__ = "scheduling_plans"
    __table_args__ = (
        UniqueConstraint("session_id", "name", name="uq_plan_session_name"),
        CheckConstraint("horizon_start_minute >= 0", name="ck_plan_start_nonnegative"),
        CheckConstraint("horizon_end_minute > horizon_start_minute", name="ck_plan_half_open_horizon"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus, native_enum=False, length=20), default=PlanStatus.DRAFT, nullable=False)
    horizon_start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    engine: Mapped[str] = mapped_column(String(20), nullable=False, default="csp")
    solver_status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNKNOWN")
    objective_value: Mapped[int | None] = mapped_column(Integer)
    maximum_delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    route_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")

    session: Mapped[SimulationSession] = relationship(back_populates="plans")
    assignments: Mapped[list[TrainAssignment]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class TrainAssignment(TimestampMixin, Base):
    __tablename__ = "train_assignments"
    __table_args__ = (
        UniqueConstraint("plan_id", "train_id", name="uq_assignment_plan_train"),
        CheckConstraint("occupancy_start_minute >= 0", name="ck_assignment_start_nonnegative"),
        CheckConstraint("occupancy_end_minute > occupancy_start_minute", name="ck_assignment_half_open_interval"),
        Index("ix_assignment_platform_interval", "platform_id", "occupancy_start_minute", "occupancy_end_minute"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("scheduling_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("trains.id", ondelete="RESTRICT"), nullable=False, index=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id", ondelete="RESTRICT"), nullable=False, index=True)
    occupancy_start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    occupancy_end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reassigned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    plan: Mapped[SchedulingPlan] = relationship(back_populates="assignments")
    train: Mapped[Train] = relationship(back_populates="assignments")
    platform: Mapped[Platform] = relationship(back_populates="assignments")
    route: Mapped[RouteMovement | None] = relationship(back_populates="assignment", cascade="all, delete-orphan", uselist=False)


class RouteMovement(TimestampMixin, Base):
    __tablename__ = "route_movements"
    __table_args__ = (UniqueConstraint("assignment_id", name="uq_route_movement_assignment"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("train_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    origin_node_code: Mapped[str | None] = mapped_column(String(40))
    destination_node_code: Mapped[str | None] = mapped_column(String(40))
    path_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    indicator: Mapped[str] = mapped_column(String(10), nullable=False, default="YELLOW")
    decision: Mapped[str] = mapped_column(String(40), nullable=False, default="MovementBlocked")
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")

    assignment: Mapped[TrainAssignment] = relationship(back_populates="route")
    reservations: Mapped[list[RouteReservation]] = relationship(back_populates="movement", cascade="all, delete-orphan")


class RouteReservation(TimestampMixin, Base):
    __tablename__ = "route_reservations"
    __table_args__ = (
        CheckConstraint("end_minute > start_minute", name="ck_route_reservation_interval"),
        Index("ix_route_resource_interval", "resource_code", "start_minute", "end_minute"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    movement_id: Mapped[int] = mapped_column(ForeignKey("route_movements.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_code: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    edge_code: Mapped[str | None] = mapped_column(String(40))
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    movement: Mapped[RouteMovement] = relationship(back_populates="reservations")


class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (CheckConstraint("reported_minute >= 0", name="ck_incident_minute_nonnegative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(Enum(IncidentSeverity, native_enum=False, length=20), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus, native_enum=False, length=20), default=IncidentStatus.OPEN, nullable=False)
    reported_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_code: Mapped[str | None] = mapped_column(String(80))
    incident_type: Mapped[IncidentType] = mapped_column(Enum(IncidentType, native_enum=False, length=40), nullable=False, default=IncidentType.TRACK_BLOCKAGE)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    session: Mapped[SimulationSession] = relationship(back_populates="incidents")


class SimulationState(TimestampMixin, Base):
    __tablename__ = "simulation_states"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_simulation_state_session"),
        CheckConstraint("current_minute >= 0", name="ck_simulation_current_nonnegative"),
        CheckConstraint("speed IN (1, 2, 5)", name="ck_simulation_speed"),
        CheckConstraint("revision >= 0", name="ck_simulation_revision_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    current_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_status: Mapped[SimulationRunStatus] = mapped_column(Enum(SimulationRunStatus, native_enum=False, length=20), nullable=False, default=SimulationRunStatus.PAUSED)
    speed: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_plan_id: Mapped[int | None] = mapped_column(ForeignKey("scheduling_plans.id", ondelete="SET NULL"))
    last_tick_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[SimulationSession] = relationship(back_populates="simulation_state")
    active_plan: Mapped[SchedulingPlan | None] = relationship(foreign_keys=[active_plan_id])


class OperationalEvent(Base):
    __tablename__ = "operational_events"
    __table_args__ = (CheckConstraint("event_minute >= 0", name="ck_event_minute_nonnegative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType, native_enum=False, length=40), nullable=False)
    event_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(String(300), nullable=False)
    resource_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    session: Mapped[SimulationSession] = relationship(back_populates="events")

