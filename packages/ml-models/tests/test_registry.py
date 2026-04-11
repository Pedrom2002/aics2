"""Tests for the model registry helpers."""

from __future__ import annotations

import json

import pytest

from src import registry as src_registry


@pytest.fixture(autouse=True)
def _reload_registry():
    src_registry.reload()
    yield
    src_registry.reload()


def test_registry_file_exists():
    assert src_registry.REGISTRY_PATH.exists(), "models_registry.json must be present"


def test_registry_json_is_valid():
    with src_registry.REGISTRY_PATH.open() as f:
        data = json.load(f)
    assert "models" in data
    assert isinstance(data["models"], list)
    assert data["models"], "registry should not be empty"


def test_list_models_returns_all_entries():
    models = src_registry.list_models()
    assert len(models) >= 4
    names = {m["name"] for m in models}
    assert {"win_prob", "player_rating", "strategy_gnn"}.issubset(names)


def test_get_model_by_name():
    entry = src_registry.get_model("win_prob")
    assert entry is not None
    assert entry["name"] == "win_prob"
    assert "metrics" in entry
    assert "auc" in entry["metrics"]
    assert entry["metrics"]["auc"] == pytest.approx(0.904, abs=1e-3)


def test_get_model_with_version_filter():
    entry = src_registry.get_model("win_prob", version="v2")
    assert entry is not None
    assert entry["version"] == "v2"

    missing = src_registry.get_model("win_prob", version="v999")
    assert missing is None


def test_get_unknown_model_returns_none():
    assert src_registry.get_model("does_not_exist") is None


def test_register_model_round_trip(tmp_path, monkeypatch):
    # Redirect REGISTRY_PATH to a tmp file so we don't pollute real registry
    fake = tmp_path / "registry.json"
    fake.write_text(json.dumps({"schema_version": "1.0", "models": []}))
    monkeypatch.setattr(src_registry, "REGISTRY_PATH", fake)
    src_registry.reload()

    entry = src_registry.register_model(
        name="test_model",
        version="v1",
        path="checkpoints/test.bin",
        framework="pytorch",
        task="classification",
        metrics={"accuracy": 0.91},
        features=["a", "b"],
        trained_at="2026-04-01",
    )
    assert entry["name"] == "test_model"

    src_registry.reload()
    listed = src_registry.list_models()
    assert any(m["name"] == "test_model" for m in listed)

    fetched = src_registry.get_model("test_model")
    assert fetched is not None
    assert fetched["metrics"]["accuracy"] == pytest.approx(0.91)


def test_register_duplicate_requires_overwrite(tmp_path, monkeypatch):
    fake = tmp_path / "registry.json"
    fake.write_text(json.dumps({"schema_version": "1.0", "models": []}))
    monkeypatch.setattr(src_registry, "REGISTRY_PATH", fake)
    src_registry.reload()

    src_registry.register_model(
        name="dup",
        version="v1",
        path="x",
        framework="lgbm",
        task="cls",
    )
    with pytest.raises(ValueError):
        src_registry.register_model(
            name="dup",
            version="v1",
            path="x",
            framework="lgbm",
            task="cls",
        )
    # overwrite=True should succeed
    src_registry.register_model(
        name="dup",
        version="v1",
        path="y",
        framework="lgbm",
        task="cls",
        overwrite=True,
    )
    src_registry.reload()
    assert src_registry.get_model("dup")["path"] == "y"


def test_ml_models_namespace_imports():
    """The public ml_models namespace must mirror src.registry."""
    from ml_models.registry import get_model, list_models, register_model  # noqa: F401

    models = list_models()
    assert isinstance(models, list)
    assert get_model("player_rating") is not None
