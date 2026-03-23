"""
Training script for the Utility Error Detection Model (LightGBM).

Usage:
    python -m src.training.train_utility --data-dir ./data/utility --output-dir ./data/checkpoints/utility
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def load_utility_dataset(data_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load utility feature vectors from .npz files."""
    features_list = []
    labels_list = []

    for f in sorted(data_dir.glob("*.npz")):
        data = np.load(f)
        features_list.append(data["features"])
        labels_list.append(int(data["label"]))

    if not features_list:
        return np.array([]), np.array([])

    return np.stack(features_list), np.array(labels_list)


def train(
    data_dir: Path,
    output_dir: Path,
    val_split: float = 0.2,
    use_mlflow: bool = True,
) -> dict:
    """Train the utility LightGBM model."""
    from src.models.utility_lgbm import UtilityClassifier, UtilityModelConfig

    X, y = load_utility_dataset(data_dir)
    if len(X) == 0:
        logger.error("No utility training data found in %s", data_dir)
        return {"error": "no_data"}

    logger.info("Loaded %d utility samples (%d features)", len(X), X.shape[1])

    # Split
    n_val = int(len(X) * val_split)
    indices = np.random.permutation(len(X))
    train_idx, val_idx = indices[n_val:], indices[:n_val]
    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]

    # MLflow
    if use_mlflow:
        try:
            import mlflow

            mlflow.set_experiment("utility-errors-v1")
            mlflow.start_run()
            mlflow.log_params({"train_size": len(X_train), "val_size": len(X_val)})
        except ImportError:
            use_mlflow = False

    # Train
    classifier = UtilityClassifier(UtilityModelConfig())
    metrics = classifier.train(X_train, y_train, X_val, y_val)

    # Evaluate
    preds, confidence = classifier.predict(X_val)
    accuracy = (preds == y_val).mean()

    # Per-class metrics
    from collections import Counter

    class_labels = ["effective", "suboptimal", "wasted", "harmful"]
    label_counts = Counter(y_val.tolist())

    per_class = {}
    for c in range(4):
        tp = ((preds == c) & (y_val == c)).sum()
        fp = ((preds == c) & (y_val != c)).sum()
        fn = ((preds != c) & (y_val == c)).sum()
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-8)
        per_class[class_labels[c]] = {"precision": float(prec), "recall": float(rec), "f1": float(f1)}

    result = {
        "accuracy": float(accuracy),
        "per_class": per_class,
        "feature_importance": classifier.feature_importance(),
        "best_iteration": metrics.get("best_iteration", 0),
    }

    logger.info("Utility model — accuracy: %.3f", accuracy)
    for label, m in per_class.items():
        logger.info("  %s: precision=%.3f recall=%.3f F1=%.3f", label, m["precision"], m["recall"], m["f1"])

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    classifier.save(output_dir / "model.lgb")
    with open(output_dir / "metrics.json", "w") as f:
        json.dump(result, f, indent=2)

    if use_mlflow:
        import mlflow

        mlflow.log_metrics({"val_accuracy": float(accuracy)})
        mlflow.end_run()

    return result


def main():
    parser = argparse.ArgumentParser(description="Train utility error detection model")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("./data/checkpoints/utility"))
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    train(args.data_dir, args.output_dir, use_mlflow=not args.no_mlflow)


if __name__ == "__main__":
    main()
