"""API endpoints for ML error detection results."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.ml import (
    MatchErrorsResponse,
    PlayerErrorSummaryResponse,
)
from src.services.ml_service import get_match_errors, get_player_error_summary

router = APIRouter(tags=["ml"])


@router.get("/matches/{match_id}/errors", response_model=MatchErrorsResponse)
async def match_errors(
    match_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get all detected errors for a match with explanations and recommendations."""
    result = await get_match_errors(session, match_id)
    return result


@router.get("/players/{steam_id}/errors", response_model=PlayerErrorSummaryResponse)
async def player_errors(
    steam_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get error summary for a player across all matches."""
    result = await get_player_error_summary(session, steam_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No errors found for this player")
    return result
