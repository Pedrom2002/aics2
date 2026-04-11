"""API endpoints for ML error detection results."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.ml import (
    MatchErrorsResponse,
    PlayerErrorSummaryResponse,
)
from src.services.ml_service import get_match_errors, get_player_error_summary

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Make the sibling ``ml-models`` package importable from this router so we
# can call into the model registry + explainability helpers without depending
# on a pip-installed wheel.
# ---------------------------------------------------------------------------

_ML_MODELS_PKG = (
    Path(__file__).resolve().parent.parent.parent.parent / "ml-models"
)
if _ML_MODELS_PKG.exists():
    p = str(_ML_MODELS_PKG)
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from ml_models.registry import get_model as _registry_get_model
    from ml_models.registry import list_models as _registry_list_models
    from ml_models.explainability import explain_prediction as _explain_prediction
except Exception as e:  # pragma: no cover - logged at runtime
    logger.warning("ml_models package not importable: %s", e)
    _registry_get_model = None
    _registry_list_models = None
    _explain_prediction = None


router = APIRouter(tags=["ml"])


# ---------------------------------------------------------------------------
# Existing endpoints (do not modify behaviour)
# ---------------------------------------------------------------------------


@router.get("/matches/{match_id}/errors", response_model=MatchErrorsResponse)
async def match_errors(
    match_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get all detected errors for a match with explanations and recommendations."""
    result = await get_match_errors(session, match_id)
    return result


@router.get("/players/{steam_id}/errors", response_model=PlayerErrorSummaryResponse)
async def player_errors(
    steam_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get error summary for a player across all matches."""
    result = await get_player_error_summary(session, steam_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No errors found for this player")
    return result


# ---------------------------------------------------------------------------
# New endpoints — model registry + explainability
# ---------------------------------------------------------------------------


class ModelEntry(BaseModel):
    name: str
    version: str | None = None
    framework: str | None = None
    task: str | None = None
    path: str | None = None
    metrics: dict[str, Any] | None = None
    features: list[str] | None = None
    trained_at: str | None = None
    training_script: str | None = None
    description: str | None = None


class ModelListResponse(BaseModel):
    count: int
    models: list[ModelEntry]


class ShapValueItem(BaseModel):
    feature: str
    value: float
    contribution: float


class ExplainRequest(BaseModel):
    model: str = Field(..., description="Registered model name (e.g. 'win_prob' or 'player_rating')")
    sample_data: dict[str, Any] = Field(default_factory=dict, description="Feature dict for the row to explain")


class ExplainResponse(BaseModel):
    model: str
    version: str | None = None
    method: str
    base_value: float
    prediction: float
    shap_values: list[ShapValueItem]


def _require_registry() -> None:
    if _registry_list_models is None:
        raise HTTPException(
            status_code=503,
            detail="ml_models package unavailable on this deployment",
        )


@router.get("/models", response_model=ModelListResponse)
async def list_ml_models() -> ModelListResponse:
    """List every model registered in ``models_registry.json``."""
    _require_registry()
    raw = _registry_list_models()  # type: ignore[misc]
    return ModelListResponse(
        count=len(raw),
        models=[ModelEntry(**m) for m in raw],
    )


@router.get("/models/{name}", response_model=ModelEntry)
async def get_ml_model(name: str, version: str | None = None) -> ModelEntry:
    """Fetch a single model entry by name (and optional version)."""
    _require_registry()
    entry = _registry_get_model(name, version)  # type: ignore[misc]
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Model '{name}' not found in registry")
    return ModelEntry(**entry)


@router.post("/explain", response_model=ExplainResponse)
async def explain(request: ExplainRequest) -> ExplainResponse:
    """Generate a SHAP-style feature attribution for a single prediction.

    Falls back to a deterministic heuristic when the trained checkpoint is
    not available so the endpoint stays callable in dev environments.
    """
    if _explain_prediction is None:
        raise HTTPException(
            status_code=503,
            detail="ml_models explainability unavailable on this deployment",
        )

    try:
        result = _explain_prediction(request.model, request.sample_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover - last resort
        logger.exception("Explainability failed")
        raise HTTPException(status_code=500, detail=f"Explainability error: {e}")

    return ExplainResponse(
        model=result["model"],
        version=result.get("version"),
        method=result["method"],
        base_value=result["base_value"],
        prediction=result["prediction"],
        shap_values=[ShapValueItem(**sv) for sv in result["shap_values"]],
    )
