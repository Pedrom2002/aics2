"""Tests for heatmap endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_heatmap_invalid_match(client: AsyncClient):
    """Heatmap for non-existent match returns 404."""
    resp = await client.get(
        "/api/v1/matches/00000000-0000-0000-0000-000000000000/heatmap?type=kills"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_heatmap_invalid_type(client: AsyncClient):
    """Heatmap with invalid type returns 422."""
    resp = await client.get(
        "/api/v1/matches/00000000-0000-0000-0000-000000000000/heatmap?type=invalid"
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_heatmap_valid_types(client: AsyncClient):
    """All valid heatmap types are accepted (kills, deaths, positions)."""
    for htype in ("kills", "deaths", "positions"):
        resp = await client.get(
            f"/api/v1/matches/00000000-0000-0000-0000-000000000000/heatmap?type={htype}"
        )
        # 404 (match not found) is expected, not 422 (type invalid)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_replay_invalid_match(client: AsyncClient):
    """Replay for non-existent match returns 404."""
    resp = await client.get(
        "/api/v1/matches/00000000-0000-0000-0000-000000000000/replay"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_replay_with_round_filter(client: AsyncClient):
    """Replay with round filter returns 404 for missing match."""
    resp = await client.get(
        "/api/v1/matches/00000000-0000-0000-0000-000000000000/replay?round=1"
    )
    assert resp.status_code == 404
