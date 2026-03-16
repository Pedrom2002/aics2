import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.team import Team


class TeamPlayer(UUIDMixin, Base):
    __tablename__ = "team_players"

    team_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    steam_id: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="rifler")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="players")

    __table_args__ = (
        UniqueConstraint("team_id", "steam_id", name="uq_team_player_steam"),
        CheckConstraint(
            "role IN ('entry', 'awp', 'support', 'lurk', 'igl', 'rifler')",
            name="ck_team_players_role",
        ),
    )
