"""
Utility Error Detection Model — LightGBM.

Classifies grenade usage (smoke, flash, HE, molotov) as:
  0 - effective:    Achieved objective
  1 - suboptimal:   Some effect but could be better
  2 - wasted:       No useful effect
  3 - harmful:      Flashed teammates, blocked own team LoS

Input: 25 features per grenade event (single-pass, no temporal sequence).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import numpy as np

try:
    import lightgbm as lgb

    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    lgb = None


class UtilityErrorClass(IntEnum):
    EFFECTIVE = 0
    SUBOPTIMAL = 1
    WASTED = 2
    HARMFUL = 3


FEATURE_NAMES = [
    # Grenade context (5)
    "is_smoke",
    "is_flash",
    "is_he",
    "is_molotov",
    "map_id",
    # Position (7)
    "throw_x",
    "throw_y",
    "throw_z",
    "land_x",
    "land_y",
    "land_z",
    "distance_to_pro_lineup",
    # Timing (3)
    "round_time_remaining",
    "time_since_round_start",
    "phase",  # 0=early, 1=mid, 2=late, 3=post-plant
    # Round context (4)
    "score_diff",
    "teammates_alive",
    "enemies_alive",
    "buy_type",  # 0=eco, 1=force, 2=semi, 3=full
    # Outcome (5)
    "enemies_flashed_count",
    "flash_duration_avg",
    "smoke_blocks_los_count",
    "molly_damage_dealt",
    "he_damage_dealt",
    # Result (1)
    "was_round_won",
]

NUM_FEATURES = len(FEATURE_NAMES)
NUM_CLASSES = 4


@dataclass
class UtilityModelConfig:
    n_estimators: int = 500
    max_depth: int = 8
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    num_leaves: int = 127
    min_child_samples: int = 20


class UtilityClassifier:
    """LightGBM wrapper for utility error classification."""

    def __init__(self, config: UtilityModelConfig | None = None):
        if not HAS_LIGHTGBM:
            raise ImportError("lightgbm is required: pip install lightgbm")

        self.config = config or UtilityModelConfig()
        self.model: lgb.Booster | None = None
        self._is_trained = False

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> dict:
        """Train the LightGBM model.

        Returns:
            Training metrics dict.
        """
        train_data = lgb.Dataset(X_train, label=y_train, feature_name=FEATURE_NAMES)

        valid_sets = [train_data]
        valid_names = ["train"]
        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(X_val, label=y_val, feature_name=FEATURE_NAMES)
            valid_sets.append(val_data)
            valid_names.append("valid")

        params = {
            "objective": "multiclass",
            "num_class": NUM_CLASSES,
            "metric": "multi_logloss",
            "max_depth": self.config.max_depth,
            "learning_rate": self.config.learning_rate,
            "subsample": self.config.subsample,
            "colsample_bytree": self.config.colsample_bytree,
            "num_leaves": self.config.num_leaves,
            "min_child_samples": self.config.min_child_samples,
            "verbosity": -1,
            "seed": 42,
        }

        callbacks = [lgb.log_evaluation(period=50)]
        if X_val is not None:
            callbacks.append(lgb.early_stopping(stopping_rounds=30))

        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=self.config.n_estimators,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks,
        )
        self._is_trained = True

        return {"best_iteration": self.model.best_iteration}

    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return predicted classes and confidence scores."""
        if not self._is_trained or self.model is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")

        probs = self.model.predict(X)  # (N, 4)
        predicted = np.argmax(probs, axis=1)
        confidence = np.max(probs, axis=1)
        return predicted, confidence

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return full probability distribution."""
        if not self._is_trained or self.model is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")
        return self.model.predict(X)

    def feature_importance(self) -> dict[str, float]:
        """Return feature importance scores."""
        if not self._is_trained or self.model is None:
            raise RuntimeError("Model not trained.")
        importance = self.model.feature_importance(importance_type="gain")
        return dict(zip(FEATURE_NAMES, importance.tolist()))

    def save(self, path: Path) -> None:
        """Save model to file."""
        if self.model is None:
            raise RuntimeError("No model to save.")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(path))
        # Save config alongside
        config_path = path.with_suffix(".config.json")
        config_path.write_text(
            json.dumps(
                {
                    "n_estimators": self.config.n_estimators,
                    "max_depth": self.config.max_depth,
                    "learning_rate": self.config.learning_rate,
                    "num_features": NUM_FEATURES,
                    "num_classes": NUM_CLASSES,
                    "feature_names": FEATURE_NAMES,
                }
            )
        )

    def load(self, path: Path) -> None:
        """Load model from file."""
        self.model = lgb.Booster(model_file=str(path))
        self._is_trained = True
