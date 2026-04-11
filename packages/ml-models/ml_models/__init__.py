"""Public ``ml_models`` namespace.

Self-contained shim around the ML model registry, strategy GNN inference
helper and explainability API. Avoids importing from the internal ``src``
package so it stays loadable from sibling packages whose ``src`` namespace
would otherwise shadow ours.

Usage::

    from ml_models.registry import list_models, get_model
    from ml_models.strategy_gnn import predict_strategy
    from ml_models.explainability import explain_prediction
"""

from ml_models.registry import (  # noqa: F401
    REGISTRY_PATH,
    get_model,
    list_models,
    register_model,
    reload,
    resolve_model_path,
)

__all__ = [
    "REGISTRY_PATH",
    "get_model",
    "list_models",
    "register_model",
    "reload",
    "resolve_model_path",
]
