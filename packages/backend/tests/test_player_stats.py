"""Tests for player stats and economy endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.services.demo_parser import ParsedDemo, PlayerData, RoundData


def _make_parsed_demo() -> ParsedDemo:
    """Create a ParsedDemo with advanced stats for testing."""
    return ParsedDemo(
        map_name="de_mirage",
        tickrate=64,
        duration_seconds=2400.5,
        team1_name=None,
        team2_name=None,
        team1_score=13,
        team2_score=10,
        total_rounds=23,
        overtime_rounds=0,
        rounds=[
            RoundData(
                round_number=i + 1,
                winner_side="T" if i % 2 == 0 else "CT",
                win_reason="elimination",
                team1_score=(i + 1) // 2 + (1 if i % 2 == 0 else 0),
                team2_score=(i + 1) // 2 + (0 if i % 2 == 0 else 1),
                start_tick=i * 4000,
                end_tick=(i + 1) * 4000 - 500,
                duration_seconds=54.7,
                t_equipment_value=25000 if i > 0 else 4000,
                ct_equipment_value=27000 if i > 0 else 4000,
                t_buy_type="pistol" if i == 0 else "full",
                ct_buy_type="pistol" if i == 0 else "full",
            )
            for i in range(23)
        ],
        players=[
            PlayerData(
                steam_id="76561198000000001",
                name="s1mple",
                team_side="CT",
                kills=28,
                deaths=15,
                assists=4,
                headshot_kills=14,
                damage=2100,
                adr=91.3,
                flash_assists=2,
                enemies_flashed=5,
                utility_damage=120,
                first_kills=6,
                first_deaths=2,
                multi_kills_3k=3,
                multi_kills_4k=1,
                multi_kills_5k=0,
                clutch_wins=2,
                trade_kills=4,
                trade_deaths=3,
                kast_rounds=19,
                rounds_survived=12,
            ),
            PlayerData(
                steam_id="76561198000000002",
                name="ZywOo",
                team_side="T",
                kills=22,
                deaths=18,
                assists=6,
                headshot_kills=10,
                damage=1800,
                adr=78.3,
                flash_assists=3,
                enemies_flashed=4,
                utility_damage=80,
                first_kills=4,
                first_deaths=3,
                multi_kills_3k=1,
                multi_kills_4k=0,
                multi_kills_5k=0,
                clutch_wins=1,
                trade_kills=2,
                trade_deaths=2,
                kast_rounds=17,
                rounds_survived=8,
            ),
        ],
    )


_register_counter = 0


async def register_and_get_token(client: AsyncClient, email: str | None = None) -> str:
    global _register_counter  # noqa: PLW0603
    _register_counter += 1
    email = email or f"player{_register_counter}@test.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": f"Stats Test Team {_register_counter}",
            "email": email,
            "password": "securepassword123",
            "display_name": "Test User",
        },
    )
    return response.json()["access_token"]


async def _setup_match(client: AsyncClient, token: str) -> tuple[str, str]:
    """Upload a demo and store match data, returning (demo_id, match_id)."""
    parsed = _make_parsed_demo()
    mock_upload = AsyncMock(return_value="abc123def456")
    mock_delay = lambda *args, **kwargs: None  # noqa: E731

    with (
        patch("src.services.demo_service.upload_to_minio", mock_upload),
        patch("src.tasks.demo_processing.process_demo.delay", mock_delay),
    ):
        upload_resp = await client.post(
            "/api/v1/demos",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test_match.dem", b"fake demo content", "application/octet-stream")},
        )
    demo_id = upload_resp.json()["id"]

    from src.tasks.demo_processing import (
        _compute_and_store_ratings,
        _get_demo_org_id,
        _store_match_data,
        _update_demo_status,
    )

    org_id = await _get_demo_org_id(demo_id)
    match_id = await _store_match_data(demo_id, org_id, parsed)
    await _compute_and_store_ratings(match_id, parsed)
    await _update_demo_status(demo_id, "completed")

    return demo_id, match_id


@pytest.mark.asyncio
async def test_player_stats_endpoint(client: AsyncClient):
    """Test GET /api/v1/players/{steam_id}/stats returns aggregated data."""
    token = await register_and_get_token(client)
    await _setup_match(client, token)

    resp = await client.get(
        "/api/v1/players/76561198000000001/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["player_steam_id"] == "76561198000000001"
    assert data["player_name"] == "s1mple"
    assert data["total_matches"] == 1
    assert data["total_kills"] == 28
    assert data["total_deaths"] == 15
    assert data["total_trade_kills"] == 4
    assert data["total_clutch_wins"] == 2
    assert data["total_kast_rounds"] == 19
    assert data["total_rounds_survived"] == 12
    assert data["avg_kd_ratio"] == pytest.approx(1.87, abs=0.01)
    assert data["avg_headshot_pct"] == pytest.approx(50.0, abs=0.1)
    assert data["avg_adr"] == pytest.approx(91.3, abs=0.1)
    assert data["avg_hltv_rating"] > 0
    assert data["maps_played"] == {"de_mirage": 1}


@pytest.mark.asyncio
async def test_player_stats_not_found(client: AsyncClient):
    """Test 404 for unknown steam_id."""
    token = await register_and_get_token(client)

    resp = await client.get(
        "/api/v1/players/nonexistent/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_match_economy_endpoint(client: AsyncClient):
    """Test GET /api/v1/matches/{match_id}/economy returns round economy data."""
    token = await register_and_get_token(client)
    _, match_id = await _setup_match(client, token)

    resp = await client.get(
        f"/api/v1/matches/{match_id}/economy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["map"] == "de_mirage"
    assert data["total_rounds"] == 23
    assert len(data["rounds"]) == 23

    # First round should be pistol
    assert data["rounds"][0]["t_buy_type"] == "pistol"
    assert data["rounds"][0]["ct_buy_type"] == "pistol"

    # Second round should be full buy
    assert data["rounds"][1]["t_buy_type"] == "full"
    assert data["rounds"][1]["t_equipment_value"] == 25000


@pytest.mark.asyncio
async def test_match_economy_not_found(client: AsyncClient):
    """Test 404 for unknown match_id."""
    token = await register_and_get_token(client)
    import uuid

    resp = await client.get(
        f"/api/v1/matches/{uuid.uuid4()}/economy",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_overall_rating_stored(client: AsyncClient):
    """Test that overall_rating is computed and stored after match processing."""
    token = await register_and_get_token(client)
    _, match_id = await _setup_match(client, token)

    resp = await client.get(
        f"/api/v1/demos/matches/{match_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    players = resp.json()["player_stats"]

    for p in players:
        assert p["overall_rating"] is not None
        assert p["overall_rating"] > 0

    # s1mple should have higher rating than ZywOo (more kills, better stats)
    s1mple = next(p for p in players if p["player_steam_id"] == "76561198000000001")
    zywoo = next(p for p in players if p["player_steam_id"] == "76561198000000002")
    assert s1mple["overall_rating"] > zywoo["overall_rating"]


@pytest.mark.asyncio
async def test_advanced_stats_stored(client: AsyncClient):
    """Test that multi-kills, clutches, trades, KAST are stored."""
    token = await register_and_get_token(client)
    _, match_id = await _setup_match(client, token)

    resp = await client.get(
        f"/api/v1/demos/matches/{match_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    players = sorted(resp.json()["player_stats"], key=lambda p: p["kills"], reverse=True)

    # s1mple
    assert players[0]["multi_kills_3k"] == 3
    assert players[0]["multi_kills_4k"] == 1
    assert players[0]["clutch_wins"] == 2
    assert players[0]["trade_kills"] == 4
    assert players[0]["trade_deaths"] == 3
    assert players[0]["kast_rounds"] == 19
    assert players[0]["rounds_survived"] == 12

    # ZywOo
    assert players[1]["multi_kills_3k"] == 1
    assert players[1]["clutch_wins"] == 1
    assert players[1]["trade_kills"] == 2
