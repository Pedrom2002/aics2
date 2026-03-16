import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.match import Match


class PlayerMatchStats(UUIDMixin, Base):
    __tablename__ = "player_match_stats"

    match_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_steam_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    player_name: Mapped[str] = mapped_column(String(100), nullable=False)
    team_side: Mapped[str | None] = mapped_column(String(5))  # starting side: T or CT

    # Core stats
    kills: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    deaths: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    assists: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    headshot_kills: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    damage: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    adr: Mapped[float | None] = mapped_column(Float)  # average damage per round

    # Utility
    flash_assists: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    enemies_flashed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    utility_damage: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Economy
    money_spent: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Clutch / multi-kills
    clutch_wins: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    multi_kills_3k: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    multi_kills_4k: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    multi_kills_5k: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # First engagements
    first_kills: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    first_deaths: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Trade kills
    trade_kills: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    trade_deaths: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # KAST & survival
    kast_rounds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rounds_survived: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # AI-computed ratings (filled after ML pipeline runs)
    overall_rating: Mapped[float | None] = mapped_column(Float)
    aim_rating: Mapped[float | None] = mapped_column(Float)
    positioning_rating: Mapped[float | None] = mapped_column(Float)
    utility_rating: Mapped[float | None] = mapped_column(Float)
    game_sense_rating: Mapped[float | None] = mapped_column(Float)
    clutch_rating: Mapped[float | None] = mapped_column(Float)

    # Relationships
    match: Mapped["Match"] = relationship(back_populates="player_stats")

    __table_args__ = (
        UniqueConstraint("match_id", "player_steam_id", name="uq_player_match_stats"),
    )
