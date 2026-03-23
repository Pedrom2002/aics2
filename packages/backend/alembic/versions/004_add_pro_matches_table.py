"""Add pro_matches table for professional demo tracking.

Revision ID: 004
Revises: 003
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pro_matches",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("source_match_id", sa.String(100), nullable=False),
        sa.Column("team1_name", sa.String(255), nullable=False),
        sa.Column("team2_name", sa.String(255), nullable=False),
        sa.Column("team1_score", sa.Integer, nullable=True),
        sa.Column("team2_score", sa.Integer, nullable=True),
        sa.Column("map", sa.String(50), nullable=False, index=True),
        sa.Column("event_name", sa.String(255), nullable=True, index=True),
        sa.Column("event_tier", sa.String(10), nullable=True),
        sa.Column("match_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("demo_id", sa.Uuid(as_uuid=True), sa.ForeignKey("demos.id", ondelete="SET NULL")),
        sa.Column("demo_url", sa.String(500), nullable=True),
        sa.Column("demo_file_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("ml_analyzed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("ml_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source", "source_match_id", name="uq_pro_match_source"),
        sa.CheckConstraint("source IN ('hltv', 'faceit', 'valve')", name="ck_pro_match_source"),
        sa.CheckConstraint(
            "status IN ('pending', 'downloading', 'parsing', 'analyzing', 'completed', 'failed')",
            name="ck_pro_match_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("pro_matches")
