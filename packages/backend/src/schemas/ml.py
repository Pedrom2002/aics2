"""Pydantic schemas for ML error detection API responses."""

from pydantic import BaseModel


class FeatureImportanceItem(BaseModel):
    feature: str
    value: float | str
    impact: float


class ErrorExplanationResponse(BaseModel):
    method: str
    explanation_text: str
    feature_importances: list[FeatureImportanceItem]


class ErrorRecommendationResponse(BaseModel):
    title: str
    description: str
    priority: int
    template_id: str | None = None
    expected_impact: str | None = None
    pro_reference: str | None = None


class DetectedErrorResponse(BaseModel):
    id: str
    player_steam_id: str
    round_number: int
    error_type: str
    severity: str
    confidence: float
    tick: int | None = None
    position_x: float | None = None
    position_y: float | None = None
    position_z: float | None = None
    description: str
    model_name: str
    model_version: str
    explanation: ErrorExplanationResponse | None = None
    recommendation: ErrorRecommendationResponse | None = None


class MatchErrorsResponse(BaseModel):
    match_id: str
    total_errors: int
    critical_count: int
    minor_count: int
    errors: list[DetectedErrorResponse]


class PlayerErrorSummaryResponse(BaseModel):
    player_steam_id: str
    total_errors: int
    positioning_errors: int
    utility_errors: int
    timing_errors: int
    critical_count: int
    minor_count: int
    top_recommendations: list[ErrorRecommendationResponse]


class MatchStrategyResponse(BaseModel):
    round_number: int
    team_side: str
    strategy_label: str
    confidence: float
    top_predictions: list[dict]


class MatchStrategiesResponse(BaseModel):
    match_id: str
    strategies: list[MatchStrategyResponse]
