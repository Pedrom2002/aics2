import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.models.demo import DemoStatus


class DemoResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    status: DemoStatus
    error_message: str | None = None
    created_at: datetime
    parsing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class DemoDetailResponse(DemoResponse):
    s3_key: str
    checksum_sha256: str
    parsing_completed_at: datetime | None = None
    processing_started_at: datetime | None = None
    match: "MatchSummaryResponse | None" = None


class MatchSummaryResponse(BaseModel):
    id: uuid.UUID
    map: str
    match_date: datetime | None = None
    team1_name: str | None = None
    team2_name: str | None = None
    team1_score: int
    team2_score: int
    total_rounds: int
    duration_seconds: float | None = None

    model_config = {"from_attributes": True}


class RoundResponse(BaseModel):
    id: uuid.UUID
    round_number: int
    winner_side: str | None = None
    win_reason: str | None = None
    team1_score: int
    team2_score: int
    t_economy: int | None = None
    ct_economy: int | None = None
    t_equipment_value: int | None = None
    ct_equipment_value: int | None = None
    t_buy_type: str | None = None
    ct_buy_type: str | None = None
    bomb_planted: bool | None = None
    bomb_defused: bool | None = None
    plant_site: str | None = None
    duration_seconds: float | None = None

    model_config = {"from_attributes": True}


class PlayerMatchStatsResponse(BaseModel):
    id: uuid.UUID
    player_steam_id: str
    player_name: str
    team_side: str | None = None
    kills: int
    deaths: int
    assists: int
    headshot_kills: int
    damage: int
    adr: float | None = None
    flash_assists: int
    enemies_flashed: int
    utility_damage: int
    first_kills: int
    first_deaths: int
    trade_kills: int
    trade_deaths: int
    kast_rounds: int
    rounds_survived: int
    clutch_wins: int
    multi_kills_3k: int
    multi_kills_4k: int
    multi_kills_5k: int
    overall_rating: float | None = None
    aim_rating: float | None = None
    positioning_rating: float | None = None
    utility_rating: float | None = None
    game_sense_rating: float | None = None
    clutch_rating: float | None = None

    model_config = {"from_attributes": True}


class MatchDetailResponse(MatchSummaryResponse):
    match_type: str | None = None
    tickrate: int
    overtime_rounds: int
    rounds: list[RoundResponse] = []
    player_stats: list[PlayerMatchStatsResponse] = []


class DemoUploadResponse(BaseModel):
    demo_id: uuid.UUID
    upload_url: str
    message: str = "Upload your .dem file to the provided URL."


class DemoListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: DemoStatus | None = None
