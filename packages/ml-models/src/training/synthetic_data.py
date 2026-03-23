"""
Generate synthetic training data for pipeline testing.

Creates realistic-looking .npz files without needing real demos.
Useful for testing the full train → evaluate → deploy pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def generate_synthetic_positioning(
    output_dir: Path,
    count: int = 1000,
    seed: int = 42,
) -> int:
    """Generate synthetic positioning training windows.

    Creates (64, 18) feature arrays with heuristic labels:
    - ~60% no_error (class 0)
    - ~25% minor (class 1)
    - ~15% critical (class 2)
    """
    rng = np.random.RandomState(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    maps = ["de_mirage", "de_dust2", "de_inferno", "de_nuke", "de_overpass", "de_ancient", "de_anubis"]

    for i in range(count):
        # Decide label
        r = rng.random()
        if r < 0.60:
            label = 0  # no_error
            # Good positioning: low angles exposed, near cover, has teammates
            angles_exposed = rng.uniform(0, 0.3)
            dist_to_cover = rng.uniform(0, 0.3)
            teammate_dist = rng.uniform(0.1, 0.4)
        elif r < 0.85:
            label = 1  # minor
            angles_exposed = rng.uniform(0.3, 0.6)
            dist_to_cover = rng.uniform(0.2, 0.5)
            teammate_dist = rng.uniform(0.3, 0.7)
        else:
            label = 2  # critical
            angles_exposed = rng.uniform(0.5, 1.0)
            dist_to_cover = rng.uniform(0.4, 1.0)
            teammate_dist = rng.uniform(0.5, 1.0)

        # Generate 64 ticks of features
        features = np.zeros((64, 18), dtype=np.float32)
        for t in range(64):
            noise = rng.normal(0, 0.02, 18).astype(np.float32)
            features[t] = [
                rng.uniform(-1, 1),           # pos_x normalized
                rng.uniform(-1, 1),           # pos_y
                rng.uniform(0, 0.5),          # pos_z
                rng.uniform(0, 1),            # yaw
                rng.uniform(-0.5, 0.5),       # pitch
                rng.uniform(0, 0.8),          # velocity
                rng.uniform(0.3, 1.0),        # health
                rng.uniform(0, 1.0),          # armor
                rng.uniform(0, 0.6),          # weapon_id
                rng.choice([0, 1]) * 0.5,     # is_scoped
                rng.uniform(0.2, 1.0),        # teammates_alive
                rng.uniform(0.2, 1.0),        # enemies_alive
                rng.choice([0, 0.5, 1.0]),    # bomb_state
                rng.uniform(0.1, 1.0),        # round_time_remaining
                teammate_dist + rng.normal(0, 0.05),  # nearest_teammate
                rng.uniform(0.2, 0.8),        # nearest_enemy
                angles_exposed + rng.normal(0, 0.03),  # angles_exposed
                dist_to_cover + rng.normal(0, 0.03),   # dist_to_cover
            ] + noise

        features = np.clip(features, 0, 1)

        map_name = rng.choice(maps)
        round_num = rng.randint(1, 31)
        player_id = f"765611980000{rng.randint(10000, 99999)}"

        filename = f"synth_{map_name}_{round_num:02d}_{player_id[-4:]}_{i:05d}.npz"
        np.savez_compressed(
            output_dir / filename,
            features=features,
            label=np.array(label, dtype=np.int64),
            player=player_id,
            round=round_num,
        )

    logger.info("Generated %d synthetic positioning windows in %s", count, output_dir)
    return count


def generate_synthetic_utility(
    output_dir: Path,
    count: int = 500,
    seed: int = 42,
) -> int:
    """Generate synthetic utility training vectors.

    Creates (25,) feature arrays with labels:
    - 0 = effective, 1 = suboptimal, 2 = wasted, 3 = harmful
    """
    rng = np.random.RandomState(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(count):
        # Decide label based on outcome features
        r = rng.random()
        if r < 0.35:
            label = 0  # effective
            enemies_flashed = rng.uniform(0.3, 1.0)
            damage = rng.uniform(0.2, 1.0)
        elif r < 0.60:
            label = 1  # suboptimal
            enemies_flashed = rng.uniform(0.1, 0.4)
            damage = rng.uniform(0.05, 0.3)
        elif r < 0.90:
            label = 2  # wasted
            enemies_flashed = 0.0
            damage = 0.0
        else:
            label = 3  # harmful
            enemies_flashed = 0.0
            damage = 0.0

        grenade_type = rng.randint(0, 4)
        one_hot = [0.0, 0.0, 0.0, 0.0]
        one_hot[grenade_type] = 1.0

        features = np.array(
            [
                # Grenade context (5)
                one_hot[0], one_hot[1], one_hot[2], one_hot[3],
                rng.uniform(0, 1),  # map_id
                # Position (7)
                rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0, 0.5),
                rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0, 0.5),
                rng.uniform(0, 1),  # distance_to_pro_lineup
                # Timing (3)
                rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0, 1),
                # Round context (4)
                rng.uniform(-1, 1), rng.uniform(0.2, 1), rng.uniform(0.2, 1),
                rng.uniform(0, 1),
                # Outcome (5)
                enemies_flashed, rng.uniform(0, 0.5) if enemies_flashed > 0 else 0,
                rng.uniform(0, 1) if grenade_type == 0 else 0,
                damage if grenade_type == 3 else 0,
                damage if grenade_type == 2 else 0,
                # Result (1)
                float(rng.choice([0, 1])),
            ],
            dtype=np.float32,
        )

        filename = f"synth_util_{i:05d}.npz"
        np.savez_compressed(
            output_dir / filename,
            features=features,
            label=np.array(label, dtype=np.int64),
            player=f"765611980000{rng.randint(10000, 99999)}",
            round=rng.randint(1, 31),
        )

    logger.info("Generated %d synthetic utility vectors in %s", count, output_dir)
    return count
