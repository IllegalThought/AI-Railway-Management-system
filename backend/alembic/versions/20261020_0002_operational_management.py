"""Add Phase 3 operational management fields.

Revision ID: 20261020_0002
Revises: 20261020_0001
Create Date: 2026-10-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261020_0002"
down_revision: str | None = "20261020_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "simulation_sessions",
        sa.Column("scenario_key", sa.String(length=60), nullable=False, server_default="normal-traffic"),
    )
    op.add_column(
        "trains",
        sa.Column(
            "service_status",
            sa.Enum("SCHEDULED", "DELAYED", "CANCELLED", name="trainstatus", native_enum=False, length=20),
            nullable=False,
            server_default="SCHEDULED",
        ),
    )
    op.add_column(
        "trains",
        sa.Column("delay_minutes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "platforms",
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "platforms",
        sa.Column("unavailable_reason", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platforms", "unavailable_reason")
    op.drop_column("platforms", "is_available")
    op.drop_column("trains", "delay_minutes")
    op.drop_column("trains", "service_status")
    op.drop_column("simulation_sessions", "scenario_key")
