"""Explainability engine: Integrated Gradients + TreeSHAP."""

from src.explainability.api import SUPPORTED_MODELS, explain_prediction  # noqa: F401

__all__ = ["SUPPORTED_MODELS", "explain_prediction"]
