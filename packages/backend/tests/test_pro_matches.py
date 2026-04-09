"""Tests for pro matches endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_pro_matches_empty(client: AsyncClient):
    """List pro matches returns empty list when no data."""
    resp = await client.get("/api/v1/pro/matches")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_pro_matches_pagination(client: AsyncClient):
    """Pagination parameters are accepted."""
    resp = await client.get("/api/v1/pro/matches?page=2&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["page_size"] == 5


@pytest.mark.asyncio
async def test_list_pro_matches_filters(client: AsyncClient):
    """All filter parameters are accepted without error."""
    resp = await client.get(
        "/api/v1/pro/matches?team=Navi&map=de_mirage&event=Major&source=hltv"
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_pro_match_not_found(client: AsyncClient):
    """Get non-existent pro match returns 404."""
    resp = await client.get("/api/v1/pro/matches/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_teams(client: AsyncClient):
    """Team search returns empty list when no data."""
    resp = await client.get("/api/v1/pro/teams?q=Navi")
    assert resp.status_code == 200
    assert resp.json()["teams"] == []


@pytest.mark.asyncio
async def test_search_teams_min_length(client: AsyncClient):
    """Team search requires minimum 2 characters."""
    resp = await client.get("/api/v1/pro/teams?q=N")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_events_empty(client: AsyncClient):
    """Events list returns empty when no data."""
    resp = await client.get("/api/v1/pro/events")
    assert resp.status_code == 200
    assert resp.json()["events"] == []
