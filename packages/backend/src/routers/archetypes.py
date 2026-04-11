"""Player archetypes and rating API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.middleware.auth import get_current_user
from src.schemas.auth import TokenPayload
from src.services.player_rating_service import (
    get_player_archetype,
    list_archetypes,
    predict_player_rating,
)

router = APIRouter(tags=["archetypes"])


@router.get("/archetypes")
async def list_player_archetypes(
    current_user: TokenPayload = Depends(get_current_user),
):
    """List all discovered player archetypes from UMAP+HDBSCAN clustering."""
    archetypes = list_archetypes()
    return {
        "total": len(archetypes),
        "archetypes": archetypes,
    }


@router.get("/players/{steam_id}/archetype")
async def get_player_archetype_endpoint(
    steam_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get the archetype assignment for a specific player."""
    archetype = get_player_archetype(steam_id)
    if archetype is None:
        raise HTTPException(status_code=404, detail="Player not found in clusters")
    return archetype


@router.post("/players/{steam_id}/predict-rating")
async def predict_rating(
    steam_id: str,
    stats: dict,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Predict HLTV-calibrated rating for a player from aggregated stats.

    POST body should contain:
        kills, deaths, assists, headshot_kills, damage,
        first_kills, first_deaths, trade_kills, trade_deaths,
        kast_rounds, rounds_survived, multi_kills_3k, multi_kills_4k,
        multi_kills_5k, clutch_wins, flash_assists, utility_damage,
        total_rounds, adr
    """
    rating = predict_player_rating(stats)
    if rating is None:
        raise HTTPException(status_code=503, detail="Rating model not available")
    return {
        "steam_id": steam_id,
        "predicted_rating": round(rating, 4),
        "model": "catboost_hltv_calibrated",
    }
