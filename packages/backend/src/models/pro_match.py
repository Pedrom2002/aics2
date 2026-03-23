"""Pro match metadata — tracks demos from HLTV, FACEIT, and other pro sources."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.demo import Demo


class ProMatch(UUIDMixin, TimestampMixin, Base):
    """Metadata for professional CS2 match demos."""

    __tablename__ = "pro_matches"

    source: Mapped[str] = mapped_column(String(20), nullable=False)  # hltv, faceit, valve
    source_match_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Match info
    team1_name: Mapped[str] = mapped_column(String(255), nullable=False)
    team2_name: Mapped[str] = mapped_column(String(255), nullable=False)
    team1_score: Mapped[int | None] = mapped_column(Integer)
    team2_score: Mapped[int | None] = mapped_column(Integer)
    map: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_name: Mapped[str | None] = mapped_column(String(255), index=True)
    event_tier: Mapped[str | None] = mapped_column(String(10))  # tier1, tier2, tier3, regional
    match_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Demo info
    demo_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("demos.id", ondelete="SET NULL"),
    )
    demo_url: Mapped[str | None] = mapped_column(String(500))
    demo_file_hash: Mapped[str | None] = mapped_column(String(64))  # SHA256 dedup

    # Processing status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending", index=True
    )  # pending, downloading, parsing, analyzing, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text)

    # ML analysis status
    ml_analyzed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    ml_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    demo: Mapped["Demo | None"] = relationship()

    __table_args__ = (
        UniqueConstraint("source", "source_match_id", name="uq_pro_match_source"),
        CheckConstraint(
            "source IN ('hltv', 'faceit', 'valve')",
            name="ck_pro_match_source",
        ),
        CheckConstraint(
            "status IN ('pending', 'downloading', 'parsing', 'analyzing', 'completed', 'failed')",
            name="ck_pro_match_status",
        ),
    )
