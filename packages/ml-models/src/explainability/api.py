"""High-level explainability API used by the FastAPI ml router.

Glues the model registry to the underlying SHAP / Integrated Gradients
explainers so callers can pass a model name + a feature dict and get back a
JSON-serialisable explanation.

Falls back to a deterministic linear/feature-importance approximation when
the trained model checkpoint is not present, so the endpoint stays useful in
dev environments without binaries.
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from src.registry import get_model, resolve_model_path

logger = logging.getLogger(__name__)


SUPPORTED_MODELS = {"win_prob", "player_rating"}


def _features_to_vector(model_entry: dict[str, Any], sample_data: dict[str, Any]) -> tuple[np.ndarray, list[str]]:
    """Coerce a feature dict into the ordered vector expected by the model."""
    feature_names: list[str] = list(model_entry.get("features") or [])
    if not feature_names:
        raise ValueError(f"Model {model_entry.get('name')} has no feature schema in registry")

    values: list[float] = []
    for name in feature_names:
        raw = sample_data.get(name, 0)
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            values.append(0.0)
    arr = np.array([values], dtype=np.float32)
    return arr, feature_names


def _explain_with_shap(model, x: np.ndarray, feature_names: list[str]) -> tuple[float, list[float], float]:
    """Run TreeSHAP and return (base_value, shap_values, prediction)."""
    import shap

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(x)

    if isinstance(shap_values, list):
        # Multi-output (binary cls) — pick the positive-class column
        sv = shap_values[1] if len(shap_values) > 1 else shap_values[0]
    else:
        sv = shap_values

    sv_row = np.asarray(sv)[0]

    # base value can be a scalar or per-class array
    base = explainer.expected_value
    if isinstance(base, (list, np.ndarray)):
        base_val = float(np.asarray(base).ravel()[-1])
    else:
        base_val = float(base)

    # Get the model prediction for the same row
    try:
        pred_raw = model.predict(x)
        prediction = float(np.asarray(pred_raw).ravel()[0])
    except Exception:
        prediction = base_val + float(sv_row.sum())

    return base_val, [float(v) for v in sv_row], prediction


def _heuristic_explanation(
    feature_names: list[str],
    x: np.ndarray,
    model_name: str,
) -> tuple[float, list[float], float]:
    """Deterministic fallback when no trained model is available.

    Produces a stable, signed contribution per feature using a hash-derived
    coefficient and a sigmoid (for win_prob) or linear (for player_rating)
    output. Not predictive — but consistent enough for tests and UI demos.
    """
    coeffs: list[float] = []
    for name in feature_names:
        # Stable pseudo-random in [-1, 1]
        h = (hash(name) & 0xFFFFFFFF) / 0xFFFFFFFF
        coeffs.append((h * 2.0) - 1.0)

    coeff_arr = np.array(coeffs, dtype=np.float32)
    contributions = coeff_arr * x[0]
    raw = float(contributions.sum())

    if model_name == "win_prob":
        prediction = 1.0 / (1.0 + math.exp(-raw))
        base_value = 0.5
    else:
        prediction = 1.0 + raw * 0.05
        base_value = 1.0

    return base_value, [float(v) for v in contributions], prediction


def _load_lightgbm(path) -> Any | None:
    try:
        import lightgbm as lgb

        return lgb.Booster(model_file=str(path))
    except Exception as e:
        logger.warning("Failed to load lightgbm model %s: %s", path, e)
        return None


def _load_catboost(path) -> Any | None:
    try:
        from catboost import CatBoostRegressor

        m = CatBoostRegressor()
        m.load_model(str(path))
        return m
    except Exception as e:
        logger.warning("Failed to load catboost model %s: %s", path, e)
        return None


def explain_prediction(model_name: str, sample_data: dict[str, Any]) -> dict[str, Any]:
    """Public entrypoint used by the FastAPI router.

    Returns a JSON-serialisable dict with shape::

        {
            "model": str,
            "version": str,
            "base_value": float,
            "prediction": float,
            "shap_values": [{"feature": str, "value": float, "contribution": float}],
            "method": "tree_shap" | "heuristic_fallback"
        }
    """
    if model_name not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported model '{model_name}'. Supported: {sorted(SUPPORTED_MODELS)}")

    entry = get_model(model_name)
    if entry is None:
        raise ValueError(f"Model '{model_name}' not found in registry")

    x, feature_names = _features_to_vector(entry, sample_data)

    framework = (entry.get("framework") or "").lower()
    path = resolve_model_path(model_name)
    model_obj = None
    if path is not None:
        if "lightgbm" in framework:
            model_obj = _load_lightgbm(path)
        elif "catboost" in framework:
            model_obj = _load_catboost(path)

    method = "tree_shap"
    if model_obj is not None:
        try:
            base_value, shap_values, prediction = _explain_with_shap(model_obj, x, feature_names)
        except Exception as e:
            logger.warning("SHAP failed for %s, falling back to heuristic: %s", model_name, e)
            base_value, shap_values, prediction = _heuristic_explanation(feature_names, x, model_name)
            method = "heuristic_fallback"
    else:
        base_value, shap_values, prediction = _heuristic_explanation(feature_names, x, model_name)
        method = "heuristic_fallback"

    contribs = [
        {
            "feature": name,
            "value": float(x[0, i]),
            "contribution": float(shap_values[i]) if i < len(shap_values) else 0.0,
        }
        for i, name in enumerate(feature_names)
    ]
    contribs.sort(key=lambda c: abs(c["contribution"]), reverse=True)

    return {
        "model": model_name,
        "version": entry.get("version"),
        "base_value": float(base_value),
        "prediction": float(prediction),
        "shap_values": contribs,
        "method": method,
    }
