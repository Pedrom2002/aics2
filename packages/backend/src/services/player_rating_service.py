"""Player rating and clustering inference service.

Loads:
- CatBoost player rating model (calibrated against HLTV Rating 2.0)
- UMAP+HDBSCAN player clusters (archetype assignments)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_loaded_rating_model = None
_loaded_clusters_data = None


def _find_checkpoint(filename: str) -> Path | None:
    """Find a checkpoint file in standard locations."""
    candidates = [
        Path(__file__).parent.parent.parent.parent.parent / "data" / "checkpoints" / filename,
        Path(__file__).parent.parent.parent.parent / "data" / "checkpoints" / filename,
        Path("D:/aics2-data/checkpoints") / filename,
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def get_rating_model():
    """Load and cache CatBoost rating model."""
    global _loaded_rating_model
    if _loaded_rating_model is not None:
        return _loaded_rating_model

    try:
        from catboost import CatBoostRegressor
    except ImportError:
        logger.warning("CatBoost not installed, rating disabled")
        return None

    path = _find_checkpoint("player_rating.cbm")
    if path is None:
        logger.warning("Player rating model not found")
        return None

    try:
        model = CatBoostRegressor()
        model.load_model(str(path))
        _loaded_rating_model = model
        logger.info("Loaded player rating model from %s", path)
        return model
    except Exception as e:
        logger.warning("Failed to load rating model: %s", e)
        return None


def get_clusters_data() -> dict | None:
    """Load and cache player cluster assignments."""
    global _loaded_clusters_data
    if _loaded_clusters_data is not None:
        return _loaded_clusters_data

    path = _find_checkpoint("player_clusters.json")
    if path is None:
        logger.warning("Player clusters data not found")
        return None

    try:
        with open(path) as f:
            _loaded_clusters_data = json.load(f)
        logger.info(
            "Loaded clusters data from %s (%d players)",
            path,
            len(_loaded_clusters_data.get("players", [])),
        )
        return _loaded_clusters_data
    except Exception as e:
        logger.warning("Failed to load clusters: %s", e)
        return None


def predict_player_rating(stats: dict) -> float | None:
    """Predict HLTV-calibrated rating from aggregated player stats.

    Stats dict should contain:
        kills, deaths, assists, headshot_kills, damage,
        first_kills, first_deaths, trade_kills, trade_deaths,
        kast_rounds, rounds_survived, multi_kills_3k, multi_kills_4k,
        multi_kills_5k, clutch_wins, flash_assists, utility_damage,
        total_rounds, adr
    """
    model = get_rating_model()
    if model is None:
        return None

    rounds = max(stats.get("total_rounds", 1), 1)
    kills = stats.get("kills", 0)
    deaths = max(stats.get("deaths", 0), 1)
    assists = stats.get("assists", 0)

    kpr = kills / rounds
    dpr = deaths / rounds
    apr = assists / rounds
    hs_pct = (stats.get("headshot_kills", 0) / max(kills, 1)) * 100
    kast = (stats.get("kast_rounds", 0) / rounds) * 100
    survival = (stats.get("rounds_survived", 0) / rounds) * 100
    opening_kr = stats.get("first_kills", 0) / rounds
    opening_dr = stats.get("first_deaths", 0) / rounds
    trade_kr = stats.get("trade_kills", 0) / rounds
    trade_dr = stats.get("trade_deaths", 0) / rounds
    multi_3k_r = stats.get("multi_kills_3k", 0) / rounds
    multi_4k_r = stats.get("multi_kills_4k", 0) / rounds
    multi_5k_r = stats.get("multi_kills_5k", 0) / rounds
    clutch_r = stats.get("clutch_wins", 0) / rounds
    flash_r = stats.get("flash_assists", 0) / rounds
    util_dmg_r = stats.get("utility_damage", 0) / rounds
    kd = kills / deaths
    adr = stats.get("adr", 0.0) or 0.0
    impact = 2.13 * multi_4k_r + 1.5 * multi_3k_r + 1.0 * opening_kr + 0.42 * clutch_r

    features = np.array(
        [
            [
                kpr,
                dpr,
                apr,
                kd,
                hs_pct,
                kast,
                survival,
                opening_kr,
                opening_dr,
                trade_kr,
                trade_dr,
                multi_3k_r,
                multi_4k_r,
                multi_5k_r,
                clutch_r,
                flash_r,
                util_dmg_r,
                adr,
                impact,
                kills,
                deaths,
                assists,
                stats.get("headshot_kills", 0),
                stats.get("first_kills", 0),
                stats.get("first_deaths", 0),
                stats.get("trade_kills", 0),
                stats.get("trade_deaths", 0),
                stats.get("kast_rounds", 0),
                stats.get("rounds_survived", 0),
                rounds,
            ]
        ],
        dtype=np.float32,
    )

    return float(model.predict(features)[0])


def get_player_archetype(steam_id: str) -> dict | None:
    """Get archetype assignment for a player from clusters data."""
    data = get_clusters_data()
    if data is None:
        return None

    for player in data.get("players", []):
        if player.get("steam_id") == steam_id:
            cluster_id = player.get("cluster")
            if cluster_id == -1:
                return {
                    "cluster_id": -1,
                    "archetype": "Unique Style",
                    "x": player.get("x"),
                    "y": player.get("y"),
                    "size": 0,
                }
            archetype = data.get("archetypes", {}).get(str(cluster_id), {})
            return {
                "cluster_id": cluster_id,
                "archetype": archetype.get("name", "Unknown"),
                "size": archetype.get("size", 0),
                "top_features": archetype.get("top_features", []),
                "x": player.get("x"),
                "y": player.get("y"),
            }
    return None


def list_archetypes() -> list[dict]:
    """List all discovered player archetypes."""
    data = get_clusters_data()
    if data is None:
        return []

    archetypes = []
    for cluster_id, info in (data.get("archetypes", {}) or {}).items():
        archetypes.append(
            {
                "cluster_id": int(cluster_id),
                "name": info.get("name"),
                "size": info.get("size"),
                "top_features": info.get("top_features", []),
                "sample_players": info.get("sample_players", []),
            }
        )

    return sorted(archetypes, key=lambda a: -a["size"])
