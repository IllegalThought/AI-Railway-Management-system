"""Create the initial RailOps AI schema.

Revision ID: 20261020_0001
Revises:
Create Date: 2026-10-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261020_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "simulation_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("session_key", sa.String(length=120), nullable=True, unique=True),
        sa.Column("status", sa.Enum("ACTIVE", "ARCHIVED", name="sessionstatus", native_enum=False, length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
    )
    op.create_table(
        "platforms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("platform_type", sa.String(length=40), nullable=False),
        sa.Column("length_meters", sa.Integer(), nullable=False),
        sa.Column("clearance_minutes", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("length_meters > 0", name="ck_platform_length_positive"),
        sa.CheckConstraint("clearance_minutes >= 0", name="ck_platform_clearance_nonnegative"),
        sa.UniqueConstraint("session_id", "code", name="uq_platform_session_code"),
    )
    op.create_index("ix_platforms_session_id", "platforms", ["session_id"])
    op.create_table(
        "trains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("arrival_minute", sa.Integer(), nullable=False),
        sa.Column("departure_minute", sa.Integer(), nullable=False),
        sa.Column("minimum_dwell_minutes", sa.Integer(), nullable=False),
        sa.Column("length_meters", sa.Integer(), nullable=False),
        sa.Column("required_platform_type", sa.String(length=40), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("priority BETWEEN 1 AND 5", name="ck_train_priority"),
        sa.CheckConstraint("arrival_minute >= 0", name="ck_train_arrival_nonnegative"),
        sa.CheckConstraint("departure_minute > arrival_minute", name="ck_train_departure_after_arrival"),
        sa.CheckConstraint("minimum_dwell_minutes > 0", name="ck_train_dwell_positive"),
        sa.CheckConstraint("departure_minute - arrival_minute >= minimum_dwell_minutes", name="ck_train_dwell_fits"),
        sa.CheckConstraint("length_meters > 0", name="ck_train_length_positive"),
        sa.UniqueConstraint("session_id", "identifier", name="uq_train_session_identifier"),
    )
    op.create_index("ix_trains_session_id", "trains", ["session_id"])
    op.create_table(
        "track_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("node_type", sa.String(length=40), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint("session_id", "code", name="uq_track_node_session_code"),
    )
    op.create_index("ix_track_nodes_session_id", "track_nodes", ["session_id"])
    op.create_table(
        "scheduling_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "READY", "ARCHIVED", name="planstatus", native_enum=False, length=20), nullable=False),
        sa.Column("horizon_start_minute", sa.Integer(), nullable=False),
        sa.Column("horizon_end_minute", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("horizon_start_minute >= 0", name="ck_plan_start_nonnegative"),
        sa.CheckConstraint("horizon_end_minute > horizon_start_minute", name="ck_plan_half_open_horizon"),
        sa.UniqueConstraint("session_id", "name", name="uq_plan_session_name"),
    )
    op.create_index("ix_scheduling_plans_session_id", "scheduling_plans", ["session_id"])
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="incidentseverity", native_enum=False, length=20), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "MONITORING", "RESOLVED", name="incidentstatus", native_enum=False, length=20), nullable=False),
        sa.Column("reported_minute", sa.Integer(), nullable=False),
        sa.Column("resource_code", sa.String(length=80), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("reported_minute >= 0", name="ck_incident_minute_nonnegative"),
    )
    op.create_index("ix_incidents_session_id", "incidents", ["session_id"])
    op.create_table(
        "operational_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.Enum("SESSION_CREATED", "TRAIN_REGISTERED", "PLAN_CREATED", "ASSIGNMENT_CREATED", "INCIDENT_REPORTED", name="eventtype", native_enum=False, length=40), nullable=False),
        sa.Column("event_minute", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=300), nullable=False),
        sa.Column("resource_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("event_minute >= 0", name="ck_event_minute_nonnegative"),
    )
    op.create_index("ix_operational_events_session_id", "operational_events", ["session_id"])
    op.create_table(
        "track_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("from_node_id", sa.Integer(), sa.ForeignKey("track_nodes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("to_node_id", sa.Integer(), sa.ForeignKey("track_nodes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("traversal_minutes", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("resource_group", sa.String(length=80), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("from_node_id <> to_node_id", name="ck_track_edge_distinct_nodes"),
        sa.CheckConstraint("traversal_minutes > 0", name="ck_track_edge_traversal_positive"),
        sa.CheckConstraint("capacity > 0", name="ck_track_edge_capacity_positive"),
        sa.UniqueConstraint("session_id", "code", name="uq_track_edge_session_code"),
    )
    op.create_index("ix_track_edges_session_id", "track_edges", ["session_id"])
    op.create_table(
        "train_platform_compatibility",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("train_id", sa.Integer(), sa.ForeignKey("trains.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_id", sa.Integer(), sa.ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("train_id", "platform_id", name="uq_train_platform_compatibility"),
    )
    op.create_table(
        "train_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("scheduling_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("train_id", sa.Integer(), sa.ForeignKey("trains.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("platform_id", sa.Integer(), sa.ForeignKey("platforms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("occupancy_start_minute", sa.Integer(), nullable=False),
        sa.Column("occupancy_end_minute", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("occupancy_start_minute >= 0", name="ck_assignment_start_nonnegative"),
        sa.CheckConstraint("occupancy_end_minute > occupancy_start_minute", name="ck_assignment_half_open_interval"),
        sa.UniqueConstraint("plan_id", "train_id", name="uq_assignment_plan_train"),
    )
    op.create_index("ix_train_assignments_plan_id", "train_assignments", ["plan_id"])
    op.create_index("ix_train_assignments_train_id", "train_assignments", ["train_id"])
    op.create_index("ix_train_assignments_platform_id", "train_assignments", ["platform_id"])
    op.create_index("ix_assignment_platform_interval", "train_assignments", ["platform_id", "occupancy_start_minute", "occupancy_end_minute"])


def downgrade() -> None:
    op.drop_table("train_assignments")
    op.drop_table("train_platform_compatibility")
    op.drop_table("track_edges")
    op.drop_table("operational_events")
    op.drop_table("incidents")
    op.drop_table("scheduling_plans")
    op.drop_table("track_nodes")
    op.drop_table("trains")
    op.drop_table("platforms")
    op.drop_table("simulation_sessions")

