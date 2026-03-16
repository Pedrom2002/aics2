import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Test Team",
            "email": "admin@test.com",
            "password": "securepassword123",
            "display_name": "Admin User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "admin@test.com"
    assert data["user"]["role"] == "admin"
    assert data["organization"]["name"] == "Test Team"
    assert data["organization"]["slug"] == "test-team"
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    # First registration
    await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Team A",
            "email": "dup@test.com",
            "password": "securepassword123",
            "display_name": "User A",
        },
    )
    # Duplicate
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Team B",
            "email": "dup@test.com",
            "password": "securepassword456",
            "display_name": "User B",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Login Team",
            "email": "login@test.com",
            "password": "securepassword123",
            "display_name": "Login User",
        },
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@test.com", "password": "securepassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "login@test.com"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    # Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Wrong PW Team",
            "email": "wrongpw@test.com",
            "password": "securepassword123",
            "display_name": "User",
        },
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@test.com", "password": "wrongpassword123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    # Register
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Refresh Team",
            "email": "refresh@test.com",
            "password": "securepassword123",
            "display_name": "User",
        },
    )
    refresh_token = reg.json()["refresh_token"]

    # Refresh
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token  # Token rotated


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    # Register
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "org_name": "Logout Team",
            "email": "logout@test.com",
            "password": "securepassword123",
            "display_name": "User",
        },
    )
    refresh_token = reg.json()["refresh_token"]

    # Logout
    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 204

    # Try to refresh with old token — should fail
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_beta_signup(client: AsyncClient):
    response = await client.post(
        "/api/v1/beta/signup",
        json={"email": "beta@test.com"},
    )
    assert response.status_code == 201
    assert "Thanks" in response.json()["message"]


@pytest.mark.asyncio
async def test_beta_signup_duplicate(client: AsyncClient):
    await client.post("/api/v1/beta/signup", json={"email": "betadup@test.com"})
    response = await client.post("/api/v1/beta/signup", json={"email": "betadup@test.com"})
    assert response.status_code == 201
    assert "already" in response.json()["message"]
