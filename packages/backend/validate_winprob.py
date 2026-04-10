#!/usr/bin/env python3
"""
Rigorous validation of win probability model.

Tests:
1. AUC with match-based split (not random)
2. AUC without score features (data leakage check)
3. AUC per game situation (1v1, 4v5, etc.)
4. Calibration (Brier score, calibration curve)

Usage:
    python validate_winprob.py --demos-dir D:/aics2-data/demos/pro
"""

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))

MAPS = ["de_mirage", "de_dust2", "de_inferno", "de_nuke", "de_overpass", "de_ancient", "de_anubis"]
MAP_TO_IDX = {m: i for i, m in enumerate(MAPS)}


def _build_alive_state_at_tick(parsed, round_num, tick):
    alive_t = []
    alive_ct = []
    seen = set()
    for t in parsed.raw_ticks:
        if t.get("round_num") != round_num:
            continue
        if abs(t.get("tick", 0) - tick) > 32:
            continue
        sid = t.get("steamid")
        if sid in seen:
            continue
        seen.add(sid)
        hp = t.get("health") or 0
        if hp <= 0:
            continue
        info = {"hp": hp, "equip": t.get("current_equip_value") or 0}
        if t.get("side") == "t":
            alive_t.append(info)
        else:
            alive_ct.append(info)
    return {
        "alive_t": min(len(alive_t), 5),
        "alive_ct": min(len(alive_ct), 5),
        "avg_hp_t": np.mean([p["hp"] for p in alive_t]) if alive_t else 0,
        "avg_hp_ct": np.mean([p["hp"] for p in alive_ct]) if alive_ct else 0,
        "total_equip_t": sum(p["equip"] for p in alive_t),
        "total_equip_ct": sum(p["equip"] for p in alive_ct),
    }


def build_dataset_with_metadata(demos_dir: Path):
    """Build dataset and return (X, y, demo_idx, situations) for stratified analysis."""
    from src.services.demo_parser import parse_demo

    dem_files = sorted(demos_dir.glob("*.dem"))
    logger.info("Loading %d demos for validation...", len(dem_files))

    features_list = []
    labels_list = []
    demo_indices = []
    situations = []  # (alive_t, alive_ct) tuples

    for di, dem_path in enumerate(dem_files):
        try:
            parsed = parse_demo(dem_path)
        except Exception:
            continue

        if not parsed.raw_kills or not parsed.raw_ticks or not parsed.rounds:
            continue

        round_winners = {}
        round_bomb_planted = {}
        round_start_ticks = {}
        round_end_ticks = {}
        for r in parsed.rounds:
            if r.winner_side:
                round_winners[r.round_number] = r.winner_side
            round_bomb_planted[r.round_number] = bool(r.bomb_planted)
            if r.start_tick is not None:
                round_start_ticks[r.round_number] = r.start_tick
            if r.end_tick is not None:
                round_end_ticks[r.round_number] = r.end_tick

        map_name = parsed.map_name or "unknown"
        map_idx = MAP_TO_IDX.get(map_name, -1)

        for kill in parsed.raw_kills:
            round_num = kill.get("round_num", 0)
            kill_tick = kill.get("tick", 0)
            victim_side = kill.get("victim_side", "")
            if round_num not in round_winners:
                continue

            state = _build_alive_state_at_tick(parsed, round_num, kill_tick - 1)

            total_rounds = len(parsed.rounds)
            t_score = sum(1 for r in parsed.rounds if r.round_number < round_num and r.winner_side == "t")
            ct_score = sum(1 for r in parsed.rounds if r.round_number < round_num and r.winner_side == "ct")

            start_t = round_start_ticks.get(round_num, kill_tick - 4000)
            end_t = round_end_ticks.get(round_num, kill_tick + 4000)
            time_progress = min((kill_tick - start_t) / max(end_t - start_t, 1), 1.0)
            time_remaining = 1 - time_progress

            equip_diff = (state["total_equip_t"] - state["total_equip_ct"]) / 25000.0
            equip_diff = max(min(equip_diff, 1.0), -1.0)

            map_oh = [0.0] * len(MAPS)
            if map_idx >= 0:
                map_oh[map_idx] = 1.0

            feat = [
                state["alive_t"] / 5.0,
                state["alive_ct"] / 5.0,
                1.0 if victim_side == "t" else 0.0,
                round_num / 30.0,
                (t_score - ct_score) / max(total_rounds, 1),
                t_score / 16.0,
                ct_score / 16.0,
                1.0 if round_num > 24 else 0.0,
                equip_diff,
                1.0 if round_bomb_planted.get(round_num, False) else 0.0,
                time_remaining,
                state["avg_hp_t"] / 100.0,
                state["avg_hp_ct"] / 100.0,
            ] + map_oh

            features_list.append(feat)
            labels_list.append(1 if round_winners[round_num] == "t" else 0)
            demo_indices.append(di)
            situations.append((state["alive_t"], state["alive_ct"]))

        if (di + 1) % 20 == 0:
            logger.info("  [%d/%d] %d snapshots", di + 1, len(dem_files), len(features_list))

    return (
        np.array(features_list, dtype=np.float32),
        np.array(labels_list, dtype=np.int32),
        np.array(demo_indices, dtype=np.int32),
        situations,
    )


def test_match_split(X, y, demo_idx):
    """Test 1: Train/val split by match (not random)."""
    import lightgbm as lgb
    from sklearn.metrics import accuracy_score, roc_auc_score

    unique_demos = np.unique(demo_idx)
    np.random.seed(42)
    np.random.shuffle(unique_demos)
    split = int(0.8 * len(unique_demos))
    train_demos = set(unique_demos[:split])

    train_mask = np.isin(demo_idx, list(train_demos))
    val_mask = ~train_mask

    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]

    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    model = lgb.train(
        {"objective": "binary", "metric": "binary_logloss", "learning_rate": 0.03,
         "num_leaves": 63, "max_depth": 7, "verbose": -1},
        train_data, num_boost_round=500, valid_sets=[val_data],
        callbacks=[lgb.early_stopping(30), lgb.log_evaluation(0)],
    )

    y_pred = model.predict(X_val)
    auc = roc_auc_score(y_val, y_pred)
    acc = accuracy_score(y_val, (y_pred > 0.5).astype(int))

    logger.info("=" * 60)
    logger.info("TEST 1: Match-based split")
    logger.info("=" * 60)
    logger.info("  Train: %d snapshots from %d matches", len(X_train), split)
    logger.info("  Val:   %d snapshots from %d matches", len(X_val), len(unique_demos) - split)
    logger.info("  AUC: %.3f, Accuracy: %.3f", auc, acc)
    return model, X_val, y_val, auc


def test_no_score_features(X, y, demo_idx):
    """Test 2: Same model without score_diff, score_t, score_ct, round_num."""
    import lightgbm as lgb
    from sklearn.metrics import accuracy_score, roc_auc_score

    # Remove indices: 3=round_num, 4=score_diff, 5=score_t, 6=score_ct
    keep_indices = [i for i in range(X.shape[1]) if i not in [3, 4, 5, 6]]
    X_no_score = X[:, keep_indices]

    unique_demos = np.unique(demo_idx)
    np.random.seed(42)
    np.random.shuffle(unique_demos)
    split = int(0.8 * len(unique_demos))
    train_demos = set(unique_demos[:split])

    train_mask = np.isin(demo_idx, list(train_demos))
    val_mask = ~train_mask

    X_train, y_train = X_no_score[train_mask], y[train_mask]
    X_val, y_val = X_no_score[val_mask], y[val_mask]

    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    model = lgb.train(
        {"objective": "binary", "metric": "binary_logloss", "learning_rate": 0.03,
         "num_leaves": 63, "max_depth": 7, "verbose": -1},
        train_data, num_boost_round=500, valid_sets=[val_data],
        callbacks=[lgb.early_stopping(30), lgb.log_evaluation(0)],
    )

    y_pred = model.predict(X_val)
    auc = roc_auc_score(y_val, y_pred)
    acc = accuracy_score(y_val, (y_pred > 0.5).astype(int))

    logger.info("=" * 60)
    logger.info("TEST 2: Without score features (only game state)")
    logger.info("=" * 60)
    logger.info("  Features dropped: round_num, score_diff, score_t, score_ct")
    logger.info("  AUC: %.3f, Accuracy: %.3f", auc, acc)
    return auc


def test_per_situation(model, X_val, y_val, situations_val):
    """Test 3: AUC per game situation (1v1, 4v5, etc.)."""
    from sklearn.metrics import roc_auc_score

    logger.info("=" * 60)
    logger.info("TEST 3: AUC per game situation")
    logger.info("=" * 60)

    by_situation = defaultdict(lambda: ([], []))
    y_pred = model.predict(X_val)

    for i, sit in enumerate(situations_val):
        key = f"{sit[0]}v{sit[1]}"
        by_situation[key][0].append(y_val[i])
        by_situation[key][1].append(y_pred[i])

    logger.info(f"  {'Situation':<10} {'N':>6} {'AUC':>8} {'Mean P':>8}")
    logger.info("-" * 40)
    for sit_key in sorted(by_situation.keys()):
        labels, preds = by_situation[sit_key]
        if len(set(labels)) < 2 or len(labels) < 30:
            continue
        auc = roc_auc_score(labels, preds)
        mean_p = np.mean(preds)
        logger.info(f"  {sit_key:<10} {len(labels):>6} {auc:>8.3f} {mean_p:>8.3f}")


def test_calibration(model, X_val, y_val):
    """Test 4: Calibration check."""
    from sklearn.calibration import calibration_curve
    from sklearn.metrics import brier_score_loss

    y_pred = model.predict(X_val)
    brier = brier_score_loss(y_val, y_pred)

    logger.info("=" * 60)
    logger.info("TEST 4: Calibration")
    logger.info("=" * 60)
    logger.info("  Brier score: %.4f (lower=better, 0=perfect, 0.25=random)", brier)

    # Calibration curve
    fraction_pos, mean_pred = calibration_curve(y_val, y_pred, n_bins=10)
    logger.info(f"  {'Predicted':>10} {'Actual':>10} {'Diff':>8}")
    logger.info("-" * 35)
    for mp, fp in zip(mean_pred, fraction_pos):
        diff = abs(mp - fp)
        marker = " ✓" if diff < 0.05 else " ✗" if diff > 0.10 else ""
        logger.info(f"  {mp:>10.3f} {fp:>10.3f} {diff:>8.3f}{marker}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demos-dir", type=Path, required=True)
    args = parser.parse_args()

    logger.info("Loading dataset...")
    X, y, demo_idx, situations = build_dataset_with_metadata(args.demos_dir)
    logger.info("Total snapshots: %d from %d demos", len(X), len(np.unique(demo_idx)))

    # Test 1: Match split
    model, X_val, y_val, auc_full = test_match_split(X, y, demo_idx)

    # Get val situations
    unique_demos = np.unique(demo_idx)
    np.random.seed(42)
    np.random.shuffle(unique_demos)
    split = int(0.8 * len(unique_demos))
    train_demos = set(unique_demos[:split])
    val_mask = ~np.isin(demo_idx, list(train_demos))
    situations_val = [situations[i] for i in range(len(situations)) if val_mask[i]]

    # Test 2: No score
    auc_no_score = test_no_score_features(X, y, demo_idx)

    # Test 3: Per situation
    test_per_situation(model, X_val, y_val, situations_val)

    # Test 4: Calibration
    test_calibration(model, X_val, y_val)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("HONESTY CHECK")
    logger.info("=" * 60)
    logger.info("  Full model AUC:        %.3f", auc_full)
    logger.info("  Without score features: %.3f", auc_no_score)
    logger.info("  Drop:                   %.3f", auc_full - auc_no_score)
    if auc_full - auc_no_score > 0.10:
        logger.info("  Verdict: ⚠️  Score features dominate — partial leakage")
    else:
        logger.info("  Verdict: ✓ Score features add value but model is genuine")


if __name__ == "__main__":
    main()
