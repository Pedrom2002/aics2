import math
import uuid

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.middleware.auth import get_current_user
from src.models.demo import DemoStatus
from src.schemas.auth import TokenPayload
from src.schemas.common import PaginatedResponse
from src.schemas.demo import (
    DemoDetailResponse,
    DemoResponse,
    MatchDetailResponse,
)
from src.services import demo_service

router = APIRouter(prefix="/demos", tags=["demos"])


@router.post("", response_model=DemoResponse, status_code=201)
async def upload_demo(
    file: UploadFile,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a .dem file for analysis."""
    file_data = await file.read()
    demo = await demo_service.upload_demo(
        db=db,
        org_id=uuid.UUID(current_user.org_id),
        user_id=uuid.UUID(current_user.sub),
        filename=file.filename or "unknown.dem",
        file_data=file_data,
    )
    return demo


@router.get("", response_model=PaginatedResponse[DemoResponse])
async def list_demos(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: DemoStatus | None = None,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List demos for the current organization."""
    demos, total = await demo_service.list_demos(
        db=db,
        org_id=uuid.UUID(current_user.org_id),
        page=page,
        page_size=page_size,
        status=status,
    )
    return PaginatedResponse(
        items=demos,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{demo_id}", response_model=DemoDetailResponse)
async def get_demo(
    demo_id: uuid.UUID,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get demo details including match summary."""
    return await demo_service.get_demo(
        db=db,
        demo_id=demo_id,
        org_id=uuid.UUID(current_user.org_id),
    )


@router.delete("/{demo_id}", status_code=204)
async def delete_demo(
    demo_id: uuid.UUID,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a demo and its associated match data."""
    await demo_service.delete_demo(
        db=db,
        demo_id=demo_id,
        org_id=uuid.UUID(current_user.org_id),
    )


@router.get("/matches/{match_id}", response_model=MatchDetailResponse)
async def get_match(
    match_id: uuid.UUID,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full match details with rounds and player stats."""
    return await demo_service.get_match_detail(
        db=db,
        match_id=match_id,
        org_id=uuid.UUID(current_user.org_id),
    )
