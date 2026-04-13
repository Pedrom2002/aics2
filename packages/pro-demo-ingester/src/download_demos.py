"""
Automatic HLTV demo downloader using real browser (Playwright) to bypass Cloudflare.

Usage:
    python -m src.download_demos --pages 1 --output ../../data/demos/pro
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import re
import tempfile
import time
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_URL = "https://www.hltv.org"
MAX_DEMO_SIZE = 500 * 1024 * 1024


class HLTVDemoDownloader:
    """Download pro demos from HLTV using Playwright (real browser)."""

    def __init__(self, output_dir: Path, resume: bool = True):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.resume = resume
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

    def _extract_dem(self, data: bytes, match_id: str) -> list[Path]:
        """Extract .dem files from archive."""
        extracted = []

        # ZIP
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for name in zf.namelist():
                    if name.lower().endswith(".dem"):
                        dem_data = zf.read(name)
                        out = self.output_dir / f"{match_id}_{Path(name).name}"
                        out.write_bytes(dem_data)
                        extracted.append(out)
                        logger.info("  Extracted (zip): %s (%.1f MB)", out.name, len(dem_data) / 1048576)
            if extracted:
                return extracted
        except zipfile.BadZipFile:
            pass

        # RAR
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
                            out = self.output_dir / f"{match_id}_{Path(name).name}"
                            out.write_bytes(dem_data)
                            extracted.append(out)
                            logger.info("  Extracted (rar): %s (%.1f MB)", out.name, len(dem_data) / 1048576)
            finally:
                os.unlink(tmp_path)
            if extracted:
                return extracted
        except ImportError:
            logger.warning("  rarfile not installed — pip install rarfile + unrar on PATH")
        except Exception as e:
            logger.warning("  RAR extraction failed: %s", e)

        # Raw .dem
        if len(data) > 1000 and data[:8] in (b"HL2DEMO\x00", b"PBDEMS2\x00"):
            out = self.output_dir / f"{match_id}.dem"
            out.write_bytes(data)
            extracted.append(out)
            logger.info("  Saved raw .dem: %s (%.1f MB)", out.name, len(data) / 1048576)

        return extracted

    def run(self, pages: int = 1):
        """Full pipeline using Playwright browser."""
        from playwright.sync_api import sync_playwright

        logger.info("=" * 60)
        logger.info("HLTV DEMO DOWNLOADER (Playwright) — %d pages", pages)
        logger.info("=" * 60)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            # Step 1: Scrape match list
            matches = []
            for pg in range(pages):
                url = f"{BASE_URL}/results?offset={pg * 50}"
                logger.info("Scraping page %d/%d: %s", pg + 1, pages, url)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    # Wait for results to load
                    page.wait_for_selector(".result-con", timeout=15000)
                    time.sleep(2)  # Let JS finish rendering

                    html = page.content()
                    from selectolax.parser import HTMLParser
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

                            teams = result.css(".team")
                            team1 = teams[0].text(strip=True) if len(teams) >= 1 else "?"
                            team2 = teams[1].text(strip=True) if len(teams) >= 2 else "?"

                            event_el = result.css_first(".event-name")
                            event = event_el.text(strip=True) if event_el else None

                            matches.append({
                                "match_id": m.group(1),
                                "team1": team1,
                                "team2": team2,
                                "event": event,
                            })
                        except (IndexError, AttributeError):
                            continue

                    logger.info("  %d matches found so far", len(matches))
                except Exception as e:
                    logger.warning("  Failed to scrape page %d: %s", pg + 1, e)

                time.sleep(3)

            logger.info("Total: %d matches found", len(matches))

            # Filter already processed
            new_matches = [
                m for m in matches
                if m["match_id"] not in self.manifest.get("downloaded", {})
                and m["match_id"] not in self.manifest.get("failed", {})
                and m["match_id"] not in self.manifest.get("no_demo", [])
            ] if self.resume else matches

            logger.info("%d new matches to process", len(new_matches))

            # Step 2: Download each
            downloaded = 0
            for i, match in enumerate(new_matches):
                mid = match["match_id"]
                label = f"{match['team1']} vs {match['team2']}"
                logger.info("[%d/%d] %s (match %s)", i + 1, len(new_matches), label, mid)

                # Visit match page to find demo URL
                try:
                    match_url = f"{BASE_URL}/matches/{mid}/-"
                    html = ""
                    for attempt in range(3):
                        page.goto(match_url, wait_until="domcontentloaded", timeout=30000)
                        try:
                            page.wait_for_selector(".standard-box, .matchstats, .match-page", timeout=10000)
                        except Exception:
                            pass
                        time.sleep(2 + attempt * 2)
                        html = page.content()
                        # Cloudflare challenge page is ~30-40KB; real page is 1MB+
                        if len(html) > 200000:
                            break
                        logger.info("  Short page (%d bytes) — retrying (attempt %d)", len(html), attempt + 2)
                    if len(html) < 200000:
                        logger.info("  Blocked by Cloudflare, skipping")
                        self.manifest["failed"][mid] = "cloudflare_blocked"
                        self._save_manifest()
                        time.sleep(5)
                        continue
                    tree = HTMLParser(html)

                    demo_url = None

                    # Find demo link
                    for el in tree.css("[data-demo-link]"):
                        dl = el.attributes.get("data-demo-link")
                        if dl:
                            demo_url = dl if dl.startswith("http") else f"{BASE_URL}{dl}"
                            break

                    if not demo_url:
                        for a in tree.css("a"):
                            href = a.attributes.get("href", "")
                            if "/download/demo/" in href or "/demos/" in href:
                                demo_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                                break

                    if not demo_url:
                        logger.info("  No demo available")
                        self.manifest["no_demo"].append(mid)
                        self._save_manifest()
                        time.sleep(3)
                        continue

                    logger.info("  Demo URL: %s", demo_url[:80])

                    # Download via Playwright (handles cookies/session)
                    try:
                        response = page.request.get(demo_url, timeout=600000)
                        if response.status != 200:
                            logger.warning("  Download HTTP %d", response.status)
                            self.manifest["failed"][mid] = f"http_{response.status}"
                            self._save_manifest()
                            continue

                        data = response.body()
                        logger.info("  Downloaded %.1f MB", len(data) / 1048576)

                        if len(data) > MAX_DEMO_SIZE:
                            logger.warning("  Too large, skipping")
                            self.manifest["failed"][mid] = "too_large"
                            self._save_manifest()
                            continue

                    except Exception as e:
                        logger.warning("  Download failed: %s", e)
                        self.manifest["failed"][mid] = str(e)[:100]
                        self._save_manifest()
                        continue

                    # Extract
                    dem_files = self._extract_dem(data, mid)
                    if not dem_files:
                        logger.warning("  No .dem found in archive (%d bytes)", len(data))
                        self.manifest["failed"][mid] = "no_dem_in_archive"
                        self._save_manifest()
                        continue

                    self.manifest["downloaded"][mid] = {
                        "files": [f.name for f in dem_files],
                        "team1": match["team1"],
                        "team2": match["team2"],
                        "event": match.get("event"),
                    }
                    self._save_manifest()
                    downloaded += 1
                    logger.info("  SUCCESS — %d .dem file(s)", len(dem_files))

                except Exception as e:
                    logger.warning("  Error processing match %s: %s", mid, e)
                    self.manifest["failed"][mid] = str(e)[:100]
                    self._save_manifest()

                time.sleep(3)

            browser.close()

        # Summary
        total_dems = len(list(self.output_dir.glob("*.dem")))
        total_size = sum(f.stat().st_size for f in self.output_dir.glob("*.dem")) / (1024 ** 3)
        logger.info("=" * 60)
        logger.info("DONE: %d new downloads, %d total .dem files (%.2f GB)", downloaded, total_dems, total_size)
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Download CS2 pro demos from HLTV (Playwright)")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--output", type=str, default="../../data/demos/pro")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
    downloader = HLTVDemoDownloader(Path(args.output), resume=not args.no_resume)
    downloader.run(pages=args.pages)


if __name__ == "__main__":
    main()
