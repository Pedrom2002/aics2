"""Team-level analytics endpoints: roster composition, archetypes, map pool."""

from __future__ import annotations

import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.middleware.auth import get_current_user
from src.models.player_match_stats import PlayerMatchStats
from src.models.pro_match import ProMatch
from src.models.team import Team
from src.models.team_player import TeamPlayer
from src.schemas.auth import TokenPayload

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/{team_id}")
async def get_team_overview(
    team_id: str,
    _user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregate team composition, map preference, and roster archetypes."""
    try:
        tid = uuid.UUID(team_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid team id") from exc

    team = (await db.execute(select(Team).where(Team.id == tid))).scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=404, detail="team not found")

    roster_rows = await db.execute(
        select(TeamPlayer.steam_id, TeamPlayer.role).where(TeamPlayer.team_id == tid)
    )
    roster = [{"steam_id": sid, "role": role} for sid, role in roster_rows.all()]
    steam_ids = [r["steam_id"] for r in roster]

    # Map preference — count ProMatches where this team name matches
    map_rows = await db.execute(
        select(ProMatch.map_name, func.count().label("n"))
        .where((ProMatch.team1_name == team.name) | (ProMatch.team2_name == team.name))
        .group_by(ProMatch.map_name)
        .order_by(func.count().desc())
    )
    map_preference = [{"map": m, "count": n} for m, n in map_rows.all() if m]

    # Roster archetypes (from clustering side-car file via registry)
    archetypes: Counter = Counter()
    if steam_ids:
        # Pull cached archetype per player via the existing service
        from src.services.player_service import get_player_archetype

        for sid in steam_ids:
            arche = await get_player_archetype(db, sid)
            if arche:
                archetypes[arche.get("archetype", "unknown")] += 1

    # Aggregate stats
    stats_rows = await db.execute(
        select(
            func.avg(PlayerMatchStats.rating).label("avg_rating"),
            func.avg(PlayerMatchStats.adr).label("avg_adr"),
            func.avg(PlayerMatchStats.hs_pct).label("avg_hs"),
        ).where(PlayerMatchStats.player_steam_id.in_(steam_ids) if steam_ids else False)
    )
    avg_rating, avg_adr, avg_hs = stats_rows.one()

    return {
        "id": str(team.id),
        "name": team.name,
        "roster": roster,
        "map_preference": map_preference,
        "archetypes": [{"archetype": a, "count": c} for a, c in archetypes.most_common()],
        "averages": {
            "rating": float(avg_rating) if avg_rating is not None else None,
            "adr": float(avg_adr) if avg_adr is not None else None,
            "hs_pct": float(avg_hs) if avg_hs is not None else None,
        },
    }
