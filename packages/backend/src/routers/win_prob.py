"""Win probability API endpoints — top deaths and round curves."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.middleware.auth import get_current_user
from src.models.match import Match
from src.models.win_prob_impact import WinProbImpact
from src.schemas.auth import TokenPayload

router = APIRouter(tags=["win-prob"])


@router.get("/matches/{match_id}/winprob")
async def get_match_winprob(
    match_id: uuid.UUID,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all win probability impacts for a match.

    Returns:
    - rounds: list of {round_number, points: [{tick, prob_t, alive_t, alive_ct}]}
    - top_deaths: top 10 mortes mais custosas
    - player_impacts: agregado por jogador
    """
    org_id = uuid.UUID(current_user.org_id)
    match_result = await db.execute(
        select(Match).where(Match.id == match_id, Match.org_id == org_id)
    )
    match = match_result.scalar_one_or_none()
    if not match:
        return {"error": "Match not found"}

    impacts_result = await db.execute(
        select(WinProbImpact)
        .where(WinProbImpact.match_id == match_id)
        .order_by(WinProbImpact.round_number, WinProbImpact.tick)
    )
    impacts = impacts_result.scalars().all()

    if not impacts:
        return {
            "match_id": str(match_id),
            "rounds": [],
            "top_deaths": [],
            "player_impacts": [],
        }

    # Group by round for win prob curve
    rounds_dict: dict[int, list] = {}
    for imp in impacts:
        rd = rounds_dict.setdefault(imp.round_number, [])
        # T win prob (after the kill)
        t_prob = imp.prob_after if imp.victim_side == "t" else imp.prob_after
        rd.append(
            {
                "tick": imp.tick,
                "prob_t": round(t_prob, 4),
                "alive_t": imp.alive_t_before - (1 if imp.victim_side == "t" else 0),
                "alive_ct": imp.alive_ct_before - (1 if imp.victim_side == "ct" else 0),
                "victim_name": imp.victim_name,
                "victim_side": imp.victim_side,
            }
        )

    rounds = [{"round_number": rn, "points": pts} for rn, pts in sorted(rounds_dict.items())]

    # Top deaths sorted by win delta (highest impact first)
    top_deaths = sorted(impacts, key=lambda i: i.win_delta, reverse=True)[:10]
    top_deaths_data = [
        {
            "round_number": d.round_number,
            "victim_name": d.victim_name,
            "victim_side": d.victim_side,
            "attacker_name": d.attacker_name,
            "weapon": d.weapon,
            "headshot": d.headshot,
            "was_traded": d.was_traded,
            "win_delta": round(d.win_delta, 4),
            "prob_before": round(d.prob_before, 4),
            "prob_after": round(d.prob_after, 4),
            "alive_t": d.alive_t_before,
            "alive_ct": d.alive_ct_before,
        }
        for d in top_deaths
    ]

    # Aggregate by player
    player_stats: dict[str, dict] = {}
    for imp in impacts:
        # Victim impact (negative for them)
        ps = player_stats.setdefault(
            imp.victim_steam_id,
            {
                "steam_id": imp.victim_steam_id,
                "name": imp.victim_name,
                "deaths": 0,
                "total_lost": 0.0,
                "kills": 0,
                "total_gained": 0.0,
            },
        )
        ps["deaths"] += 1
        ps["total_lost"] += imp.win_delta

        # Attacker impact (positive for them)
        if imp.attacker_steam_id:
            asp = player_stats.setdefault(
                imp.attacker_steam_id,
                {
                    "steam_id": imp.attacker_steam_id,
                    "name": imp.attacker_name or "Unknown",
                    "deaths": 0,
                    "total_lost": 0.0,
                    "kills": 0,
                    "total_gained": 0.0,
                },
            )
            asp["kills"] += 1
            asp["total_gained"] += imp.win_delta

    player_impacts = sorted(
        [
            {
                **p,
                "net_impact": round(p["total_gained"] - p["total_lost"], 4),
                "avg_lost_per_death": round(p["total_lost"] / max(p["deaths"], 1), 4),
                "avg_gained_per_kill": round(p["total_gained"] / max(p["kills"], 1), 4),
                "total_lost": round(p["total_lost"], 4),
                "total_gained": round(p["total_gained"], 4),
            }
            for p in player_stats.values()
        ],
        key=lambda p: p["net_impact"],
        reverse=True,
    )

    return {
        "match_id": str(match_id),
        "map": match.map,
        "total_kills": len(impacts),
        "rounds": rounds,
        "top_deaths": top_deaths_data,
        "player_impacts": player_impacts,
    }
