import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _to_uuid(value: str | uuid.UUID) -> uuid.UUID:
    """Convert string to UUID if needed."""
    return uuid.UUID(value) if isinstance(value, str) else value


async def _update_demo_status(demo_id: str, status: str, error_message: str | None = None):
    """Update demo status in the database."""
    from datetime import UTC, datetime

    from sqlalchemy import update

    from src.database import _get_engine, _get_session_factory
    from src.models.demo import Demo

    _get_engine()
    demo_uuid = _to_uuid(demo_id)
    async with _get_session_factory()() as session:
        values: dict = {"status": status, "updated_at": datetime.now(UTC)}

        if status == "parsing":
            values["parsing_started_at"] = datetime.now(UTC)
        elif status == "extracting_features":
            values["parsing_completed_at"] = datetime.now(UTC)
            values["processing_started_at"] = datetime.now(UTC)
        elif status == "completed":
            values["processing_completed_at"] = datetime.now(UTC)
        elif status in ("failed", "error"):
            values["error_message"] = error_message

        result = await session.execute(update(Demo).where(Demo.id == demo_uuid).values(**values))
        await session.commit()

        if result.rowcount == 0:
            logger.warning("Demo %s not found when updating status to %s", demo_id, status)


async def _check_demo_exists(demo_id: str) -> bool:
    """Check if a demo record exists in the database."""
    from sqlalchemy import select

    from src.database import _get_engine, _get_session_factory
    from src.models.demo import Demo

    _get_engine()
    demo_uuid = _to_uuid(demo_id)
    async with _get_session_factory()() as session:
        result = await session.execute(select(Demo.id).where(Demo.id == demo_uuid))
        return result.scalar_one_or_none() is not None


async def _get_demo_org_id(demo_id: str) -> uuid.UUID | None:
    """Get the org_id for a demo."""
    from sqlalchemy import select

    from src.database import _get_engine, _get_session_factory
    from src.models.demo import Demo

    _get_engine()
    demo_uuid = _to_uuid(demo_id)
    async with _get_session_factory()() as session:
        result = await session.execute(select(Demo.org_id).where(Demo.id == demo_uuid))
        return result.scalar_one_or_none()


async def _download_demo(s3_key: str) -> bytes:
    """Download demo file from MinIO."""
    from src.services.storage_service import download_from_minio

    return await download_from_minio(s3_key)


async def _store_match_data(demo_id: str, org_id: uuid.UUID, parsed) -> str:
    """Store parsed demo data as Match, Round, and PlayerMatchStats records."""
    from src.database import _get_engine, _get_session_factory
    from src.models.match import Match
    from src.models.player_match_stats import PlayerMatchStats
    from src.models.round import Round

    _get_engine()
    async with _get_session_factory()() as session:
        # Create Match
        match = Match(
            demo_id=uuid.UUID(demo_id),
            org_id=org_id,
            map=parsed.map_name,
            tickrate=parsed.tickrate,
            team1_name=parsed.team1_name,
            team2_name=parsed.team2_name,
            team1_score=parsed.team1_score,
            team2_score=parsed.team2_score,
            match_type="competitive",
            total_rounds=parsed.total_rounds,
            overtime_rounds=parsed.overtime_rounds,
            duration_seconds=parsed.duration_seconds,
        )
        session.add(match)
        await session.flush()

        match_id = match.id

        # Create Rounds
        for rd in parsed.rounds:
            session.add(
                Round(
                    match_id=match_id,
                    round_number=rd.round_number,
                    winner_side=rd.winner_side,
                    win_reason=rd.win_reason,
                    team1_score=rd.team1_score,
                    team2_score=rd.team2_score,
                    bomb_planted=rd.bomb_planted,
                    bomb_defused=rd.bomb_defused,
                    plant_site=rd.plant_site,
                    t_equipment_value=rd.t_equipment_value,
                    ct_equipment_value=rd.ct_equipment_value,
                    t_buy_type=rd.t_buy_type,
                    ct_buy_type=rd.ct_buy_type,
                    start_tick=rd.start_tick,
                    end_tick=rd.end_tick,
                    duration_seconds=rd.duration_seconds,
                )
            )

        # Create PlayerMatchStats
        for player in parsed.players:
            session.add(
                PlayerMatchStats(
                    match_id=match_id,
                    org_id=org_id,
                    player_steam_id=player.steam_id,
                    player_name=player.name,
                    team_side=player.team_side,
                    kills=player.kills,
                    deaths=player.deaths,
                    assists=player.assists,
                    headshot_kills=player.headshot_kills,
                    damage=player.damage,
                    adr=player.adr,
                    flash_assists=player.flash_assists,
                    enemies_flashed=player.enemies_flashed,
                    utility_damage=player.utility_damage,
                    first_kills=player.first_kills,
                    first_deaths=player.first_deaths,
                    multi_kills_3k=player.multi_kills_3k,
                    multi_kills_4k=player.multi_kills_4k,
                    multi_kills_5k=player.multi_kills_5k,
                    clutch_wins=player.clutch_wins,
                    trade_kills=player.trade_kills,
                    trade_deaths=player.trade_deaths,
                    kast_rounds=player.kast_rounds,
                    rounds_survived=player.rounds_survived,
                )
            )

        await session.commit()
        logger.info(
            "Stored match %s: %s on %s (%d rounds, %d players)",
            match_id,
            f"{parsed.team1_score}-{parsed.team2_score}",
            parsed.map_name,
            len(parsed.rounds),
            len(parsed.players),
        )
        return str(match_id)


async def _compute_and_store_ratings(match_id: str, parsed) -> None:
    """Compute feature-based ratings and store them on PlayerMatchStats."""
    from sqlalchemy import update

    from src.database import _get_engine, _get_session_factory
    from src.models.player_match_stats import PlayerMatchStats
    from src.services.feature_engine import compute_match_features

    _get_engine()
    match_uuid = _to_uuid(match_id)

    async with _get_session_factory()() as session:
        for player in parsed.players:
            features = compute_match_features(
                player_steam_id=player.steam_id,
                player_name=player.name,
                match_id=match_id,
                kills=player.kills,
                deaths=player.deaths,
                assists=player.assists,
                headshot_kills=player.headshot_kills,
                damage=player.damage,
                total_rounds=parsed.total_rounds,
                flash_assists=player.flash_assists,
                utility_damage=player.utility_damage,
                first_kills=player.first_kills,
                first_deaths=player.first_deaths,
                trade_kills=player.trade_kills,
                trade_deaths=player.trade_deaths,
                clutch_wins=player.clutch_wins,
                multi_kills_3k=player.multi_kills_3k,
                multi_kills_4k=player.multi_kills_4k,
                multi_kills_5k=player.multi_kills_5k,
                kast_rounds=player.kast_rounds,
                rounds_survived=player.rounds_survived,
            )

            await session.execute(
                update(PlayerMatchStats)
                .where(
                    PlayerMatchStats.match_id == match_uuid,
                    PlayerMatchStats.player_steam_id == player.steam_id,
                )
                .values(overall_rating=features.hltv_rating_approx)
            )

        await session.commit()
        logger.info("Computed ratings for match %s (%d players)", match_id, len(parsed.players))


@celery_app.task(bind=True, max_retries=3, name="src.tasks.demo_processing.process_demo")
def process_demo(self, demo_id: str, s3_key: str):
    """
    Process a CS2 demo file.

    Pipeline:
    1. Download .dem from MinIO
    2. Parse with awpy via demo-parser
    3. Extract match metadata, rounds, player stats
    4. Store in PostgreSQL
    5. Update demo status -> completed
    """
    logger.info("Processing demo %s from %s", demo_id, s3_key)

    try:
        # Verify demo exists before processing
        if not asyncio.run(_check_demo_exists(demo_id)):
            logger.error("Demo %s not found in database, aborting", demo_id)
            return {"demo_id": demo_id, "status": "not_found"}

        # Get org_id for the demo
        org_id = asyncio.run(_get_demo_org_id(demo_id))
        if not org_id:
            logger.error("Demo %s has no org_id, aborting", demo_id)
            return {"demo_id": demo_id, "status": "error"}

        # Step 1: Mark as parsing & download from MinIO
        asyncio.run(_update_demo_status(demo_id, "parsing"))
        logger.info("Downloading demo %s from %s", demo_id, s3_key)
        file_data = asyncio.run(_download_demo(s3_key))
        logger.info("Downloaded %d bytes for demo %s", len(file_data), demo_id)

        # Step 2: Write to temp file and parse with awpy
        with tempfile.TemporaryDirectory() as tmp_dir:
            dem_path = Path(tmp_dir) / "demo.dem"
            dem_path.write_bytes(file_data)
            del file_data  # Free memory

            logger.info("Parsing demo %s with awpy", demo_id)

            from src.services.demo_parser import parse_demo as awpy_parse

            parsed = awpy_parse(dem_path)

        logger.info(
            "Parsed demo %s: %s, %d-%d, %d rounds, %d players",
            demo_id,
            parsed.map_name,
            parsed.team1_score,
            parsed.team2_score,
            parsed.total_rounds,
            len(parsed.players),
        )

        # Step 3: Store match data in PostgreSQL
        asyncio.run(_update_demo_status(demo_id, "extracting_features"))
        match_id = asyncio.run(_store_match_data(demo_id, org_id, parsed))

        # Step 4: Compute and store feature ratings
        asyncio.run(_compute_and_store_ratings(match_id, parsed))

        # Step 5: Mark as completed
        asyncio.run(_update_demo_status(demo_id, "completed"))
        logger.info("Demo %s processing completed (match %s)", demo_id, match_id)

        return {"demo_id": demo_id, "match_id": match_id, "status": "completed"}

    except Exception as exc:
        logger.exception("Failed to process demo %s", demo_id)
        try:
            asyncio.run(_update_demo_status(demo_id, "failed", str(exc)[:500]))
        except Exception:
            logger.exception("Failed to update demo %s status to failed", demo_id)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1)) from exc
