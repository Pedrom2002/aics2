"""API endpoints for browsing professional CS2 matches."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.pro_match import ProMatch

router = APIRouter(prefix="/pro", tags=["pro-matches"])


@router.get("/matches")
async def list_pro_matches(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    team: str | None = Query(default=None),
    map_name: str | None = Query(default=None, alias="map"),
    event: str | None = Query(default=None),
    tier: str | None = Query(default=None),
    source: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    """Browse professional CS2 matches with filters."""
    query = select(ProMatch)

    if team:
        team_filter = f"%{team}%"
        query = query.where(
            (ProMatch.team1_name.ilike(team_filter)) | (ProMatch.team2_name.ilike(team_filter))
        )
    if map_name:
        query = query.where(ProMatch.map == map_name)
    if event:
        query = query.where(ProMatch.event_name.ilike(f"%{event}%"))
    if tier:
        query = query.where(ProMatch.event_tier == tier)
    if source:
        query = query.where(ProMatch.source == source)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = (
        query.order_by(desc(ProMatch.match_date)).offset((page - 1) * page_size).limit(page_size)
    )
    result = await session.execute(query)
    matches = result.scalars().all()

    return {
        "items": [
            {
                "id": str(m.id),
                "source": m.source,
                "team1_name": m.team1_name,
                "team2_name": m.team2_name,
                "team1_score": m.team1_score,
                "team2_score": m.team2_score,
                "map": m.map,
                "event_name": m.event_name,
                "event_tier": m.event_tier,
                "match_date": m.match_date.isoformat() if m.match_date else None,
                "status": m.status,
                "ml_analyzed": m.ml_analyzed,
            }
            for m in matches
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@router.get("/matches/{pro_match_id}")
async def get_pro_match(
    pro_match_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get details of a specific pro match."""
    from uuid import UUID

    result = await session.execute(select(ProMatch).where(ProMatch.id == UUID(pro_match_id)))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=404, detail="Pro match not found")

    return {
        "id": str(match.id),
        "source": match.source,
        "source_match_id": match.source_match_id,
        "team1_name": match.team1_name,
        "team2_name": match.team2_name,
        "team1_score": match.team1_score,
        "team2_score": match.team2_score,
        "map": match.map,
        "event_name": match.event_name,
        "event_tier": match.event_tier,
        "match_date": match.match_date.isoformat() if match.match_date else None,
        "demo_id": str(match.demo_id) if match.demo_id else None,
        "status": match.status,
        "ml_analyzed": match.ml_analyzed,
        "ml_analyzed_at": match.ml_analyzed_at.isoformat() if match.ml_analyzed_at else None,
        "created_at": match.created_at.isoformat(),
    }


@router.get("/teams")
async def search_teams(
    q: str = Query(min_length=2),
    session: AsyncSession = Depends(get_db),
):
    """Search for teams across pro matches (autocomplete)."""
    # Union of team1 and team2 names matching query
    query = (
        select(ProMatch.team1_name).where(ProMatch.team1_name.ilike(f"%{q}%")).distinct().limit(10)
    )
    result1 = await session.execute(query)
    names1 = {r[0] for r in result1}

    query2 = (
        select(ProMatch.team2_name).where(ProMatch.team2_name.ilike(f"%{q}%")).distinct().limit(10)
    )
    result2 = await session.execute(query2)
    names2 = {r[0] for r in result2}

    all_names = sorted(names1 | names2)[:10]
    return {"teams": all_names}


@router.get("/events")
async def list_events(
    session: AsyncSession = Depends(get_db),
):
    """List all events with match counts."""
    result = await session.execute(
        select(ProMatch.event_name, func.count(ProMatch.id))
        .where(ProMatch.event_name.isnot(None))
        .group_by(ProMatch.event_name)
        .order_by(desc(func.count(ProMatch.id)))
        .limit(50)
    )
    events = [{"name": name, "match_count": count} for name, count in result]
    return {"events": events}
