"""
Automatic HLTV demo downloader.

Scrapes HLTV for pro match demos, downloads and extracts .dem files.

Usage:
    # Download ~2000 demos (40 pages × ~50 matches)
    python -m src.download_demos --pages 40 --output ../../data/demos/pro

    # Quick test (2 pages)
    python -m src.download_demos --pages 2 --output ../../data/demos/pro

    # Resume interrupted download (skips existing files)
    python -m src.download_demos --pages 40 --output ../../data/demos/pro --resume

Requirements:
    pip install httpx selectolax rarfile tqdm
    Also needs 'unrar' binary on PATH for .rar extraction:
      - Windows: download from https://www.rarlab.com/rar_add.htm
      - Linux: apt install unrar
      - macOS: brew install unrar
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# HLTV configuration
BASE_URL = "https://www.hltv.org"
REQUEST_DELAY = 5.0  # seconds between page requests
DOWNLOAD_DELAY = 2.0  # seconds between demo downloads
MAX_DEMO_SIZE = 500 * 1024 * 1024  # 500 MB
DOWNLOAD_TIMEOUT = 600  # 10 min per demo

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


class HLTVDemoDownloader:
    """Full automatic pipeline: scrape → download → extract → save .dem files."""

    def __init__(self, output_dir: Path, resume: bool = True):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.resume = resume
        self._ua_idx = 0
        self._last_request = 0.0

        # Track progress
        self.manifest_path = output_dir / "_manifest.json"
        self.manifest: dict = self._load_manifest()

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            with open(self.manifest_path) as f:
                return json.load(f)
        return {"downloaded": {}, "failed": {}, "no_demo": []}

    def _save_manifest(self):
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2, default=str)

    def _headers(self) -> dict[str, str]:
        ua = USER_AGENTS[self._ua_idx % len(USER_AGENTS)]
        self._ua_idx += 1
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{BASE_URL}/results",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
        }

    async def _rate_limit(self, delay: float = REQUEST_DELAY):
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last_request = asyncio.get_event_loop().time()

    async def _fetch_page(self, url: str, client: httpx.AsyncClient) -> str | None:
        await self._rate_limit(REQUEST_DELAY)

        for attempt in range(3):
            try:
                resp = await client.get(url, headers=self._headers(), timeout=30)
                if resp.status_code == 200:
                    return resp.text
                if resp.status_code == 429:
                    wait = REQUEST_DELAY * (2 ** (attempt + 1))
                    logger.warning("Rate limited (429), waiting %.0fs...", wait)
                    await asyncio.sleep(wait)
                elif resp.status_code == 403:
                    wait = REQUEST_DELAY * 5
                    logger.warning("Cloudflare (403), waiting %.0fs...", wait)
                    await asyncio.sleep(wait)
                else:
                    logger.warning("HTTP %d for %s", resp.status_code, url)
                    return None
            except httpx.TimeoutException:
                logger.warning("Timeout %s (attempt %d/3)", url, attempt + 1)
                await asyncio.sleep(REQUEST_DELAY * 2)
            except httpx.HTTPError as e:
                logger.error("HTTP error: %s", e)
                return None
        return None

    async def _download_file(self, url: str, client: httpx.AsyncClient) -> bytes | None:
        """Download a file with progress tracking."""
        await self._rate_limit(DOWNLOAD_DELAY)

        try:
            async with client.stream("GET", url, headers=self._headers(), timeout=DOWNLOAD_TIMEOUT) as resp:
                if resp.status_code != 200:
                    logger.warning("Download HTTP %d for %s", resp.status_code, url[:80])
                    return None

                content_length = int(resp.headers.get("content-length", 0))
                if content_length > MAX_DEMO_SIZE:
                    logger.warning("File too large: %d MB", content_length // (1024 * 1024))
                    return None

                chunks = []
                downloaded = 0
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    if downloaded > MAX_DEMO_SIZE:
                        logger.warning("Download exceeded max size, aborting")
                        return None

                return b"".join(chunks)
        except (httpx.TimeoutException, httpx.HTTPError) as e:
            logger.error("Download failed: %s", e)
            return None

    def _extract_dem_files(self, data: bytes, match_id: str) -> list[Path]:
        """Extract .dem files from downloaded archive (rar/zip/gz)."""
        extracted = []

        # Try ZIP first
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for name in zf.namelist():
                    if name.lower().endswith(".dem"):
                        dem_data = zf.read(name)
                        out_path = self.output_dir / f"{match_id}_{Path(name).name}"
                        out_path.write_bytes(dem_data)
                        extracted.append(out_path)
                        logger.info("  Extracted (zip): %s (%.1f MB)", out_path.name, len(dem_data) / 1024 / 1024)
                if extracted:
                    return extracted
        except zipfile.BadZipFile:
            pass

        # Try RAR
        try:
            import rarfile

            with tempfile.NamedTemporaryFile(suffix=".rar", delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            try:
                with rarfile.RarFile(tmp_path) as rf:
                    for name in rf.namelist():
                        if name.lower().endswith(".dem"):
                            dem_data = rf.read(name)
                            out_path = self.output_dir / f"{match_id}_{Path(name).name}"
                            out_path.write_bytes(dem_data)
                            extracted.append(out_path)
                            logger.info("  Extracted (rar): %s (%.1f MB)", out_path.name, len(dem_data) / 1024 / 1024)
            finally:
                os.unlink(tmp_path)

            if extracted:
                return extracted
        except ImportError:
            logger.warning("rarfile not installed. Install with: pip install rarfile")
        except Exception as e:
            logger.warning("RAR extraction failed: %s", e)

        # Try raw .dem (some downloads are uncompressed)
        if len(data) > 1000 and data[:8] in (b"HL2DEMO\x00", b"PBDEMS2\x00"):
            out_path = self.output_dir / f"{match_id}.dem"
            out_path.write_bytes(data)
            extracted.append(out_path)
            logger.info("  Saved raw .dem: %s (%.1f MB)", out_path.name, len(data) / 1024 / 1024)

        return extracted

    async def scrape_match_list(self, pages: int) -> list[dict]:
        """Scrape HLTV results pages to get match IDs."""
        from selectolax.parser import HTMLParser
        import re

        matches = []
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for page in range(pages):
                url = f"{BASE_URL}/results?offset={page * 50}"
                logger.info("Scraping page %d/%d: %s", page + 1, pages, url)
                html = await self._fetch_page(url, client)
                if not html:
                    logger.warning("Failed to fetch page %d", page + 1)
                    continue

                tree = HTMLParser(html)
                for result in tree.css(".result-con"):
                    try:
                        link = result.css_first("a.a-reset")
                        if not link:
                            continue
                        href = link.attributes.get("href", "")
                        m = re.search(r"/matches/(\d+)/", href)
                        if not m:
                            continue

                        match_id = m.group(1)

                        teams = result.css(".team")
                        team1 = teams[0].text(strip=True) if len(teams) >= 1 else "?"
                        team2 = teams[1].text(strip=True) if len(teams) >= 2 else "?"

                        event_el = result.css_first(".event-name")
                        event = event_el.text(strip=True) if event_el else None

                        matches.append({
                            "match_id": match_id,
                            "team1": team1,
                            "team2": team2,
                            "event": event,
                            "url": f"{BASE_URL}{href}",
                        })
                    except (IndexError, AttributeError):
                        continue

                logger.info("  Found %d matches so far", len(matches))

        return matches

    async def get_demo_url(self, match_id: str, client: httpx.AsyncClient) -> str | None:
        """Get demo download URL from match page."""
        from selectolax.parser import HTMLParser

        url = f"{BASE_URL}/matches/{match_id}/-"
        html = await self._fetch_page(url, client)
        if not html:
            return None

        tree = HTMLParser(html)

        # Method 1: data-demo-link attribute
        demo_link = tree.css_first("[data-demo-link]")
        if demo_link:
            dl = demo_link.attributes.get("data-demo-link")
            if dl:
                return dl if dl.startswith("http") else f"{BASE_URL}{dl}"

        # Method 2: /download/demo/ href
        for a in tree.css("a"):
            href = a.attributes.get("href", "")
            if "/download/demo/" in href or "/demos/" in href:
                return href if href.startswith("http") else f"{BASE_URL}{href}"

        # Method 3: GOTV demo link
        for a in tree.css("a"):
            text = a.text(strip=True).lower()
            if "demo" in text and "gotv" in text:
                href = a.attributes.get("href", "")
                if href:
                    return href if href.startswith("http") else f"{BASE_URL}{href}"

        return None

    async def run(self, pages: int = 40):
        """Full pipeline: scrape → download → extract.

        Args:
            pages: Number of HLTV result pages (each ~50 matches, 40 pages ≈ 2000 matches)
        """
        try:
            from tqdm import tqdm
        except ImportError:
            tqdm = None

        # Step 1: Scrape match list
        logger.info("=" * 60)
        logger.info("HLTV AUTO-DOWNLOADER — targeting %d pages", pages)
        logger.info("=" * 60)

        matches = await self.scrape_match_list(pages)
        logger.info("Found %d matches total", len(matches))

        # Filter out already processed matches
        new_matches = []
        for m in matches:
            mid = m["match_id"]
            if self.resume and (
                mid in self.manifest["downloaded"]
                or mid in self.manifest["failed"]
                or mid in self.manifest["no_demo"]
            ):
                continue
            new_matches.append(m)

        logger.info(
            "%d new matches to process (%d already done)",
            len(new_matches),
            len(matches) - len(new_matches),
        )

        # Step 2: Download demos
        downloaded = 0
        failed = 0
        no_demo = 0

        items = tqdm(new_matches, desc="Downloading demos") if tqdm else new_matches

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for match in items:
                mid = match["match_id"]
                label = f"{match['team1']} vs {match['team2']}"

                if tqdm:
                    items.set_postfix_str(f"{label[:30]}...")

                # Get demo URL
                demo_url = await self.get_demo_url(mid, client)
                if not demo_url:
                    self.manifest["no_demo"].append(mid)
                    self._save_manifest()
                    no_demo += 1
                    continue

                # Download
                logger.info("[%d/%d] Downloading %s — %s", downloaded + failed + no_demo + 1, len(new_matches), label, demo_url[:60])
                data = await self._download_file(demo_url, client)
                if not data:
                    self.manifest["failed"][mid] = {"error": "download_failed", "url": demo_url}
                    self._save_manifest()
                    failed += 1
                    continue

                # Extract
                dem_files = self._extract_dem_files(data, mid)
                if not dem_files:
                    self.manifest["failed"][mid] = {"error": "extraction_failed", "size": len(data)}
                    self._save_manifest()
                    failed += 1
                    continue

                self.manifest["downloaded"][mid] = {
                    "files": [str(f.name) for f in dem_files],
                    "team1": match["team1"],
                    "team2": match["team2"],
                    "event": match.get("event"),
                    "date": datetime.now(timezone.utc).isoformat(),
                }
                self._save_manifest()
                downloaded += 1

        # Summary
        total_dems = len(list(self.output_dir.glob("*.dem")))
        total_size = sum(f.stat().st_size for f in self.output_dir.glob("*.dem")) / (1024 * 1024 * 1024)

        logger.info("=" * 60)
        logger.info("DOWNLOAD COMPLETE")
        logger.info("  Downloaded: %d matches (%d new)", len(self.manifest["downloaded"]), downloaded)
        logger.info("  No demo available: %d", len(self.manifest["no_demo"]))
        logger.info("  Failed: %d", len(self.manifest["failed"]))
        logger.info("  Total .dem files: %d (%.1f GB)", total_dems, total_size)
        logger.info("=" * 60)


async def main_async(args):
    downloader = HLTVDemoDownloader(
        output_dir=Path(args.output),
        resume=args.resume,
    )
    await downloader.run(pages=args.pages)


def main():
    parser = argparse.ArgumentParser(
        description="Download CS2 pro demos from HLTV automatically",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download ~2000 demos (takes several hours due to rate limiting)
  python -m src.download_demos --pages 40 --output ../../data/demos/pro

  # Quick test with 2 pages (~100 matches)
  python -m src.download_demos --pages 2 --output ../../data/demos/pro

  # Resume an interrupted download
  python -m src.download_demos --pages 40 --output ../../data/demos/pro --resume

Note: HLTV has rate limiting and Cloudflare protection.
      Downloads are rate-limited to ~1 request per 5 seconds.
      40 pages ≈ 2000 matches ≈ 3-4 hours of scraping + download time.
      Not all matches have demos available (~60-70% do).
        """,
    )
    parser.add_argument("--pages", type=int, default=40, help="HLTV result pages to scrape (50 matches/page)")
    parser.add_argument("--output", type=str, default="../../data/demos/pro", help="Output directory for .dem files")
    parser.add_argument("--resume", action="store_true", default=True, help="Skip already downloaded matches")
    parser.add_argument("--no-resume", action="store_false", dest="resume", help="Re-download everything")

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
