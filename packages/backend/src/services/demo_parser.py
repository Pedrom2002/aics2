"""CS2 demo parser wrapper around awpy v2.

Parses a .dem file and returns structured data ready for DB insertion.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Trade kill window: kill within 5 seconds (320 ticks at 64 tick)
TRADE_KILL_WINDOW_TICKS = 320


@dataclass
class PlayerData:
    steam_id: str
    name: str
    team_side: str | None  # starting side: "T" or "CT"
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    headshot_kills: int = 0
    damage: int = 0
    adr: float | None = None
    flash_assists: int = 0
    enemies_flashed: int = 0
    utility_damage: int = 0
    first_kills: int = 0
    first_deaths: int = 0
    # Advanced stats
    multi_kills_3k: int = 0
    multi_kills_4k: int = 0
    multi_kills_5k: int = 0
    clutch_wins: int = 0
    trade_kills: int = 0
    trade_deaths: int = 0
    kast_rounds: int = 0
    rounds_survived: int = 0


@dataclass
class RoundData:
    round_number: int
    winner_side: str | None  # "T" or "CT"
    win_reason: str | None
    team1_score: int = 0
    team2_score: int = 0
    bomb_planted: bool | None = None
    bomb_defused: bool | None = None
    plant_site: str | None = None
    start_tick: int | None = None
    end_tick: int | None = None
    duration_seconds: float | None = None
    # Economy (populated from ticks data if available)
    t_economy: int | None = None
    ct_economy: int | None = None
    t_equipment_value: int | None = None
    ct_equipment_value: int | None = None
    t_buy_type: str | None = None
    ct_buy_type: str | None = None


@dataclass
class ParsedDemo:
    map_name: str
    tickrate: int
    duration_seconds: float | None
    team1_name: str | None
    team2_name: str | None
    team1_score: int
    team2_score: int
    total_rounds: int
    overtime_rounds: int
    rounds: list[RoundData] = field(default_factory=list)
    players: list[PlayerData] = field(default_factory=list)


def _classify_win_reason(reason: str | None) -> str | None:
    """Normalize awpy win_reason strings to our schema values."""
    if reason is None:
        return None
    r = reason.lower()
    if "bomb" in r and "explo" in r:
        return "bomb_exploded"
    if "defus" in r:
        return "defuse"
    if "elim" in r or "death" in r or "kill" in r:
        return "elimination"
    if "time" in r or "timer" in r:
        return "time"
    if "surrender" in r:
        return "surrender"
    return reason[:30]


def _classify_buy_type(equipment_value: int) -> str:
    """Classify buy type based on total equipment value."""
    if equipment_value < 2000:
        return "eco"
    if equipment_value < 3500:
        return "force"
    if equipment_value < 4500:
        return "semi"
    return "full"


def _is_pistol_round(round_number: int) -> bool:
    """Check if a round is a pistol round (1st or 16th)."""
    return round_number in (1, 16)


@dataclass
class _KillEvent:
    """Internal kill event for advanced stats computation."""

    tick: int
    round_num: int
    killer_sid: str
    victim_sid: str
    killer_side: str
    victim_side: str


def _compute_advanced_stats(
    kill_events: list[_KillEvent],
    rounds: list[RoundData],
    player_sides: dict[str, str],
    player_assists_per_round: dict[str, set[int]],
    total_rounds: int,
) -> dict[str, dict[str, int]]:
    """Compute multi-kills, clutches, trade kills, KAST, rounds survived."""
    # Per-player results
    multi_3k: dict[str, int] = {}
    multi_4k: dict[str, int] = {}
    multi_5k: dict[str, int] = {}
    clutch_wins: dict[str, int] = {}
    trade_kills: dict[str, int] = {}
    trade_deaths: dict[str, int] = {}
    kast_rounds: dict[str, int] = {}
    rounds_survived: dict[str, int] = {}

    # Group kills by round
    kills_by_round: dict[int, list[_KillEvent]] = {}
    for ke in kill_events:
        kills_by_round.setdefault(ke.round_num, []).append(ke)

    # Build round winner lookup
    round_winners: dict[int, str | None] = {}
    for rd in rounds:
        round_winners[rd.round_number] = rd.winner_side

    # Collect all player IDs (from kills + known sides)
    all_players: set[str] = set()
    for ke in kill_events:
        if ke.killer_sid and ke.killer_sid != "0":
            all_players.add(ke.killer_sid)
        if ke.victim_sid and ke.victim_sid != "0":
            all_players.add(ke.victim_sid)
    for sid in player_sides:
        if sid and sid != "0":
            all_players.add(sid)

    for rnd_num in range(1, total_rounds + 1):
        round_kills = kills_by_round.get(rnd_num, [])
        winner_side = round_winners.get(rnd_num)
        dead_in_round: set[str] = set()

        # --- Multi-kills per round ---
        kills_per_player: dict[str, int] = {}
        for ke in round_kills:
            if ke.killer_sid and ke.killer_sid != "0":
                kills_per_player[ke.killer_sid] = kills_per_player.get(ke.killer_sid, 0) + 1

        for sid, k in kills_per_player.items():
            if k >= 3:
                multi_3k[sid] = multi_3k.get(sid, 0) + 1
            if k >= 4:
                multi_4k[sid] = multi_4k.get(sid, 0) + 1
            if k >= 5:
                multi_5k[sid] = multi_5k.get(sid, 0) + 1

        # --- Trade kills (kill within TRADE_KILL_WINDOW_TICKS of teammate death) ---
        # Sort by tick
        sorted_kills = sorted(round_kills, key=lambda x: x.tick)
        traded_victims: set[str] = set()

        for i, ke in enumerate(sorted_kills):
            if ke.victim_sid and ke.victim_sid != "0":
                dead_in_round.add(ke.victim_sid)

            # Check if this kill is a trade
            if ke.killer_sid and ke.killer_sid != "0":
                for prev in sorted_kills[:i]:
                    # Previous kill where a teammate of current killer was killed
                    if (
                        prev.victim_sid != "0"
                        and prev.victim_sid != ke.killer_sid
                        and prev.victim_sid in player_sides
                        and ke.killer_sid in player_sides
                        and player_sides.get(prev.victim_sid) == player_sides.get(ke.killer_sid)
                        and ke.tick - prev.tick <= TRADE_KILL_WINDOW_TICKS
                        and prev.victim_sid not in traded_victims
                    ):
                        trade_kills[ke.killer_sid] = trade_kills.get(ke.killer_sid, 0) + 1
                        trade_deaths[prev.victim_sid] = trade_deaths.get(prev.victim_sid, 0) + 1
                        traded_victims.add(prev.victim_sid)
                        break

        # --- Clutch detection ---
        # Detect situations where a player is last alive on their team and wins
        if winner_side and sorted_kills:
            # Track alive players per side through the round
            t_alive: set[str] = set()
            ct_alive: set[str] = set()
            for sid in all_players:
                side = player_sides.get(sid)
                if side == "T":
                    t_alive.add(sid)
                elif side == "CT":
                    ct_alive.add(sid)

            clutch_player = None
            for ke in sorted_kills:
                if ke.victim_sid and ke.victim_sid != "0":
                    victim_side = player_sides.get(ke.victim_sid)
                    if victim_side == "T":
                        t_alive.discard(ke.victim_sid)
                    elif victim_side == "CT":
                        ct_alive.discard(ke.victim_sid)

                    # Check if a team is down to 1 player
                    if len(t_alive) == 1 and len(ct_alive) >= 1:
                        clutch_player = next(iter(t_alive))
                    elif len(ct_alive) == 1 and len(t_alive) >= 1:
                        clutch_player = next(iter(ct_alive))

            if clutch_player and player_sides.get(clutch_player) == winner_side:
                clutch_wins[clutch_player] = clutch_wins.get(clutch_player, 0) + 1

        # --- KAST (Kill, Assist, Survived, Traded) ---
        for sid in all_players:
            has_k = kills_per_player.get(sid, 0) > 0
            has_a = rnd_num in player_assists_per_round.get(sid, set())
            has_s = sid not in dead_in_round
            has_t = sid in traded_victims
            if has_k or has_a or has_s or has_t:
                kast_rounds[sid] = kast_rounds.get(sid, 0) + 1

        # --- Rounds survived ---
        for sid in all_players:
            if sid not in dead_in_round:
                rounds_survived[sid] = rounds_survived.get(sid, 0) + 1

    return {
        "multi_3k": multi_3k,
        "multi_4k": multi_4k,
        "multi_5k": multi_5k,
        "clutch_wins": clutch_wins,
        "trade_kills": trade_kills,
        "trade_deaths": trade_deaths,
        "kast_rounds": kast_rounds,
        "rounds_survived": rounds_survived,
    }


def _get_awpy_demo_class():
    """Lazy import of awpy.Demo to avoid hard dependency at import time."""
    from awpy import Demo

    return Demo


def parse_demo(dem_path: str | Path, _demo_cls=None) -> ParsedDemo:
    """Parse a CS2 .dem file and return structured data.

    Requires awpy>=2.0.0 to be installed.
    """
    dem_path = Path(dem_path)
    if not dem_path.exists():
        raise FileNotFoundError(f"Demo file not found: {dem_path}")

    Demo = _demo_cls or _get_awpy_demo_class()  # noqa: N806

    logger.info("Parsing demo: %s", dem_path.name)
    dem = Demo(str(dem_path))
    dem.parse()

    # --- Header ---
    header = dem.header
    map_name = header.get("map_name", "unknown") if isinstance(header, dict) else "unknown"

    # --- Rounds ---
    rounds_df = dem.rounds
    rounds: list[RoundData] = []
    t_score = 0
    ct_score = 0

    if rounds_df is not None and len(rounds_df) > 0:
        for row in rounds_df.iter_rows(named=True):
            round_num = row.get("round_num", len(rounds) + 1)
            winner = row.get("winner")

            if winner == "T":
                t_score += 1
            elif winner == "CT":
                ct_score += 1

            start_tick = row.get("start")
            end_tick = row.get("end")
            duration = None
            if start_tick is not None and end_tick is not None:
                duration = (end_tick - start_tick) / 64.0

            bomb_plant_tick = row.get("bomb_plant")
            bomb_site = row.get("bomb_site")

            rounds.append(
                RoundData(
                    round_number=round_num,
                    winner_side=winner,
                    win_reason=_classify_win_reason(row.get("reason")),
                    team1_score=t_score,
                    team2_score=ct_score,
                    bomb_planted=bomb_plant_tick is not None and bomb_plant_tick > 0,
                    bomb_defused="defus" in row.get("reason", "").lower()
                    if row.get("reason")
                    else None,
                    plant_site=bomb_site if bomb_site else None,
                    start_tick=start_tick,
                    end_tick=end_tick,
                    duration_seconds=round(duration, 2) if duration else None,
                )
            )

    total_rounds = len(rounds)
    overtime_rounds = max(0, total_rounds - 30) if total_rounds > 30 else 0

    # --- Kills analysis ---
    kills_df = dem.kills
    player_kills: dict[str, int] = {}
    player_deaths: dict[str, int] = {}
    player_assists: dict[str, int] = {}
    player_hs_kills: dict[str, int] = {}
    player_flash_assists: dict[str, int] = {}
    player_first_kills: dict[str, int] = {}
    player_first_deaths: dict[str, int] = {}
    player_names: dict[str, str] = {}
    player_assists_per_round: dict[str, set[int]] = {}
    kill_events: list[_KillEvent] = []

    if kills_df is not None and len(kills_df) > 0:
        seen_rounds: set[int] = set()

        for row in kills_df.iter_rows(named=True):
            killer_sid = str(row.get("steamid", ""))
            victim_sid = str(row.get("victim_steamid", ""))
            killer_name = row.get("name", "")
            victim_name = row.get("victim_name", "")
            round_num = row.get("round_num")
            tick = row.get("tick", 0) or 0

            if killer_sid and killer_sid != "0":
                player_kills[killer_sid] = player_kills.get(killer_sid, 0) + 1
                player_names[killer_sid] = killer_name

                if row.get("headshot", False):
                    player_hs_kills[killer_sid] = player_hs_kills.get(killer_sid, 0) + 1

            if victim_sid and victim_sid != "0":
                player_deaths[victim_sid] = player_deaths.get(victim_sid, 0) + 1
                player_names[victim_sid] = victim_name

            # Assists
            assister_sid = (
                str(row.get("assister_steamid", "")) if row.get("assister_steamid") else ""
            )
            if assister_sid and assister_sid != "0":
                player_assists[assister_sid] = player_assists.get(assister_sid, 0) + 1
                if row.get("assistedflash", False):
                    player_flash_assists[assister_sid] = (
                        player_flash_assists.get(assister_sid, 0) + 1
                    )
                if round_num is not None:
                    player_assists_per_round.setdefault(assister_sid, set()).add(round_num)

            # First kill/death per round
            if round_num is not None and round_num not in seen_rounds:
                seen_rounds.add(round_num)
                if killer_sid and killer_sid != "0":
                    player_first_kills[killer_sid] = player_first_kills.get(killer_sid, 0) + 1
                if victim_sid and victim_sid != "0":
                    player_first_deaths[victim_sid] = player_first_deaths.get(victim_sid, 0) + 1

            # Collect kill events for advanced stats
            if round_num is not None:
                killer_side = row.get("side", "") or ""
                victim_side = row.get("victim_side", "") or ""
                kill_events.append(
                    _KillEvent(
                        tick=tick,
                        round_num=round_num,
                        killer_sid=killer_sid,
                        victim_sid=victim_sid,
                        killer_side=str(killer_side).upper() if killer_side else "",
                        victim_side=str(victim_side).upper() if victim_side else "",
                    )
                )

    # --- Damage analysis ---
    damages_df = dem.damages
    player_damage: dict[str, int] = {}
    player_utility_dmg: dict[str, int] = {}

    if damages_df is not None and len(damages_df) > 0:
        for row in damages_df.iter_rows(named=True):
            attacker_sid = str(row.get("steamid", "") or row.get("attacker_steamid", ""))
            dmg = row.get("dmg_health_real", 0) or 0

            if attacker_sid and attacker_sid != "0" and dmg > 0:
                player_damage[attacker_sid] = player_damage.get(attacker_sid, 0) + dmg
                attacker_name = row.get("attacker_name", "") or row.get("name", "")
                if attacker_name:
                    player_names[attacker_sid] = attacker_name

                weapon = str(row.get("weapon", "")).lower()
                if weapon in (
                    "hegrenade",
                    "molotov",
                    "incgrenade",
                    "inferno",
                    "flashbang",
                    "smokegrenade",
                ):
                    player_utility_dmg[attacker_sid] = player_utility_dmg.get(attacker_sid, 0) + dmg

    # --- Build player list ---
    all_steam_ids = set(player_kills.keys()) | set(player_deaths.keys()) | set(player_damage.keys())

    # Try to determine team sides from ticks data
    player_sides: dict[str, str] = {}
    ticks_df = dem.ticks

    # Also try to extract economy data per round from ticks
    round_economy: dict[int, dict] = {}

    if ticks_df is not None and len(ticks_df) > 0:
        try:
            cols = ticks_df.columns
            if "side" in cols or "team" in cols:
                side_col = "side" if "side" in cols else "team"
                first_round = ticks_df.filter(ticks_df["round_num"] == 1)
                if len(first_round) > 0:
                    for row in first_round.unique(subset=["steamid"]).iter_rows(named=True):
                        sid = str(row.get("steamid", ""))
                        side = row.get(side_col, "")
                        if sid and side:
                            player_sides[sid] = str(side).upper()
        except Exception:
            logger.debug("Could not extract team sides from ticks data")

        # Extract economy data per round
        try:
            cols = ticks_df.columns
            has_economy = "current_equip_value" in cols or "equipment_value" in cols
            side_col = "side" if "side" in cols else ("team" if "team" in cols else None)

            if has_economy and side_col:
                equip_col = (
                    "current_equip_value" if "current_equip_value" in cols else "equipment_value"
                )

                for rnd_num in range(1, total_rounds + 1):
                    rnd_ticks = ticks_df.filter(ticks_df["round_num"] == rnd_num)
                    if len(rnd_ticks) == 0:
                        continue

                    # Get first tick of the round for equipment values
                    first_tick = rnd_ticks.head(10 * 5)  # ~5 ticks for 10 players
                    t_equip = 0
                    ct_equip = 0
                    t_count = 0
                    ct_count = 0

                    seen_players: set[str] = set()
                    for row in first_tick.iter_rows(named=True):
                        sid = str(row.get("steamid", ""))
                        if sid in seen_players:
                            continue
                        seen_players.add(sid)

                        side = str(row.get(side_col, "")).upper()
                        eq = row.get(equip_col, 0) or 0

                        if side == "T":
                            t_equip += eq
                            t_count += 1
                        elif side == "CT":
                            ct_equip += eq
                            ct_count += 1

                    if t_count > 0 or ct_count > 0:
                        round_economy[rnd_num] = {
                            "t_equipment_value": t_equip,
                            "ct_equipment_value": ct_equip,
                            "t_buy_type": _classify_buy_type(t_equip // max(t_count, 1))
                            if t_count
                            else None,
                            "ct_buy_type": _classify_buy_type(ct_equip // max(ct_count, 1))
                            if ct_count
                            else None,
                        }
        except Exception:
            logger.debug("Could not extract economy data from ticks")

    # If player_sides is empty, try to infer from kill events
    if not player_sides:
        for ke in kill_events:
            if ke.killer_sid and ke.killer_sid != "0" and ke.killer_side:
                player_sides.setdefault(ke.killer_sid, ke.killer_side)
            if ke.victim_sid and ke.victim_sid != "0" and ke.victim_side:
                player_sides.setdefault(ke.victim_sid, ke.victim_side)

    # Apply economy data to rounds
    for rd in rounds:
        eco = round_economy.get(rd.round_number)
        if eco:
            rd.t_equipment_value = eco["t_equipment_value"]
            rd.ct_equipment_value = eco["ct_equipment_value"]
            rd.t_buy_type = eco["t_buy_type"]
            rd.ct_buy_type = eco["ct_buy_type"]
        if _is_pistol_round(rd.round_number):
            rd.t_buy_type = "pistol"
            rd.ct_buy_type = "pistol"

    # --- Compute advanced stats ---
    advanced = _compute_advanced_stats(
        kill_events, rounds, player_sides, player_assists_per_round, total_rounds
    )

    players: list[PlayerData] = []
    for sid in all_steam_ids:
        name = player_names.get(sid, f"Player_{sid[-4:]}")
        kills = player_kills.get(sid, 0)
        deaths = player_deaths.get(sid, 0)
        damage = player_damage.get(sid, 0)
        adr = round(damage / total_rounds, 1) if total_rounds > 0 else None

        players.append(
            PlayerData(
                steam_id=sid,
                name=name,
                team_side=player_sides.get(sid),
                kills=kills,
                deaths=deaths,
                assists=player_assists.get(sid, 0),
                headshot_kills=player_hs_kills.get(sid, 0),
                damage=damage,
                adr=adr,
                flash_assists=player_flash_assists.get(sid, 0),
                enemies_flashed=0,
                utility_damage=player_utility_dmg.get(sid, 0),
                first_kills=player_first_kills.get(sid, 0),
                first_deaths=player_first_deaths.get(sid, 0),
                multi_kills_3k=advanced["multi_3k"].get(sid, 0),
                multi_kills_4k=advanced["multi_4k"].get(sid, 0),
                multi_kills_5k=advanced["multi_5k"].get(sid, 0),
                clutch_wins=advanced["clutch_wins"].get(sid, 0),
                trade_kills=advanced["trade_kills"].get(sid, 0),
                trade_deaths=advanced["trade_deaths"].get(sid, 0),
                kast_rounds=advanced["kast_rounds"].get(sid, 0),
                rounds_survived=advanced["rounds_survived"].get(sid, 0),
            )
        )

    # Sort players by kills descending
    players.sort(key=lambda p: p.kills, reverse=True)

    # Estimate total duration
    total_duration = None
    if rounds and rounds[-1].end_tick and rounds[0].start_tick:
        total_duration = round((rounds[-1].end_tick - rounds[0].start_tick) / 64.0, 1)

    return ParsedDemo(
        map_name=map_name,
        tickrate=64,
        duration_seconds=total_duration,
        team1_name=None,
        team2_name=None,
        team1_score=t_score,
        team2_score=ct_score,
        total_rounds=total_rounds,
        overtime_rounds=overtime_rounds,
        rounds=rounds,
        players=players,
    )
