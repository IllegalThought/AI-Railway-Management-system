"""Add Phase 7 analytics and benchmark persistence.

Revision ID: 20261020_0006
Revises: 20261020_0005
Create Date: 2026-10-20
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261020_0006"
down_revision: str | None = "20261020_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scheduling_plans", sa.Column("execution_time_ms", sa.Float(), nullable=True))
    op.create_table(
        "solver_benchmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("benchmark_id", sa.String(length=36), nullable=False),
        sa.Column("scenario_identifier", sa.String(length=120), nullable=False),
        sa.Column("engine", sa.String(length=20), nullable=False),
        sa.Column("solver_status", sa.String(length=20), nullable=False),
        sa.Column("execution_time_ms", sa.Float(), nullable=False),
        sa.Column("total_delay_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("maximum_delay_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_train_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("objective_value", sa.Integer(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("benchmark_id", "engine", name="uq_benchmark_engine"),
        sa.CheckConstraint("execution_time_ms >= 0", name="ck_benchmark_execution_nonnegative"),
    )
    op.create_index("ix_solver_benchmarks_session_id", "solver_benchmarks", ["session_id"])
    op.create_index("ix_solver_benchmarks_benchmark_id", "solver_benchmarks", ["benchmark_id"])
    op.create_index("ix_solver_benchmarks_scenario_identifier", "solver_benchmarks", ["scenario_identifier"])


def downgrade() -> None:
    op.drop_table("solver_benchmarks")
    op.drop_column("scheduling_plans", "execution_time_ms")
