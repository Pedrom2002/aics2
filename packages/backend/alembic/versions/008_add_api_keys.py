"""Add api_keys table for public API access.

Revision ID: 008_add_api_keys
Revises: 007_add_scout_reports
Create Date: 2026-04-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_prefix", sa.String(length=12), nullable=False, index=True),
        sa.Column("key_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("scopes", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_api_keys_active", "api_keys", ["org_id"],
                    postgresql_where=sa.text("revoked_at IS NULL"))


def downgrade() -> None:
    op.drop_index("ix_api_keys_active", table_name="api_keys")
    op.drop_table("api_keys")
