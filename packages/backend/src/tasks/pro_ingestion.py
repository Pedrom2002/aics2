"""Celery tasks for automatic pro demo ingestion.

Runs on Celery Beat schedule (every 30 minutes) to scrape and ingest
professional CS2 demos from HLTV and FACEIT.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Default FACEIT hub IDs for CS2 (EU Premium, NA Premium)
FACEIT_HUB_IDS = os.environ.get(
    "FACEIT_HUB_IDS",
    "",
).split(",")


async def _check_pro_match_exists(source: str, source_match_id: str) -> bool:
    """Check if a pro match already exists in the database."""
    from sqlalchemy import select

    from src.database import _get_engine, _get_session_factory
    from src.models.pro_match import ProMatch

    _get_engine()
    async with _get_session_factory()() as session:
        result = await session.execute(
            select(ProMatch.id).where(
                ProMatch.source == source,
                ProMatch.source_match_id == source_match_id,
            )
        )
        return result.scalar_one_or_none() is not None


async def _store_pro_match(
    source: str,
    source_match_id: str,
    team1_name: str,
    team2_name: str,
    team1_score: int | None,
    team2_score: int | None,
    map_name: str,
    event_name: str | None,
    match_date: datetime,
    status: str = "pending",
) -> str:
    """Store a new pro match record in the database."""
    from src.database import _get_engine, _get_session_factory
    from src.models.pro_match import ProMatch

    _get_engine()
    async with _get_session_factory()() as session:
        pro_match = ProMatch(
            source=source,
            source_match_id=source_match_id,
            team1_name=team1_name,
            team2_name=team2_name,
            team1_score=team1_score,
            team2_score=team2_score,
            map=map_name,
            event_name=event_name,
            match_date=match_date,
            status=status,
        )
        session.add(pro_match)
        await session.commit()
        return str(pro_match.id)


@celery_app.task(name="src.tasks.pro_ingestion.ingest_hltv")
def ingest_hltv():
    """Periodic task: scrape recent HLTV matches and store new ones.

    Runs every 30 minutes via Celery Beat.
    """
    logger.info("Starting HLTV pro demo ingestion")

    try:
        # Add pro-demo-ingester to path
        ingester_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "pro-demo-ingester"
        )
        if ingester_path not in sys.path:
            sys.path.insert(0, ingester_path)

        from src.scrapers.hltv import HLTVScraper

        async def _run():
            scraper = HLTVScraper()
            matches = await scraper.get_recent_matches(pages=2)

            new_count = 0
            for match in matches:
                source_id = str(match.match_id)

                # Dedup
                if await _check_pro_match_exists("hltv", source_id):
                    continue

                # Store
                await _store_pro_match(
                    source="hltv",
                    source_match_id=source_id,
                    team1_name=match.team1_name,
                    team2_name=match.team2_name,
                    team1_score=match.team1_score,
                    team2_score=match.team2_score,
                    map_name=match.map_name,
                    event_name=match.event_name,
                    match_date=match.match_date,
                )
                new_count += 1

            logger.info(
                "HLTV ingestion complete: %d new matches from %d total", new_count, len(matches)
            )
            return new_count

        return asyncio.run(_run())

    except Exception as exc:
        logger.exception("HLTV ingestion failed")
        return {"error": str(exc)}


@celery_app.task(name="src.tasks.pro_ingestion.ingest_faceit")
def ingest_faceit():
    """Periodic task: fetch recent FACEIT matches and store new ones.

    Runs every 30 minutes via Celery Beat.
    Requires FACEIT_API_KEY and FACEIT_HUB_IDS environment variables.
    """
    if not FACEIT_HUB_IDS or FACEIT_HUB_IDS == [""]:
        logger.debug("No FACEIT hub IDs configured, skipping")
        return {"skipped": True}

    logger.info("Starting FACEIT pro demo ingestion")

    try:
        ingester_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "pro-demo-ingester"
        )
        if ingester_path not in sys.path:
            sys.path.insert(0, ingester_path)

        from src.clients.faceit import FACEITClient

        async def _run():
            client = FACEITClient()
            total_new = 0

            for hub_id in FACEIT_HUB_IDS:
                hub_id = hub_id.strip()
                if not hub_id:
                    continue

                matches = await client.get_hub_matches(hub_id, limit=20)

                for match in matches:
                    if match.status != "finished":
                        continue

                    if await _check_pro_match_exists("faceit", match.match_id):
                        continue

                    await _store_pro_match(
                        source="faceit",
                        source_match_id=match.match_id,
                        team1_name=match.team1_name,
                        team2_name=match.team2_name,
                        team1_score=match.team1_score,
                        team2_score=match.team2_score,
                        map_name=match.map_name,
                        event_name=None,
                        match_date=match.match_date,
                    )
                    total_new += 1

            logger.info("FACEIT ingestion complete: %d new matches", total_new)
            return total_new

        return asyncio.run(_run())

    except Exception as exc:
        logger.exception("FACEIT ingestion failed")
        return {"error": str(exc)}


@celery_app.task(name="src.tasks.pro_ingestion.backfill_hltv")
def backfill_hltv(pages: int = 30):
    """One-time task: backfill last ~3 months of HLTV matches.

    Usage:
        from src.tasks.pro_ingestion import backfill_hltv
        backfill_hltv.delay(pages=30)  # ~30 pages × 50 matches = ~1500 matches

    Or from CLI:
        celery -A src.tasks.celery_app call src.tasks.pro_ingestion.backfill_hltv --args='[30]'
    """
    logger.info("Starting HLTV backfill (%d pages)", pages)

    try:
        ingester_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "pro-demo-ingester"
        )
        if ingester_path not in sys.path:
            sys.path.insert(0, ingester_path)

        from src.scrapers.hltv import HLTVScraper

        async def _run():
            scraper = HLTVScraper()
            matches = await scraper.get_recent_matches(pages=pages)

            new_count = 0
            for match in matches:
                source_id = str(match.match_id)
                if await _check_pro_match_exists("hltv", source_id):
                    continue

                await _store_pro_match(
                    source="hltv",
                    source_match_id=source_id,
                    team1_name=match.team1_name,
                    team2_name=match.team2_name,
                    team1_score=match.team1_score,
                    team2_score=match.team2_score,
                    map_name=match.map_name,
                    event_name=match.event_name,
                    match_date=match.match_date,
                )
                new_count += 1

            logger.info(
                "HLTV backfill complete: %d new matches from %d total", new_count, len(matches)
            )
            return new_count

        return asyncio.run(_run())

    except Exception as exc:
        logger.exception("HLTV backfill failed")
        return {"error": str(exc)}
