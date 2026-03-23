"""
HLTV.org scraper for professional CS2 demo downloads.

Rate limiting: 1 request per 5 seconds (conservative).
Respects Cloudflare protection with proper headers and backoff.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from selectolax.parser import HTMLParser

logger = logging.getLogger(__name__)

BASE_URL = "https://www.hltv.org"
REQUEST_DELAY = 5.0  # seconds between requests

# Rotate user agents to reduce blocking risk
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


@dataclass
class HLTVMatchInfo:
    """Parsed match info from HLTV."""

    match_id: int
    team1_name: str
    team2_name: str
    team1_score: int | None
    team2_score: int | None
    map_name: str
    event_name: str | None
    event_tier: str | None
    match_date: datetime
    match_url: str
    demo_id: int | None = None
    demo_url: str | None = None


class HLTVScraper:
    """Scrapes professional CS2 match data and demo links from HLTV.org.

    Usage:
        scraper = HLTVScraper()
        matches = await scraper.get_recent_matches(pages=3)
        for match in matches:
            demo_url = await scraper.get_demo_url(match.match_id)
    """

    def __init__(self, request_delay: float = REQUEST_DELAY):
        self._delay = request_delay
        self._ua_index = 0
        self._last_request_time = 0.0

    def _get_headers(self) -> dict[str, str]:
        ua = USER_AGENTS[self._ua_index % len(USER_AGENTS)]
        self._ua_index += 1
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": BASE_URL,
        }

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self._delay:
            await asyncio.sleep(self._delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _fetch(self, url: str, client: httpx.AsyncClient) -> str | None:
        """Fetch a URL with rate limiting, retries, and backoff."""
        await self._rate_limit()

        for attempt in range(3):
            try:
                resp = await client.get(url, headers=self._get_headers(), timeout=30)
                if resp.status_code == 200:
                    return resp.text
                elif resp.status_code == 429:
                    # Rate limited — exponential backoff
                    wait = self._delay * (2**attempt)
                    logger.warning("HLTV rate limited (429), waiting %.1fs", wait)
                    await asyncio.sleep(wait)
                elif resp.status_code == 403:
                    logger.warning("HLTV blocked (403), possible Cloudflare challenge")
                    await asyncio.sleep(self._delay * 3)
                else:
                    logger.warning("HLTV returned %d for %s", resp.status_code, url)
                    return None
            except httpx.TimeoutException:
                logger.warning("Timeout fetching %s (attempt %d)", url, attempt + 1)
                await asyncio.sleep(self._delay)
            except httpx.HTTPError as e:
                logger.warning("HTTP error fetching %s: %s", url, e)
                return None

        return None

    async def get_recent_matches(self, pages: int = 5) -> list[HLTVMatchInfo]:
        """Scrape recent match results from HLTV.

        Args:
            pages: Number of result pages to scrape (each ~50 matches).

        Returns:
            List of HLTVMatchInfo with basic match data.
        """
        matches: list[HLTVMatchInfo] = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for page_offset in range(pages):
                url = f"{BASE_URL}/results?offset={page_offset * 50}"
                html = await self._fetch(url, client)
                if html is None:
                    continue

                page_matches = self._parse_results_page(html)
                matches.extend(page_matches)
                logger.info("Scraped %d matches from HLTV page %d", len(page_matches), page_offset + 1)

        return matches

    def _parse_results_page(self, html: str) -> list[HLTVMatchInfo]:
        """Parse a HLTV results page HTML into match info."""
        tree = HTMLParser(html)
        matches: list[HLTVMatchInfo] = []

        for result in tree.css(".result-con"):
            try:
                # Extract match URL and ID
                link = result.css_first("a.a-reset")
                if not link or not link.attributes.get("href"):
                    continue
                match_url = link.attributes["href"]
                match_id_match = re.search(r"/matches/(\d+)/", match_url)
                if not match_id_match:
                    continue
                match_id = int(match_id_match.group(1))

                # Teams
                teams = result.css(".team")
                if len(teams) < 2:
                    continue
                team1_name = teams[0].text(strip=True)
                team2_name = teams[1].text(strip=True)

                # Scores
                scores = result.css(".result-score span")
                team1_score = int(scores[0].text(strip=True)) if len(scores) >= 2 else None
                team2_score = int(scores[1].text(strip=True)) if len(scores) >= 2 else None

                # Event
                event_el = result.css_first(".event-name")
                event_name = event_el.text(strip=True) if event_el else None

                # Map (may not always be available in list)
                map_el = result.css_first(".map-text")
                map_name = map_el.text(strip=True) if map_el else "unknown"

                matches.append(
                    HLTVMatchInfo(
                        match_id=match_id,
                        team1_name=team1_name,
                        team2_name=team2_name,
                        team1_score=team1_score,
                        team2_score=team2_score,
                        map_name=map_name,
                        event_name=event_name,
                        event_tier=None,
                        match_date=datetime.now(timezone.utc),
                        match_url=f"{BASE_URL}{match_url}",
                    )
                )
            except (ValueError, IndexError, AttributeError):
                continue

        return matches

    async def get_demo_url(self, match_id: int) -> str | None:
        """Get the demo download URL for a specific match.

        Returns the direct URL or None if no demo is available.
        """
        url = f"{BASE_URL}/matches/{match_id}/-"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            html = await self._fetch(url, client)
            if html is None:
                return None

        tree = HTMLParser(html)

        # Look for demo download link
        demo_link = tree.css_first("a.stream-box[data-demo-link]")
        if demo_link and demo_link.attributes.get("data-demo-link"):
            return demo_link.attributes["data-demo-link"]

        # Alternative: look for /download/demo/ links
        for link in tree.css("a"):
            href = link.attributes.get("href", "")
            if "/download/demo/" in href:
                return f"{BASE_URL}{href}" if href.startswith("/") else href

        return None

    async def get_match_detail(self, match_id: int) -> HLTVMatchInfo | None:
        """Get detailed match info from the match page."""
        url = f"{BASE_URL}/matches/{match_id}/-"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            html = await self._fetch(url, client)
            if html is None:
                return None

        tree = HTMLParser(html)

        try:
            # Teams
            teams = tree.css(".teamName")
            team1 = teams[0].text(strip=True) if len(teams) >= 1 else "Unknown"
            team2 = teams[1].text(strip=True) if len(teams) >= 2 else "Unknown"

            # Event
            event_el = tree.css_first(".event a")
            event_name = event_el.text(strip=True) if event_el else None

            # Date
            date_el = tree.css_first(".date[data-unix]")
            if date_el and date_el.attributes.get("data-unix"):
                ts = int(date_el.attributes["data-unix"]) / 1000
                match_date = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                match_date = datetime.now(timezone.utc)

            # Maps played
            maps = tree.css(".mapholder .mapname")
            map_name = maps[0].text(strip=True) if maps else "unknown"

            return HLTVMatchInfo(
                match_id=match_id,
                team1_name=team1,
                team2_name=team2,
                team1_score=None,
                team2_score=None,
                map_name=map_name,
                event_name=event_name,
                event_tier=None,
                match_date=match_date,
                match_url=url,
            )
        except (IndexError, AttributeError, ValueError):
            return None
