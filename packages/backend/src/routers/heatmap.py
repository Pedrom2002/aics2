"""Heatmap and replay data API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.heatmap_service import get_match_heatmap, get_match_replay_data

router = APIRouter(tags=["heatmap"])


@router.get("/matches/{match_id}/heatmap")
async def match_heatmap(
    match_id: str,
    heatmap_type: str = Query(default="kills", alias="type", pattern="^(kills|deaths|positions)$"),
    player: str | None = Query(default=None),
    side: str | None = Query(default=None, pattern="^(T|CT)$"),
    session: AsyncSession = Depends(get_db),
):
    """Get heatmap data for a match.

    Supports kill, death, and position heatmaps with optional player/side filters.
    """
    result = await get_match_heatmap(
        session, match_id, heatmap_type=heatmap_type, player_steam_id=player, side=side
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return result


@router.get("/matches/{match_id}/replay")
async def match_replay(
    match_id: str,
    round_num: int | None = Query(default=None, alias="round", ge=1),
    session: AsyncSession = Depends(get_db),
):
    """Get replay data for a match.

    Returns round-level data with player info and tick ranges.
    Query with ?round=N to get a specific round.
    """
    result = await get_match_replay_data(session, match_id, round_number=round_num)
    if result is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return result
