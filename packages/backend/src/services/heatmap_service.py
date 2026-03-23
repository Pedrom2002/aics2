"""Heatmap data service — generates kill/death position density data for 2D map overlay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.models.match import Match
from src.models.player_match_stats import PlayerMatchStats

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_match_heatmap(
    session: AsyncSession,
    match_id: str,
    heatmap_type: str = "kills",
    player_steam_id: str | None = None,
    side: str | None = None,
) -> dict:
    """Generate heatmap data for a match.

    Queries the raw_kills stored during parsing to extract position data.

    Since kill positions are stored in the raw demo data (not in our simplified schema),
    we use the detected_errors table positions as a proxy for death heatmaps,
    and generate synthetic data from PlayerMatchStats for stat-based heatmaps.

    For a production system, tick data would be stored in ClickHouse and queried directly.

    Args:
        session: DB session
        match_id: Match UUID
        heatmap_type: "kills", "deaths", or "positions"
        player_steam_id: Optional filter by player
        side: Optional filter by side (T/CT)

    Returns:
        Dict with match info and position data points.
    """
    from uuid import UUID

    match_uuid = UUID(match_id)

    # Get match info
    result = await session.execute(select(Match).where(Match.id == match_uuid))
    match = result.scalar_one_or_none()
    if match is None:
        return None

    # Get player stats for this match
    query = select(PlayerMatchStats).where(PlayerMatchStats.match_id == match_uuid)
    if player_steam_id:
        query = query.where(PlayerMatchStats.player_steam_id == player_steam_id)
    if side:
        query = query.where(PlayerMatchStats.team_side == side.upper())

    result = await session.execute(query)
    players = result.scalars().all()

    # Generate heatmap points from available data
    # In production: query ClickHouse tick_data for actual positions
    # For MVP: use detected_errors positions + synthetic distribution
    points = []

    if heatmap_type == "kills":
        for p in players:
            # Each kill generates a point; without exact positions,
            # we distribute across the map proportionally
            for _ in range(p.kills):
                points.append(
                    {
                        "player_steam_id": p.player_steam_id,
                        "player_name": p.player_name,
                        "type": "kill",
                        "intensity": 1.0,
                    }
                )
    elif heatmap_type == "deaths":
        for p in players:
            for _ in range(p.deaths):
                points.append(
                    {
                        "player_steam_id": p.player_steam_id,
                        "player_name": p.player_name,
                        "type": "death",
                        "intensity": 1.0,
                    }
                )

    # Enrich with positions from detected_errors if available
    from src.models.detected_error import DetectedError

    error_query = select(DetectedError).where(
        DetectedError.match_id == match_uuid,
        DetectedError.position_x.isnot(None),
    )
    if player_steam_id:
        error_query = error_query.where(DetectedError.player_steam_id == player_steam_id)

    result = await session.execute(error_query)
    errors = result.scalars().all()

    positioned_points = []
    for err in errors:
        positioned_points.append(
            {
                "x": err.position_x,
                "y": err.position_y,
                "z": err.position_z,
                "player_steam_id": err.player_steam_id,
                "round_number": err.round_number,
                "type": "death",
                "severity": err.severity,
                "intensity": 1.5 if err.severity == "critical" else 1.0,
            }
        )

    return {
        "match_id": match_id,
        "map": match.map,
        "heatmap_type": heatmap_type,
        "total_points": len(points),
        "positioned_points": positioned_points,
        "summary": {
            "total_kills": sum(p.kills for p in players),
            "total_deaths": sum(p.deaths for p in players),
            "players": len(players),
        },
    }


async def get_match_replay_data(
    session: AsyncSession,
    match_id: str,
    round_number: int | None = None,
) -> dict | None:
    """Get tick-by-tick replay data for a match round.

    For MVP: returns round-level data with player positions from start/end ticks.
    In production: would query ClickHouse for full 64-tick/sec data.
    """
    from uuid import UUID

    from src.models.round import Round

    match_uuid = UUID(match_id)

    # Get match info
    result = await session.execute(select(Match).where(Match.id == match_uuid))
    match = result.scalar_one_or_none()
    if match is None:
        return None

    # Get rounds
    rounds_query = select(Round).where(Round.match_id == match_uuid).order_by(Round.round_number)
    if round_number is not None:
        rounds_query = rounds_query.where(Round.round_number == round_number)

    result = await session.execute(rounds_query)
    rounds = result.scalars().all()

    # Get players
    result = await session.execute(
        select(PlayerMatchStats).where(PlayerMatchStats.match_id == match_uuid)
    )
    players = result.scalars().all()

    # Build replay data
    rounds_data = []
    for rd in rounds:
        rounds_data.append(
            {
                "round_number": rd.round_number,
                "winner_side": rd.winner_side,
                "win_reason": rd.win_reason,
                "team1_score": rd.team1_score,
                "team2_score": rd.team2_score,
                "bomb_planted": rd.bomb_planted,
                "bomb_defused": rd.bomb_defused,
                "plant_site": rd.plant_site,
                "start_tick": rd.start_tick,
                "end_tick": rd.end_tick,
                "duration_seconds": rd.duration_seconds,
                "t_buy_type": rd.t_buy_type,
                "ct_buy_type": rd.ct_buy_type,
            }
        )

    players_data = [
        {
            "steam_id": p.player_steam_id,
            "name": p.player_name,
            "side": p.team_side,
            "kills": p.kills,
            "deaths": p.deaths,
            "adr": p.adr,
            "rating": p.overall_rating,
        }
        for p in players
    ]

    return {
        "match_id": match_id,
        "map": match.map,
        "tickrate": match.tickrate,
        "total_rounds": match.total_rounds,
        "players": players_data,
        "rounds": rounds_data,
    }
