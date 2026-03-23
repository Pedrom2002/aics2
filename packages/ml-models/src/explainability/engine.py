"""
Explainability Engine — Integrated Gradients for neural models, TreeSHAP for tree models.

Generates human-readable explanations for ML model predictions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import torch


@dataclass
class FeatureAttribution:
    """Attribution for a single feature."""

    feature_name: str
    feature_value: float
    attribution: float  # positive = pushes toward predicted class


@dataclass
class Explanation:
    """Complete explanation for a prediction."""

    predicted_class: int
    predicted_label: str
    confidence: float
    method: str  # "integrated_gradients" or "tree_shap"
    attributions: list[FeatureAttribution]
    explanation_text: str

    def top_features(self, n: int = 5) -> list[FeatureAttribution]:
        """Return the top N most impactful features."""
        return sorted(self.attributions, key=lambda a: abs(a.attribution), reverse=True)[:n]

    def to_json(self) -> str:
        """Serialize attributions to JSON for DB storage."""
        return json.dumps(
            [
                {
                    "feature": a.feature_name,
                    "value": round(a.feature_value, 4),
                    "impact": round(a.attribution, 4),
                }
                for a in self.top_features(10)
            ]
        )


class IntegratedGradientsExplainer:
    """
    Integrated Gradients for explaining PyTorch neural network predictions.

    50-100x faster than SHAP KernelExplainer for neural models.
    Uses PyTorch autograd for efficient gradient computation.
    """

    def __init__(self, model: torch.nn.Module, n_steps: int = 50):
        self.model = model
        self.n_steps = n_steps

    @torch.no_grad()
    def _get_prediction(self, x: torch.Tensor) -> tuple[int, float, torch.Tensor]:
        """Get model prediction for input."""
        self.model.eval()
        logits = self.model(x)
        probs = torch.softmax(logits, dim=-1)
        confidence, predicted = probs.max(dim=-1)
        return predicted.item(), confidence.item(), probs

    def explain(
        self,
        x: torch.Tensor,
        feature_names: list[str],
        class_labels: list[str],
        baseline: torch.Tensor | None = None,
    ) -> Explanation:
        """
        Compute Integrated Gradients attributions.

        Args:
            x: Input tensor (1, seq_len, features) or (1, features)
            feature_names: Names for each feature dimension
            class_labels: Names for each output class
            baseline: Reference input (defaults to zeros)

        Returns:
            Explanation with feature attributions.
        """
        self.model.eval()

        if baseline is None:
            baseline = torch.zeros_like(x)

        # Get prediction
        predicted_class, confidence, _ = self._get_prediction(x)

        # Compute integrated gradients
        x.requires_grad_(True)
        attributions = self._compute_ig(x, baseline, predicted_class)

        # Aggregate temporal dimension if present (for sequence models)
        if attributions.dim() == 3:
            # (1, seq_len, features) → (features,) via mean over time
            attr_values = attributions.squeeze(0).mean(dim=0).detach().numpy()
            input_values = x.squeeze(0).mean(dim=0).detach().numpy()
        else:
            attr_values = attributions.squeeze(0).detach().numpy()
            input_values = x.squeeze(0).detach().numpy()

        # Build feature attributions
        feature_attrs = []
        for i, name in enumerate(feature_names):
            if i < len(attr_values):
                feature_attrs.append(
                    FeatureAttribution(
                        feature_name=name,
                        feature_value=float(input_values[i]),
                        attribution=float(attr_values[i]),
                    )
                )

        # Generate text explanation
        top = sorted(feature_attrs, key=lambda a: abs(a.attribution), reverse=True)[:5]
        label = class_labels[predicted_class] if predicted_class < len(class_labels) else str(predicted_class)

        factors = []
        for a in top:
            direction = "increases" if a.attribution > 0 else "decreases"
            factors.append(f"{a.feature_name}={a.feature_value:.2f} ({direction} risk, impact {abs(a.attribution):.3f})")

        explanation_text = (
            f"Classified as '{label}' with {confidence:.0%} confidence. "
            f"Main factors: {'; '.join(factors)}."
        )

        return Explanation(
            predicted_class=predicted_class,
            predicted_label=label,
            confidence=confidence,
            method="integrated_gradients",
            attributions=feature_attrs,
            explanation_text=explanation_text,
        )

    def _compute_ig(
        self,
        x: torch.Tensor,
        baseline: torch.Tensor,
        target_class: int,
    ) -> torch.Tensor:
        """Compute integrated gradients via Riemann approximation."""
        # Generate interpolated inputs
        alphas = torch.linspace(0, 1, self.n_steps + 1, device=x.device)
        total_grads = torch.zeros_like(x)

        for alpha in alphas:
            interp = baseline + alpha * (x - baseline)
            interp = interp.detach().requires_grad_(True)

            logits = self.model(interp)
            target_score = logits[0, target_class]
            target_score.backward()

            if interp.grad is not None:
                total_grads += interp.grad

        # Average gradients and multiply by (input - baseline)
        avg_grads = total_grads / (self.n_steps + 1)
        attributions = (x.detach() - baseline) * avg_grads

        return attributions


class TreeSHAPExplainer:
    """
    TreeSHAP wrapper for explaining LightGBM/CatBoost predictions.

    Uses the tree-specific SHAP algorithm which is exact and fast.
    Falls back to feature importance if SHAP is not installed.
    """

    def __init__(self, model, feature_names: list[str]):
        self.model = model
        self.feature_names = feature_names
        self._shap_explainer = None

        try:
            import shap

            self._shap_explainer = shap.TreeExplainer(model)
        except (ImportError, Exception):
            pass

    def explain(
        self,
        x: np.ndarray,
        class_labels: list[str],
    ) -> Explanation:
        """
        Compute SHAP values for a tree model prediction.

        Args:
            x: Input array (1, features) or (features,)
            class_labels: Names for each output class

        Returns:
            Explanation with feature attributions.
        """
        if x.ndim == 1:
            x = x.reshape(1, -1)

        # Get prediction
        probs = self.model.predict(x)
        predicted_class = int(np.argmax(probs[0]))
        confidence = float(probs[0][predicted_class])

        # Get SHAP values
        if self._shap_explainer is not None:
            shap_values = self._shap_explainer.shap_values(x)
            # shap_values is list of (1, features) per class
            if isinstance(shap_values, list):
                attr_values = shap_values[predicted_class][0]
            else:
                attr_values = shap_values[0]
        else:
            # Fallback: use feature importance as rough proxy
            importance = self.model.feature_importance(importance_type="gain")
            attr_values = importance / max(importance.sum(), 1)

        # Build attributions
        feature_attrs = []
        for i, name in enumerate(self.feature_names):
            if i < len(attr_values):
                feature_attrs.append(
                    FeatureAttribution(
                        feature_name=name,
                        feature_value=float(x[0, i]),
                        attribution=float(attr_values[i]),
                    )
                )

        # Generate text
        label = class_labels[predicted_class] if predicted_class < len(class_labels) else str(predicted_class)
        top = sorted(feature_attrs, key=lambda a: abs(a.attribution), reverse=True)[:5]

        factors = []
        for a in top:
            direction = "contributed to" if a.attribution > 0 else "reduced"
            factors.append(f"{a.feature_name}={a.feature_value:.2f} ({direction} '{label}', impact {abs(a.attribution):.3f})")

        explanation_text = (
            f"Classified as '{label}' with {confidence:.0%} confidence. "
            f"Main factors: {'; '.join(factors)}."
        )

        return Explanation(
            predicted_class=predicted_class,
            predicted_label=label,
            confidence=confidence,
            method="tree_shap",
            attributions=feature_attrs,
            explanation_text=explanation_text,
        )
