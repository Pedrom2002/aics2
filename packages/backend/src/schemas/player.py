from pydantic import BaseModel


class PlayerAggregatedStatsResponse(BaseModel):
    """Aggregated player stats across all matches in the org."""

    player_steam_id: str
    player_name: str
    total_matches: int
    total_rounds: int

    # Totals
    total_kills: int
    total_deaths: int
    total_assists: int
    total_headshot_kills: int
    total_damage: int
    total_flash_assists: int
    total_utility_damage: int
    total_first_kills: int
    total_first_deaths: int
    total_trade_kills: int
    total_trade_deaths: int
    total_clutch_wins: int
    total_multi_kills_3k: int
    total_multi_kills_4k: int
    total_multi_kills_5k: int
    total_kast_rounds: int
    total_rounds_survived: int

    # Averages
    avg_kills_per_round: float
    avg_deaths_per_round: float
    avg_kd_ratio: float
    avg_headshot_pct: float
    avg_adr: float
    avg_kast_pct: float
    avg_survival_rate: float
    avg_opening_duel_win_rate: float
    avg_trade_kill_rate: float
    avg_impact_rating: float
    avg_hltv_rating: float
    rating_std_deviation: float

    # Map stats
    maps_played: dict[str, int]
    best_map: str | None = None
    worst_map: str | None = None


class MatchEconomyRoundResponse(BaseModel):
    """Economy data for a single round."""

    round_number: int
    winner_side: str | None = None
    t_equipment_value: int | None = None
    ct_equipment_value: int | None = None
    t_buy_type: str | None = None
    ct_buy_type: str | None = None
    team1_score: int
    team2_score: int

    model_config = {"from_attributes": True}


class MatchEconomyResponse(BaseModel):
    """Economy overview for a match."""

    match_id: str
    map: str
    total_rounds: int
    rounds: list[MatchEconomyRoundResponse]
