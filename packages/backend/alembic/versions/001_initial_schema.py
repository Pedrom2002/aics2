"""Initial schema — all tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # === Organizations ===
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("max_demos_per_month", sa.Integer, nullable=False, server_default="10"),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "tier IN ('free', 'solo', 'team', 'pro', 'enterprise')",
            name="ck_organizations_tier",
        ),
    )

    # === Users ===
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("steam_id", sa.String(50), index=True),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "role IN ('admin', 'coach', 'analyst', 'player', 'viewer')",
            name="ck_users_role",
        ),
    )

    # === Refresh Tokens ===
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Invitations ===
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("invited_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(255), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Teams ===
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tag", sa.String(10)),
        sa.Column("game_team_name", sa.String(255)),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Team Players ===
    op.create_table(
        "team_players",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("team_id", sa.Uuid(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("steam_id", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="rifler"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("team_id", "steam_id", name="uq_team_player_steam"),
        sa.CheckConstraint(
            "role IN ('entry', 'awp', 'support', 'lurk', 'igl', 'rifler')",
            name="ck_team_players_role",
        ),
    )

    # === Beta Signups ===
    op.create_table(
        "beta_signups",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("source", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Demos ===
    demo_status_enum = sa.Enum(
        "uploaded", "queued", "downloading", "parsing",
        "extracting_features", "running_models",
        "completed", "failed", "error",
        name="demo_status",
    )
    op.create_table(
        "demos",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("uploaded_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("status", demo_status_enum, nullable=False, server_default="uploaded", index=True),
        sa.Column("error_message", sa.Text),
        sa.Column("parsing_started_at", sa.DateTime(timezone=True)),
        sa.Column("parsing_completed_at", sa.DateTime(timezone=True)),
        sa.Column("processing_started_at", sa.DateTime(timezone=True)),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # === Matches ===
    op.create_table(
        "matches",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("demo_id", sa.Uuid(as_uuid=True), sa.ForeignKey("demos.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("map", sa.String(50), nullable=False, index=True),
        sa.Column("match_date", sa.DateTime(timezone=True)),
        sa.Column("tickrate", sa.Integer, nullable=False, server_default="64"),
        sa.Column("team1_name", sa.String(100)),
        sa.Column("team2_name", sa.String(100)),
        sa.Column("team1_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("team2_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("our_team_id", sa.Uuid(as_uuid=True), sa.ForeignKey("teams.id", ondelete="SET NULL")),
        sa.Column("match_type", sa.String(30)),
        sa.Column("total_rounds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("overtime_rounds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("team1_score >= 0", name="ck_match_team1_score_positive"),
        sa.CheckConstraint("team2_score >= 0", name="ck_match_team2_score_positive"),
        sa.CheckConstraint("total_rounds >= 0", name="ck_match_total_rounds_positive"),
        sa.CheckConstraint("overtime_rounds >= 0", name="ck_match_overtime_rounds_positive"),
    )

    # === Rounds ===
    op.create_table(
        "rounds",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("match_id", sa.Uuid(as_uuid=True), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("winner_side", sa.String(5)),
        sa.Column("win_reason", sa.String(30)),
        sa.Column("team1_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("team2_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("t_economy", sa.Integer),
        sa.Column("ct_economy", sa.Integer),
        sa.Column("t_equipment_value", sa.Integer),
        sa.Column("ct_equipment_value", sa.Integer),
        sa.Column("t_buy_type", sa.String(20)),
        sa.Column("ct_buy_type", sa.String(20)),
        sa.Column("bomb_planted", sa.Boolean),
        sa.Column("bomb_defused", sa.Boolean),
        sa.Column("plant_site", sa.String(5)),
        sa.Column("start_tick", sa.BigInteger),
        sa.Column("end_tick", sa.BigInteger),
        sa.Column("duration_seconds", sa.Float),
        sa.UniqueConstraint("match_id", "round_number", name="uq_round_match_number"),
        sa.CheckConstraint("round_number > 0", name="ck_round_number_positive"),
        sa.CheckConstraint("team1_score >= 0", name="ck_round_team1_score_positive"),
        sa.CheckConstraint("team2_score >= 0", name="ck_round_team2_score_positive"),
    )

    # === Player Match Stats ===
    op.create_table(
        "player_match_stats",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("match_id", sa.Uuid(as_uuid=True), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("org_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("player_steam_id", sa.String(20), nullable=False, index=True),
        sa.Column("player_name", sa.String(100), nullable=False),
        sa.Column("team_side", sa.String(5)),
        # Core stats
        sa.Column("kills", sa.Integer, nullable=False, server_default="0"),
        sa.Column("deaths", sa.Integer, nullable=False, server_default="0"),
        sa.Column("assists", sa.Integer, nullable=False, server_default="0"),
        sa.Column("headshot_kills", sa.Integer, nullable=False, server_default="0"),
        sa.Column("damage", sa.Integer, nullable=False, server_default="0"),
        sa.Column("adr", sa.Float),
        # Utility
        sa.Column("flash_assists", sa.Integer, nullable=False, server_default="0"),
        sa.Column("enemies_flashed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("utility_damage", sa.Integer, nullable=False, server_default="0"),
        # Economy
        sa.Column("money_spent", sa.Integer, nullable=False, server_default="0"),
        # Clutch / multi-kills
        sa.Column("clutch_wins", sa.Integer, nullable=False, server_default="0"),
        sa.Column("multi_kills_3k", sa.Integer, nullable=False, server_default="0"),
        sa.Column("multi_kills_4k", sa.Integer, nullable=False, server_default="0"),
        sa.Column("multi_kills_5k", sa.Integer, nullable=False, server_default="0"),
        # First engagements
        sa.Column("first_kills", sa.Integer, nullable=False, server_default="0"),
        sa.Column("first_deaths", sa.Integer, nullable=False, server_default="0"),
        # AI ratings
        sa.Column("overall_rating", sa.Float),
        sa.Column("aim_rating", sa.Float),
        sa.Column("positioning_rating", sa.Float),
        sa.Column("utility_rating", sa.Float),
        sa.Column("game_sense_rating", sa.Float),
        sa.Column("clutch_rating", sa.Float),
        sa.UniqueConstraint("match_id", "player_steam_id", name="uq_player_match_stats"),
    )


def downgrade() -> None:
    op.drop_table("player_match_stats")
    op.drop_table("rounds")
    op.drop_table("matches")
    op.drop_table("demos")
    sa.Enum(name="demo_status").drop(op.get_bind(), checkfirst=True)
    op.drop_table("beta_signups")
    op.drop_table("team_players")
    op.drop_table("teams")
    op.drop_table("invitations")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("organizations")
