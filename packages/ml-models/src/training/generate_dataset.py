"""
Generate training dataset from parsed CS2 demos.

Extracts 64-tick positioning windows with heuristic labels from parsed demo data
and saves as .npz files ready for model training.

Usage:
    python -m src.training.generate_dataset --demos-dir ./demos --output-dir ./data/positioning

Each .npz file contains:
    features: (64, 18) float32 — normalized tick features
    label: int — 0 (no_error), 1 (minor), 2 (critical)
    player: str — steam ID
    round: int — round number
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def generate_from_demo(dem_path: Path, output_dir: Path) -> int:
    """Parse a single demo and generate training windows.

    Returns number of windows generated.
    """
    # Import parser — add backend to path if needed
    backend_src = dem_path.parent
    while backend_src.name != "packages" and backend_src != backend_src.parent:
        backend_src = backend_src.parent
    backend_path = backend_src / "backend"
    if backend_path.exists() and str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    try:
        from src.services.demo_parser import parse_demo
        from src.services.ml_feature_extractor import (
            PlayerDeathEvent,
            TickSnapshot,
            extract_positioning_windows,
            label_positioning_from_parsed_data,
        )
    except ImportError:
        logger.error(
            "Cannot import parser/feature extractor. "
            "Run from packages/ml-models with backend in PYTHONPATH."
        )
        return 0

    # Parse demo
    logger.info("Parsing %s", dem_path.name)
    try:
        parsed = parse_demo(dem_path)
    except Exception as e:
        logger.error("Failed to parse %s: %s", dem_path.name, e)
        return 0

    # Generate death events for heuristic labeling
    death_events = label_positioning_from_parsed_data(
        kills_df_rows=parsed.raw_kills,
        ticks_df_rows=parsed.raw_ticks,
        trade_kill_sids=parsed.trade_kill_victim_sids,
        total_rounds=parsed.total_rounds,
    )

    # Convert raw ticks to TickSnapshot objects
    tick_snapshots: list[TickSnapshot] = []
    for row in parsed.raw_ticks:
        try:
            tick_snapshots.append(
                TickSnapshot(
                    tick=row.get("tick", 0),
                    round_number=row.get("round_num", 0),
                    player_steam_id=str(row.get("steamid", "")),
                    pos_x=float(row.get("X", row.get("x", 0))),
                    pos_y=float(row.get("Y", row.get("y", 0))),
                    pos_z=float(row.get("Z", row.get("z", 0))),
                    yaw=float(row.get("yaw", row.get("viewangle_yaw", 0))),
                    pitch=float(row.get("pitch", row.get("viewangle_pitch", 0))),
                    velocity=float(row.get("velocity", 0)),
                    health=int(row.get("health", 100)),
                    armor=int(row.get("armor", 0)),
                    is_alive=bool(row.get("is_alive", True)),
                )
            )
        except (ValueError, TypeError):
            continue

    if not tick_snapshots:
        logger.warning("No tick data in %s, skipping", dem_path.name)
        return 0

    # Extract windows with heuristic labels
    windows = extract_positioning_windows(
        tick_snapshots, death_events, window_size=64, stride=32
    )

    # Save each window as .npz
    output_dir.mkdir(parents=True, exist_ok=True)
    demo_stem = dem_path.stem
    count = 0

    for i, w in enumerate(windows):
        if w.label is None:
            continue

        filename = f"{demo_stem}_r{w.round_number}_{w.player_steam_id[-4:]}_{i:04d}.npz"
        np.savez_compressed(
            output_dir / filename,
            features=w.features,
            label=np.array(w.label, dtype=np.int64),
            player=w.player_steam_id,
            round=w.round_number,
        )
        count += 1

    logger.info("Generated %d windows from %s (%d labeled)", count, dem_path.name, count)
    return count


def generate_dataset(demos_dir: Path, output_dir: Path) -> dict:
    """Process all .dem files in a directory and generate training data.

    Returns summary statistics.
    """
    dem_files = sorted(demos_dir.glob("**/*.dem"))
    if not dem_files:
        logger.error("No .dem files found in %s", demos_dir)
        return {"error": "no_demos", "total": 0}

    logger.info("Found %d demo files in %s", len(dem_files), demos_dir)

    total_windows = 0
    processed = 0
    failed = 0

    for dem_path in dem_files:
        try:
            count = generate_from_demo(dem_path, output_dir)
            total_windows += count
            processed += 1
        except Exception as e:
            logger.error("Failed to process %s: %s", dem_path.name, e)
            failed += 1

    # Count label distribution
    label_counts = {0: 0, 1: 0, 2: 0}
    for npz_file in output_dir.glob("*.npz"):
        data = np.load(npz_file)
        label = int(data["label"])
        label_counts[label] = label_counts.get(label, 0) + 1

    summary = {
        "demos_processed": processed,
        "demos_failed": failed,
        "total_windows": total_windows,
        "label_distribution": {
            "no_error": label_counts.get(0, 0),
            "minor": label_counts.get(1, 0),
            "critical": label_counts.get(2, 0),
        },
    }

    logger.info(
        "Dataset generation complete: %d demos → %d windows "
        "(no_error=%d, minor=%d, critical=%d)",
        processed,
        total_windows,
        label_counts.get(0, 0),
        label_counts.get(1, 0),
        label_counts.get(2, 0),
    )

    return summary


def main():
    parser = argparse.ArgumentParser(description="Generate ML training dataset from CS2 demos")
    parser.add_argument("--demos-dir", type=Path, required=True, help="Directory with .dem files")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./data/positioning"),
        help="Output directory for .npz files",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    summary = generate_dataset(args.demos_dir, args.output_dir)
    print(f"\nDataset summary: {summary}")


if __name__ == "__main__":
    main()
