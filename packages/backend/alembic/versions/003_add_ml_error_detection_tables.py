"""Add ML error detection tables: detected_errors, error_explanations, error_recommendations, match_strategies.

Revision ID: 003
Revises: 002
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "detected_errors",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "match_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("matches.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "org_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("player_steam_id", sa.String(20), nullable=False, index=True),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("error_type", sa.String(30), nullable=False, index=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("tick", sa.Integer, nullable=True),
        sa.Column("position_x", sa.Float, nullable=True),
        sa.Column("position_y", sa.Float, nullable=True),
        sa.Column("position_z", sa.Float, nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("model_name", sa.String(50), nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "error_explanations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "error_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("detected_errors.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("feature_importances", sa.Text, nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("explanation_text", sa.Text, nullable=False),
    )

    op.create_table(
        "error_recommendations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "error_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("detected_errors.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="1"),
        sa.Column("template_id", sa.String(50), nullable=True),
        sa.Column("pro_reference", sa.Text, nullable=True),
        sa.Column("expected_impact", sa.String(200), nullable=True),
    )

    op.create_table(
        "match_strategies",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "match_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("matches.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("team_side", sa.String(5), nullable=False),
        sa.Column("strategy_label", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("top_predictions", sa.Text, nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("match_strategies")
    op.drop_table("error_recommendations")
    op.drop_table("error_explanations")
    op.drop_table("detected_errors")
