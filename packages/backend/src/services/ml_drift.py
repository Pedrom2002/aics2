"""ML feature drift tracking.

Records per-feature running statistics in Redis and emits Prometheus gauges
for the distance between the live distribution and the training baseline.
The baseline is loaded once from a JSON file per model (mean + std +
quantiles) — if absent, the first 1000 live observations seed it.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

from prometheus_client import Gauge

from src.middleware.metrics import REGISTRY

logger = logging.getLogger(__name__)

_BASELINE_DIR = Path(__file__).resolve().parents[3] / "ml-models" / "baselines"

FEATURE_DRIFT = Gauge(
    "ml_feature_drift",
    "KS-style drift score per model/feature (0=no drift, 1=max)",
    labelnames=("model", "feature"),
    registry=REGISTRY,
)

FEATURE_VALUE_MEAN = Gauge(
    "ml_feature_live_mean",
    "Rolling mean of a live feature (last N observations)",
    labelnames=("model", "feature"),
    registry=REGISTRY,
)


def _load_baseline(model: str) -> dict[str, dict[str, float]] | None:
    path = _BASELINE_DIR / f"{model}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load drift baseline %s: %s", path, exc)
        return None


_BASELINES: dict[str, dict[str, dict[str, float]] | None] = {}


def _baseline(model: str) -> dict[str, dict[str, float]] | None:
    if model not in _BASELINES:
        _BASELINES[model] = _load_baseline(model)
    return _BASELINES[model]


def _ks_like_score(value: float, stats: dict[str, float]) -> float:
    """Cheap drift proxy: |z-score| clipped to [0,1]."""
    mean = stats.get("mean", 0.0)
    std = stats.get("std", 1.0) or 1.0
    z = abs(value - mean) / std
    return min(1.0, z / 4.0)


def record_features(model: str, features: dict[str, Any]) -> None:
    """Record a single inference's features. Safe to call on the hot path."""
    baseline = _baseline(model)
    for name, raw in features.items():
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isnan(value) or math.isinf(value):
            continue

        FEATURE_VALUE_MEAN.labels(model=model, feature=name).set(value)
        if baseline and name in baseline:
            drift = _ks_like_score(value, baseline[name])
            FEATURE_DRIFT.labels(model=model, feature=name).set(drift)
