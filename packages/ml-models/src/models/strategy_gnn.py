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
