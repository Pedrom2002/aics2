"""
Timing Error Detection Model — Mamba (State Space Model).

Detects when a player peeks, rotates, or pushes at the wrong moment.

Input: (batch, 320, 14) — 5-second window (320 ticks at 64/sec), 14 features per tick.
Output: 4-class softmax (good_timing, too_early, too_late, unnecessary).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import torch
import torch.nn as nn
import torch.nn.functional as F

from src.models.positioning_mamba import MambaBlock


class TimingErrorClass(IntEnum):
    GOOD_TIMING = 0
    TOO_EARLY = 1
    TOO_LATE = 2
    UNNECESSARY = 3


FEATURE_NAMES = [
    # Player state (1)
    "movement_state",  # 0=holding, 1=moving, 2=peeking
    # Round state (7)
    "round_clock",
    "recent_kills_own_team_3s",
    "recent_kills_enemy_team_3s",
    "teammates_alive",
    "enemies_alive",
    "info_level",  # 0=none, 1=partial, 2=full
    "economy_advantage",  # normalized diff
    # Team context (4)
    "teammate_1_dist",
    "teammate_1_angle",
    "teammate_2_dist",
    "teammate_2_angle",
    # Game state (2)
    "bomb_state",  # 0=not_planted, 1=planted, 2=defusing
    "has_flash_available",
]

NUM_FEATURES = len(FEATURE_NAMES)
SEQ_LEN = 320  # 5 seconds at 64 tick
NUM_CLASSES = 4


@dataclass
class TimingConfig:
    d_input: int = NUM_FEATURES  # 14
    d_model: int = 96
    d_state: int = 16
    d_conv: int = 4
    expand: int = 2
    n_layers: int = 2
    dropout: float = 0.1
    num_classes: int = NUM_CLASSES
    seq_len: int = SEQ_LEN


class TimingMamba(nn.Module):
    """
    Mamba-based model for timing error detection.

    Architecture:
        LinearProj(14→96) → MambaBlock×2 → GlobalAvgPool → MLP(96→32→4)
    """

    def __init__(self, config: TimingConfig | None = None):
        super().__init__()
        if config is None:
            config = TimingConfig()
        self.config = config

        self.input_proj = nn.Linear(config.d_input, config.d_model)

        self.layers = nn.ModuleList(
            [
                MambaBlock(config.d_model, config.d_state, config.d_conv, config.expand)
                for _ in range(config.n_layers)
            ]
        )

        self.norm_f = nn.LayerNorm(config.d_model)
        self.dropout = nn.Dropout(config.dropout)

        self.classifier = nn.Sequential(
            nn.Linear(config.d_model, 32),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(32, config.num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, 320, 14)
        Returns:
            logits: (batch, 4)
        """
        h = self.input_proj(x)
        h = self.dropout(h)

        for layer in self.layers:
            h = layer(h)

        h = self.norm_f(h)
        h = h.mean(dim=1)
        return self.classifier(h)

    def predict(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        logits = self.forward(x)
        probs = F.softmax(logits, dim=-1)
        confidence, predicted = probs.max(dim=-1)
        return predicted, confidence
