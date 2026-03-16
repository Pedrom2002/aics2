"""Feature engine: computes derived player features from match data.

Produces ~40 features per player per match, and aggregated career stats.
Features are grouped into categories matching the ML pipeline spec.
"""

from dataclasses import dataclass, field


@dataclass
class PlayerFeatures:
    """Computed features for a single player in a single match."""

    player_steam_id: str
    player_name: str
    match_id: str

    # --- Aim & Mechanics ---
    kills_per_round: float = 0.0
    deaths_per_round: float = 0.0
    kd_ratio: float = 0.0
    headshot_pct: float = 0.0
    adr: float = 0.0

    # --- Game Sense ---
    opening_duel_attempts: int = 0
    opening_duel_win_rate: float = 0.0
    trade_kill_rate: float = 0.0
    trade_death_rate: float = 0.0
    kast_pct: float = 0.0
    survival_rate: float = 0.0

    # --- Impact ---
    multi_kill_rounds: int = 0  # total 3k+4k+5k rounds
    clutch_wins: int = 0
    rounds_with_kill_pct: float = 0.0
    first_kill_rate: float = 0.0
    impact_rating: float = 0.0

    # --- Utility ---
    flash_assists_per_round: float = 0.0
    utility_damage_per_round: float = 0.0

    # --- Economy ---
    # (requires round-level buy type correlation — computed from match context)
    eco_kill_efficiency: float | None = None

    # --- Consistency (only meaningful across multiple matches) ---
    # Filled by aggregate functions

    # --- Composite rating ---
    hltv_rating_approx: float = 0.0


@dataclass
class AggregatedPlayerStats:
    """Aggregated stats across multiple matches for a player."""

    player_steam_id: str
    player_name: str
    total_matches: int = 0
    total_rounds: int = 0
    total_kills: int = 0
    total_deaths: int = 0
    total_assists: int = 0
    total_headshot_kills: int = 0
    total_damage: int = 0
    total_flash_assists: int = 0
    total_utility_damage: int = 0
    total_first_kills: int = 0
    total_first_deaths: int = 0
    total_trade_kills: int = 0
    total_trade_deaths: int = 0
    total_clutch_wins: int = 0
    total_multi_kills_3k: int = 0
    total_multi_kills_4k: int = 0
    total_multi_kills_5k: int = 0
    total_kast_rounds: int = 0
    total_rounds_survived: int = 0

    # Computed averages
    avg_kills_per_round: float = 0.0
    avg_deaths_per_round: float = 0.0
    avg_kd_ratio: float = 0.0
    avg_headshot_pct: float = 0.0
    avg_adr: float = 0.0
    avg_kast_pct: float = 0.0
    avg_survival_rate: float = 0.0
    avg_opening_duel_win_rate: float = 0.0
    avg_trade_kill_rate: float = 0.0
    avg_impact_rating: float = 0.0
    avg_hltv_rating: float = 0.0

    # Per-match ratings for consistency analysis
    match_ratings: list[float] = field(default_factory=list)
    rating_std_deviation: float = 0.0

    # Map stats
    maps_played: dict[str, int] = field(default_factory=dict)
    best_map: str | None = None
    worst_map: str | None = None


def compute_match_features(
    player_steam_id: str,
    player_name: str,
    match_id: str,
    kills: int,
    deaths: int,
    assists: int,
    headshot_kills: int,
    damage: int,
    total_rounds: int,
    flash_assists: int,
    utility_damage: int,
    first_kills: int,
    first_deaths: int,
    trade_kills: int,
    trade_deaths: int,
    clutch_wins: int,
    multi_kills_3k: int,
    multi_kills_4k: int,
    multi_kills_5k: int,
    kast_rounds: int,
    rounds_survived: int,
) -> PlayerFeatures:
    """Compute derived features for a player in a single match."""
    tr = max(total_rounds, 1)  # avoid division by zero

    kpr = round(kills / tr, 3)
    dpr = round(deaths / tr, 3)
    kd = round(kills / max(deaths, 1), 2)
    hs_pct = round(headshot_kills / max(kills, 1) * 100, 1)
    adr = round(damage / tr, 1)

    opening_attempts = first_kills + first_deaths
    opening_win_rate = round(first_kills / max(opening_attempts, 1) * 100, 1)

    trade_opportunities = deaths  # approximate: each death is a potential trade opportunity
    t_kill_rate = (
        round(trade_kills / max(trade_opportunities, 1) * 100, 1)
        if trade_opportunities > 0
        else 0.0
    )
    t_death_rate = round(trade_deaths / max(deaths, 1) * 100, 1) if deaths > 0 else 0.0

    kast_pct = round(kast_rounds / tr * 100, 1)
    survival = round(rounds_survived / tr * 100, 1)

    multi_total = multi_kills_3k + multi_kills_4k + multi_kills_5k
    fk_rate = round(first_kills / tr * 100, 1)

    # HLTV Rating 2.0 approximation
    # Based on: KPR, SPR (survival per round), impact (multi-kills, first kills)
    # Simplified formula inspired by public HLTV rating methodology
    kpr_component = kpr * 0.75
    spr_component = (rounds_survived / tr) * 0.7 if tr > 0 else 0
    impact_component = (
        first_kills * 0.15 + trade_kills * 0.1 + clutch_wins * 0.2 + multi_total * 0.1
    ) / tr
    adr_component = (adr / 150.0) * 0.3  # normalize ADR contribution

    hltv_approx = round(kpr_component + spr_component + impact_component + adr_component, 2)

    # Impact rating (0-100 scale)
    impact = round(
        min(
            100,
            (
                kpr * 30
                + (first_kills / tr) * 20
                + (clutch_wins / tr) * 25
                + (multi_total / tr) * 15
                + (adr / 150) * 10
            ),
        ),
        1,
    )

    return PlayerFeatures(
        player_steam_id=player_steam_id,
        player_name=player_name,
        match_id=match_id,
        kills_per_round=kpr,
        deaths_per_round=dpr,
        kd_ratio=kd,
        headshot_pct=hs_pct,
        adr=adr,
        opening_duel_attempts=opening_attempts,
        opening_duel_win_rate=opening_win_rate,
        trade_kill_rate=t_kill_rate,
        trade_death_rate=t_death_rate,
        kast_pct=kast_pct,
        survival_rate=survival,
        multi_kill_rounds=multi_total,
        clutch_wins=clutch_wins,
        rounds_with_kill_pct=fk_rate,
        first_kill_rate=fk_rate,
        impact_rating=impact,
        flash_assists_per_round=round(flash_assists / tr, 2),
        utility_damage_per_round=round(utility_damage / tr, 1),
        hltv_rating_approx=hltv_approx,
    )


def compute_aggregated_stats(
    player_steam_id: str,
    match_stats: list[dict],
) -> AggregatedPlayerStats:
    """Compute aggregated stats across multiple matches.

    Each item in match_stats should have keys matching PlayerMatchStats columns
    plus 'total_rounds' from the associated Match.
    """
    if not match_stats:
        return AggregatedPlayerStats(
            player_steam_id=player_steam_id,
            player_name="Unknown",
        )

    agg = AggregatedPlayerStats(
        player_steam_id=player_steam_id,
        player_name=match_stats[0].get("player_name", "Unknown"),
        total_matches=len(match_stats),
    )

    match_ratings: list[float] = []

    for ms in match_stats:
        tr = ms.get("total_rounds", 1) or 1
        agg.total_rounds += tr
        agg.total_kills += ms.get("kills", 0)
        agg.total_deaths += ms.get("deaths", 0)
        agg.total_assists += ms.get("assists", 0)
        agg.total_headshot_kills += ms.get("headshot_kills", 0)
        agg.total_damage += ms.get("damage", 0)
        agg.total_flash_assists += ms.get("flash_assists", 0)
        agg.total_utility_damage += ms.get("utility_damage", 0)
        agg.total_first_kills += ms.get("first_kills", 0)
        agg.total_first_deaths += ms.get("first_deaths", 0)
        agg.total_trade_kills += ms.get("trade_kills", 0)
        agg.total_trade_deaths += ms.get("trade_deaths", 0)
        agg.total_clutch_wins += ms.get("clutch_wins", 0)
        agg.total_multi_kills_3k += ms.get("multi_kills_3k", 0)
        agg.total_multi_kills_4k += ms.get("multi_kills_4k", 0)
        agg.total_multi_kills_5k += ms.get("multi_kills_5k", 0)
        agg.total_kast_rounds += ms.get("kast_rounds", 0)
        agg.total_rounds_survived += ms.get("rounds_survived", 0)

        # Map tracking
        map_name = ms.get("map", "unknown")
        agg.maps_played[map_name] = agg.maps_played.get(map_name, 0) + 1

        # Per-match rating for consistency
        features = compute_match_features(
            player_steam_id=player_steam_id,
            player_name=agg.player_name,
            match_id=ms.get("match_id", ""),
            kills=ms.get("kills", 0),
            deaths=ms.get("deaths", 0),
            assists=ms.get("assists", 0),
            headshot_kills=ms.get("headshot_kills", 0),
            damage=ms.get("damage", 0),
            total_rounds=tr,
            flash_assists=ms.get("flash_assists", 0),
            utility_damage=ms.get("utility_damage", 0),
            first_kills=ms.get("first_kills", 0),
            first_deaths=ms.get("first_deaths", 0),
            trade_kills=ms.get("trade_kills", 0),
            trade_deaths=ms.get("trade_deaths", 0),
            clutch_wins=ms.get("clutch_wins", 0),
            multi_kills_3k=ms.get("multi_kills_3k", 0),
            multi_kills_4k=ms.get("multi_kills_4k", 0),
            multi_kills_5k=ms.get("multi_kills_5k", 0),
            kast_rounds=ms.get("kast_rounds", 0),
            rounds_survived=ms.get("rounds_survived", 0),
        )
        match_ratings.append(features.hltv_rating_approx)

    # Compute averages from totals
    tr = max(agg.total_rounds, 1)
    agg.avg_kills_per_round = round(agg.total_kills / tr, 3)
    agg.avg_deaths_per_round = round(agg.total_deaths / tr, 3)
    agg.avg_kd_ratio = round(agg.total_kills / max(agg.total_deaths, 1), 2)
    agg.avg_headshot_pct = round(agg.total_headshot_kills / max(agg.total_kills, 1) * 100, 1)
    agg.avg_adr = round(agg.total_damage / tr, 1)
    agg.avg_kast_pct = round(agg.total_kast_rounds / tr * 100, 1)
    agg.avg_survival_rate = round(agg.total_rounds_survived / tr * 100, 1)

    opening_attempts = agg.total_first_kills + agg.total_first_deaths
    agg.avg_opening_duel_win_rate = round(agg.total_first_kills / max(opening_attempts, 1) * 100, 1)
    agg.avg_trade_kill_rate = round(agg.total_trade_kills / max(agg.total_deaths, 1) * 100, 1)

    # Impact rating average
    multi_total = agg.total_multi_kills_3k + agg.total_multi_kills_4k + agg.total_multi_kills_5k
    agg.avg_impact_rating = round(
        min(
            100,
            (
                (agg.total_kills / tr) * 30
                + (agg.total_first_kills / tr) * 20
                + (agg.total_clutch_wins / tr) * 25
                + (multi_total / tr) * 15
                + (agg.avg_adr / 150) * 10
            ),
        ),
        1,
    )

    # HLTV rating
    agg.match_ratings = match_ratings
    agg.avg_hltv_rating = round(sum(match_ratings) / max(len(match_ratings), 1), 2)

    # Rating consistency (std deviation)
    if len(match_ratings) > 1:
        mean = agg.avg_hltv_rating
        variance = sum((r - mean) ** 2 for r in match_ratings) / len(match_ratings)
        agg.rating_std_deviation = round(variance**0.5, 3)

    # Best/worst map by win-rate approximation (maps played count as proxy)
    if agg.maps_played:
        agg.best_map = max(agg.maps_played, key=agg.maps_played.get)  # type: ignore[arg-type]
        agg.worst_map = min(agg.maps_played, key=agg.maps_played.get)  # type: ignore[arg-type]

    return agg
