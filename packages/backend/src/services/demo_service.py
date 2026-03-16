import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.demo import Demo, DemoStatus
from src.models.match import Match
from src.models.organization import Organization
from src.services.storage_service import _sanitize_filename, generate_s3_key, upload_to_minio


async def upload_demo(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
    file_data: bytes,
) -> Demo:
    """Upload a demo file and create a Demo record."""
    # Check org demo quota
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Count demos this month
    month_count_q = select(func.count(Demo.id)).where(
        Demo.org_id == org_id,
        func.extract("month", Demo.created_at) == func.extract("month", func.now()),
        func.extract("year", Demo.created_at) == func.extract("year", func.now()),
    )
    result = await db.execute(month_count_q)
    month_count = result.scalar() or 0

    if month_count >= org.max_demos_per_month:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly demo limit reached ({org.max_demos_per_month}). Upgrade your plan.",
        )

    # Sanitize filename
    filename = _sanitize_filename(filename)

    # Validate file
    if not filename.lower().endswith(".dem"):
        raise HTTPException(status_code=400, detail="Only .dem files are accepted.")

    max_size = 200 * 1024 * 1024  # 200MB
    if len(file_data) > max_size:
        raise HTTPException(status_code=400, detail="File exceeds 200MB limit.")

    # Upload to MinIO
    s3_key = generate_s3_key(org_id, filename)
    checksum = await upload_to_minio(s3_key, file_data)

    # Create demo record
    demo = Demo(
        org_id=org_id,
        uploaded_by=user_id,
        s3_key=s3_key,
        original_filename=filename,
        file_size_bytes=len(file_data),
        checksum_sha256=checksum,
        status=DemoStatus.uploaded,
    )
    db.add(demo)
    await db.flush()
    await db.refresh(demo)

    # Commit before queuing Celery task to avoid race condition
    # where the task runs before the demo record is persisted
    await db.commit()

    # Queue Celery task for processing
    from src.tasks.demo_processing import process_demo

    process_demo.delay(str(demo.id), s3_key)

    return demo


async def list_demos(
    db: AsyncSession,
    org_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status: DemoStatus | None = None,
) -> tuple[list[Demo], int]:
    """List demos for an organization with pagination."""
    query = select(Demo).where(Demo.org_id == org_id)

    if status is not None:
        query = query.where(Demo.status == status)

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(Demo.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    demos = list(result.scalars().all())

    return demos, total


async def get_demo(db: AsyncSession, demo_id: uuid.UUID, org_id: uuid.UUID) -> Demo:
    """Get a demo with its match relationship."""
    query = (
        select(Demo)
        .options(selectinload(Demo.match))
        .where(Demo.id == demo_id, Demo.org_id == org_id)
    )
    result = await db.execute(query)
    demo = result.scalar_one_or_none()

    if not demo:
        raise HTTPException(status_code=404, detail="Demo not found")

    return demo


async def delete_demo(db: AsyncSession, demo_id: uuid.UUID, org_id: uuid.UUID) -> None:
    """Delete a demo and its associated match data (cascade)."""
    query = select(Demo).where(Demo.id == demo_id, Demo.org_id == org_id)
    result = await db.execute(query)
    demo = result.scalar_one_or_none()

    if not demo:
        raise HTTPException(status_code=404, detail="Demo not found")

    # Try to delete from S3/MinIO (best effort)
    try:
        from src.services.storage_service import delete_from_minio

        await delete_from_minio(demo.s3_key)
    except Exception:
        pass  # Don't fail the delete if S3 cleanup fails

    await db.delete(demo)
    await db.commit()


async def get_match_detail(db: AsyncSession, match_id: uuid.UUID, org_id: uuid.UUID) -> Match:
    """Get match with rounds and player stats."""
    query = (
        select(Match)
        .options(
            selectinload(Match.rounds),
            selectinload(Match.player_stats),
        )
        .where(Match.id == match_id, Match.org_id == org_id)
    )
    result = await db.execute(query)
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    return match
