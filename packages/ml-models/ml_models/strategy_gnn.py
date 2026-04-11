"""Strategy GNN heuristic + label vocabulary (self-contained).

This module is intentionally free of any ``src.*`` imports so it stays
loadable from sibling packages whose ``src`` namespace would otherwise
shadow ours. The actual GraphSAGE architecture lives in
``src/models/strategy_gnn.py``; this file only owns the inference helper
that callers (FastAPI router, tactics endpoint) need.
"""

from __future__ import annotations

T_STRATEGIES = [
    "a_execute",
    "b_execute",
    "mid_control_to_a",
    "mid_control_to_b",
    "split_a",
    "split_b",
    "fast_a",
    "fast_b",
    "a_fake_b",
    "b_fake_a",
    "default_spread",
    "slow_default",
    "eco_rush",
    "force_buy_execute",
    "save",
]

CT_STRATEGIES = [
    "standard_2_1_2",
    "stack_a",
    "stack_b",
    "aggressive_mid",
    "aggressive_a",
    "passive_default",
    "retake_setup",
    "anti_eco_push",
    "save",
    "mixed",
]


def _heuristic_t_strategy(round_data: dict) -> tuple[str, float]:
    eco = float(round_data.get("equipment_value", 0) or 0)
    enemy_eco = float(round_data.get("enemy_equipment_value", 0) or 0)
    time_remaining = float(round_data.get("time_remaining", 1.0) or 0)
    bomb_planted = bool(round_data.get("bomb_planted", False))
    bomb_site = (round_data.get("bomb_site") or "").upper()
    avg_x = float(round_data.get("avg_team_x", 0) or 0)
    avg_y = float(round_data.get("avg_team_y", 0) or 0)
    alive = int(round_data.get("alive_team", 5) or 5)

    if eco < 5000:
        if enemy_eco > 15000:
            return "save", 0.85
        return "eco_rush", 0.7

    if eco < 12000:
        return "force_buy_execute", 0.6

    if bomb_planted:
        return ("a_execute" if bomb_site == "A" else "b_execute"), 0.9

    if time_remaining > 0.7:
        return "default_spread", 0.55

    if time_remaining < 0.3 and alive >= 4:
        return ("fast_a" if avg_x >= 0 else "fast_b"), 0.6

    if avg_x > 500:
        return "split_a", 0.5
    if avg_x < -500:
        return "split_b", 0.5
    return ("mid_control_to_a" if avg_y >= 0 else "mid_control_to_b"), 0.5


def _heuristic_ct_strategy(round_data: dict) -> tuple[str, float]:
    eco = float(round_data.get("equipment_value", 0) or 0)
    enemy_eco = float(round_data.get("enemy_equipment_value", 0) or 0)
    time_remaining = float(round_data.get("time_remaining", 1.0) or 0)
    bomb_planted = bool(round_data.get("bomb_planted", False))
    a_count = int(round_data.get("ct_at_a", 0) or 0)
    b_count = int(round_data.get("ct_at_b", 0) or 0)

    if eco < 5000:
        return "save", 0.85

    if enemy_eco < 5000:
        return "anti_eco_push", 0.8

    if bomb_planted:
        return "retake_setup", 0.9

    if a_count >= 3:
        return "stack_a", 0.7
    if b_count >= 3:
        return "stack_b", 0.7

    if time_remaining > 0.8:
        return "aggressive_mid", 0.5

    if time_remaining < 0.25:
        return "passive_default", 0.55

    return "standard_2_1_2", 0.5


def predict_strategy(round_data: dict) -> dict:
    """Predict the team strategy for a round.

    Args:
        round_data: Dict describing the round state. Recognised keys:
            side: "T" | "CT" (default "T")
            equipment_value: total team equipment value
            enemy_equipment_value: opponent team equipment value
            time_remaining: 0..1 fraction of round time left
            bomb_planted: bool
            bomb_site: "A" | "B"
            avg_team_x, avg_team_y: aggregated team coordinates
            alive_team: number of alive teammates
            ct_at_a, ct_at_b: number of CTs holding each site

    Returns:
        ``{"strategy_type": str, "confidence": float, "side": str, "method": str}``
    """
    side = str(round_data.get("side", "T")).upper()
    if side == "CT":
        label, conf = _heuristic_ct_strategy(round_data)
        valid = CT_STRATEGIES
    else:
        label, conf = _heuristic_t_strategy(round_data)
        valid = T_STRATEGIES

    if label not in valid:
        label = valid[0]
        conf = 0.4

    return {
        "strategy_type": label,
        "confidence": float(round(conf, 4)),
        "side": side,
        "method": "heuristic_fallback",
    }


__all__ = ["T_STRATEGIES", "CT_STRATEGIES", "predict_strategy"]
