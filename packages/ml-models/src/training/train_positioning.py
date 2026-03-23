"""
Training script for the Positioning Error Detection Model (Mamba).

Usage:
    python -m src.training.train_positioning --data-dir ./data --epochs 50

Tracks experiments with MLflow (if installed).
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader, Dataset, random_split

from src.models.positioning_mamba import (
    NUM_CLASSES,
    NUM_FEATURES,
    SEQ_LEN,
    FocalLoss,
    MambaConfig,
    PositioningMamba,
)

logger = logging.getLogger(__name__)


class PositioningDataset(Dataset):
    """Dataset of (64, 18) positioning windows with labels."""

    def __init__(self, data_dir: Path):
        self.features: list[np.ndarray] = []
        self.labels: list[int] = []

        # Load .npz files from data directory
        for f in sorted(data_dir.glob("*.npz")):
            data = np.load(f)
            self.features.append(data["features"])  # (64, 18)
            self.labels.append(int(data["label"]))

        if not self.features:
            logger.warning("No training data found in %s", data_dir)

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = torch.tensor(self.features[idx], dtype=torch.float32)
        y = torch.tensor(self.labels[idx], dtype=torch.long)
        return x, y


def train(
    data_dir: Path,
    output_dir: Path,
    epochs: int = 50,
    batch_size: int = 256,
    lr: float = 1e-3,
    d_model: int = 128,
    n_layers: int = 2,
    val_split: float = 0.2,
    use_mlflow: bool = True,
) -> dict:
    """Train the positioning Mamba model.

    Args:
        data_dir: Directory with .npz training files
        output_dir: Where to save model checkpoints
        epochs: Number of training epochs
        batch_size: Batch size
        lr: Learning rate
        d_model: Model hidden dimension
        n_layers: Number of Mamba layers
        val_split: Fraction for validation
        use_mlflow: Whether to log to MLflow

    Returns:
        Training metrics dict.
    """
    # Setup MLflow
    mlflow_run = None
    if use_mlflow:
        try:
            import mlflow

            mlflow.set_experiment("positioning-errors-v1")
            mlflow_run = mlflow.start_run()
            mlflow.log_params(
                {
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "lr": lr,
                    "d_model": d_model,
                    "n_layers": n_layers,
                    "val_split": val_split,
                }
            )
        except ImportError:
            logger.info("MLflow not installed, skipping experiment tracking")
            use_mlflow = False

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training on %s", device)

    # Dataset
    dataset = PositioningDataset(data_dir)
    if len(dataset) == 0:
        logger.error("No data found. Generate training data first.")
        return {"error": "no_data"}

    val_size = int(len(dataset) * val_split)
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    # Model
    config = MambaConfig(d_model=d_model, n_layers=n_layers)
    model = PositioningMamba(config).to(device)
    param_count = PositioningMamba.count_parameters(model)
    logger.info("Model parameters: %d", param_count)

    # Training setup
    loss_fn = FocalLoss()
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_f1 = 0.0
    best_metrics = {}

    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)

            optimizer.zero_grad()
            logits = model(batch_x)
            loss = loss_fn(logits, batch_y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item() * len(batch_x)
            train_correct += (logits.argmax(dim=1) == batch_y).sum().item()
            train_total += len(batch_x)

        scheduler.step()
        avg_train_loss = train_loss / max(train_total, 1)
        train_acc = train_correct / max(train_total, 1)

        # Validate
        model.eval()
        val_loss = 0.0
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                logits = model(batch_x)
                loss = loss_fn(logits, batch_y)
                val_loss += loss.item() * len(batch_x)
                all_preds.extend(logits.argmax(dim=1).cpu().numpy())
                all_labels.extend(batch_y.cpu().numpy())

        avg_val_loss = val_loss / max(len(all_labels), 1)
        preds_arr = np.array(all_preds)
        labels_arr = np.array(all_labels)
        val_acc = (preds_arr == labels_arr).mean()

        # Per-class metrics
        precision_per_class = []
        recall_per_class = []
        for c in range(NUM_CLASSES):
            tp = ((preds_arr == c) & (labels_arr == c)).sum()
            fp = ((preds_arr == c) & (labels_arr != c)).sum()
            fn = ((preds_arr != c) & (labels_arr == c)).sum()
            prec = tp / max(tp + fp, 1)
            rec = tp / max(tp + fn, 1)
            precision_per_class.append(prec)
            recall_per_class.append(rec)

        avg_precision = np.mean(precision_per_class)
        avg_recall = np.mean(recall_per_class)
        f1 = 2 * avg_precision * avg_recall / max(avg_precision + avg_recall, 1e-8)

        logger.info(
            "Epoch %d/%d — train_loss: %.4f, val_loss: %.4f, val_acc: %.3f, "
            "precision: %.3f, recall: %.3f, F1: %.3f",
            epoch + 1,
            epochs,
            avg_train_loss,
            avg_val_loss,
            val_acc,
            avg_precision,
            avg_recall,
            f1,
        )

        if use_mlflow:
            import mlflow

            mlflow.log_metrics(
                {
                    "train_loss": avg_train_loss,
                    "val_loss": avg_val_loss,
                    "val_accuracy": float(val_acc),
                    "val_precision": float(avg_precision),
                    "val_recall": float(avg_recall),
                    "val_f1": float(f1),
                },
                step=epoch,
            )

        # Save best model
        if f1 > best_val_f1:
            best_val_f1 = f1
            best_metrics = {
                "epoch": epoch + 1,
                "val_accuracy": float(val_acc),
                "val_precision": float(avg_precision),
                "val_recall": float(avg_recall),
                "val_f1": float(f1),
            }
            output_dir.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), output_dir / "best_model.pt")
            with open(output_dir / "best_metrics.json", "w") as f:
                json.dump(best_metrics, f, indent=2)

    # Save final model
    torch.save(model.state_dict(), output_dir / "final_model.pt")

    if use_mlflow:
        import mlflow

        mlflow.log_metrics(
            {
                "best_val_f1": best_val_f1,
                "best_val_precision": best_metrics.get("val_precision", 0),
                "best_val_recall": best_metrics.get("val_recall", 0),
            }
        )
        mlflow.pytorch.log_model(model, "model")
        mlflow.end_run()

    logger.info("Training complete. Best F1: %.3f at epoch %d", best_val_f1, best_metrics.get("epoch", 0))
    return best_metrics


def main():
    parser = argparse.ArgumentParser(description="Train positioning error detection model")
    parser.add_argument("--data-dir", type=Path, required=True, help="Training data directory")
    parser.add_argument("--output-dir", type=Path, default=Path("./checkpoints/positioning"))
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--d-model", type=int, default=128)
    parser.add_argument("--n-layers", type=int, default=2)
    parser.add_argument("--no-mlflow", action="store_true")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        d_model=args.d_model,
        n_layers=args.n_layers,
        use_mlflow=not args.no_mlflow,
    )


if __name__ == "__main__":
    main()
