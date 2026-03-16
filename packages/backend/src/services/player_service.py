"""Player stats aggregation service."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.match import Match
from src.models.player_match_stats import PlayerMatchStats
from src.services.feature_engine import AggregatedPlayerStats, compute_aggregated_stats


async def get_player_aggregated_stats(
    db: AsyncSession,
    org_id: uuid.UUID,
    steam_id: str,
) -> AggregatedPlayerStats | None:
    """Get aggregated stats for a player across all matches in the org."""
    stmt = (
        select(PlayerMatchStats, Match.total_rounds, Match.map)
        .join(Match, PlayerMatchStats.match_id == Match.id)
        .where(
            PlayerMatchStats.org_id == org_id,
            PlayerMatchStats.player_steam_id == steam_id,
        )
        .order_by(Match.created_at.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return None

    match_stats = []
    for pms, total_rounds, map_name in rows:
        match_stats.append(
            {
                "match_id": str(pms.match_id),
                "player_name": pms.player_name,
                "kills": pms.kills,
                "deaths": pms.deaths,
                "assists": pms.assists,
                "headshot_kills": pms.headshot_kills,
                "damage": pms.damage,
                "flash_assists": pms.flash_assists,
                "utility_damage": pms.utility_damage,
                "first_kills": pms.first_kills,
                "first_deaths": pms.first_deaths,
                "trade_kills": pms.trade_kills,
                "trade_deaths": pms.trade_deaths,
                "clutch_wins": pms.clutch_wins,
                "multi_kills_3k": pms.multi_kills_3k,
                "multi_kills_4k": pms.multi_kills_4k,
                "multi_kills_5k": pms.multi_kills_5k,
                "kast_rounds": pms.kast_rounds,
                "rounds_survived": pms.rounds_survived,
                "total_rounds": total_rounds,
                "map": map_name,
            }
        )

    return compute_aggregated_stats(steam_id, match_stats)


async def get_match_economy(
    db: AsyncSession,
    org_id: uuid.UUID,
    match_id: uuid.UUID,
) -> dict | None:
    """Get economy data for all rounds in a match."""
    from src.models.round import Round

    # Verify match belongs to org
    match_result = await db.execute(
        select(Match).where(Match.id == match_id, Match.org_id == org_id)
    )
    match = match_result.scalar_one_or_none()
    if not match:
        return None

    rounds_result = await db.execute(
        select(Round).where(Round.match_id == match_id).order_by(Round.round_number)
    )
    rounds = rounds_result.scalars().all()

    return {
        "match_id": str(match_id),
        "map": match.map,
        "total_rounds": match.total_rounds,
        "rounds": [
            {
                "round_number": r.round_number,
                "winner_side": r.winner_side,
                "t_equipment_value": r.t_equipment_value,
                "ct_equipment_value": r.ct_equipment_value,
                "t_buy_type": r.t_buy_type,
                "ct_buy_type": r.ct_buy_type,
                "team1_score": r.team1_score,
                "team2_score": r.team2_score,
            }
            for r in rounds
        ],
    }
