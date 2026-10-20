"""Add Phase 5 route planning and reservations.

Revision ID: 20261020_0004
Revises: 20261020_0003
Create Date: 2026-10-20
"""

from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "20261020_0004"
down_revision: str | None = "20261020_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("trains", sa.Column("origin_node_code", sa.String(length=40), nullable=True))
    op.add_column("trains", sa.Column("destination_node_code", sa.String(length=40), nullable=True))
    op.add_column("track_nodes", sa.Column("x", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("track_nodes", sa.Column("y", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scheduling_plans", sa.Column("route_validated", sa.Boolean(), nullable=False, server_default=sa.false()))
    _upgrade_existing_synthetic_networks()
    op.create_table(
        "route_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("train_assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("origin_node_code", sa.String(length=40), nullable=True),
        sa.Column("destination_node_code", sa.String(length=40), nullable=True),
        sa.Column("path_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("indicator", sa.String(length=10), nullable=False, server_default="YELLOW"),
        sa.Column("decision", sa.String(length=40), nullable=False, server_default="MovementBlocked"),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        *timestamp_columns(),
        sa.UniqueConstraint("assignment_id", name="uq_route_movement_assignment"),
    )
    op.create_index("ix_route_movements_assignment_id", "route_movements", ["assignment_id"])
    op.create_table(
        "route_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("movement_id", sa.Integer(), sa.ForeignKey("route_movements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_code", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("edge_code", sa.String(length=40), nullable=True),
        sa.Column("start_minute", sa.Integer(), nullable=False),
        sa.Column("end_minute", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("end_minute > start_minute", name="ck_route_reservation_interval"),
    )
    op.create_index("ix_route_reservations_movement_id", "route_reservations", ["movement_id"])
    op.create_index("ix_route_resource_interval", "route_reservations", ["resource_code", "start_minute", "end_minute"])


def _upgrade_existing_synthetic_networks() -> None:
    bind = op.get_bind()
    sessions = sa.table("simulation_sessions", sa.column("id", sa.Integer()))
    trains = sa.table("trains", sa.column("origin_node_code", sa.String()), sa.column("destination_node_code", sa.String()))
    nodes = sa.table(
        "track_nodes",
        sa.column("id", sa.Integer()), sa.column("session_id", sa.Integer()), sa.column("code", sa.String()), sa.column("name", sa.String()),
        sa.column("node_type", sa.String()), sa.column("x", sa.Integer()), sa.column("y", sa.Integer()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    edges = sa.table(
        "track_edges",
        sa.column("session_id", sa.Integer()), sa.column("code", sa.String()), sa.column("from_node_id", sa.Integer()), sa.column("to_node_id", sa.Integer()),
        sa.column("traversal_minutes", sa.Integer()), sa.column("capacity", sa.Integer()), sa.column("resource_group", sa.String()), sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    bind.execute(trains.update().values(origin_node_code="ENTRY-W", destination_node_code="EXIT-E"))
    bind.execute(edges.delete())
    bind.execute(nodes.delete())
    definitions = (
        ("ENTRY-W", "West Entry", "entry", 40, 210), ("J-W", "West Junction", "junction", 180, 210), ("SW-W", "West Switch", "switch", 300, 210),
        ("P1", "Platform 1", "platform", 470, 70), ("P2", "Platform 2", "platform", 470, 140), ("P3", "Platform 3", "platform", 470, 210),
        ("P4", "Platform 4", "platform", 470, 280), ("P5", "Platform 5", "platform", 470, 350), ("SW-E", "East Switch", "switch", 650, 210),
        ("J-E", "East Junction", "junction", 770, 210), ("EXIT-E", "East Exit", "exit", 910, 210), ("ENTRY-E", "East Entry", "entry", 910, 300),
        ("EXIT-W", "West Exit", "exit", 40, 300), ("BYPASS-N", "North Bypass", "junction", 470, 15),
    )
    base_edges = [
        ("T-WEST-01", "ENTRY-W", "J-W", 2, "WEST-THROAT"), ("T-WEST-02", "J-W", "SW-W", 2, "WEST-THROAT"),
        ("T-EAST-IN-01", "ENTRY-E", "J-E", 2, "EAST-THROAT"), ("T-EAST-IN-02", "J-E", "SW-E", 2, "EAST-THROAT"),
        ("T-EAST-OUT-01", "SW-E", "J-E", 2, "EAST-THROAT"), ("T-EAST-OUT-02", "J-E", "EXIT-E", 2, "EAST-THROAT"),
        ("T-WEST-OUT-01", "SW-W", "J-W", 2, "WEST-THROAT"), ("T-WEST-OUT-02", "J-W", "EXIT-W", 2, "WEST-THROAT"),
        ("T-W-BYPASS", "J-W", "BYPASS-N", 4, "NORTH-BYPASS"), ("T-BYPASS-E", "BYPASS-N", "SW-E", 4, "NORTH-BYPASS"),
        ("T-E-BYPASS", "J-E", "BYPASS-N", 4, "NORTH-BYPASS"), ("T-BYPASS-W", "BYPASS-N", "SW-W", 4, "NORTH-BYPASS"),
    ]
    for platform_number in range(1, 6):
        platform = f"P{platform_number}"
        base_edges.extend([(f"T-W-{platform}", "SW-W", platform, 2, f"BERTH-{platform}"), (f"T-{platform}-E", platform, "SW-E", 2, f"BERTH-{platform}"), (f"T-E-{platform}", "SW-E", platform, 2, f"BERTH-{platform}"), (f"T-{platform}-W", platform, "SW-W", 2, f"BERTH-{platform}")])
    now = datetime.now(timezone.utc)
    for session_id in bind.execute(sa.select(sessions.c.id)).scalars():
        bind.execute(nodes.insert(), [{"session_id": session_id, "code": code, "name": name, "node_type": node_type, "x": x, "y": y, "created_at": now, "updated_at": now} for code, name, node_type, x, y in definitions])
        node_ids = dict(bind.execute(sa.select(nodes.c.code, nodes.c.id).where(nodes.c.session_id == session_id)).all())
        bind.execute(edges.insert(), [{"session_id": session_id, "code": code, "from_node_id": node_ids[start], "to_node_id": node_ids[end], "traversal_minutes": minutes, "capacity": 1, "resource_group": group, "created_at": now, "updated_at": now} for code, start, end, minutes, group in base_edges])


def downgrade() -> None:
    op.drop_table("route_reservations")
    op.drop_table("route_movements")
    op.drop_column("scheduling_plans", "route_validated")
    op.drop_column("track_nodes", "y")
    op.drop_column("track_nodes", "x")
    op.drop_column("trains", "destination_node_code")
    op.drop_column("trains", "origin_node_code")
