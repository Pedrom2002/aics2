"""
Training script for the Strategy Classification GNN (GraphSAGE).

Uses weak supervision: the deterministic heuristic from
``src.models.strategy_gnn`` labels rounds, and the GNN learns to generalize
the same mapping from raw per-player graph features instead of hand-crafted
aggregates. When a ``--real-data`` directory is supplied, it reads
``*.npz`` files with keys ``x`` (5,16), ``adj`` (5,5), ``side`` (str),
``round_data`` (dict) — otherwise it generates synthetic graphs.

Reduces the native taxonomy (15 T + 10 CT) to coarser families that are
more robust under weak supervision: execute / fake / default / eco /
force / save (T) and stack / aggressive / default / retake / save (CT).

Usage:
    python -m src.training.train_strategy_gnn --side T --epochs 20
    python -m src.training.train_strategy_gnn --side CT --real-data ./data/strategy
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, Dataset, random_split

from src.models.strategy_gnn import (
    CT_STRATEGIES,
    NODE_FEATURES,
    T_STRATEGIES,
    StrategyClassifier,
    StrategyGNNConfig,
    predict_strategy,
)

logger = logging.getLogger(__name__)

# Coarse taxonomy mapping (weak-supervision target)
T_COARSE = {
    "a_execute": "execute",
    "b_execute": "execute",
    "split_a": "execute",
    "split_b": "execute",
    "fast_a": "execute",
    "fast_b": "execute",
    "force_buy_execute": "force",
    "a_fake_b": "fake",
    "b_fake_a": "fake",
    "default_spread": "default",
    "slow_default": "default",
    "mid_control_to_a": "default",
    "mid_control_to_b": "default",
    "eco_rush": "eco",
    "save": "save",
}
T_COARSE_LABELS = ["execute", "fake", "default", "eco", "force", "save"]

CT_COARSE = {
    "stack_a": "stack",
    "stack_b": "stack",
    "aggressive_mid": "aggressive",
    "aggressive_a": "aggressive",
    "standard_2_1_2": "default",
    "passive_default": "default",
    "mixed": "default",
    "retake_setup": "retake",
    "anti_eco_push": "aggressive",
    "save": "save",
}
CT_COARSE_LABELS = ["stack", "aggressive", "default", "retake", "save"]


def _coarse_label(fine: str, side: str) -> str:
    table = T_COARSE if side == "T" else CT_COARSE
    return table.get(fine, "default")


def _label_index(coarse: str, side: str) -> int:
    labels = T_COARSE_LABELS if side == "T" else CT_COARSE_LABELS
    return labels.index(coarse)


def _synth_round(side: str) -> tuple[np.ndarray, np.ndarray, dict]:
    """Generate a plausible random round and its 5-node graph."""
    eco = random.choice([2000, 3500, 8000, 12000, 18000, 22000])
    enemy = random.choice([2500, 4000, 10000, 15000, 20000])
    time_remaining = random.random()
    bomb_planted = random.random() < 0.15
    bomb_site = random.choice(["A", "B"])
    avg_x = random.uniform(-1500, 1500)
    avg_y = random.uniform(-1500, 1500)
    alive = random.randint(1, 5)
    a_count = random.randint(0, alive)
    b_count = alive - a_count

    round_data = {
        "side": side,
        "equipment_value": eco,
        "enemy_equipment_value": enemy,
        "time_remaining": time_remaining,
        "bomb_planted": bomb_planted,
        "bomb_site": bomb_site,
        "avg_team_x": avg_x,
        "avg_team_y": avg_y,
        "alive_team": alive,
        "ct_at_a": a_count,
        "ct_at_b": b_count,
    }

    # 5 players × 16 features — positions jittered around team centroid
    x = np.zeros((5, NODE_FEATURES), dtype=np.float32)
    for p in range(5):
        px = (avg_x + random.uniform(-400, 400)) / 2000.0
        py = (avg_y + random.uniform(-400, 400)) / 2000.0
        alive_p = 1.0 if p < alive else 0.0
        hp = random.uniform(0.2, 1.0) if alive_p else 0.0
        armor = random.uniform(0, 1)
        weapon_value = random.uniform(0, 1)
        has_bomb = 1.0 if (side == "T" and p == 0 and not bomb_planted) else 0.0
        x[p] = [
            px, py, alive_p, hp, armor, weapon_value, has_bomb,
            eco / 25000.0, enemy / 25000.0, time_remaining,
            float(bomb_planted), 1.0 if bomb_site == "A" else 0.0,
            alive / 5.0, a_count / 5.0, b_count / 5.0, random.random(),
        ]

    # Adjacency: proximity threshold
    adj = np.zeros((5, 5), dtype=np.float32)
    for i in range(5):
        for j in range(5):
            if i == j:
                continue
            d = np.linalg.norm(x[i, :2] - x[j, :2])
            if d < 0.4:
                adj[i, j] = 1.0
    # Ensure each node has at least one neighbor
    for i in range(5):
        if adj[i].sum() == 0:
            j = (i + 1) % 5
            adj[i, j] = adj[j, i] = 1.0

    return x, adj, round_data


class StrategyDataset(Dataset):
    def __init__(self, side: str, size: int, real_dir: Path | None):
        self.side = side
        self.items: list[tuple[np.ndarray, np.ndarray, int]] = []

        if real_dir and real_dir.exists():
            for f in sorted(real_dir.glob("*.npz")):
                data = np.load(f, allow_pickle=True)
                if str(data.get("side", side)) != side:
                    continue
                round_data = data["round_data"].item() if "round_data" in data.files else {}
                round_data.setdefault("side", side)
                pred = predict_strategy(round_data)
                coarse = _coarse_label(pred["strategy_type"], side)
                self.items.append((data["x"].astype(np.float32),
                                   data["adj"].astype(np.float32),
                                   _label_index(coarse, side)))
            logger.info("Loaded %d real rounds from %s", len(self.items), real_dir)
            if not self.items:
                logger.warning("No real data found — falling back to synthetic")

        if not self.items:
            for _ in range(size):
                x, adj, round_data = _synth_round(side)
                pred = predict_strategy(round_data)
                coarse = _coarse_label(pred["strategy_type"], side)
                self.items.append((x, adj, _label_index(coarse, side)))

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int):
        x, adj, y = self.items[idx]
        return torch.from_numpy(x), torch.from_numpy(adj), torch.tensor(y, dtype=torch.long)


def _collate(batch):
    xs = torch.stack([b[0] for b in batch])
    adjs = torch.stack([b[1] for b in batch])
    ys = torch.stack([b[2] for b in batch])
    return xs, adjs, ys


def train(
    side: str,
    epochs: int,
    batch_size: int,
    lr: float,
    synthetic_size: int,
    real_dir: Path | None,
    output_dir: Path,
    device: str,
) -> dict:
    assert side in ("T", "CT")
    num_classes = len(T_COARSE_LABELS if side == "T" else CT_COARSE_LABELS)

    dataset = StrategyDataset(side, synthetic_size, real_dir)
    n = len(dataset)
    n_val = max(1, int(0.1 * n))
    n_test = max(1, int(0.1 * n))
    n_train = n - n_val - n_test
    train_ds, val_ds, test_ds = random_split(
        dataset, [n_train, n_val, n_test], generator=torch.Generator().manual_seed(42)
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=_collate)
    val_loader = DataLoader(val_ds, batch_size=batch_size, collate_fn=_collate)
    test_loader = DataLoader(test_ds, batch_size=batch_size, collate_fn=_collate)

    config = StrategyGNNConfig(
        num_t_strategies=num_classes if side == "T" else len(T_STRATEGIES),
        num_ct_strategies=num_classes if side == "CT" else len(CT_STRATEGIES),
    )
    model = StrategyClassifier(config=config, side=side).to(device)

    # The classifier head expects fine-vocab size — replace with coarse head
    model.classifier = nn.Sequential(
        nn.Linear(config.output_dim, 64),
        nn.ReLU(),
        nn.Dropout(config.dropout),
        nn.Linear(64, num_classes),
    ).to(device)

    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for x, adj, y in train_loader:
            x, adj, y = x.to(device), adj.to(device), y.to(device)
            optimizer.zero_grad()
            logits = model(x, adj)
            loss = criterion(logits, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item() * y.size(0)
        scheduler.step()

        model.eval()
        correct = total = 0
        with torch.no_grad():
            for x, adj, y in val_loader:
                x, adj, y = x.to(device), adj.to(device), y.to(device)
                preds = model(x, adj).argmax(dim=-1)
                correct += (preds == y).sum().item()
                total += y.size(0)
        val_acc = correct / max(total, 1)
        logger.info(
            "epoch=%d train_loss=%.4f val_acc=%.4f", epoch, total_loss / max(n_train, 1), val_acc
        )
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            output_dir.mkdir(parents=True, exist_ok=True)
            torch.save(
                {"model_state_dict": model.state_dict(), "config": config.__dict__, "side": side},
                output_dir / f"strategy_gnn_{side.lower()}.pt",
            )

    # Test set
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for x, adj, y in test_loader:
            x, adj, y = x.to(device), adj.to(device), y.to(device)
            preds = model(x, adj).argmax(dim=-1)
            correct += (preds == y).sum().item()
            total += y.size(0)
    test_acc = correct / max(total, 1)
    logger.info("test_acc=%.4f", test_acc)

    metrics = {
        "side": side,
        "best_val_acc": round(best_val_acc, 4),
        "test_acc": round(test_acc, 4),
        "num_classes": num_classes,
        "dataset_size": n,
        "labels": T_COARSE_LABELS if side == "T" else CT_COARSE_LABELS,
    }
    (output_dir / f"strategy_gnn_{side.lower()}_metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Train the Strategy GNN (weak supervision)")
    parser.add_argument("--side", choices=("T", "CT", "both"), default="both")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--synthetic-size", type=int, default=4000)
    parser.add_argument("--real-data", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("models/strategy_gnn"))
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    sides = ["T", "CT"] if args.side == "both" else [args.side]
    for side in sides:
        train(
            side=side,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            synthetic_size=args.synthetic_size,
            real_dir=args.real_data,
            output_dir=args.output_dir,
            device=args.device,
        )


if __name__ == "__main__":
    main()
