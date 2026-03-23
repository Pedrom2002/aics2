"""
FACEIT Downloads API client for semi-pro CS2 demo downloads.

Requires approved FACEIT Downloads API application.
Apply at: https://fce.gg/downloads-api-application
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

FACEIT_API_BASE = "https://open.faceit.com/data/v4"
FACEIT_DOWNLOADS_BASE = "https://open.faceit.com/download/v2"


@dataclass
class FACEITMatchInfo:
    """Match info from FACEIT API."""

    match_id: str
    game: str
    region: str
    team1_name: str
    team2_name: str
    team1_score: int | None
    team2_score: int | None
    map_name: str
    match_date: datetime
    demo_url: str | None = None
    status: str = "finished"


class FACEITClient:
    """Official FACEIT API client for match data and demo downloads.

    Requires a FACEIT API key with Downloads API scope.

    Usage:
        client = FACEITClient(api_key="your-key")
        matches = await client.get_hub_matches(hub_id="...")
        for match in matches:
            demo_url = await client.get_demo_url(match.match_id)
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("FACEIT_API_KEY", "")
        if not self.api_key:
            logger.warning("FACEIT API key not set. Set FACEIT_API_KEY env var.")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    async def get_hub_matches(
        self,
        hub_id: str,
        offset: int = 0,
        limit: int = 20,
    ) -> list[FACEITMatchInfo]:
        """Get recent matches from a FACEIT hub.

        Args:
            hub_id: FACEIT hub ID (e.g., for CS2 Premium hub)
            offset: Pagination offset
            limit: Number of matches to return (max 20)
        """
        url = f"{FACEIT_API_BASE}/hubs/{hub_id}/matches"
        params = {"offset": offset, "limit": min(limit, 20)}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=self._headers(), params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                logger.error("FACEIT API error: %s", e)
                return []

        matches: list[FACEITMatchInfo] = []
        for item in data.get("items", []):
            try:
                teams = item.get("teams", {})
                faction1 = teams.get("faction1", {})
                faction2 = teams.get("faction2", {})

                results = item.get("results", {})
                score = results.get("score", {})

                started_at = item.get("started_at")
                match_date = (
                    datetime.fromtimestamp(started_at, tz=timezone.utc)
                    if started_at
                    else datetime.now(timezone.utc)
                )

                # Map from voting
                voting = item.get("voting", {})
                map_pick = voting.get("map", {}).get("pick", ["unknown"])
                map_name = map_pick[0] if map_pick else "unknown"

                matches.append(
                    FACEITMatchInfo(
                        match_id=item["match_id"],
                        game=item.get("game", "cs2"),
                        region=item.get("region", "EU"),
                        team1_name=faction1.get("name", "Team 1"),
                        team2_name=faction2.get("name", "Team 2"),
                        team1_score=score.get("faction1"),
                        team2_score=score.get("faction2"),
                        map_name=map_name,
                        match_date=match_date,
                        status=item.get("status", "finished"),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue

        return matches

    async def get_demo_url(self, match_id: str) -> str | None:
        """Get demo download URL for a FACEIT match.

        Uses the FACEIT Downloads API (requires approved application).

        Returns a signed URL valid for a limited time, or None.
        """
        url = f"{FACEIT_DOWNLOADS_BASE}/demos/download"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    url,
                    headers=self._headers(),
                    json={"match_id": match_id},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("url") or data.get("demo_url")
                elif resp.status_code == 404:
                    logger.debug("No demo available for FACEIT match %s", match_id)
                    return None
                else:
                    logger.warning("FACEIT demo download returned %d for %s", resp.status_code, match_id)
                    return None
            except httpx.HTTPError as e:
                logger.error("FACEIT demo download error: %s", e)
                return None

    async def get_match_detail(self, match_id: str) -> FACEITMatchInfo | None:
        """Get detailed match info from FACEIT API."""
        url = f"{FACEIT_API_BASE}/matches/{match_id}"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=self._headers(), timeout=15)
                resp.raise_for_status()
                item = resp.json()
            except httpx.HTTPError as e:
                logger.error("FACEIT match detail error: %s", e)
                return None

        try:
            teams = item.get("teams", {})
            faction1 = teams.get("faction1", {})
            faction2 = teams.get("faction2", {})
            results = item.get("results", {})
            score = results.get("score", {})

            started_at = item.get("started_at")
            match_date = (
                datetime.fromtimestamp(started_at, tz=timezone.utc)
                if started_at
                else datetime.now(timezone.utc)
            )

            voting = item.get("voting", {})
            map_pick = voting.get("map", {}).get("pick", ["unknown"])
            map_name = map_pick[0] if map_pick else "unknown"

            demo_urls = item.get("demo_url", [])
            demo_url = demo_urls[0] if demo_urls else None

            return FACEITMatchInfo(
                match_id=item["match_id"],
                game=item.get("game", "cs2"),
                region=item.get("region", "EU"),
                team1_name=faction1.get("name", "Team 1"),
                team2_name=faction2.get("name", "Team 2"),
                team1_score=score.get("faction1"),
                team2_score=score.get("faction2"),
                map_name=map_name,
                match_date=match_date,
                demo_url=demo_url,
                status=item.get("status", "finished"),
            )
        except (KeyError, TypeError, ValueError):
            return None
