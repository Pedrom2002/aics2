import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.match import Match


class Round(UUIDMixin, Base):
    __tablename__ = "rounds"

    match_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Result
    winner_side: Mapped[str | None] = mapped_column(String(5))  # 'T' or 'CT'
    win_reason: Mapped[str | None] = mapped_column(
        String(30)
    )  # bomb_exploded, defuse, elimination, time

    # Scores at end of round
    team1_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    team2_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Economy
    t_economy: Mapped[int | None] = mapped_column(Integer)
    ct_economy: Mapped[int | None] = mapped_column(Integer)
    t_equipment_value: Mapped[int | None] = mapped_column(Integer)
    ct_equipment_value: Mapped[int | None] = mapped_column(Integer)
    t_buy_type: Mapped[str | None] = mapped_column(String(20))  # full, force, eco, pistol
    ct_buy_type: Mapped[str | None] = mapped_column(String(20))

    # Bomb
    bomb_planted: Mapped[bool | None] = mapped_column()
    bomb_defused: Mapped[bool | None] = mapped_column()
    plant_site: Mapped[str | None] = mapped_column(String(5))  # A, B

    # Tick range
    start_tick: Mapped[int | None] = mapped_column(BigInteger)
    end_tick: Mapped[int | None] = mapped_column(BigInteger)
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Relationships
    match: Mapped["Match"] = relationship(back_populates="rounds")

    __table_args__ = (
        UniqueConstraint("match_id", "round_number", name="uq_round_match_number"),
        CheckConstraint("round_number > 0", name="ck_round_number_positive"),
        CheckConstraint("team1_score >= 0", name="ck_round_team1_score_positive"),
        CheckConstraint("team2_score >= 0", name="ck_round_team2_score_positive"),
    )
