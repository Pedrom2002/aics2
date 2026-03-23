import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.match import Match


class DetectedError(UUIDMixin, TimestampMixin, Base):
    """An error detected by the ML pipeline for a specific player in a round."""

    __tablename__ = "detected_errors"

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
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Error classification
    error_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # positioning, utility, timing
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical, minor, info
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Context
    tick: Mapped[int | None] = mapped_column(Integer)
    position_x: Mapped[float | None] = mapped_column(Float)
    position_y: Mapped[float | None] = mapped_column(Float)
    position_z: Mapped[float | None] = mapped_column(Float)

    # Human-readable description
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Model info
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    match: Mapped["Match"] = relationship()
    explanation: Mapped["ErrorExplanation | None"] = relationship(
        back_populates="error", uselist=False, cascade="all, delete-orphan"
    )
    recommendation: Mapped["ErrorRecommendation | None"] = relationship(
        back_populates="error", uselist=False, cascade="all, delete-orphan"
    )


class ErrorExplanation(UUIDMixin, Base):
    """SHAP/IG explanation for a detected error."""

    __tablename__ = "error_explanations"

    error_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("detected_errors.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Top contributing features (JSON-like, stored as text for simplicity)
    feature_importances: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON: [{"feature": "angles_exposed", "value": 3, "impact": 0.45}, ...]

    method: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # integrated_gradients, tree_shap

    # Natural language explanation
    explanation_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    error: Mapped["DetectedError"] = relationship(back_populates="explanation")


class ErrorRecommendation(UUIDMixin, Base):
    """Actionable recommendation for a detected error."""

    __tablename__ = "error_recommendations"

    error_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("detected_errors.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Recommendation content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )  # 1=high, 2=medium, 3=low

    # Template info
    template_id: Mapped[str | None] = mapped_column(String(50))

    # Pro reference
    pro_reference: Mapped[str | None] = mapped_column(
        Text
    )  # JSON: {"player": "device", "situation": "...", "outcome": "..."}

    # Expected improvement
    expected_impact: Mapped[str | None] = mapped_column(String(200))

    # Relationships
    error: Mapped["DetectedError"] = relationship(back_populates="recommendation")


class MatchStrategy(UUIDMixin, Base):
    """Strategy classification per round per team."""

    __tablename__ = "match_strategies"

    match_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    team_side: Mapped[str] = mapped_column(String(5), nullable=False)  # T or CT

    # Strategy classification
    strategy_label: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Top 3 predictions
    top_predictions: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON: [{"label": "a_execute", "prob": 0.45}, ...]

    model_version: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    match: Mapped["Match"] = relationship()
