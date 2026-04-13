"""Real-time match prediction streams.

A live match ingestor (``live_worker`` Celery task, not included here) is
expected to publish per-tick JSON messages to Redis pub/sub under the
channel ``live:match:{match_id}``. This router subscribes to that channel
and relays events over SSE to the frontend.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from src.config import settings
from src.middleware.auth import get_current_user
from src.schemas.auth import TokenPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live", tags=["live"])


@router.get("/{match_id}/win-prob/sse")
async def live_win_prob_stream(
    match_id: str,
    _user: TokenPayload = Depends(get_current_user),
):
    """Stream live win-probability updates for an in-progress match."""

    async def event_generator():
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        channel = f"live:match:{match_id}"
        await pubsub.subscribe(channel)
        try:
            # Send a heartbeat so the client learns the connection is live
            yield 'event: open\ndata: {"status": "subscribed"}\n\n'

            last_heartbeat = asyncio.get_event_loop().time()
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                now = asyncio.get_event_loop().time()
                if msg and msg.get("type") == "message":
                    data = msg["data"]
                    try:
                        json.loads(data)
                    except (TypeError, ValueError):
                        data = json.dumps({"raw": str(data)})
                    yield f"event: win_prob\ndata: {data}\n\n"
                if now - last_heartbeat > 15:
                    yield "event: ping\ndata: {}\n\n"
                    last_heartbeat = now
        except asyncio.CancelledError:
            raise
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await redis_client.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
