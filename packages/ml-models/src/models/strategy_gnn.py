"""
Strategy Classification Model — GraphSAGE GNN.

Classifies team strategy per round from player positions/state graph.

Input: Graph with 5 nodes (players), 16 features each, edges by proximity.
Output: Strategy label (15 T-side or 10 CT-side options per map).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

# T-side strategies (generic, applicable to most maps)
T_STRATEGIES = [
    "a_execute",
    "b_execute",
    "mid_control_to_a",
    "mid_control_to_b",
    "split_a",
    "split_b",
    "fast_a",
    "fast_b",
    "a_fake_b",
    "b_fake_a",
    "default_spread",
    "slow_default",
    "eco_rush",
    "force_buy_execute",
    "save",
]

# CT-side strategies
CT_STRATEGIES = [
    "standard_2_1_2",
    "stack_a",
    "stack_b",
    "aggressive_mid",
    "aggressive_a",
    "passive_default",
    "retake_setup",
    "anti_eco_push",
    "save",
    "mixed",
]

NODE_FEATURES = 16  # per player


@dataclass
class StrategyGNNConfig:
    node_features: int = NODE_FEATURES
    hidden_dim: int = 64
    output_dim: int = 128
    num_t_strategies: int = len(T_STRATEGIES)
    num_ct_strategies: int = len(CT_STRATEGIES)
    dropout: float = 0.1


class SimpleSAGEConv(nn.Module):
    """
    Simplified GraphSAGE convolution (mean aggregation).

    For production, use torch_geometric.nn.SAGEConv.
    This pure-PyTorch version works without torch-geometric installed.
    """

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.linear_self = nn.Linear(in_channels, out_channels)
        self.linear_neigh = nn.Linear(in_channels, out_channels)

    def forward(
        self, x: torch.Tensor, adj: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            x: (num_nodes, in_channels)
            adj: (num_nodes, num_nodes) adjacency matrix (0/1 or weighted)
        Returns:
            (num_nodes, out_channels)
        """
        # Mean aggregation of neighbors
        deg = adj.sum(dim=-1, keepdim=True).clamp(min=1)
        neigh_agg = adj @ x / deg  # (N, in_channels)

        out = self.linear_self(x) + self.linear_neigh(neigh_agg)
        return out


class StrategyClassifier(nn.Module):
    """
    GraphSAGE-based strategy classifier.

    Works on a team graph (5 players) to classify round strategy.

    Architecture:
        SAGEConv(16→64) → ReLU → SAGEConv(64→128) → GlobalMeanPool → MLP
    """

    def __init__(self, config: StrategyGNNConfig | None = None, side: str = "T"):
        super().__init__()
        if config is None:
            config = StrategyGNNConfig()
        self.config = config
        self.side = side

        num_strategies = config.num_t_strategies if side == "T" else config.num_ct_strategies

        self.conv1 = SimpleSAGEConv(config.node_features, config.hidden_dim)
        self.conv2 = SimpleSAGEConv(config.hidden_dim, config.output_dim)

        self.classifier = nn.Sequential(
            nn.Linear(config.output_dim, 64),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(64, num_strategies),
        )

    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, 5, node_features) or (5, node_features) for single graph
            adj: (batch, 5, 5) or (5, 5) adjacency matrix
        Returns:
            logits: (batch, num_strategies) or (num_strategies,)
        """
        single = x.dim() == 2
        if single:
            x = x.unsqueeze(0)
            adj = adj.unsqueeze(0)

        batch_size = x.shape[0]
        outputs = []

        for i in range(batch_size):
            h = F.relu(self.conv1(x[i], adj[i]))
            h = F.relu(self.conv2(h, adj[i]))
            # Global mean pool over 5 players
            h = h.mean(dim=0)  # (output_dim,)
            outputs.append(h)

        pooled = torch.stack(outputs)  # (batch, output_dim)
        logits = self.classifier(pooled)

        return logits.squeeze(0) if single else logits

    def predict(self, x: torch.Tensor, adj: torch.Tensor) -> tuple[list[str], torch.Tensor]:
        """Return strategy labels and confidence."""
        logits = self.forward(x, adj)
        probs = F.softmax(logits, dim=-1)
        confidence, indices = probs.max(dim=-1)

        strategies = T_STRATEGIES if self.side == "T" else CT_STRATEGIES
        if indices.dim() == 0:
            labels = [strategies[indices.item()]]
        else:
            labels = [strategies[i.item()] for i in indices]

        return labels, confidence


# ---------------------------------------------------------------------------
# Public inference helper used by the tactics endpoint.
#
# A trained checkpoint for the GraphSAGE model is not yet shipped, so this
# function falls back to a deterministic heuristic over economy / time /
# bomb state. The signature is stable: when a checkpoint becomes available,
# only the body needs to change.
#
# The implementation lives in ``ml_models.strategy_gnn`` so it can be
# imported by sibling packages without colliding with their own ``src``
# namespace; this local copy is kept so tests that import via
# ``src.models.strategy_gnn`` still work.
# ---------------------------------------------------------------------------


def _heuristic_t_strategy(round_data: dict) -> tuple[str, float]:
    """Pick a T-side strategy from coarse round features."""
    eco = float(round_data.get("equipment_value", 0) or 0)
    enemy_eco = float(round_data.get("enemy_equipment_value", 0) or 0)
    time_remaining = float(round_data.get("time_remaining", 1.0) or 0)
    bomb_planted = bool(round_data.get("bomb_planted", False))
    bomb_site = (round_data.get("bomb_site") or "").upper()
    avg_x = float(round_data.get("avg_team_x", 0) or 0)
    avg_y = float(round_data.get("avg_team_y", 0) or 0)
    alive = int(round_data.get("alive_team", 5) or 5)

    if eco < 5000:
        if enemy_eco > 15000:
            return "save", 0.85
        return "eco_rush", 0.7

    if eco < 12000:
        return "force_buy_execute", 0.6

    if bomb_planted:
        return ("a_execute" if bomb_site == "A" else "b_execute"), 0.9

    # Full buy — choose by clock + position bias
    if time_remaining > 0.7:
        return "default_spread", 0.55

    if time_remaining < 0.3 and alive >= 4:
        return ("fast_a" if avg_x >= 0 else "fast_b"), 0.6

    if avg_x > 500:
        return "split_a", 0.5
    if avg_x < -500:
        return "split_b", 0.5
    return ("mid_control_to_a" if avg_y >= 0 else "mid_control_to_b"), 0.5


def _heuristic_ct_strategy(round_data: dict) -> tuple[str, float]:
    """Pick a CT-side strategy from coarse round features."""
    eco = float(round_data.get("equipment_value", 0) or 0)
    enemy_eco = float(round_data.get("enemy_equipment_value", 0) or 0)
    time_remaining = float(round_data.get("time_remaining", 1.0) or 0)
    bomb_planted = bool(round_data.get("bomb_planted", False))
    a_count = int(round_data.get("ct_at_a", 0) or 0)
    b_count = int(round_data.get("ct_at_b", 0) or 0)

    if eco < 5000:
        return "save", 0.85

    if enemy_eco < 5000:
        return "anti_eco_push", 0.8

    if bomb_planted:
        return "retake_setup", 0.9

    if a_count >= 3:
        return "stack_a", 0.7
    if b_count >= 3:
        return "stack_b", 0.7

    if time_remaining > 0.8:
        return "aggressive_mid", 0.5

    if time_remaining < 0.25:
        return "passive_default", 0.55

    return "standard_2_1_2", 0.5


# Coarse taxonomy (matches training script)
_T_COARSE_LABELS = ["execute", "fake", "default", "eco", "force", "save"]
_CT_COARSE_LABELS = ["stack", "aggressive", "default", "retake", "save"]
_T_COARSE_MAP = {
    "a_execute": "execute", "b_execute": "execute", "split_a": "execute",
    "split_b": "execute", "fast_a": "execute", "fast_b": "execute",
    "force_buy_execute": "force", "a_fake_b": "fake", "b_fake_a": "fake",
    "default_spread": "default", "slow_default": "default",
    "mid_control_to_a": "default", "mid_control_to_b": "default",
    "eco_rush": "eco", "save": "save",
}
_CT_COARSE_MAP = {
    "stack_a": "stack", "stack_b": "stack", "aggressive_mid": "aggressive",
    "aggressive_a": "aggressive", "standard_2_1_2": "default",
    "passive_default": "default", "mixed": "default", "retake_setup": "retake",
    "anti_eco_push": "aggressive", "save": "save",
}

# Checkpoint cache
_CHECKPOINT_CACHE: dict[str, StrategyClassifier | None] = {}


def _checkpoint_path(side: str) -> Path:
    from pathlib import Path as _P
    return _P(__file__).resolve().parents[2] / "models" / "strategy_gnn" / f"strategy_gnn_{side.lower()}.pt"


def _load_checkpoint(side: str) -> StrategyClassifier | None:
    if side in _CHECKPOINT_CACHE:
        return _CHECKPOINT_CACHE[side]
    path = _checkpoint_path(side)
    if not path.exists():
        _CHECKPOINT_CACHE[side] = None
        return None
    try:
        from pathlib import Path  # noqa: F401
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        num_classes = len(_T_COARSE_LABELS if side == "T" else _CT_COARSE_LABELS)
        config = StrategyGNNConfig(
            num_t_strategies=num_classes if side == "T" else len(T_STRATEGIES),
            num_ct_strategies=num_classes if side == "CT" else len(CT_STRATEGIES),
        )
        model = StrategyClassifier(config=config, side=side)
        model.classifier = nn.Sequential(
            nn.Linear(config.output_dim, 64),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(64, num_classes),
        )
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        _CHECKPOINT_CACHE[side] = model
        return model
    except Exception:
        _CHECKPOINT_CACHE[side] = None
        return None


def _build_round_graph(round_data: dict) -> tuple[torch.Tensor, torch.Tensor]:
    """Synthesize the 5×16 node feature matrix + 5×5 adjacency from round_data."""
    eco = float(round_data.get("equipment_value", 0) or 0)
    enemy = float(round_data.get("enemy_equipment_value", 0) or 0)
    time_remaining = float(round_data.get("time_remaining", 1.0) or 0)
    bomb_planted = 1.0 if round_data.get("bomb_planted") else 0.0
    bomb_site = 1.0 if str(round_data.get("bomb_site", "")).upper() == "A" else 0.0
    avg_x = float(round_data.get("avg_team_x", 0) or 0) / 2000.0
    avg_y = float(round_data.get("avg_team_y", 0) or 0) / 2000.0
    alive = int(round_data.get("alive_team", 5) or 5)
    a_count = float(round_data.get("ct_at_a", 0) or 0)
    b_count = float(round_data.get("ct_at_b", 0) or 0)

    x = torch.zeros(5, NODE_FEATURES, dtype=torch.float32)
    for p in range(5):
        alive_p = 1.0 if p < alive else 0.0
        x[p] = torch.tensor([
            avg_x, avg_y, alive_p, alive_p, 0.5, 0.5, 0.0,
            eco / 25000.0, enemy / 25000.0, time_remaining,
            bomb_planted, bomb_site, alive / 5.0, a_count / 5.0, b_count / 5.0, 0.5,
        ])
    adj = torch.ones(5, 5) - torch.eye(5)
    return x, adj


def predict_strategy(round_data: dict) -> dict:
    """Predict the team strategy for a round.

    Uses the trained GraphSAGE checkpoint when available; otherwise falls
    back to the deterministic heuristic so the endpoint stays callable.
    """
    side = str(round_data.get("side", "T")).upper()

    model = _load_checkpoint(side)
    if model is not None:
        try:
            x, adj = _build_round_graph(round_data)
            with torch.no_grad():
                logits = model(x, adj)
                probs = F.softmax(logits, dim=-1)
                confidence, idx = probs.max(dim=-1)
            labels = _T_COARSE_LABELS if side == "T" else _CT_COARSE_LABELS
            return {
                "strategy_type": labels[int(idx.item())],
                "confidence": float(round(confidence.item(), 4)),
                "side": side,
                "method": "gnn_v1",
            }
        except Exception:
            pass  # fall through to heuristic

    if side == "CT":
        label, conf = _heuristic_ct_strategy(round_data)
        valid = CT_STRATEGIES
        coarse_map = _CT_COARSE_MAP
    else:
        label, conf = _heuristic_t_strategy(round_data)
        valid = T_STRATEGIES
        coarse_map = _T_COARSE_MAP

    if label not in valid:
        label = valid[0]
        conf = 0.4

    return {
        "strategy_type": coarse_map.get(label, label),
        "confidence": float(round(conf, 4)),
        "side": side,
        "method": "heuristic_fallback",
    }
