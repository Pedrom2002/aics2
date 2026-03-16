"""Add trade kills, KAST, and rounds survived to player_match_stats.

Revision ID: 002
Revises: 001
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "player_match_stats",
        sa.Column("trade_kills", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "player_match_stats",
        sa.Column("trade_deaths", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "player_match_stats",
        sa.Column("kast_rounds", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "player_match_stats",
        sa.Column("rounds_survived", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("player_match_stats", "rounds_survived")
    op.drop_column("player_match_stats", "kast_rounds")
    op.drop_column("player_match_stats", "trade_deaths")
    op.drop_column("player_match_stats", "trade_kills")
