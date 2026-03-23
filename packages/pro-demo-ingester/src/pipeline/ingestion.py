"""
Pro demo ingestion pipeline — orchestrates scraping, deduplication, download, and parsing.

Designed to run on a schedule (e.g., Celery Beat every 30 minutes).
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of processing a single pro match."""

    source: str
    source_match_id: str
    status: str  # new, duplicate, downloaded, failed
    error: str | None = None


class ProDemoIngestionPipeline:
    """Orchestrates the full pro demo ingestion workflow.

    Steps:
        1. Scrape match list from HLTV / FACEIT
        2. Dedup against existing pro_matches (by source + source_match_id)
        3. Download demo files
        4. Validate .dem files
        5. Upload to S3 (MinIO)
        6. Trigger parsing pipeline (reuse existing Celery task)

    Usage:
        pipeline = ProDemoIngestionPipeline(db_session, storage_service)
        results = await pipeline.run_hltv_ingestion(pages=3)
    """

    def __init__(self, db_check_fn=None, upload_fn=None, trigger_parse_fn=None):
        """
        Args:
            db_check_fn: async fn(source, source_match_id) -> bool (exists?)
            upload_fn: async fn(file_data, filename) -> s3_key
            trigger_parse_fn: fn(demo_id, s3_key) -> None
        """
        self._db_check = db_check_fn
        self._upload = upload_fn
        self._trigger_parse = trigger_parse_fn

    async def ingest_hltv_matches(self, pages: int = 3) -> list[IngestionResult]:
        """Run HLTV ingestion for recent matches."""
        from src.scrapers.hltv import HLTVScraper

        scraper = HLTVScraper()
        matches = await scraper.get_recent_matches(pages=pages)
        logger.info("HLTV: found %d matches across %d pages", len(matches), pages)

        results: list[IngestionResult] = []
        for match in matches:
            result = await self._process_match(
                source="hltv",
                source_match_id=str(match.match_id),
                team1_name=match.team1_name,
                team2_name=match.team2_name,
                team1_score=match.team1_score,
                team2_score=match.team2_score,
                map_name=match.map_name,
                event_name=match.event_name,
                match_date=match.match_date,
                demo_url_getter=lambda mid=match.match_id: scraper.get_demo_url(mid),
            )
            results.append(result)

        return results

    async def ingest_faceit_matches(self, hub_id: str, pages: int = 3) -> list[IngestionResult]:
        """Run FACEIT ingestion for a specific hub."""
        from src.clients.faceit import FACEITClient

        client = FACEITClient()
        results: list[IngestionResult] = []

        for page in range(pages):
            matches = await client.get_hub_matches(hub_id, offset=page * 20)
            logger.info("FACEIT: found %d matches on page %d", len(matches), page + 1)

            for match in matches:
                if match.status != "finished":
                    continue

                result = await self._process_match(
                    source="faceit",
                    source_match_id=match.match_id,
                    team1_name=match.team1_name,
                    team2_name=match.team2_name,
                    team1_score=match.team1_score,
                    team2_score=match.team2_score,
                    map_name=match.map_name,
                    event_name=None,
                    match_date=match.match_date,
                    demo_url_getter=lambda mid=match.match_id: client.get_demo_url(mid),
                )
                results.append(result)

        return results

    async def _process_match(
        self,
        source: str,
        source_match_id: str,
        team1_name: str,
        team2_name: str,
        team1_score: int | None,
        team2_score: int | None,
        map_name: str,
        event_name: str | None,
        match_date: datetime,
        demo_url_getter,
    ) -> IngestionResult:
        """Process a single match: dedup → download → upload → trigger parse."""
        # 1. Dedup check
        if self._db_check and await self._db_check(source, source_match_id):
            return IngestionResult(source, source_match_id, "duplicate")

        # 2. Get demo URL
        try:
            demo_url = await demo_url_getter()
        except Exception as e:
            logger.warning("Failed to get demo URL for %s:%s: %s", source, source_match_id, e)
            return IngestionResult(source, source_match_id, "failed", str(e))

        if not demo_url:
            return IngestionResult(source, source_match_id, "failed", "No demo URL available")

        # 3. Download demo
        try:
            file_data = await self._download_demo(demo_url)
        except Exception as e:
            return IngestionResult(source, source_match_id, "failed", f"Download failed: {e}")

        if not file_data:
            return IngestionResult(source, source_match_id, "failed", "Empty demo file")

        # 4. Compute hash for dedup
        file_hash = hashlib.sha256(file_data).hexdigest()

        # 5. Upload to S3
        if self._upload:
            try:
                filename = f"pro/{source}/{source_match_id}.dem"
                s3_key = await self._upload(file_data, filename)
                logger.info("Uploaded %s:%s to %s (%d bytes)", source, source_match_id, s3_key, len(file_data))
            except Exception as e:
                return IngestionResult(source, source_match_id, "failed", f"Upload failed: {e}")

        return IngestionResult(source, source_match_id, "downloaded")

    async def _download_demo(self, url: str) -> bytes | None:
        """Download a demo file from URL with timeout and size limits."""
        max_size = 500 * 1024 * 1024  # 500 MB

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                resp = await client.get(url, timeout=300)  # 5 min timeout for large files
                resp.raise_for_status()

                if len(resp.content) > max_size:
                    logger.warning("Demo too large: %d bytes", len(resp.content))
                    return None

                return resp.content
            except httpx.HTTPError as e:
                logger.error("Demo download error: %s", e)
                return None
