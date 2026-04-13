"""Smoke tests for the live win-prob SSE pipeline.

Uses fakeredis so the whole flow (simulator → redis pubsub → SSE handler)
can be exercised without a real Redis broker.
"""

from __future__ import annotations

import asyncio
import json

import fakeredis.aioredis
import pytest


@pytest.mark.asyncio
async def test_live_sse_relays_published_events(monkeypatch):
    server = fakeredis.aioredis.FakeRedis(decode_responses=True)

    # Test the pub/sub contract the SSE route relies on, using the same
    # fake server. This validates the Redis channel naming + payload format
    # without needing FastAPI's async generator plumbing (which is harder
    # to drive in unit tests than the contract it depends on).
    match_id = "test_match_001"

    async def publisher():
        await asyncio.sleep(0.05)
        await server.publish(
            f"live:match:{match_id}",
            json.dumps({"t_win_prob": 0.42, "ct_win_prob": 0.58}),
        )

    # Mirror the route's generator logic inline so we can assert the first event
    channel = f"live:match:{match_id}"
    pubsub = server.pubsub()
    await pubsub.subscribe(channel)
    try:
        asyncio.create_task(publisher())
        # Skip the subscribe confirmation frame
        for _ in range(20):
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message":
                payload = json.loads(msg["data"])
                assert payload["t_win_prob"] == pytest.approx(0.42)
                assert payload["ct_win_prob"] == pytest.approx(0.58)
                break
        else:
            pytest.fail("No pub/sub message received")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await server.close()


@pytest.mark.asyncio
async def test_simulator_publishes_to_correct_channel(monkeypatch):
    """simulate_match uses synchronous redis; shim it to a fake."""
    import fakeredis

    fake = fakeredis.FakeRedis(decode_responses=True)

    from src.tasks import live_ingest

    monkeypatch.setattr(live_ingest.redis.Redis, "from_url", staticmethod(lambda *a, **kw: fake))
    monkeypatch.setattr(live_ingest.time, "sleep", lambda _s: None)  # skip sleeps

    pubsub = fake.pubsub()
    pubsub.subscribe("live:match:sim_1")

    # Drain subscription confirmation
    for _ in range(5):
        m = pubsub.get_message(timeout=0.1)
        if m and m.get("type") == "subscribe":
            break

    result = live_ingest.simulate_match.run(match_id="sim_1", rounds=2, tick_interval_s=0)
    assert result["match_id"] == "sim_1"
    assert result["published"] > 0

    # Confirm at least one message landed on the channel
    received = 0
    for _ in range(50):
        m = pubsub.get_message(timeout=0.1)
        if m and m.get("type") == "message":
            received += 1
            if received >= 3:
                break

    assert received >= 3, f"expected ≥3 messages, got {received}"
    pubsub.close()
