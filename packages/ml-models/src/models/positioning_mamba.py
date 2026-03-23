"""
Positioning Error Detection Model — Mamba (State Space Model).

Detects when a player is in a dangerous position:
- Exposed to multiple angles
- Far from cover
- No teammate support

Input: (batch, 64, 18) — 64 ticks (1 second) of gameplay, 18 features per tick.
Output: 3-class softmax (no_error, minor_error, critical_error).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import torch
import torch.nn as nn
import torch.nn.functional as F


class PositioningErrorClass(IntEnum):
    NO_ERROR = 0
    MINOR = 1
    CRITICAL = 2


# Feature indices for the 18-dim input vector
FEATURE_NAMES = [
    "pos_x",
    "pos_y",
    "pos_z",
    "yaw",
    "pitch",
    "velocity",
    "health",
    "armor",
    "weapon_id",
    "is_scoped",
    "teammates_alive",
    "enemies_alive",
    "bomb_state",
    "round_time_remaining",
    "nearest_teammate_dist",
    "nearest_enemy_dist_est",
    "angles_exposed_count",
    "distance_to_nearest_cover",
]

NUM_FEATURES = len(FEATURE_NAMES)
SEQ_LEN = 64  # ticks (1 second at 64 tick)
NUM_CLASSES = 3


@dataclass
class MambaConfig:
    """Configuration for the Mamba-based positioning model."""

    d_input: int = NUM_FEATURES  # 18
    d_model: int = 128
    d_state: int = 16
    d_conv: int = 4
    expand: int = 2
    n_layers: int = 2
    dropout: float = 0.1
    num_classes: int = NUM_CLASSES
    seq_len: int = SEQ_LEN


class SelectiveSSM(nn.Module):
    """
    Simplified Selective State Space Model (S6) block.

    This is a simplified version of the Mamba selective scan mechanism.
    For production, use the official mamba-ssm package with CUDA kernels.
    This pure-PyTorch version works on CPU/GPU without custom CUDA ops.
    """

    def __init__(self, d_model: int, d_state: int = 16, d_conv: int = 4, expand: int = 2):
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state
        d_inner = d_model * expand

        # Input projection
        self.in_proj = nn.Linear(d_model, d_inner * 2, bias=False)

        # Convolution (local context)
        self.conv1d = nn.Conv1d(
            d_inner, d_inner, kernel_size=d_conv, padding=d_conv - 1, groups=d_inner
        )

        # SSM parameters — input-dependent (selective)
        self.x_proj = nn.Linear(d_inner, d_state * 2, bias=False)  # B, C projections
        self.dt_proj = nn.Linear(d_inner, d_inner, bias=True)  # delta (step size)

        # Learnable log(A) — initialized for stability
        A = torch.arange(1, d_state + 1, dtype=torch.float32).unsqueeze(0).expand(d_inner, -1)
        self.A_log = nn.Parameter(torch.log(A))

        # D (skip connection)
        self.D = nn.Parameter(torch.ones(d_inner))

        # Output projection
        self.out_proj = nn.Linear(d_inner, d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, d_model)
        Returns:
            (batch, seq_len, d_model)
        """
        batch, seq_len, _ = x.shape

        # Project and split into two branches
        xz = self.in_proj(x)  # (B, L, 2*d_inner)
        x_branch, z = xz.chunk(2, dim=-1)  # each (B, L, d_inner)

        # Causal convolution
        x_conv = x_branch.transpose(1, 2)  # (B, d_inner, L)
        x_conv = self.conv1d(x_conv)[:, :, :seq_len]  # trim to causal
        x_conv = x_conv.transpose(1, 2)  # (B, L, d_inner)
        x_conv = F.silu(x_conv)

        # Selective SSM parameters
        x_dbl = self.x_proj(x_conv)  # (B, L, 2*d_state)
        B, C = x_dbl.chunk(2, dim=-1)  # each (B, L, d_state)

        dt = F.softplus(self.dt_proj(x_conv))  # (B, L, d_inner) — step sizes
        A = -torch.exp(self.A_log)  # (d_inner, d_state) — stable (negative)

        # Discretized selective scan (simplified linear recurrence)
        # For each position, compute: h_t = A_bar * h_{t-1} + B_bar * x_t
        y = self._selective_scan(x_conv, dt, A, B, C)

        # Gate with z branch + skip connection
        y = y * F.silu(z) + x_conv * self.D.unsqueeze(0).unsqueeze(0)
        return self.out_proj(y)

    def _selective_scan(
        self,
        x: torch.Tensor,
        dt: torch.Tensor,
        A: torch.Tensor,
        B: torch.Tensor,
        C: torch.Tensor,
    ) -> torch.Tensor:
        """Simplified selective scan (linear recurrence).

        This is O(n) in sequence length. For training efficiency,
        production should use parallel scan (mamba-ssm CUDA kernels).
        """
        batch, seq_len, d_inner = x.shape
        d_state = self.d_state

        # Initialize hidden state
        h = torch.zeros(batch, d_inner, d_state, device=x.device, dtype=x.dtype)
        outputs = []

        for t in range(seq_len):
            # Discretize: A_bar = exp(A * dt), B_bar = dt * B
            dt_t = dt[:, t, :].unsqueeze(-1)  # (B, d_inner, 1)
            A_bar = torch.exp(A.unsqueeze(0) * dt_t)  # (B, d_inner, d_state)
            B_t = B[:, t, :].unsqueeze(1).expand(-1, d_inner, -1)  # (B, d_inner, d_state)
            x_t = x[:, t, :].unsqueeze(-1)  # (B, d_inner, 1)

            # State update
            h = A_bar * h + B_t * x_t * dt_t

            # Output
            C_t = C[:, t, :].unsqueeze(1).expand(-1, d_inner, -1)  # (B, d_inner, d_state)
            y_t = (h * C_t).sum(dim=-1)  # (B, d_inner)
            outputs.append(y_t)

        return torch.stack(outputs, dim=1)  # (B, L, d_inner)


class MambaBlock(nn.Module):
    """A single Mamba block with residual connection and layer norm."""

    def __init__(self, d_model: int, d_state: int = 16, d_conv: int = 4, expand: int = 2):
        super().__init__()
        self.norm = nn.LayerNorm(d_model)
        self.ssm = SelectiveSSM(d_model, d_state, d_conv, expand)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.ssm(self.norm(x))


class PositioningMamba(nn.Module):
    """
    Mamba-based model for positioning error detection.

    Architecture:
        LinearProj(18→128) → MambaBlock×2 → GlobalAvgPool → MLP(128→64→3)
    """

    def __init__(self, config: MambaConfig | None = None):
        super().__init__()
        if config is None:
            config = MambaConfig()
        self.config = config

        # Input projection
        self.input_proj = nn.Linear(config.d_input, config.d_model)

        # Mamba layers
        self.layers = nn.ModuleList(
            [
                MambaBlock(config.d_model, config.d_state, config.d_conv, config.expand)
                for _ in range(config.n_layers)
            ]
        )

        self.norm_f = nn.LayerNorm(config.d_model)
        self.dropout = nn.Dropout(config.dropout)

        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(config.d_model, 64),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(64, config.num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, d_input) — 64 ticks, 18 features
        Returns:
            logits: (batch, num_classes)
        """
        # Project input
        h = self.input_proj(x)  # (B, L, d_model)
        h = self.dropout(h)

        # Mamba blocks
        for layer in self.layers:
            h = layer(h)

        # Global average pooling
        h = self.norm_f(h)
        h = h.mean(dim=1)  # (B, d_model)

        # Classify
        return self.classifier(h)  # (B, num_classes)

    def predict(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return predicted class and confidence."""
        logits = self.forward(x)
        probs = F.softmax(logits, dim=-1)
        confidence, predicted = probs.max(dim=-1)
        return predicted, confidence

    @staticmethod
    def count_parameters(model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)


class FocalLoss(nn.Module):
    """Focal loss for handling class imbalance in error detection."""

    def __init__(self, alpha: list[float] | None = None, gamma: float = 2.0):
        super().__init__()
        self.gamma = gamma
        if alpha is not None:
            self.alpha = torch.tensor(alpha)
        else:
            # Default: weight critical errors higher
            self.alpha = torch.tensor([0.25, 0.5, 1.0])

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce_loss = F.cross_entropy(logits, targets, reduction="none")
        pt = torch.exp(-ce_loss)
        alpha = self.alpha.to(logits.device)[targets]
        focal_loss = alpha * (1 - pt) ** self.gamma * ce_loss
        return focal_loss.mean()
