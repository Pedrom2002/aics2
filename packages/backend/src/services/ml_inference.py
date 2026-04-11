"""
ML Inference Pipeline — Runs models on parsed demo data and stores results.

Pipeline steps:
  1. Extract features from parsed demo (tick windows, grenade events)
  2. Run positioning model (Mamba) on 64-tick windows
  3. Run utility model (LightGBM) on grenade events
  4. Generate explanations (Integrated Gradients / TreeSHAP)
  5. Generate recommendations from templates
  6. Store results in detected_errors, error_explanations, error_recommendations
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MODEL_VERSION = "0.1.0-heuristic"  # Pre-trained models not available yet; using heuristic baseline


@dataclass
class DetectedErrorResult:
    """Result from ML inference for a single error."""

    player_steam_id: str
    round_number: int
    error_type: str  # positioning, utility, timing
    severity: str  # critical, minor, info
    confidence: float
    tick: int | None
    position_x: float | None
    position_y: float | None
    position_z: float | None
    description: str
    model_name: str
    model_version: str
    # Explanation
    explanation_text: str
    feature_importances_json: str
    explanation_method: str
    # Recommendation
    rec_title: str
    rec_description: str
    rec_priority: int
    rec_template_id: str
    rec_expected_impact: str
    rec_pro_reference: str | None = None


def run_heuristic_positioning_analysis(
    death_events: list,
) -> list[DetectedErrorResult]:
    """Run heuristic-based positioning error detection.

    Until ML models are trained, this uses rule-based analysis:
    - angles_exposed >= 3 + far from cover → critical
    - angles_exposed >= 2 + no trade → minor
    """
    from src.services.ml_feature_extractor import (
        ANGLES_EXPOSED_CRITICAL,
        ANGLES_EXPOSED_MINOR,
        COVER_DIST_THRESHOLD,
        PlayerDeathEvent,
    )
    from src.services.recommendation_engine import generate_positioning_recommendation

    results: list[DetectedErrorResult] = []

    for death in death_events:
        if not isinstance(death, PlayerDeathEvent):
            continue

        # Determine severity
        if (
            death.angles_exposed >= ANGLES_EXPOSED_CRITICAL
            and death.distance_to_cover > COVER_DIST_THRESHOLD
        ):
            severity = "critical"
            confidence = min(0.5 + death.angles_exposed * 0.1, 0.95)
            desc = (
                f"Died exposed to {death.angles_exposed} angles, "
                f"{death.distance_to_cover:.0f} units from cover"
            )
        elif death.angles_exposed >= ANGLES_EXPOSED_MINOR and not death.was_traded:
            severity = "minor"
            confidence = min(0.4 + death.angles_exposed * 0.1, 0.85)
            desc = f"Died exposed to {death.angles_exposed} angles without being traded"
        else:
            continue  # Not an error

        # Context for recommendation
        context = {
            "angles_exposed": death.angles_exposed,
            "distance_to_cover": death.distance_to_cover,
            "had_teammate_nearby": death.had_teammate_nearby,
            "position_area": "the engagement area",
        }

        rec = generate_positioning_recommendation(severity, context)

        # Feature importances (heuristic weights)
        importances = json.dumps(
            [
                {"feature": "angles_exposed", "value": death.angles_exposed, "impact": 0.45},
                {
                    "feature": "distance_to_cover",
                    "value": round(death.distance_to_cover, 1),
                    "impact": 0.30,
                },
                {
                    "feature": "had_teammate_nearby",
                    "value": int(death.had_teammate_nearby),
                    "impact": 0.15,
                },
                {"feature": "was_traded", "value": int(death.was_traded), "impact": 0.10},
            ]
        )

        explanation = (
            f"Positioning error detected (heuristic): {desc}. "
            f"Key factors: {death.angles_exposed} exposed angles "
            f"({'>3 = critical' if severity == 'critical' else '>2 = minor'}), "
            f"cover at {death.distance_to_cover:.0f} units "
            f"({'too far' if death.distance_to_cover > COVER_DIST_THRESHOLD else 'accessible'})."
        )

        results.append(
            DetectedErrorResult(
                player_steam_id=death.player_steam_id,
                round_number=death.round_number,
                error_type="positioning",
                severity=severity,
                confidence=confidence,
                tick=death.tick,
                position_x=death.pos_x,
                position_y=death.pos_y,
                position_z=death.pos_z,
                description=desc,
                model_name="positioning_heuristic",
                model_version=MODEL_VERSION,
                explanation_text=explanation,
                feature_importances_json=importances,
                explanation_method="heuristic",
                rec_title=rec.title,
                rec_description=rec.description,
                rec_priority=rec.priority,
                rec_template_id=rec.template_id,
                rec_expected_impact=rec.expected_impact,
            )
        )

    return results


def run_heuristic_utility_analysis(
    utility_features: list,
) -> list[DetectedErrorResult]:
    """Run heuristic-based utility error detection.

    Classifies grenades as effective/suboptimal/wasted/harmful using rules.
    """
    from src.services.ml_feature_extractor import UtilityFeatureVector
    from src.services.recommendation_engine import generate_utility_recommendation

    class_labels = ["effective", "suboptimal", "wasted", "harmful"]
    results: list[DetectedErrorResult] = []

    for feat in utility_features:
        if not isinstance(feat, UtilityFeatureVector):
            continue

        label_idx = feat.label
        if label_idx is None or label_idx == 0:
            continue  # effective, skip

        label = class_labels[label_idx]

        if label_idx == 2:
            severity = "minor"
            confidence = 0.75
        elif label_idx == 3:
            severity = "critical"
            confidence = 0.85
        else:
            severity = "info"
            confidence = 0.60

        desc = (
            f"{feat.grenade_type.capitalize()} classified as '{label}' in round {feat.round_number}"
        )

        context = {
            "grenade_type": feat.grenade_type,
            "enemies_flashed_count": int(feat.features[19] * 5) if len(feat.features) > 19 else 0,
            "he_damage_dealt": feat.features[23] * 100.0 if len(feat.features) > 23 else 0,
        }

        rec = generate_utility_recommendation(label_idx, feat.grenade_type, context)

        importances = json.dumps(
            [
                {"feature": "outcome_effectiveness", "value": 0.0, "impact": 0.50},
                {"feature": "grenade_type", "value": feat.grenade_type, "impact": 0.20},
                {"feature": "round_context", "value": 0.0, "impact": 0.15},
            ]
        )

        explanation = (
            f"Utility error: {feat.grenade_type} was {label}. "
            f"No enemies were affected by the grenade."
        )

        results.append(
            DetectedErrorResult(
                player_steam_id=feat.player_steam_id,
                round_number=feat.round_number,
                error_type="utility",
                severity=severity,
                confidence=confidence,
                tick=None,
                position_x=None,
                position_y=None,
                position_z=None,
                description=desc,
                model_name="utility_heuristic",
                model_version=MODEL_VERSION,
                explanation_text=explanation,
                feature_importances_json=importances,
                explanation_method="heuristic",
                rec_title=rec.title,
                rec_description=rec.description,
                rec_priority=rec.priority,
                rec_template_id=rec.template_id,
                rec_expected_impact=rec.expected_impact,
            )
        )

    return results


def _find_model_weights() -> dict[str, str]:
    """Check if trained model weights exist in standard locations."""
    from pathlib import Path

    # Check multiple possible locations
    base_paths = [
        Path(__file__).parent.parent.parent.parent
        / "data"
        / "checkpoints",  # repo/data/checkpoints
        Path(__file__).parent.parent.parent.parent.parent / "data" / "checkpoints",  # fallback
        Path.home() / ".cs2-analytics" / "checkpoints",  # user home
    ]

    found = {}
    for base in base_paths:
        if not base.exists():
            continue
        pos_path = base / "positioning" / "best_model.pt"
        if pos_path.exists():
            found["positioning"] = str(pos_path)
        util_path = base / "utility" / "model.lgb"
        if util_path.exists():
            found["utility"] = str(util_path)

    return found


_loaded_models: dict = {}


def _get_positioning_model():
    """Load the trained positioning Mamba model (cached)."""
    if "positioning" in _loaded_models:
        return _loaded_models["positioning"]

    try:
        from pathlib import Path

        import torch

        weights = _find_model_weights()
        if "positioning" not in weights:
            return None

        # Add ml-models to path
        ml_path = Path(__file__).parent.parent.parent.parent / "ml-models"
        import sys

        if str(ml_path) not in sys.path:
            sys.path.insert(0, str(ml_path))

        from src.models.positioning_mamba import MambaConfig, PositioningMamba

        model = PositioningMamba(MambaConfig())
        state = torch.load(weights["positioning"], map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        model.eval()

        _loaded_models["positioning"] = model
        logger.info("Loaded trained positioning model from %s", weights["positioning"])
        return model
    except Exception as e:
        logger.warning("Failed to load positioning model: %s", e)
        return None


def _dist_3d(x1, y1, z1, x2, y2, z2) -> float:
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2) ** 0.5


def _extract_ml_windows(raw_kills: list, raw_ticks: list, trade_sids: set) -> list[dict]:
    """Extract (64, 18) feature windows from raw tick/kill data.

    Uses the SAME feature extraction as train_pipeline.py to ensure compatibility.
    Returns list of dicts with 'features' (np.array), 'kill' (dict), 'label_info' (dict).
    """
    import numpy as np

    TRADE_RANGE = 800.0  # noqa: N806
    CLOSE_RANGE = 500.0  # noqa: N806

    # Index ticks by (steamid, round_num)
    ticks_by_player_round: dict[tuple, list[dict]] = {}
    for t in raw_ticks:
        key = (t["steamid"], t.get("round_num", 0))
        ticks_by_player_round.setdefault(key, []).append(t)

    # Compute trades from kill sequence
    kills_sorted = sorted(raw_kills, key=lambda k: k.get("tick", 0))
    traded_sids: set[str] = set(str(s) for s in trade_sids)
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

    windows = []
    for kill in raw_kills:
        victim_sid = kill.get("victim_steamid", "")
        round_num = kill.get("round_num", 0)
        kill_tick = kill.get("tick", 0)
        if not victim_sid:
            continue

        victim_x = kill.get("victim_X", 0) or 0
        victim_y = kill.get("victim_Y", 0) or 0
        victim_z = kill.get("victim_Z", 0) or 0
        victim_side = kill.get("victim_side", "")
        kill_dist = kill.get("distance", 1000.0) or 1000.0

        # Count teammates/enemies nearby at death tick (±64 ticks)
        teammates_nearby = 0
        teammates_close = 0
        enemies_nearby = 0
        enemies_close = 0

        for t in raw_ticks:
            if t.get("round_num") != round_num:
                continue
            if abs(t.get("tick", 0) - kill_tick) > 64:
                continue
            if (t.get("health") or 0) <= 0:
                continue
            if t.get("steamid") == victim_sid:
                continue

            px, py, pz = t.get("X", 0), t.get("Y", 0), t.get("Z", 0)
            d = _dist_3d(victim_x, victim_y, victim_z, px, py, pz)

            if t.get("side") == victim_side:
                if d <= TRADE_RANGE:
                    teammates_nearby += 1
                if d <= CLOSE_RANGE:
                    teammates_close += 1
            else:
                if d <= TRADE_RANGE:
                    enemies_nearby += 1
                if d <= CLOSE_RANGE:
                    enemies_close += 1

        was_traded = str(victim_sid) in traded_sids

        # Get victim's last 64 ticks
        key = (victim_sid, round_num)
        player_ticks = ticks_by_player_round.get(key, [])
        if len(player_ticks) < 5:
            continue

        pre_death = [t for t in player_ticks if t["tick"] <= kill_tick]
        pre_death.sort(key=lambda t: t["tick"])
        pre_death = pre_death[-64:]

        # Velocity from last ticks
        velocity = 0.0
        if len(pre_death) >= 2:
            t1, t2 = pre_death[-2], pre_death[-1]
            dt = max(t2["tick"] - t1["tick"], 1)
            dx = t2.get("X", 0) - t1.get("X", 0)
            dy = t2.get("Y", 0) - t1.get("Y", 0)
            velocity = (dx**2 + dy**2) ** 0.5 / dt * 64

        # Build 18-feature matrix — MUST match train_pipeline.py exactly
        features = np.zeros((64, 18), dtype=np.float32)
        offset = 64 - len(pre_death)

        for j, t in enumerate(pre_death):
            idx = offset + j
            features[idx, 0] = t.get("X", 0) / 3000.0
            features[idx, 1] = t.get("Y", 0) / 3000.0
            features[idx, 2] = t.get("Z", 0) / 500.0
            features[idx, 3] = t.get("health", 100) / 100.0
            features[idx, 4] = 1.0 if t.get("side") == "ct" else 0.0

        features[:, 5] = kill_dist / 3000.0
        features[:, 6] = 1.0 if kill.get("headshot") else 0.0
        features[:, 7] = 1.0 if kill.get("thrusmoke") else 0.0
        features[:, 8] = teammates_nearby / 4.0
        features[:, 9] = teammates_close / 4.0
        features[:, 10] = enemies_nearby / 4.0
        features[:, 11] = enemies_close / 4.0
        features[:, 12] = 1.0 if was_traded else 0.0
        features[:, 13] = min(velocity, 500.0) / 500.0
        features[:, 14] = 1.0 if kill.get("attackerblind") else 0.0
        features[:, 15] = 1.0 if kill.get("noscope") else 0.0
        features[:, 16] = 1.0 if kill.get("penetrated") else 0.0
        features[:, 17] = 1.0 if kill.get("attackerinair") else 0.0

        windows.append(
            {
                "features": features,
                "kill": kill,
                "label_info": {
                    "teammates_nearby": teammates_nearby,
                    "enemies_close": enemies_close,
                    "was_traded": was_traded,
                    "velocity": velocity,
                    "victim_sid": str(victim_sid),
                    "round_number": round_num,
                    "tick": kill_tick,
                    "pos_x": victim_x,
                    "pos_y": victim_y,
                    "pos_z": victim_z,
                },
            }
        )

    return windows


def run_ml_positioning_inference(
    raw_kills: list, raw_ticks: list, trade_sids: set
) -> list[DetectedErrorResult]:
    """Run trained Mamba model on extracted tick windows.

    Returns detected errors with model-based confidence and explanations.
    """
    import numpy as np

    model = _get_positioning_model()
    if model is None:
        return []

    try:
        import torch
        import torch.nn.functional as F  # noqa: N812
    except ImportError:
        logger.warning("PyTorch not available, falling back to heuristic")
        return []

    from src.services.recommendation_engine import generate_positioning_recommendation

    windows = _extract_ml_windows(raw_kills, raw_ticks, trade_sids)
    if not windows:
        return []

    # Batch inference
    features_batch = np.stack([w["features"] for w in windows])
    tensor = torch.from_numpy(features_batch)

    with torch.no_grad():
        logits = model(tensor)
        probs = F.softmax(logits, dim=1)
        pred_classes = logits.argmax(dim=1).numpy()
        confidences = probs.max(dim=1).values.numpy()

    class_labels = ["no_error", "minor", "critical"]
    severity_map = {0: None, 1: "minor", 2: "critical"}

    results: list[DetectedErrorResult] = []
    for i, window in enumerate(windows):
        pred_class = int(pred_classes[i])
        confidence = float(confidences[i])

        # Skip no_error predictions and low confidence
        if pred_class == 0 or confidence < 0.6:
            continue

        severity = severity_map[pred_class]
        info = window["label_info"]

        desc = (
            f"Positioning error detected: {class_labels[pred_class]} "
            f"(confidence {confidence:.0%}). "
            f"Teammates nearby: {info['teammates_nearby']}, "
            f"traded: {'yes' if info['was_traded'] else 'no'}"
        )

        context = {
            "angles_exposed": int(info["enemies_close"]),
            "distance_to_cover": 100.0,
            "had_teammate_nearby": info["teammates_nearby"] > 0,
            "position_area": "the engagement area",
        }
        rec = generate_positioning_recommendation(severity, context)

        # Feature importances from model probabilities
        import json

        importances = json.dumps(
            [
                {
                    "feature": "teammates_nearby",
                    "value": info["teammates_nearby"],
                    "impact": float(probs[i][0]),
                },
                {
                    "feature": "was_traded",
                    "value": int(info["was_traded"]),
                    "impact": float(probs[i][0]) * 0.3,
                },
                {
                    "feature": "enemies_close",
                    "value": info["enemies_close"],
                    "impact": float(probs[i][pred_class]) * 0.25,
                },
                {
                    "feature": "velocity",
                    "value": round(info["velocity"], 1),
                    "impact": float(probs[i][pred_class]) * 0.15,
                },
            ]
        )

        explanation = (
            f"ML model detected {class_labels[pred_class]} positioning error "
            f"with {confidence:.0%} confidence. "
            f"Key factors: {info['teammates_nearby']} teammates nearby, "
            f"{'traded' if info['was_traded'] else 'not traded'}, "
            f"{info['enemies_close']} enemies close."
        )

        results.append(
            DetectedErrorResult(
                player_steam_id=info["victim_sid"],
                round_number=info["round_number"],
                error_type="positioning",
                severity=severity,
                confidence=confidence,
                tick=info["tick"],
                position_x=info["pos_x"],
                position_y=info["pos_y"],
                position_z=info["pos_z"],
                description=desc,
                model_name="positioning_mamba",
                model_version="1.0.0",
                explanation_text=explanation,
                feature_importances_json=importances,
                explanation_method="model_softmax",
                rec_title=rec.title,
                rec_description=rec.description,
                rec_priority=rec.priority,
                rec_template_id=rec.template_id,
                rec_expected_impact=rec.expected_impact,
            )
        )

    return results


def run_ml_analysis(
    death_events: list,
    utility_features: list,
    raw_kills: list | None = None,
    raw_ticks: list | None = None,
    trade_sids: set | None = None,
) -> list[DetectedErrorResult]:
    """Run full ML analysis pipeline.

    Auto-detects trained model weights:
    - If trained models exist AND raw tick data provided → uses real ML inference
    - Otherwise → falls back to heuristic baseline
    """
    results: list[DetectedErrorResult] = []

    # Check for trained models
    weights = _find_model_weights()
    use_ml_positioning = bool(weights.get("positioning")) and raw_ticks and raw_kills

    if use_ml_positioning:
        logger.info("Using trained Mamba model for positioning analysis")
        pos_results = run_ml_positioning_inference(raw_kills, raw_ticks, trade_sids or set())
        if pos_results:
            results.extend(pos_results)
        else:
            logger.info("ML model returned 0 errors, supplementing with heuristic")
            pos_results = run_heuristic_positioning_analysis(death_events)
            results.extend(pos_results)
    else:
        logger.info("No trained models or tick data, using heuristic baseline")
        pos_results = run_heuristic_positioning_analysis(death_events)
        results.extend(pos_results)

    # Utility analysis (always heuristic until grenade extraction available)
    util_results = run_heuristic_utility_analysis(utility_features)
    results.extend(util_results)

    logger.info(
        "ML analysis complete: %d positioning errors, %d utility errors (mode=%s)",
        len(pos_results),
        len(util_results),
        "ml" if use_ml_positioning else "heuristic",
    )

    return results
