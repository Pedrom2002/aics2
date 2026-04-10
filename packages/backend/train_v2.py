#!/usr/bin/env python3
"""
ML Pipeline V2 — Win Prob v2 + Mamba Regression + Player Rating + Clustering

Key improvements over V1:
- Win Prob: 21 features (vs 5) — equipment, bomb, time, map, hp, scores
- Mamba: REGRESSION instead of classification (predict win delta directly)
- No more heuristic labels — labels come from win prob model output
- Player Rating: CatBoost calibrated against HLTV rating
- Clustering: UMAP + HDBSCAN for player archetypes

Usage:
    python train_v2.py --demos-dir D:/aics2-data/demos/pro --output-dir D:/aics2-data
"""

import argparse
import gc
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))

# Active duty maps for one-hot encoding
MAPS = ["de_mirage", "de_dust2", "de_inferno", "de_nuke", "de_overpass", "de_ancient", "de_anubis"]
MAP_TO_IDX = {m: i for i, m in enumerate(MAPS)}


def _dist_3d(x1, y1, z1, x2, y2, z2) -> float:
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2) ** 0.5


def _build_alive_state_at_tick(parsed, round_num: int, tick: int) -> dict:
    """Returns dict with alive counts, hp avg, equipment values."""
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
        info = {
            "hp": hp,
            "armor": t.get("armor") or 0,
            "equip": t.get("current_equip_value") or 0,
            "is_scoped": t.get("is_scoped") or False,
            "is_walking": t.get("is_walking") or False,
        }
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


def build_win_prob_v2_dataset(demos_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Build training data for IMPROVED win probability model.

    21 features per snapshot:
    - alive_t, alive_ct (normalized 0-1)
    - victim_side (T or CT)
    - round number, score_diff, abs_score_t, abs_score_ct, is_overtime
    - equipment_diff (T-CT) normalized
    - bomb_planted, time_remaining
    - avg_hp_t, avg_hp_ct
    - map_id one-hot (7 maps)
    """
    from src.services.demo_parser import parse_demo

    dem_files = sorted(demos_dir.glob("*.dem"))
    logger.info("Building win prob v2 dataset from %d demos", len(dem_files))

    features_list = []
    labels_list = []

    for i, dem_path in enumerate(dem_files):
        try:
            parsed = parse_demo(dem_path)
        except Exception as e:
            logger.error("  [%d] Failed: %s", i + 1, e)
            continue

        if not parsed.raw_kills or not parsed.raw_ticks or not parsed.rounds:
            continue

        gc.collect()

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

        # Map one-hot
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

            # Time remaining (normalized)
            start_t = round_start_ticks.get(round_num, kill_tick - 4000)
            end_t = round_end_ticks.get(round_num, kill_tick + 4000)
            round_duration_ticks = max(end_t - start_t, 1)
            time_progress = min((kill_tick - start_t) / round_duration_ticks, 1.0)
            time_remaining = 1 - time_progress

            # Equipment diff (T - CT), normalized to ±1
            equip_diff = (state["total_equip_t"] - state["total_equip_ct"]) / 25000.0
            equip_diff = max(min(equip_diff, 1.0), -1.0)

            # Map one-hot
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
                1.0 if round_num > 24 else 0.0,  # is_overtime
                equip_diff,
                1.0 if round_bomb_planted.get(round_num, False) else 0.0,
                time_remaining,
                state["avg_hp_t"] / 100.0,
                state["avg_hp_ct"] / 100.0,
            ] + map_oh  # +7 features

            features_list.append(feat)
            labels_list.append(1 if round_winners[round_num] == "t" else 0)

        if (i + 1) % 10 == 0:
            logger.info("  [%d/%d] %d snapshots", i + 1, len(dem_files), len(features_list))

    X = np.array(features_list, dtype=np.float32)
    y = np.array(labels_list, dtype=np.int32)
    logger.info("Win prob v2 dataset: %d snapshots, %d features", len(X), X.shape[1])
    return X, y


def train_win_prob_v2(X: np.ndarray, y: np.ndarray):
    """Train improved win probability model."""
    import lightgbm as lgb
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "learning_rate": 0.03,
        "num_leaves": 63,
        "max_depth": 7,
        "min_child_samples": 20,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "verbose": -1,
    }

    model = lgb.train(
        params,
        train_data,
        num_boost_round=500,
        valid_sets=[val_data],
        callbacks=[lgb.early_stopping(30), lgb.log_evaluation(50)],
    )

    y_pred = model.predict(X_val)
    acc = accuracy_score(y_val, (y_pred > 0.5).astype(int))
    auc = roc_auc_score(y_val, y_pred)
    logger.info("=" * 60)
    logger.info("WIN PROB V2 — Acc: %.3f, AUC: %.3f", acc, auc)
    logger.info("=" * 60)

    # Feature importance
    feat_names = [
        "alive_t", "alive_ct", "victim_is_t", "round_num", "score_diff",
        "score_t", "score_ct", "is_overtime", "equip_diff", "bomb_planted",
        "time_remaining", "avg_hp_t", "avg_hp_ct",
    ] + [f"map_{m}" for m in MAPS]

    importances = sorted(zip(feat_names, model.feature_importance()), key=lambda x: -x[1])
    logger.info("Top 10 features:")
    for name, imp in importances[:10]:
        logger.info("  %s: %d", name, imp)

    return model


def build_regression_dataset(demos_dir: Path, output_dir: Path, win_prob_model) -> int:
    """Build (64, 18) training windows with WIN DELTA as label (regression).

    Each window's label is the win probability delta caused by that death.
    No heuristics, no classification — pure regression on game impact.
    """
    from src.services.demo_parser import parse_demo

    pos_dir = output_dir / "positioning"
    pos_dir.mkdir(parents=True, exist_ok=True)

    dem_files = sorted(demos_dir.glob("*.dem"))
    total = 0
    deltas = []

    TRADE_RANGE = 800.0
    CLOSE_RANGE = 500.0

    for i, dem_path in enumerate(dem_files):
        logger.info("[%d/%d] %s", i + 1, len(dem_files), dem_path.name)
        try:
            parsed = parse_demo(dem_path)
        except Exception as e:
            logger.error("  Failed: %s", e)
            continue

        if not parsed.raw_kills or not parsed.raw_ticks or not parsed.rounds:
            continue

        gc.collect()

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
        map_oh = [0.0] * len(MAPS)
        if map_idx >= 0:
            map_oh[map_idx] = 1.0

        # Index ticks
        ticks_by_player_round: dict[tuple, list[dict]] = {}
        for t in parsed.raw_ticks:
            key = (t["steamid"], t.get("round_num", 0))
            ticks_by_player_round.setdefault(key, []).append(t)

        # Compute trades
        kills_sorted = sorted(parsed.raw_kills, key=lambda k: k.get("tick", 0))
        traded_sids: set[str] = set()
        for ki, k1 in enumerate(kills_sorted):
            k1_victim = str(k1.get("victim_steamid", ""))
            k1_tick = k1.get("tick", 0)
            k1_attacker = str(k1.get("attacker_steamid", ""))
            for k2 in kills_sorted[ki + 1:]:
                if k2.get("tick", 0) - k1_tick > 320:
                    break
                if str(k2.get("victim_steamid", "")) == k1_attacker:
                    traded_sids.add(k1_victim)
                    break

        window_count = 0
        for kill in parsed.raw_kills:
            victim_sid = kill.get("victim_steamid", "")
            round_num = kill.get("round_num", 0)
            kill_tick = kill.get("tick", 0)
            victim_side = kill.get("victim_side", "")
            if not victim_sid or round_num not in round_winners:
                continue

            victim_x = kill.get("victim_X", 0) or 0
            victim_y = kill.get("victim_Y", 0) or 0
            victim_z = kill.get("victim_Z", 0) or 0
            kill_dist = kill.get("distance", 1000.0) or 1000.0

            # === Compute win prob BEFORE and AFTER ===
            state_before = _build_alive_state_at_tick(parsed, round_num, kill_tick - 1)

            total_rounds = len(parsed.rounds)
            t_score = sum(1 for r in parsed.rounds if r.round_number < round_num and r.winner_side == "t")
            ct_score = sum(1 for r in parsed.rounds if r.round_number < round_num and r.winner_side == "ct")

            start_t = round_start_ticks.get(round_num, kill_tick - 4000)
            end_t = round_end_ticks.get(round_num, kill_tick + 4000)
            time_progress = min((kill_tick - start_t) / max(end_t - start_t, 1), 1.0)
            time_remaining = 1 - time_progress

            equip_diff = (state_before["total_equip_t"] - state_before["total_equip_ct"]) / 25000.0
            equip_diff = max(min(equip_diff, 1.0), -1.0)

            base_feat = [
                state_before["alive_t"] / 5.0,
                state_before["alive_ct"] / 5.0,
                1.0 if victim_side == "t" else 0.0,  # will be set
                round_num / 30.0,
                (t_score - ct_score) / max(total_rounds, 1),
                t_score / 16.0,
                ct_score / 16.0,
                1.0 if round_num > 24 else 0.0,
                equip_diff,
                1.0 if round_bomb_planted.get(round_num, False) else 0.0,
                time_remaining,
                state_before["avg_hp_t"] / 100.0,
                state_before["avg_hp_ct"] / 100.0,
            ] + map_oh

            feat_before = np.array([base_feat], dtype=np.float32)
            feat_before[0, 2] = 0.0  # before kill
            prob_before = win_prob_model.predict(feat_before)[0]

            # After: reduce victim's team alive
            after_feat = base_feat.copy()
            if victim_side == "t":
                after_feat[0] = max((state_before["alive_t"] - 1) / 5.0, 0)
            else:
                after_feat[1] = max((state_before["alive_ct"] - 1) / 5.0, 0)
            after_feat[2] = 1.0 if victim_side == "t" else 0.0  # mark side died

            feat_after = np.array([after_feat], dtype=np.float32)
            prob_after = win_prob_model.predict(feat_after)[0]

            # Delta from victim's team perspective (positive = bad for victim)
            if victim_side == "t":
                win_delta = float(prob_before - prob_after)
            else:
                win_delta = float((1 - prob_before) - (1 - prob_after))

            # Skip irrelevant deaths (low impact)
            # Keep in dataset but flag - all deaths matter for training
            deltas.append(win_delta)

            # === Build feature window ===
            key = (victim_sid, round_num)
            player_ticks = ticks_by_player_round.get(key, [])
            if len(player_ticks) < 5:
                continue

            pre_death = [t for t in player_ticks if t["tick"] <= kill_tick]
            pre_death.sort(key=lambda t: t["tick"])
            pre_death = pre_death[-64:]

            velocity = 0.0
            if len(pre_death) >= 2:
                t1, t2 = pre_death[-2], pre_death[-1]
                dt = max(t2["tick"] - t1["tick"], 1)
                dx = t2.get("X", 0) - t1.get("X", 0)
                dy = t2.get("Y", 0) - t1.get("Y", 0)
                velocity = (dx ** 2 + dy ** 2) ** 0.5 / dt * 64

            # Teammates/enemies count
            teammates_nearby = 0
            enemies_close = 0
            for t in parsed.raw_ticks:
                if t.get("round_num") != round_num:
                    continue
                if abs(t.get("tick", 0) - kill_tick) > 64:
                    continue
                if (t.get("health") or 0) <= 0 or t.get("steamid") == victim_sid:
                    continue
                px, py, pz = t.get("X", 0), t.get("Y", 0), t.get("Z", 0)
                d = _dist_3d(victim_x, victim_y, victim_z, px, py, pz)
                if t.get("side") == victim_side and d <= TRADE_RANGE:
                    teammates_nearby += 1
                elif t.get("side") != victim_side and d <= CLOSE_RANGE:
                    enemies_close += 1

            was_traded = str(victim_sid) in traded_sids

            features = np.zeros((64, 18), dtype=np.float32)
            offset = 64 - len(pre_death)
            for j, t in enumerate(pre_death):
                idx = offset + j
                features[idx, 0] = t.get("X", 0) / 3000.0
                features[idx, 1] = t.get("Y", 0) / 3000.0
                features[idx, 2] = t.get("Z", 0) / 500.0
                features[idx, 3] = (t.get("health") or 0) / 100.0
                features[idx, 4] = (t.get("armor") or 0) / 100.0
                features[idx, 5] = 1.0 if t.get("side") == "ct" else 0.0
                features[idx, 6] = (t.get("current_equip_value") or 0) / 5000.0
                features[idx, 7] = 1.0 if t.get("is_scoped") else 0.0
                features[idx, 8] = 1.0 if t.get("is_walking") else 0.0

            # Death context
            features[:, 9] = kill_dist / 3000.0
            features[:, 10] = 1.0 if kill.get("headshot") else 0.0
            features[:, 11] = teammates_nearby / 4.0
            features[:, 12] = enemies_close / 4.0
            features[:, 13] = 1.0 if was_traded else 0.0
            features[:, 14] = min(velocity, 500.0) / 500.0
            features[:, 15] = time_remaining
            features[:, 16] = 1.0 if round_bomb_planted.get(round_num, False) else 0.0
            features[:, 17] = (state_before["alive_t"] + state_before["alive_ct"]) / 10.0

            sid_str = str(victim_sid)[-6:]
            window_id = f"{dem_path.stem}_r{round_num}_t{kill_tick}_{sid_str}"
            np.savez_compressed(
                pos_dir / f"{window_id}.npz",
                features=features,
                label=np.array(win_delta, dtype=np.float32),
            )
            window_count += 1

        total += window_count
        logger.info("  %d windows", window_count)

    if deltas:
        deltas_arr = np.array(deltas)
        logger.info(
            "Delta distribution — mean: %.3f, std: %.3f, min: %.3f, max: %.3f",
            deltas_arr.mean(), deltas_arr.std(), deltas_arr.min(), deltas_arr.max(),
        )
        logger.info(
            "  >0.20 (high impact): %d (%.0f%%)",
            (deltas_arr > 0.20).sum(), (deltas_arr > 0.20).mean() * 100,
        )
        logger.info(
            "  0.05-0.20 (medium): %d (%.0f%%)",
            ((deltas_arr > 0.05) & (deltas_arr <= 0.20)).sum(),
            ((deltas_arr > 0.05) & (deltas_arr <= 0.20)).mean() * 100,
        )
        logger.info(
            "  <=0.05 (low): %d (%.0f%%)",
            (deltas_arr <= 0.05).sum(), (deltas_arr <= 0.05).mean() * 100,
        )

    return total


def train_mamba_regression(data_dir: Path, output_dir: Path, epochs: int = 100):
    """Train Mamba as REGRESSION model — predict win delta directly."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, Dataset

    # Inline Mamba (same as train_pipeline.py but regression head)
    class SelectiveSSM(nn.Module):
        def __init__(self, d_model, d_state=8, d_conv=4, expand=2):
            super().__init__()
            d_inner = d_model * expand
            self.d_inner = d_inner
            self.d_state = d_state
            self.in_proj = nn.Linear(d_model, d_inner * 2, bias=False)
            self.conv1d = nn.Conv1d(d_inner, d_inner, d_conv, padding=d_conv - 1, groups=d_inner)
            self.x_proj = nn.Linear(d_inner, d_state * 2, bias=False)
            self.dt_proj = nn.Linear(d_state, d_inner, bias=True)
            A = torch.arange(1, d_state + 1, dtype=torch.float32).unsqueeze(0).expand(d_inner, -1)
            self.A_log = nn.Parameter(torch.log(A))
            self.D = nn.Parameter(torch.ones(d_inner))
            self.out_proj = nn.Linear(d_inner, d_model, bias=False)

        def forward(self, x):
            b, l, d = x.shape
            xz = self.in_proj(x)
            x_part, z = xz.chunk(2, dim=-1)
            x_conv = self.conv1d(x_part.transpose(1, 2))[:, :, :l].transpose(1, 2)
            x_conv = F.silu(x_conv)
            x_dbl = self.x_proj(x_conv)
            delta, B_val = x_dbl.split(self.d_state, dim=-1)
            delta = F.softplus(self.dt_proj(delta))
            A = -torch.exp(self.A_log)
            y = torch.zeros_like(x_conv)
            h = torch.zeros(b, self.d_inner, self.d_state, device=x.device)
            for i in range(l):
                h = h * torch.exp(delta[:, i].unsqueeze(-1) * A.unsqueeze(0)) + \
                    B_val[:, i].unsqueeze(1) * x_conv[:, i].unsqueeze(-1)
                y[:, i] = (h * B_val[:, i].unsqueeze(1)).sum(-1) + self.D * x_conv[:, i]
            return self.out_proj(y * F.silu(z))

    class MambaBlock(nn.Module):
        def __init__(self, d_model, **kw):
            super().__init__()
            self.norm = nn.LayerNorm(d_model)
            self.ssm = SelectiveSSM(d_model, **kw)

        def forward(self, x):
            return x + self.ssm(self.norm(x))

    class PositioningMambaRegression(nn.Module):
        def __init__(self):
            super().__init__()
            self.input_proj = nn.Linear(18, 64)
            self.layers = nn.ModuleList([MambaBlock(64, d_state=8, d_conv=4, expand=2) for _ in range(2)])
            self.head = nn.Sequential(
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Dropout(0.25),
                nn.Linear(32, 1),
                nn.Sigmoid(),  # Output in [0, 1] for win prob delta
            )

        def forward(self, x):
            x = self.input_proj(x)
            for layer in self.layers:
                x = layer(x)
            return self.head(x.mean(dim=1)).squeeze(-1)

    class NpzRegressionDataset(Dataset):
        def __init__(self, files):
            self.files = files

        def __len__(self):
            return len(self.files)

        def __getitem__(self, idx):
            d = np.load(self.files[idx])
            return torch.from_numpy(d["features"]), torch.tensor(float(d["label"]), dtype=torch.float32)

    pos_dir = data_dir / "positioning"
    files = sorted(pos_dir.glob("*.npz"))
    if not files:
        logger.error("No training data")
        return

    # Split by match
    demo_stems = [f.stem.rsplit("_r", 1)[0] for f in files]
    unique_stems = sorted(set(demo_stems))
    np.random.seed(42)
    np.random.shuffle(unique_stems)
    split_idx = int(0.8 * len(unique_stems))
    train_stems = set(unique_stems[:split_idx])

    train_files = [f for f, s in zip(files, demo_stems) if s in train_stems]
    val_files = [f for f, s in zip(files, demo_stems) if s not in train_stems]

    logger.info("Split by match: %d train (%d matches), %d val (%d matches)",
                len(train_files), split_idx, len(val_files), len(unique_stems) - split_idx)

    train_loader = DataLoader(NpzRegressionDataset(train_files), batch_size=32, shuffle=True)
    val_loader = DataLoader(NpzRegressionDataset(val_files), batch_size=32, shuffle=False)

    model = PositioningMambaRegression()
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.02)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.MSELoss()

    checkpoint_dir = output_dir / "checkpoints" / "positioning"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    best_val_mae = float("inf")
    no_improve = 0
    patience = 15

    for epoch in range(epochs):
        model.train()
        train_loss = 0
        train_mae = 0
        n_train = 0
        for feats, labels in train_loader:
            optimizer.zero_grad()
            preds = model(feats)
            loss = criterion(preds, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item() * feats.size(0)
            train_mae += (preds - labels).abs().sum().item()
            n_train += feats.size(0)

        model.eval()
        val_loss = 0
        val_mae = 0
        n_val = 0
        with torch.no_grad():
            for feats, labels in val_loader:
                preds = model(feats)
                loss = criterion(preds, labels)
                val_loss += loss.item() * feats.size(0)
                val_mae += (preds - labels).abs().sum().item()
                n_val += feats.size(0)

        scheduler.step()
        train_mse = train_loss / n_train
        val_mse = val_loss / n_val
        train_mae_avg = train_mae / n_train
        val_mae_avg = val_mae / n_val

        logger.info(
            "Epoch %d/%d - train_mse=%.4f train_mae=%.4f val_mse=%.4f val_mae=%.4f",
            epoch + 1, epochs, train_mse, train_mae_avg, val_mse, val_mae_avg,
        )

        if val_mae_avg < best_val_mae:
            best_val_mae = val_mae_avg
            no_improve = 0
            torch.save(model.state_dict(), checkpoint_dir / "best_model.pt")
            logger.info("  Saved best model (val_mae=%.4f)", best_val_mae)
        else:
            no_improve += 1
            if no_improve >= patience:
                logger.info("  Early stopping at epoch %d", epoch + 1)
                break

    torch.save(model.state_dict(), checkpoint_dir / "final_model.pt")
    logger.info("Training complete. Best val_mae=%.4f", best_val_mae)


def main():
    parser = argparse.ArgumentParser(description="ML Pipeline V2")
    parser.add_argument("--demos-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--skip-winprob", action="store_true")
    parser.add_argument("--skip-relabel", action="store_true")
    parser.add_argument("--skip-train", action="store_true")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("ML PIPELINE V2 — Win Prob v2 + Mamba Regression")
    logger.info("=" * 60)

    win_prob_path = args.output_dir / "checkpoints" / "win_prob_v2.lgb"

    if not args.skip_winprob:
        logger.info("\n[1/3] Building & training Win Prob v2 (21 features)...")
        X, y = build_win_prob_v2_dataset(args.demos_dir)
        win_prob_model = train_win_prob_v2(X, y)
        win_prob_path.parent.mkdir(parents=True, exist_ok=True)
        win_prob_model.save_model(str(win_prob_path))
        logger.info("Win prob v2 saved to %s", win_prob_path)
    else:
        import lightgbm as lgb
        win_prob_model = lgb.Booster(model_file=str(win_prob_path))
        logger.info("Loaded existing win prob v2 from %s", win_prob_path)

    if not args.skip_relabel:
        logger.info("\n[2/3] Building regression dataset (win delta as label)...")
        import shutil
        pos_dir = args.output_dir / "positioning"
        if pos_dir.exists():
            shutil.rmtree(pos_dir)
        total = build_regression_dataset(args.demos_dir, args.output_dir, win_prob_model)
        logger.info("Regression dataset: %d windows", total)

    if not args.skip_train:
        logger.info("\n[3/3] Training Mamba regression model...")
        train_mamba_regression(args.output_dir, args.output_dir, epochs=args.epochs)

    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE V2 COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
