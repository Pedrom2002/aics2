"""SSE endpoint for real-time demo processing status updates."""

import asyncio
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.middleware.auth import get_current_user
from src.models.demo import Demo
from src.schemas.auth import TokenPayload

router = APIRouter(prefix="/demos", tags=["demos"])


@router.get("/{demo_id}/status")
async def demo_status_stream(
    demo_id: uuid.UUID,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE stream of demo processing status updates.

    Sends status events until the demo reaches a terminal state
    (completed, failed, error).
    """

    async def event_generator():
        terminal_states = {"completed", "failed", "error"}
        last_status = None

        for _ in range(120):  # max 120 iterations (~2 min with 1s interval)
            result = await db.execute(
                select(Demo.status, Demo.error_message).where(
                    Demo.id == demo_id,
                    Demo.org_id == uuid.UUID(current_user.org_id),
                )
            )
            row = result.first()
            if row is None:
                yield 'event: error\ndata: {"error": "Demo not found"}\n\n'
                return

            status, error_message = row
            current_status = status.value if hasattr(status, "value") else str(status)

            if current_status != last_status:
                data = f'{{"status": "{current_status}"'
                if error_message:
                    # Escape quotes in error message
                    safe_msg = str(error_message).replace('"', '\\"')[:200]
                    data += f', "error_message": "{safe_msg}"'
                data += "}"
                yield f"event: status\ndata: {data}\n\n"
                last_status = current_status

                if current_status in terminal_states:
                    yield f'event: done\ndata: {{"final_status": "{current_status}"}}\n\n'
                    return

            await asyncio.sleep(1)

        yield 'event: timeout\ndata: {"error": "Stream timeout"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
