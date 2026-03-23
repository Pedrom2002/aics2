"""Tests for ML model architectures — verify shapes, forward pass, and predictions."""

import torch

from src.models.positioning_mamba import (
    FocalLoss,
    MambaConfig,
    PositioningMamba,
    NUM_FEATURES,
    SEQ_LEN,
    NUM_CLASSES,
)
from src.models.timing_mamba import TimingConfig, TimingMamba
from src.models.strategy_gnn import StrategyClassifier, StrategyGNNConfig, T_STRATEGIES, CT_STRATEGIES


class TestPositioningMamba:
    def test_forward_shape(self):
        model = PositioningMamba()
        x = torch.randn(4, SEQ_LEN, NUM_FEATURES)
        logits = model(x)
        assert logits.shape == (4, NUM_CLASSES)

    def test_single_sample(self):
        model = PositioningMamba()
        x = torch.randn(1, SEQ_LEN, NUM_FEATURES)
        logits = model(x)
        assert logits.shape == (1, NUM_CLASSES)

    def test_predict(self):
        model = PositioningMamba()
        x = torch.randn(4, SEQ_LEN, NUM_FEATURES)
        predicted, confidence = model.predict(x)
        assert predicted.shape == (4,)
        assert confidence.shape == (4,)
        assert (confidence >= 0).all() and (confidence <= 1).all()
        assert (predicted >= 0).all() and (predicted < NUM_CLASSES).all()

    def test_custom_config(self):
        config = MambaConfig(d_model=64, n_layers=1, dropout=0.2)
        model = PositioningMamba(config)
        x = torch.randn(2, SEQ_LEN, NUM_FEATURES)
        logits = model(x)
        assert logits.shape == (2, NUM_CLASSES)

    def test_parameter_count(self):
        model = PositioningMamba()
        count = PositioningMamba.count_parameters(model)
        assert count > 0
        # Mamba with d_model=128 should have reasonable param count
        assert count < 5_000_000  # well under 5M

    def test_focal_loss(self):
        loss_fn = FocalLoss()
        logits = torch.randn(8, NUM_CLASSES)
        targets = torch.randint(0, NUM_CLASSES, (8,))
        loss = loss_fn(logits, targets)
        assert loss.shape == ()
        assert loss.item() > 0


class TestTimingMamba:
    def test_forward_shape(self):
        model = TimingMamba()
        x = torch.randn(4, 320, 14)
        logits = model(x)
        assert logits.shape == (4, 4)

    def test_predict(self):
        model = TimingMamba()
        x = torch.randn(2, 320, 14)
        predicted, confidence = model.predict(x)
        assert predicted.shape == (2,)
        assert (predicted >= 0).all() and (predicted < 4).all()


class TestStrategyGNN:
    def test_t_side_forward(self):
        model = StrategyClassifier(side="T")
        x = torch.randn(3, 5, 16)  # batch of 3, 5 players, 16 features
        adj = torch.ones(3, 5, 5)  # fully connected
        logits = model(x, adj)
        assert logits.shape == (3, len(T_STRATEGIES))

    def test_ct_side_forward(self):
        model = StrategyClassifier(side="CT")
        x = torch.randn(2, 5, 16)
        adj = torch.ones(2, 5, 5)
        logits = model(x, adj)
        assert logits.shape == (2, len(CT_STRATEGIES))

    def test_single_graph(self):
        model = StrategyClassifier(side="T")
        x = torch.randn(5, 16)
        adj = torch.ones(5, 5)
        logits = model(x, adj)
        assert logits.shape == (len(T_STRATEGIES),)

    def test_predict_labels(self):
        model = StrategyClassifier(side="T")
        x = torch.randn(5, 16)
        adj = torch.ones(5, 5)
        labels, confidence = model.predict(x, adj)
        assert len(labels) == 1
        assert labels[0] in T_STRATEGIES
        assert 0 <= confidence.item() <= 1
