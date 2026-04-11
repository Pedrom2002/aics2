"""Tests for the explainability API + strategy_gnn predict_strategy helper."""

from __future__ import annotations

import pytest

from src.explainability.api import explain_prediction
from src.models.strategy_gnn import T_STRATEGIES, CT_STRATEGIES, predict_strategy


# ---------------------------------------------------------------------------
# explain_prediction
# ---------------------------------------------------------------------------


def _win_prob_sample() -> dict:
    return {
        "alive_t": 4,
        "alive_ct": 5,
        "victim_is_t": 0,
        "round_num": 12,
        "score_diff": 0.1,
        "score_t": 0.4,
        "score_ct": 0.3,
        "is_overtime": 0,
        "equip_diff": 0.05,
        "bomb_planted": 0,
        "time_remaining": 0.6,
        "avg_hp_t": 0.85,
        "avg_hp_ct": 0.9,
        "map_de_mirage": 1,
        "map_de_dust2": 0,
        "map_de_inferno": 0,
        "map_de_nuke": 0,
        "map_de_overpass": 0,
        "map_de_ancient": 0,
        "map_de_anubis": 0,
    }


def _player_rating_sample() -> dict:
    return {
        "kpr": 0.8,
        "dpr": 0.6,
        "apr": 0.2,
        "kd": 1.33,
        "hs_pct": 55.0,
        "kast": 75.0,
        "survival": 35.0,
        "opening_kr": 0.12,
        "opening_dr": 0.10,
        "trade_kr": 0.15,
        "trade_dr": 0.08,
        "multi_3k_r": 0.05,
        "multi_4k_r": 0.01,
        "multi_5k_r": 0.0,
        "clutch_r": 0.04,
        "flash_r": 0.10,
        "util_dmg_r": 4.5,
        "adr": 78.0,
        "impact": 0.9,
        "kills": 22,
        "deaths": 16,
        "assists": 6,
        "headshot_kills": 12,
        "first_kills": 3,
        "first_deaths": 2,
        "trade_kills": 4,
        "trade_deaths": 2,
        "kast_rounds": 18,
        "rounds_survived": 8,
        "total_rounds": 24,
    }


def test_explain_win_prob_returns_expected_shape():
    result = explain_prediction("win_prob", _win_prob_sample())
    assert result["model"] == "win_prob"
    assert "version" in result
    assert "base_value" in result
    assert "prediction" in result
    assert "shap_values" in result
    assert "method" in result
    assert isinstance(result["shap_values"], list)
    # registry win_prob entry has 13 numeric features + 7 map one-hots = 20
    assert len(result["shap_values"]) == 20
    for item in result["shap_values"]:
        assert "feature" in item
        assert "value" in item
        assert "contribution" in item


def test_explain_win_prob_prediction_in_unit_range():
    result = explain_prediction("win_prob", _win_prob_sample())
    pred = result["prediction"]
    assert 0.0 <= pred <= 1.0


def test_explain_player_rating_returns_expected_shape():
    result = explain_prediction("player_rating", _player_rating_sample())
    assert result["model"] == "player_rating"
    assert isinstance(result["shap_values"], list)
    assert len(result["shap_values"]) == 30  # registry has 30 features
    assert isinstance(result["prediction"], float)


def test_explain_unknown_model_raises():
    with pytest.raises(ValueError):
        explain_prediction("not_a_model", {})


def test_explain_top_feature_first():
    result = explain_prediction("win_prob", _win_prob_sample())
    abs_contribs = [abs(c["contribution"]) for c in result["shap_values"]]
    # sorted descending
    assert abs_contribs == sorted(abs_contribs, reverse=True)


def test_explain_missing_features_default_to_zero():
    """Missing keys should not raise; they default to 0."""
    result = explain_prediction("win_prob", {"alive_t": 5})
    assert len(result["shap_values"]) == 20


# ---------------------------------------------------------------------------
# predict_strategy heuristic
# ---------------------------------------------------------------------------


def test_predict_strategy_t_eco_save():
    out = predict_strategy({
        "side": "T",
        "equipment_value": 1500,
        "enemy_equipment_value": 22000,
        "time_remaining": 0.9,
    })
    assert out["strategy_type"] == "save"
    assert out["confidence"] > 0
    assert out["side"] == "T"
    assert out["strategy_type"] in T_STRATEGIES


def test_predict_strategy_t_force_buy():
    out = predict_strategy({
        "side": "T",
        "equipment_value": 8000,
        "enemy_equipment_value": 16000,
        "time_remaining": 0.8,
    })
    assert out["strategy_type"] == "force_buy_execute"


def test_predict_strategy_t_post_plant():
    out = predict_strategy({
        "side": "T",
        "equipment_value": 20000,
        "enemy_equipment_value": 18000,
        "bomb_planted": True,
        "bomb_site": "A",
    })
    assert out["strategy_type"] == "a_execute"


def test_predict_strategy_ct_retake():
    out = predict_strategy({
        "side": "CT",
        "equipment_value": 18000,
        "enemy_equipment_value": 18000,
        "bomb_planted": True,
    })
    assert out["strategy_type"] == "retake_setup"
    assert out["side"] == "CT"
    assert out["strategy_type"] in CT_STRATEGIES


def test_predict_strategy_ct_anti_eco():
    out = predict_strategy({
        "side": "CT",
        "equipment_value": 22000,
        "enemy_equipment_value": 2000,
        "time_remaining": 0.95,
    })
    assert out["strategy_type"] == "anti_eco_push"


def test_predict_strategy_returns_valid_label_always():
    """Even with empty input, the function returns a valid label."""
    out = predict_strategy({})
    assert out["strategy_type"] in T_STRATEGIES
    assert "confidence" in out
    assert 0.0 <= out["confidence"] <= 1.0


def test_predict_strategy_namespace_export():
    """The ml_models.strategy_gnn alias must expose predict_strategy."""
    from ml_models.strategy_gnn import predict_strategy as ns_predict

    out = ns_predict({"side": "T", "equipment_value": 0})
    assert out["strategy_type"] in T_STRATEGIES
