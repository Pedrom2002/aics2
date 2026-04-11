"""Self-contained explainability API for the ``ml_models`` namespace.

Same logic as ``src/explainability/api.py`` but without the ``src.*``
imports so it can be loaded next to other packages that own their own
``src`` namespace (e.g. the FastAPI backend).
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from ml_models.registry import get_model, resolve_model_path

logger = logging.getLogger(__name__)


SUPPORTED_MODELS = {"win_prob", "player_rating"}


def _features_to_vector(model_entry: dict[str, Any], sample_data: dict[str, Any]) -> tuple[np.ndarray, list[str]]:
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
    return np.array([values], dtype=np.float32), feature_names


def _explain_with_shap(model, x: np.ndarray, feature_names: list[str]) -> tuple[float, list[float], float]:
    import shap

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(x)

    if isinstance(shap_values, list):
        sv = shap_values[1] if len(shap_values) > 1 else shap_values[0]
    else:
        sv = shap_values

    sv_arr = np.asarray(sv)
    if sv_arr.ndim == 3:
        # (samples, features, classes) — pick positive class
        sv_arr = sv_arr[..., -1]
    if sv_arr.ndim == 2:
        sv_row = sv_arr[0]
    else:
        sv_row = sv_arr

    base = explainer.expected_value
    if isinstance(base, (list, np.ndarray)):
        base_val = float(np.asarray(base).ravel()[-1])
    else:
        base_val = float(base)

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
    coeffs: list[float] = []
    for name in feature_names:
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


__all__ = ["SUPPORTED_MODELS", "explain_prediction"]
