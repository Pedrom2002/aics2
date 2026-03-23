"""Service layer for ML error detection queries."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.detected_error import DetectedError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_match_errors(session: AsyncSession, match_id: str) -> dict:
    """Get all detected errors for a match with explanations and recommendations."""
    from uuid import UUID

    match_uuid = UUID(match_id)

    result = await session.execute(
        select(DetectedError)
        .where(DetectedError.match_id == match_uuid)
        .options(
            selectinload(DetectedError.explanation),
            selectinload(DetectedError.recommendation),
        )
        .order_by(DetectedError.round_number, DetectedError.severity.desc())
    )
    errors = result.scalars().all()

    critical = sum(1 for e in errors if e.severity == "critical")
    minor = sum(1 for e in errors if e.severity == "minor")

    return {
        "match_id": match_id,
        "total_errors": len(errors),
        "critical_count": critical,
        "minor_count": minor,
        "errors": [_format_error(e) for e in errors],
    }


async def get_player_error_summary(session: AsyncSession, steam_id: str) -> dict | None:
    """Get error summary for a player across all matches."""
    result = await session.execute(
        select(DetectedError)
        .where(DetectedError.player_steam_id == steam_id)
        .options(selectinload(DetectedError.recommendation))
        .order_by(DetectedError.created_at.desc())
    )
    errors = result.scalars().all()

    if not errors:
        return None

    positioning = sum(1 for e in errors if e.error_type == "positioning")
    utility = sum(1 for e in errors if e.error_type == "utility")
    timing = sum(1 for e in errors if e.error_type == "timing")
    critical = sum(1 for e in errors if e.severity == "critical")
    minor = sum(1 for e in errors if e.severity == "minor")

    # Collect unique recommendations, prioritized
    seen_templates: set[str] = set()
    top_recs: list[dict] = []
    for e in sorted(errors, key=lambda x: x.recommendation.priority if x.recommendation else 99):
        if e.recommendation and e.recommendation.template_id not in seen_templates:
            seen_templates.add(e.recommendation.template_id or "")
            top_recs.append(
                {
                    "title": e.recommendation.title,
                    "description": e.recommendation.description,
                    "priority": e.recommendation.priority,
                    "template_id": e.recommendation.template_id,
                    "expected_impact": e.recommendation.expected_impact,
                    "pro_reference": e.recommendation.pro_reference,
                }
            )
            if len(top_recs) >= 5:
                break

    return {
        "player_steam_id": steam_id,
        "total_errors": len(errors),
        "positioning_errors": positioning,
        "utility_errors": utility,
        "timing_errors": timing,
        "critical_count": critical,
        "minor_count": minor,
        "top_recommendations": top_recs,
    }


def _format_error(error: DetectedError) -> dict:
    """Format a DetectedError with its relationships for API response."""
    result: dict = {
        "id": str(error.id),
        "player_steam_id": error.player_steam_id,
        "round_number": error.round_number,
        "error_type": error.error_type,
        "severity": error.severity,
        "confidence": error.confidence,
        "tick": error.tick,
        "position_x": error.position_x,
        "position_y": error.position_y,
        "position_z": error.position_z,
        "description": error.description,
        "model_name": error.model_name,
        "model_version": error.model_version,
        "explanation": None,
        "recommendation": None,
    }

    if error.explanation:
        try:
            importances = json.loads(error.explanation.feature_importances)
        except (json.JSONDecodeError, TypeError):
            importances = []

        result["explanation"] = {
            "method": error.explanation.method,
            "explanation_text": error.explanation.explanation_text,
            "feature_importances": importances,
        }

    if error.recommendation:
        result["recommendation"] = {
            "title": error.recommendation.title,
            "description": error.recommendation.description,
            "priority": error.recommendation.priority,
            "template_id": error.recommendation.template_id,
            "expected_impact": error.recommendation.expected_impact,
            "pro_reference": error.recommendation.pro_reference,
        }

    return result
