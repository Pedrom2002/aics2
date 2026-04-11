"""Model registry — JSON-backed catalog of trained CS2 ML models.

Supports lookup by name (and optional version), listing, and dynamic
registration. The registry file lives at
``packages/ml-models/models_registry.json`` so it is editable without code
changes and can be diffed in PRs.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "models_registry.json"

_lock = threading.Lock()
_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    """Load the registry JSON from disk (cached)."""
    global _cache
    if _cache is not None:
        return _cache

    with _lock:
        if _cache is not None:
            return _cache
        if not REGISTRY_PATH.exists():
            logger.warning("Registry file not found at %s — using empty registry", REGISTRY_PATH)
            _cache = {"schema_version": "1.0", "models": []}
        else:
            with REGISTRY_PATH.open("r", encoding="utf-8") as f:
                _cache = json.load(f)
    return _cache


def _save(data: dict[str, Any]) -> None:
    """Persist the registry back to disk and refresh cache."""
    global _cache
    with _lock:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRY_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        _cache = data


def reload() -> None:
    """Drop the in-memory cache and force re-read on next access."""
    global _cache
    with _lock:
        _cache = None


def list_models() -> list[dict[str, Any]]:
    """Return all models in the registry."""
    return list(_load().get("models", []))


def get_model(name: str, version: str | None = None) -> dict[str, Any] | None:
    """Look up a model by name (and optionally a specific version).

    If ``version`` is None, returns the first match (typically the latest
    registered version for that name).
    """
    for entry in _load().get("models", []):
        if entry.get("name") != name:
            continue
        if version is None or entry.get("version") == version:
            return entry
    return None


def register_model(
    name: str,
    version: str,
    path: str,
    framework: str,
    task: str,
    metrics: dict[str, Any] | None = None,
    features: list[str] | None = None,
    trained_at: str | None = None,
    training_script: str | None = None,
    description: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Register a new model (or replace an existing entry).

    Returns the entry that was inserted/updated.
    """
    data = _load()
    models = list(data.get("models", []))

    entry = {
        "name": name,
        "version": version,
        "framework": framework,
        "task": task,
        "path": path,
        "metrics": metrics or {},
        "features": features or [],
        "trained_at": trained_at,
        "training_script": training_script,
        "description": description,
    }

    existing_idx = None
    for i, m in enumerate(models):
        if m.get("name") == name and m.get("version") == version:
            existing_idx = i
            break

    if existing_idx is not None:
        if not overwrite:
            raise ValueError(
                f"Model {name}@{version} already registered. Pass overwrite=True to replace."
            )
        models[existing_idx] = entry
    else:
        models.append(entry)

    new_data = dict(data)
    new_data["models"] = models
    _save(new_data)
    return entry


def resolve_model_path(name: str, version: str | None = None) -> Path | None:
    """Resolve the on-disk path for a registered model, searching common roots.

    Returns the first existing path or None if no checkpoint can be located.
    """
    entry = get_model(name, version)
    if entry is None:
        return None

    rel = entry.get("path")
    if not rel:
        return None

    candidates = [
        REGISTRY_PATH.parent / rel,
        REGISTRY_PATH.parent.parent.parent / "data" / rel,
        Path("D:/aics2-data") / rel,
        Path.home() / ".cs2-analytics" / rel,
    ]
    for p in candidates:
        if p.exists():
            return p
    return None
