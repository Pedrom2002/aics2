"""
ML Feature Extractor — Extracts features for ML model inference from parsed demo data.

Produces:
  - 64-tick windows (18 features) for positioning model
  - Grenade event features (25 features) for utility model
  - Heuristic pseudo-labels for positioning errors
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class TickSnapshot:
    """Per-tick game state for a single player."""

    tick: int
    round_number: int
    player_steam_id: str
    pos_x: float = 0.0
    pos_y: float = 0.0
    pos_z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    velocity: float = 0.0
    health: int = 100
    armor: int = 0
    weapon_id: int = 0
    is_scoped: bool = False
    teammates_alive: int = 4
    enemies_alive: int = 5
    bomb_state: int = 0  # 0=not_planted, 1=planted, 2=defusing
    round_time_remaining: float = 115.0
    nearest_teammate_dist: float = 0.0
    nearest_enemy_dist_est: float = 0.0
    angles_exposed_count: int = 0
    distance_to_nearest_cover: float = 0.0
    side: str = "T"
    is_alive: bool = True


@dataclass
class GrenadeEvent:
    """A single grenade usage event."""

    tick: int
    round_number: int
    player_steam_id: str
    grenade_type: str  # smoke, flash, he, molotov
    throw_x: float = 0.0
    throw_y: float = 0.0
    throw_z: float = 0.0
    land_x: float = 0.0
    land_y: float = 0.0
    land_z: float = 0.0
    # Outcomes (filled post-event)
    enemies_flashed_count: int = 0
    flash_duration_avg: float = 0.0
    smoke_blocks_los_count: int = 0
    molly_damage_dealt: float = 0.0
    he_damage_dealt: float = 0.0
    # Context
    round_time_remaining: float = 115.0
    time_since_round_start: float = 0.0
    score_diff: int = 0
    teammates_alive: int = 4
    enemies_alive: int = 5
    buy_type: int = 3  # 0=eco, 1=force, 2=semi, 3=full
    was_round_won: bool = False
    map_name: str = ""


@dataclass
class PlayerDeathEvent:
    """Records when/where a player died for labeling."""

    tick: int
    round_number: int
    player_steam_id: str
    pos_x: float
    pos_y: float
    pos_z: float
    angles_exposed: int
    distance_to_cover: float
    had_teammate_nearby: bool
    was_traded: bool


@dataclass
class PositioningWindow:
    """A 64-tick window of features for the positioning model."""

    features: np.ndarray  # (64, 18)
    player_steam_id: str
    round_number: int
    center_tick: int
    label: int | None = None  # 0=no_error, 1=minor, 2=critical (None if unlabeled)
    death_event: PlayerDeathEvent | None = None


@dataclass
class UtilityFeatureVector:
    """25-feature vector for the utility model."""

    features: np.ndarray  # (25,)
    player_steam_id: str
    round_number: int
    grenade_type: str
    label: int | None = None  # 0=effective, 1=suboptimal, 2=wasted, 3=harmful


# ---------- POSITIONING FEATURE EXTRACTION ----------


def extract_positioning_windows(
    ticks: list[TickSnapshot],
    death_events: list[PlayerDeathEvent],
    window_size: int = 64,
    stride: int = 32,
) -> list[PositioningWindow]:
    """Extract 64-tick windows from tick data for the positioning model.

    Windows are centered around death events (for labeled data) and
    sampled with stride for general inference.
    """
    if not ticks:
        return []

    # Group ticks by player
    player_ticks: dict[str, list[TickSnapshot]] = {}
    for t in ticks:
        if t.is_alive:
            player_ticks.setdefault(t.player_steam_id, []).append(t)

    windows: list[PositioningWindow] = []

    for player_id, pticks in player_ticks.items():
        pticks.sort(key=lambda t: t.tick)

        # Extract windows with stride
        for start in range(0, max(1, len(pticks) - window_size + 1), stride):
            end = start + window_size
            if end > len(pticks):
                break

            window_ticks = pticks[start:end]
            features = _ticks_to_features(window_ticks)
            center_tick = window_ticks[window_size // 2].tick

            windows.append(
                PositioningWindow(
                    features=features,
                    player_steam_id=player_id,
                    round_number=window_ticks[0].round_number,
                    center_tick=center_tick,
                )
            )

    # Label windows that overlap with death events
    _apply_heuristic_labels(windows, death_events)

    return windows


def _ticks_to_features(ticks: list[TickSnapshot]) -> np.ndarray:
    """Convert a list of TickSnapshots to an (N, 18) feature array."""
    features = np.zeros((len(ticks), 18), dtype=np.float32)
    for i, t in enumerate(ticks):
        features[i] = [
            t.pos_x / 1000.0,  # normalize positions
            t.pos_y / 1000.0,
            t.pos_z / 100.0,
            t.yaw / 360.0,  # normalize angle
            t.pitch / 90.0,
            t.velocity / 250.0,  # normalize by max run speed
            t.health / 100.0,
            t.armor / 100.0,
            t.weapon_id / 50.0,  # rough normalize
            float(t.is_scoped),
            t.teammates_alive / 4.0,
            t.enemies_alive / 5.0,
            t.bomb_state / 2.0,
            t.round_time_remaining / 115.0,
            min(t.nearest_teammate_dist, 2000.0) / 2000.0,
            min(t.nearest_enemy_dist_est, 3000.0) / 3000.0,
            min(t.angles_exposed_count, 5) / 5.0,
            min(t.distance_to_nearest_cover, 500.0) / 500.0,
        ]
    return features


# ---------- HEURISTIC LABELING ----------


COVER_DIST_THRESHOLD = 200.0  # units — if farther, possibly bad position
ANGLES_EXPOSED_MINOR = 2
ANGLES_EXPOSED_CRITICAL = 3


def _apply_heuristic_labels(
    windows: list[PositioningWindow],
    death_events: list[PlayerDeathEvent],
) -> None:
    """Apply heuristic pseudo-labels to windows overlapping death events.

    Labeling rules:
      - Player died AND angles_exposed >= 3 AND cover_dist > threshold → critical (2)
      - Player died AND angles_exposed >= 2 AND no trade → minor (1)
      - All other windows → no_error (0) by default
    """
    # Index deaths by (player, round)
    death_map: dict[tuple[str, int], PlayerDeathEvent] = {}
    for d in death_events:
        death_map[(d.player_steam_id, d.round_number)] = d

    for w in windows:
        key = (w.player_steam_id, w.round_number)
        death = death_map.get(key)

        if death is None:
            w.label = 0  # no death in this round → no error
            continue

        # Check if the window's center tick is close to the death tick
        if abs(w.center_tick - death.tick) > 128:  # 2 seconds
            w.label = 0
            continue

        w.death_event = death

        if (
            death.angles_exposed >= ANGLES_EXPOSED_CRITICAL
            and death.distance_to_cover > COVER_DIST_THRESHOLD
        ):
            w.label = 2  # critical
        elif death.angles_exposed >= ANGLES_EXPOSED_MINOR and not death.was_traded:
            w.label = 1  # minor
        else:
            w.label = 0  # death happened but position was ok


def label_positioning_from_parsed_data(
    kills_df_rows: list[dict],
    ticks_df_rows: list[dict],
    trade_kill_sids: set[str],
    total_rounds: int,
) -> list[PlayerDeathEvent]:
    """Generate PlayerDeathEvents from parsed demo data for heuristic labeling.

    This uses available tick data to estimate angles_exposed and distance_to_cover.
    When tick data is limited, applies conservative heuristics.
    """
    death_events: list[PlayerDeathEvent] = []

    for kill in kills_df_rows:
        victim_sid = kill.get("victim_steam_id") or kill.get("victim_steamid", "")
        if not victim_sid:
            continue

        death_tick = kill.get("tick", 0)
        round_num = kill.get("round", 0)

        # Find victim position from tick data around the death
        pos_x, pos_y, pos_z = 0.0, 0.0, 0.0
        angles_exposed = 1  # default conservative
        distance_to_cover = 100.0  # default

        # Look for victim tick data
        for tick_row in ticks_df_rows:
            if (
                tick_row.get("steamid", "") == victim_sid
                and abs(tick_row.get("tick", 0) - death_tick) < 64
            ):
                pos_x = tick_row.get("X", tick_row.get("x", 0.0))
                pos_y = tick_row.get("Y", tick_row.get("y", 0.0))
                pos_z = tick_row.get("Z", tick_row.get("z", 0.0))
                break

        # Count nearby enemies as proxy for angles_exposed
        enemy_count = 0
        for tick_row in ticks_df_rows:
            if (
                tick_row.get("steamid", "") != victim_sid
                and tick_row.get("team_name", "") != kill.get("victim_team", "")
                and abs(tick_row.get("tick", 0) - death_tick) < 32
            ):
                ex = tick_row.get("X", tick_row.get("x", 0.0))
                ey = tick_row.get("Y", tick_row.get("y", 0.0))
                dist = math.sqrt((pos_x - ex) ** 2 + (pos_y - ey) ** 2)
                if dist < 2000:  # within engagement range
                    enemy_count += 1

        if enemy_count > 0:
            angles_exposed = min(enemy_count, 5)

        # Check if victim was traded
        was_traded = victim_sid in trade_kill_sids

        # Check if teammate was nearby
        had_teammate_nearby = False
        for tick_row in ticks_df_rows:
            if (
                tick_row.get("steamid", "") != victim_sid
                and tick_row.get("team_name", "") == kill.get("victim_team", "")
                and abs(tick_row.get("tick", 0) - death_tick) < 32
            ):
                tx = tick_row.get("X", tick_row.get("x", 0.0))
                ty = tick_row.get("Y", tick_row.get("y", 0.0))
                dist = math.sqrt((pos_x - tx) ** 2 + (pos_y - ty) ** 2)
                if dist < 800:  # trade range
                    had_teammate_nearby = True
                    break

        death_events.append(
            PlayerDeathEvent(
                tick=death_tick,
                round_number=round_num,
                player_steam_id=victim_sid,
                pos_x=pos_x,
                pos_y=pos_y,
                pos_z=pos_z,
                angles_exposed=angles_exposed,
                distance_to_cover=distance_to_cover,
                had_teammate_nearby=had_teammate_nearby,
                was_traded=was_traded,
            )
        )

    return death_events


# ---------- UTILITY FEATURE EXTRACTION ----------

MAP_IDS = {
    "de_mirage": 0,
    "de_dust2": 1,
    "de_inferno": 2,
    "de_nuke": 3,
    "de_overpass": 4,
    "de_ancient": 5,
    "de_anubis": 6,
    "de_vertigo": 7,
}


def extract_utility_features(events: list[GrenadeEvent]) -> list[UtilityFeatureVector]:
    """Convert grenade events into feature vectors for the utility model."""
    vectors: list[UtilityFeatureVector] = []

    for event in events:
        grenade_one_hot = [0.0, 0.0, 0.0, 0.0]
        type_map = {"smoke": 0, "flash": 1, "he": 2, "molotov": 3, "incendiary": 3}
        idx = type_map.get(event.grenade_type, 0)
        grenade_one_hot[idx] = 1.0

        map_id = MAP_IDS.get(event.map_name, 0) / 7.0

        # Phase classification
        if event.time_since_round_start < 15:
            phase = 0  # early
        elif event.time_since_round_start < 45:
            phase = 1  # mid
        elif event.round_time_remaining > 0:
            phase = 2  # late
        else:
            phase = 3  # post-plant

        features = np.array(
            [
                # Grenade context (5)
                grenade_one_hot[0],
                grenade_one_hot[1],
                grenade_one_hot[2],
                grenade_one_hot[3],
                map_id,
                # Position (7)
                event.throw_x / 1000.0,
                event.throw_y / 1000.0,
                event.throw_z / 100.0,
                event.land_x / 1000.0,
                event.land_y / 1000.0,
                event.land_z / 100.0,
                0.0,  # distance_to_pro_lineup (placeholder, needs lineup DB)
                # Timing (3)
                event.round_time_remaining / 115.0,
                event.time_since_round_start / 115.0,
                phase / 3.0,
                # Round context (4)
                max(-5, min(5, event.score_diff)) / 5.0,
                event.teammates_alive / 4.0,
                event.enemies_alive / 5.0,
                event.buy_type / 3.0,
                # Outcome (5)
                min(event.enemies_flashed_count, 5) / 5.0,
                min(event.flash_duration_avg, 5.0) / 5.0,
                min(event.smoke_blocks_los_count, 3) / 3.0,
                min(event.molly_damage_dealt, 200.0) / 200.0,
                min(event.he_damage_dealt, 100.0) / 100.0,
                # Result (1)
                float(event.was_round_won),
            ],
            dtype=np.float32,
        )

        # Heuristic label
        label = _heuristic_utility_label(event)

        vectors.append(
            UtilityFeatureVector(
                features=features,
                player_steam_id=event.player_steam_id,
                round_number=event.round_number,
                grenade_type=event.grenade_type,
                label=label,
            )
        )

    return vectors


def _heuristic_utility_label(event: GrenadeEvent) -> int:
    """Heuristic labeling for utility usage."""
    if event.grenade_type == "flash":
        if event.enemies_flashed_count >= 2:
            return 0  # effective
        elif event.enemies_flashed_count == 1:
            return 1  # suboptimal (could flash more)
        else:
            return 2  # wasted (no one flashed)

    elif event.grenade_type == "smoke":
        if event.smoke_blocks_los_count >= 1:
            return 0  # effective
        else:
            return 2  # wasted

    elif event.grenade_type in ("he", "molotov", "incendiary"):
        damage = event.he_damage_dealt + event.molly_damage_dealt
        if damage >= 30:
            return 0  # effective
        elif damage > 0:
            return 1  # suboptimal
        else:
            return 2  # wasted

    return 1  # default suboptimal
