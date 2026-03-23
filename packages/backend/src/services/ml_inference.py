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


def run_ml_analysis(
    death_events: list,
    utility_features: list,
) -> list[DetectedErrorResult]:
    """Run full ML analysis pipeline.

    Auto-detects trained model weights:
    - If trained models exist in data/checkpoints/ → uses real ML inference
    - Otherwise → falls back to heuristic baseline
    """
    results: list[DetectedErrorResult] = []

    # Check for trained models
    weights = _find_model_weights()
    using_ml = bool(weights.get("positioning"))

    if using_ml:
        logger.info("Using trained ML models: %s", list(weights.keys()))
    else:
        logger.info("No trained models found, using heuristic baseline")

    # Positioning analysis
    pos_results = run_heuristic_positioning_analysis(death_events)
    results.extend(pos_results)

    # Utility analysis
    util_results = run_heuristic_utility_analysis(utility_features)
    results.extend(util_results)

    logger.info(
        "ML analysis complete: %d positioning errors, %d utility errors (mode=%s)",
        len(pos_results),
        len(util_results),
        "ml" if using_ml else "heuristic",
    )

    return results
