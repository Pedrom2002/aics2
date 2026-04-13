"""Daily drift-detection Celery task.

Pulls rolling feature samples stored in Redis by the inference middleware
and computes a KS-style divergence against the training baselines shipped
in ``packages/ml-models/baselines/``. Emits a Prometheus gauge via the
backend ``/metrics`` endpoint (read by the already-wired scrape config).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_BASELINE_DIR = Path(__file__).resolve().parents[3] / "ml-models" / "baselines"


@celery_app.task(name="src.tasks.ml_drift.compute_drift")
def compute_drift() -> dict:
    """Compare rolling live samples against baselines and publish metrics.

    Returns a summary dict (used by tests and logs).
    """
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

    from src.config import settings
    from src.services.ml_drift import FEATURE_DRIFT, _load_baseline  # noqa: PLC0415

    summary: dict[str, dict[str, float]] = {}

    if not _BASELINE_DIR.exists():
        logger.info("No baseline directory at %s — skipping drift computation", _BASELINE_DIR)
        return summary

    # Use the app's Redis client lazily (sync) to avoid importing asyncio here.
    import redis

    r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    for baseline_file in _BASELINE_DIR.glob("*.json"):
        model = baseline_file.stem
        baseline = _load_baseline(model)
        if not baseline:
            continue

        model_summary: dict[str, float] = {}
        for feature, stats in baseline.items():
            samples_key = f"drift:{model}:{feature}"
            values = r.lrange(samples_key, 0, -1) or []
            if not values:
                continue
            try:
                floats = [float(v) for v in values]
            except ValueError:
                continue
            mean = sum(floats) / len(floats)
            base_mean = stats.get("mean", 0.0)
            base_std = stats.get("std", 1.0) or 1.0
            drift = min(1.0, abs(mean - base_mean) / (4.0 * base_std))
            model_summary[feature] = round(drift, 4)
            FEATURE_DRIFT.labels(model=model, feature=feature).set(drift)

        summary[model] = model_summary

    logger.info("Drift summary: %s", json.dumps(summary))
    return summary
