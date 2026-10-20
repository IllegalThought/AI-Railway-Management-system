"""Add Phase 4 scheduling state.

Revision ID: 20261020_0003
Revises: 20261020_0002
Create Date: 2026-10-20
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261020_0003"
down_revision: str | None = "20261020_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scheduling_plans", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("scheduling_plans", sa.Column("engine", sa.String(length=20), nullable=False, server_default="csp"))
    op.add_column("scheduling_plans", sa.Column("solver_status", sa.String(length=20), nullable=False, server_default="UNKNOWN"))
    op.add_column("scheduling_plans", sa.Column("objective_value", sa.Integer(), nullable=True))
    op.add_column("scheduling_plans", sa.Column("maximum_delay_minutes", sa.Integer(), nullable=False, server_default="30"))
    op.add_column("scheduling_plans", sa.Column("is_validated", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("scheduling_plans", sa.Column("explanation", sa.Text(), nullable=False, server_default=""))
    op.add_column("train_assignments", sa.Column("delay_minutes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("train_assignments", sa.Column("reassigned", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("train_assignments", "reassigned")
    op.drop_column("train_assignments", "delay_minutes")
    op.drop_column("scheduling_plans", "explanation")
    op.drop_column("scheduling_plans", "is_validated")
    op.drop_column("scheduling_plans", "maximum_delay_minutes")
    op.drop_column("scheduling_plans", "objective_value")
    op.drop_column("scheduling_plans", "solver_status")
    op.drop_column("scheduling_plans", "engine")
    op.drop_column("scheduling_plans", "version")
