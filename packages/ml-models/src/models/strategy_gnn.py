"""
Strategy Classification Model — GraphSAGE GNN.

Classifies team strategy per round from player positions/state graph.

Input: Graph with 5 nodes (players), 16 features each, edges by proximity.
Output: Strategy label (15 T-side or 10 CT-side options per map).
"""

from __future__ import annotations

from dataclasses import dataclass

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


def predict_strategy(round_data: dict) -> dict:
    """Predict the team strategy for a round.

    Args:
        round_data: Dict describing the round state. Recognised keys:
            side: "T" | "CT" (default "T")
            equipment_value: total team equipment value
            enemy_equipment_value: opponent team equipment value
            time_remaining: 0..1 fraction of round time left
            bomb_planted: bool
            bomb_site: "A" | "B"
            avg_team_x, avg_team_y: aggregated team coordinates
            alive_team: number of alive teammates
            ct_at_a, ct_at_b: number of CTs holding each site

    Returns:
        ``{"strategy_type": str, "confidence": float, "side": str, "method": str}``
    """
    side = str(round_data.get("side", "T")).upper()
    if side == "CT":
        label, conf = _heuristic_ct_strategy(round_data)
        valid = CT_STRATEGIES
    else:
        label, conf = _heuristic_t_strategy(round_data)
        valid = T_STRATEGIES

    if label not in valid:
        # Defensive: never return a label outside the canonical vocab
        label = valid[0]
        conf = 0.4

    return {
        "strategy_type": label,
        "confidence": float(round(conf, 4)),
        "side": side,
        "method": "heuristic_fallback",
    }
