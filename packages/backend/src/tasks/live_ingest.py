"""Live-match win-probability producer.

Polls a configured live data source (HLTV live page, a local demo relay,
or a simulator) and publishes per-tick win-prob updates to Redis. The
``/live/{match_id}/win-prob/sse`` router subscribes to the resulting
pub/sub channel.

In this repo we ship a **simulator** backend by default so the SSE
endpoint is demonstrable end-to-end without a third-party feed.
"""

from __future__ import annotations

import json
import logging
import random
import time

import redis

from src.config import settings
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _channel(match_id: str) -> str:
    return f"live:match:{match_id}"


@celery_app.task(name="src.tasks.live_ingest.simulate_match")
def simulate_match(match_id: str, rounds: int = 24, tick_interval_s: float = 2.0) -> dict:
    """Publish a plausible live win-prob curve for ``match_id``.

    Each ``tick_interval_s`` seconds we push a JSON event to the Redis
    channel the SSE route subscribes to. The curve drifts between 0.3
    and 0.7 with round-end jumps.
    """
    r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    channel = _channel(match_id)

    t_win = 0.5
    published = 0
    for round_num in range(1, rounds + 1):
        for tick_in_round in range(5):
            t_win = max(0.05, min(0.95, t_win + random.uniform(-0.08, 0.08)))
            event = {
                "match_id": match_id,
                "round": round_num,
                "tick_in_round": tick_in_round,
                "t_win_prob": round(t_win, 4),
                "ct_win_prob": round(1 - t_win, 4),
                "ts": int(time.time()),
            }
            r.publish(channel, json.dumps(event))
            published += 1
            time.sleep(tick_interval_s)

        # Round-end jump toward the winner
        winner = "T" if random.random() < t_win else "CT"
        t_win = 0.55 if winner == "T" else 0.45
        r.publish(
            channel,
            json.dumps({"match_id": match_id, "round": round_num, "winner": winner, "ts": int(time.time())}),
        )
        published += 1

    logger.info("Published %d live events for match=%s", published, match_id)
    return {"match_id": match_id, "published": published}


@celery_app.task(name="src.tasks.live_ingest.ingest_hltv_live")
def ingest_hltv_live(hltv_match_url: str) -> dict:
    """Poll an HLTV live match page and republish state.

    Placeholder: the HLTV live DOM structure changes often; instantiate
    this with whichever scraper the team settles on, keeping the
    ``_channel`` publish contract so the SSE router doesn't need changes.
    """
    raise NotImplementedError("HLTV live scraper goes here — use simulate_match for demos.")
