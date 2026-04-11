"""Win Probability inference service.

Loads the trained win prob v2 LightGBM model and computes win probability
delta for each kill in a parsed demo. Used for:
- Top impact deaths visualization
- Win probability curve per round
- Player impact metrics

The model uses 21 features:
  alive_t, alive_ct, victim_is_t, round_num, score_diff, score_t, score_ct,
  is_overtime, equip_diff, bomb_planted, time_remaining, avg_hp_t, avg_hp_ct,
  + 7 map one-hot
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

MAPS = [
    "de_mirage",
    "de_dust2",
    "de_inferno",
    "de_nuke",
    "de_overpass",
    "de_ancient",
    "de_anubis",
]
MAP_TO_IDX = {m: i for i, m in enumerate(MAPS)}

_loaded_model = None


def _find_win_prob_model() -> Path | None:
    """Find win prob v2 checkpoint."""
    candidates = [
        Path(__file__).parent.parent.parent.parent.parent
        / "data"
        / "checkpoints"
        / "win_prob_v2.lgb",
        Path(__file__).parent.parent.parent.parent / "data" / "checkpoints" / "win_prob_v2.lgb",
        Path("D:/aics2-data/checkpoints/win_prob_v2.lgb"),
        Path.home() / ".cs2-analytics" / "checkpoints" / "win_prob_v2.lgb",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def get_win_prob_model():
    """Load and cache win prob v2 model."""
    global _loaded_model
    if _loaded_model is not None:
        return _loaded_model

    try:
        import lightgbm as lgb
    except ImportError:
        logger.warning("LightGBM not installed, win prob disabled")
        return None

    path = _find_win_prob_model()
    if path is None:
        logger.warning("Win prob v2 model not found")
        return None

    try:
        _loaded_model = lgb.Booster(model_file=str(path))
        logger.info("Loaded win prob v2 model from %s", path)
        return _loaded_model
    except Exception as e:
        logger.warning("Failed to load win prob model: %s", e)
        return None


@dataclass
class WinProbDelta:
    """Computed win probability impact for a single kill."""

    round_number: int
    tick: int
    victim_steam_id: str
    victim_name: str
    victim_side: str
    attacker_steam_id: str | None
    attacker_name: str | None
    prob_before: float
    prob_after: float
    win_delta: float
    alive_t_before: int
    alive_ct_before: int
    bomb_planted: bool
    weapon: str | None
    headshot: bool
    was_traded: bool
    victim_x: float | None
    victim_y: float | None
    victim_z: float | None


def _build_alive_state(raw_ticks: list, round_num: int, tick: int) -> dict:
    """Compute alive players and HP/equipment at a given tick."""
    alive_t = []
    alive_ct = []
    seen = set()
    for t in raw_ticks:
        if t.get("round_num") != round_num:
            continue
        if abs(t.get("tick", 0) - tick) > 32:
            continue
        sid = t.get("steamid")
        if sid in seen:
            continue
        seen.add(sid)
        hp = t.get("health") or 0
        if hp <= 0:
            continue
        info = {
            "hp": hp,
            "equip": t.get("current_equip_value") or 0,
        }
        if t.get("side") == "t":
            alive_t.append(info)
        else:
            alive_ct.append(info)
    return {
        "alive_t": min(len(alive_t), 5),
        "alive_ct": min(len(alive_ct), 5),
        "avg_hp_t": float(np.mean([p["hp"] for p in alive_t])) if alive_t else 0.0,
        "avg_hp_ct": float(np.mean([p["hp"] for p in alive_ct])) if alive_ct else 0.0,
        "total_equip_t": sum(p["equip"] for p in alive_t),
        "total_equip_ct": sum(p["equip"] for p in alive_ct),
    }


def _build_features(
    state: dict,
    victim_side: str,
    round_num: int,
    t_score: int,
    ct_score: int,
    total_rounds: int,
    bomb_planted: bool,
    time_remaining: float,
    map_idx: int,
) -> np.ndarray:
    """Build 21-feature vector matching train_v2.py."""
    equip_diff = (state["total_equip_t"] - state["total_equip_ct"]) / 25000.0
    equip_diff = max(min(equip_diff, 1.0), -1.0)

    map_oh = [0.0] * len(MAPS)
    if map_idx >= 0:
        map_oh[map_idx] = 1.0

    return np.array(
        [
            [
                state["alive_t"] / 5.0,
                state["alive_ct"] / 5.0,
                1.0 if victim_side == "t" else 0.0,
                round_num / 30.0,
                (t_score - ct_score) / max(total_rounds, 1),
                t_score / 16.0,
                ct_score / 16.0,
                1.0 if round_num > 24 else 0.0,
                equip_diff,
                1.0 if bomb_planted else 0.0,
                time_remaining,
                state["avg_hp_t"] / 100.0,
                state["avg_hp_ct"] / 100.0,
            ]
            + map_oh
        ],
        dtype=np.float32,
    )


def compute_win_prob_impacts(parsed) -> list[WinProbDelta]:
    """Compute win probability delta for every kill in a parsed demo.

    Returns list of WinProbDelta entries (one per kill).
    """
    model = get_win_prob_model()
    if model is None:
        logger.info("Win prob model unavailable, skipping impact computation")
        return []

    if not parsed.raw_kills or not parsed.raw_ticks or not parsed.rounds:
        return []

    # Build round outcome and metadata maps
    round_winners: dict[int, str] = {}
    round_bomb_planted: dict[int, bool] = {}
    round_start_ticks: dict[int, int] = {}
    round_end_ticks: dict[int, int] = {}
    for r in parsed.rounds:
        if r.winner_side:
            round_winners[r.round_number] = r.winner_side
        round_bomb_planted[r.round_number] = bool(r.bomb_planted)
        if r.start_tick is not None:
            round_start_ticks[r.round_number] = r.start_tick
        if r.end_tick is not None:
            round_end_ticks[r.round_number] = r.end_tick

    map_name = getattr(parsed, "map_name", None) or "unknown"
    map_idx = MAP_TO_IDX.get(map_name, -1)
    total_rounds = len(parsed.rounds)

    # Compute trades
    kills_sorted = sorted(parsed.raw_kills, key=lambda k: k.get("tick", 0))
    traded_sids: set[str] = set()
    for ki, k1 in enumerate(kills_sorted):
        k1_victim = str(k1.get("victim_steamid", ""))
        k1_tick = k1.get("tick", 0)
        k1_attacker = str(k1.get("attacker_steamid", ""))
        for k2 in kills_sorted[ki + 1 :]:
            if k2.get("tick", 0) - k1_tick > 320:
                break
            if str(k2.get("victim_steamid", "")) == k1_attacker:
                traded_sids.add(k1_victim)
                break

    impacts: list[WinProbDelta] = []
    for kill in parsed.raw_kills:
        round_num = kill.get("round_num", 0)
        kill_tick = kill.get("tick", 0)
        victim_side = kill.get("victim_side", "")
        victim_sid = str(kill.get("victim_steamid", ""))
        if not victim_sid or round_num not in round_winners:
            continue

        state = _build_alive_state(parsed.raw_ticks, round_num, kill_tick - 1)

        t_score = sum(
            1 for r in parsed.rounds if r.round_number < round_num and r.winner_side == "t"
        )
        ct_score = sum(
            1 for r in parsed.rounds if r.round_number < round_num and r.winner_side == "ct"
        )

        start_t = round_start_ticks.get(round_num, kill_tick - 4000)
        end_t = round_end_ticks.get(round_num, kill_tick + 4000)
        time_progress = min((kill_tick - start_t) / max(end_t - start_t, 1), 1.0)
        time_remaining = 1.0 - time_progress

        bomb_planted = round_bomb_planted.get(round_num, False)

        feat_before = _build_features(
            state,
            victim_side,
            round_num,
            t_score,
            ct_score,
            total_rounds,
            bomb_planted,
            time_remaining,
            map_idx,
        )
        prob_before = float(model.predict(feat_before)[0])

        # State after death
        state_after = dict(state)
        if victim_side == "t":
            state_after["alive_t"] = max(state["alive_t"] - 1, 0)
        else:
            state_after["alive_ct"] = max(state["alive_ct"] - 1, 0)

        feat_after = _build_features(
            state_after,
            victim_side,
            round_num,
            t_score,
            ct_score,
            total_rounds,
            bomb_planted,
            time_remaining,
            map_idx,
        )
        prob_after = float(model.predict(feat_after)[0])

        # Delta from victim's team perspective (positive = bad for victim)
        if victim_side == "t":
            win_delta = prob_before - prob_after
        else:
            win_delta = (1.0 - prob_before) - (1.0 - prob_after)

        impacts.append(
            WinProbDelta(
                round_number=round_num,
                tick=kill_tick,
                victim_steam_id=victim_sid,
                victim_name=str(kill.get("victim_name") or "Unknown"),
                victim_side=victim_side,
                attacker_steam_id=str(kill.get("attacker_steamid") or "") or None,
                attacker_name=str(kill.get("attacker_name") or "") or None,
                prob_before=prob_before,
                prob_after=prob_after,
                win_delta=float(win_delta),
                alive_t_before=state["alive_t"],
                alive_ct_before=state["alive_ct"],
                bomb_planted=bomb_planted,
                weapon=kill.get("weapon"),
                headshot=bool(kill.get("headshot")),
                was_traded=victim_sid in traded_sids,
                victim_x=kill.get("victim_X"),
                victim_y=kill.get("victim_Y"),
                victim_z=kill.get("victim_Z"),
            )
        )

    logger.info("Computed win prob impact for %d kills", len(impacts))
    return impacts
