from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.user import User


class Organization(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="free",
    )
    max_demos_per_month: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
    logo_url: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="organization")

    __table_args__ = (
        CheckConstraint(
            "tier IN ('free', 'solo', 'team', 'pro', 'enterprise')",
            name="ck_organizations_tier",
        ),
    )
