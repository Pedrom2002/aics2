"""
BentoML model serving configuration for CS2 ML models.

Serves all models behind a single API for batch match analysis.

Usage:
    bentoml serve src.inference.serving:svc

Or build and containerize:
    bentoml build
    bentoml containerize cs2_analytics:latest
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Model registry — paths to saved model weights
MODEL_DIR = Path(__file__).parent.parent.parent / "checkpoints"

_positioning_model = None
_timing_model = None


def _load_positioning_model():
    """Lazy-load the positioning Mamba model."""
    global _positioning_model
    if _positioning_model is not None:
        return _positioning_model

    from src.models.positioning_mamba import MambaConfig, PositioningMamba

    model_path = MODEL_DIR / "positioning" / "best_model.pt"
    model = PositioningMamba(MambaConfig())

    if model_path.exists():
        state = torch.load(model_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        logger.info("Loaded positioning model from %s", model_path)
    else:
        logger.warning("No trained positioning model found at %s, using random weights", model_path)

    model.eval()
    _positioning_model = model
    return model


def _load_timing_model():
    """Lazy-load the timing Mamba model."""
    global _timing_model
    if _timing_model is not None:
        return _timing_model

    from src.models.timing_mamba import TimingConfig, TimingMamba

    model_path = MODEL_DIR / "timing" / "best_model.pt"
    model = TimingMamba(TimingConfig())

    if model_path.exists():
        state = torch.load(model_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        logger.info("Loaded timing model from %s", model_path)
    else:
        logger.warning("No trained timing model found at %s, using random weights", model_path)

    model.eval()
    _timing_model = model
    return model


async def analyze_positioning(windows: list[np.ndarray]) -> list[dict]:
    """Run positioning error detection on a batch of 64-tick windows.

    Args:
        windows: List of (64, 18) numpy arrays.

    Returns:
        List of {class, confidence, label} dicts.
    """
    if not windows:
        return []

    model = _load_positioning_model()

    batch = torch.tensor(np.stack(windows), dtype=torch.float32)

    with torch.no_grad():
        predicted, confidence = model.predict(batch)

    labels = ["no_error", "minor", "critical"]
    results = []
    for i in range(len(windows)):
        cls = predicted[i].item()
        conf = confidence[i].item()
        results.append(
            {
                "class": cls,
                "label": labels[cls],
                "confidence": round(conf, 4),
            }
        )

    return results


async def analyze_timing(windows: list[np.ndarray]) -> list[dict]:
    """Run timing error detection on a batch of 320-tick windows.

    Args:
        windows: List of (320, 14) numpy arrays.

    Returns:
        List of {class, confidence, label} dicts.
    """
    if not windows:
        return []

    model = _load_timing_model()

    batch = torch.tensor(np.stack(windows), dtype=torch.float32)

    with torch.no_grad():
        predicted, confidence = model.predict(batch)

    labels = ["good_timing", "too_early", "too_late", "unnecessary"]
    results = []
    for i in range(len(windows)):
        cls = predicted[i].item()
        conf = confidence[i].item()
        results.append(
            {
                "class": cls,
                "label": labels[cls],
                "confidence": round(conf, 4),
            }
        )

    return results


async def analyze_match(match_data: dict) -> dict:
    """Full match analysis endpoint — runs all applicable models.

    Args:
        match_data: Dict with 'positioning_windows', 'timing_windows', etc.

    Returns:
        Combined analysis results.
    """
    results = {}

    pos_windows = match_data.get("positioning_windows", [])
    if pos_windows:
        results["positioning_errors"] = await analyze_positioning(pos_windows)

    timing_windows = match_data.get("timing_windows", [])
    if timing_windows:
        results["timing_errors"] = await analyze_timing(timing_windows)

    results["model_versions"] = {
        "positioning": "mamba-v1",
        "timing": "mamba-v1",
    }

    return results


# BentoML service definition (used when running `bentoml serve`)
try:
    import bentoml

    svc = bentoml.Service("cs2_analytics", runners=[])

    @svc.api(input=bentoml.io.JSON(), output=bentoml.io.JSON())
    async def predict(input_data: dict) -> dict:
        return await analyze_match(input_data)

except ImportError:
    # BentoML not installed — serving module still usable as a library
    svc = None
