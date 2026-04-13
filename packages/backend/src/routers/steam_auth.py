"""Steam OpenID 2.0 sign-in.

Implements the minimal flow: redirect the user to Steam, validate the
callback by sending the params back to Steam with ``openid.mode=check_authentication``,
and link or create a user bound to the resolved ``steamid64``.
"""

from __future__ import annotations

import logging
import re
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models.organization import Organization
from src.models.user import User
from src.services.auth_service import _create_access_token, _create_refresh_token_value, _hash_token
from src.models.refresh_token import RefreshToken
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/steam", tags=["auth"])

_STEAM_OPENID = "https://steamcommunity.com/openid/login"
_STEAM_ID_RE = re.compile(r"^https?://steamcommunity\.com/openid/id/(\d+)$")


def _return_to(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}/api/v1/auth/steam/callback"


@router.get("/login")
async def steam_login(request: Request) -> RedirectResponse:
    """Redirect the browser to Steam's OpenID endpoint."""
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": _return_to(request),
        "openid.realm": f"{request.url.scheme}://{request.url.netloc}/",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return RedirectResponse(f"{_STEAM_OPENID}?{urlencode(params)}")


async def _verify_openid(params: dict[str, str]) -> str | None:
    """Return the steamid64 on success, or None on verification failure."""
    verification = {**params, "openid.mode": "check_authentication"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(_STEAM_OPENID, data=verification)
    if resp.status_code != 200 or "is_valid:true" not in resp.text:
        return None

    claimed = params.get("openid.claimed_id", "")
    match = _STEAM_ID_RE.match(claimed)
    return match.group(1) if match else None


@router.get("/callback")
async def steam_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate the OpenID response, link to an existing user or create one."""
    params = dict(request.query_params)
    steam_id = await _verify_openid(params)
    if not steam_id:
        raise HTTPException(status_code=401, detail="Steam OpenID verification failed")

    # Link to an existing user
    result = await db.execute(select(User).where(User.steam_id == steam_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Create a standalone "personal" org + user bound to the steam id
        slug = f"steam-{steam_id[-8:]}-{secrets.token_hex(3)}"
        org = Organization(name=f"Steam {steam_id}", slug=slug)
        db.add(org)
        await db.flush()

        user = User(
            org_id=org.id,
            email=f"{steam_id}@steam.local",
            password_hash="!steam-only",  # password auth disabled
            display_name=f"SteamUser{steam_id[-4:]}",
            role="admin",
            steam_id=steam_id,
            last_login_at=datetime.now(UTC),
        )
        db.add(user)
        await db.flush()
    else:
        user.last_login_at = datetime.now(UTC)

    # Issue tokens
    access_token = _create_access_token(user)
    refresh_value = _create_refresh_token_value()
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(refresh_value),
        expires_at=datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_token)
    await db.commit()

    # Redirect back to the frontend with the tokens as a short-lived fragment.
    target = (
        f"{settings.FRONTEND_URL}/auth/steam/done"
        f"#access_token={access_token}&refresh_token={refresh_value}"
    )
    return RedirectResponse(target)
