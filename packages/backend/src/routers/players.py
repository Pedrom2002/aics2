"""Player stats endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.middleware.auth import get_current_user
from src.schemas.auth import TokenPayload
from src.schemas.player import (
    MatchEconomyResponse,
    PlayerAggregatedStatsResponse,
)
from src.services import player_service

router = APIRouter(tags=["players"])


@router.get(
    "/players/{steam_id}/stats",
    response_model=PlayerAggregatedStatsResponse,
)
async def get_player_stats(
    steam_id: str,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated stats for a player across all matches."""
    stats = await player_service.get_player_aggregated_stats(
        db=db,
        org_id=uuid.UUID(current_user.org_id),
        steam_id=steam_id,
    )
    if stats is None:
        raise HTTPException(status_code=404, detail="Player not found")

    return PlayerAggregatedStatsResponse(
        player_steam_id=stats.player_steam_id,
        player_name=stats.player_name,
        total_matches=stats.total_matches,
        total_rounds=stats.total_rounds,
        total_kills=stats.total_kills,
        total_deaths=stats.total_deaths,
        total_assists=stats.total_assists,
        total_headshot_kills=stats.total_headshot_kills,
        total_damage=stats.total_damage,
        total_flash_assists=stats.total_flash_assists,
        total_utility_damage=stats.total_utility_damage,
        total_first_kills=stats.total_first_kills,
        total_first_deaths=stats.total_first_deaths,
        total_trade_kills=stats.total_trade_kills,
        total_trade_deaths=stats.total_trade_deaths,
        total_clutch_wins=stats.total_clutch_wins,
        total_multi_kills_3k=stats.total_multi_kills_3k,
        total_multi_kills_4k=stats.total_multi_kills_4k,
        total_multi_kills_5k=stats.total_multi_kills_5k,
        total_kast_rounds=stats.total_kast_rounds,
        total_rounds_survived=stats.total_rounds_survived,
        avg_kills_per_round=stats.avg_kills_per_round,
        avg_deaths_per_round=stats.avg_deaths_per_round,
        avg_kd_ratio=stats.avg_kd_ratio,
        avg_headshot_pct=stats.avg_headshot_pct,
        avg_adr=stats.avg_adr,
        avg_kast_pct=stats.avg_kast_pct,
        avg_survival_rate=stats.avg_survival_rate,
        avg_opening_duel_win_rate=stats.avg_opening_duel_win_rate,
        avg_trade_kill_rate=stats.avg_trade_kill_rate,
        avg_impact_rating=stats.avg_impact_rating,
        avg_hltv_rating=stats.avg_hltv_rating,
        rating_std_deviation=stats.rating_std_deviation,
        maps_played=stats.maps_played,
        best_map=stats.best_map,
        worst_map=stats.worst_map,
    )


@router.get(
    "/matches/{match_id}/economy",
    response_model=MatchEconomyResponse,
)
async def get_match_economy(
    match_id: uuid.UUID,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get economy data for all rounds in a match."""
    economy = await player_service.get_match_economy(
        db=db,
        org_id=uuid.UUID(current_user.org_id),
        match_id=match_id,
    )
    if economy is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return economy
