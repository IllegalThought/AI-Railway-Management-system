"""Add Phase 6 persisted simulation and incident fields.

Revision ID: 20261020_0005
Revises: 20261020_0004
Create Date: 2026-10-20
"""

from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "20261020_0005"
down_revision: str | None = "20261020_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("incident_type", sa.String(length=40), nullable=False, server_default="TRACK_BLOCKAGE"))
    op.add_column("incidents", sa.Column("start_minute", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("incidents", sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"))
    incidents = sa.table("incidents", sa.column("reported_minute", sa.Integer()), sa.column("start_minute", sa.Integer()))
    op.get_bind().execute(incidents.update().values(start_minute=incidents.c.reported_minute))
    op.create_table(
        "simulation_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("current_minute", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_status", sa.String(length=20), nullable=False, server_default="PAUSED"),
        sa.Column("speed", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_plan_id", sa.Integer(), sa.ForeignKey("scheduling_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_tick_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", name="uq_simulation_state_session"),
        sa.CheckConstraint("current_minute >= 0", name="ck_simulation_current_nonnegative"),
        sa.CheckConstraint("speed IN (1, 2, 5)", name="ck_simulation_speed"),
        sa.CheckConstraint("revision >= 0", name="ck_simulation_revision_nonnegative"),
    )
    op.create_index("ix_simulation_states_session_id", "simulation_states", ["session_id"])
    now = datetime.now(timezone.utc)
    sessions = sa.table("simulation_sessions", sa.column("id", sa.Integer()))
    states = sa.table(
        "simulation_states",
        sa.column("session_id", sa.Integer()), sa.column("current_minute", sa.Integer()),
        sa.column("run_status", sa.String()), sa.column("speed", sa.Integer()), sa.column("revision", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    for session_id in op.get_bind().execute(sa.select(sessions.c.id)).scalars():
        op.get_bind().execute(states.insert().values(session_id=session_id, current_minute=0, run_status="PAUSED", speed=1, revision=0, created_at=now, updated_at=now))


def downgrade() -> None:
    op.drop_table("simulation_states")
    op.drop_column("incidents", "duration_minutes")
    op.drop_column("incidents", "start_minute")
    op.drop_column("incidents", "incident_type")
