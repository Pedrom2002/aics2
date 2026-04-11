"""Self-contained model registry shim for the ``ml_models`` namespace.

This file intentionally does NOT import from ``src.registry`` because the
``src`` name collides with sibling packages (e.g. ``packages/backend/src``)
when both are on ``sys.path``. Instead it reads the JSON file directly using
the same on-disk schema and exposes an identical public API.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "models_registry.json"

_lock = threading.Lock()
_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is not None:
            return _cache
        if not REGISTRY_PATH.exists():
            _cache = {"schema_version": "1.0", "models": []}
        else:
            with REGISTRY_PATH.open("r", encoding="utf-8") as f:
                _cache = json.load(f)
    return _cache


def _save(data: dict[str, Any]) -> None:
    global _cache
    with _lock:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRY_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        _cache = data


def reload() -> None:
    global _cache
    with _lock:
        _cache = None


def list_models() -> list[dict[str, Any]]:
    return list(_load().get("models", []))


def get_model(name: str, version: str | None = None) -> dict[str, Any] | None:
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


__all__ = [
    "REGISTRY_PATH",
    "get_model",
    "list_models",
    "register_model",
    "reload",
    "resolve_model_path",
]
