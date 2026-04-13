"""Read-only public API, authenticated via API keys.

Key format: ``csk_<prefix>_<secret>`` where prefix is stored in plaintext
for log lookups and the SHA-256 of the full key is stored in ``api_keys.key_hash``.
Rate limiting is keyed off the prefix.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from slowapi import Limiter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.middleware.auth import get_current_user
from src.models.api_key import ApiKey
from src.schemas.auth import TokenPayload

router = APIRouter(prefix="/public", tags=["public"])
admin_router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _extract_key_parts(header: str) -> tuple[str, str] | None:
    if not header or not header.startswith("csk_"):
        return None
    try:
        _, prefix, secret = header.split("_", 2)
    except ValueError:
        return None
    return prefix, secret


async def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required (X-API-Key header)")

    parts = _extract_key_parts(x_api_key)
    if not parts:
        raise HTTPException(status_code=401, detail="Malformed API key")

    digest = hashlib.sha256(x_api_key.encode()).hexdigest()
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == digest, ApiKey.revoked_at.is_(None))
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    key.last_used_at = datetime.now(UTC)
    await db.commit()

    request.state.api_key = key
    return key


def _api_key_rate_key(request: Request) -> str:
    key: ApiKey | None = getattr(request.state, "api_key", None)
    if key:
        return f"apikey:{key.id}"
    return request.client.host if request.client else "anonymous"


limiter = Limiter(key_func=_api_key_rate_key)


@admin_router.post("", status_code=201)
async def create_api_key(
    name: str = Query(..., min_length=1, max_length=100),
    scopes: list[str] = Query(default_factory=lambda: ["read:matches", "read:players"]),
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mint a new API key for the caller's org. The plaintext is returned ONCE."""
    prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    plaintext = f"csk_{prefix}_{secret}"
    digest = hashlib.sha256(plaintext.encode()).hexdigest()

    import uuid

    key = ApiKey(
        org_id=uuid.UUID(current_user.org_id),
        name=name,
        key_prefix=prefix,
        key_hash=digest,
        scopes=scopes,
    )
    db.add(key)
    await db.commit()
    return {"id": str(key.id), "name": name, "key": plaintext, "prefix": prefix}


@admin_router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    import uuid

    result = await db.execute(
        select(ApiKey).where(ApiKey.id == uuid.UUID(key_id),
                             ApiKey.org_id == uuid.UUID(current_user.org_id))
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    key.revoked_at = datetime.now(UTC)
    await db.commit()


# -----------------------------------------------------------------
# Read endpoints
# -----------------------------------------------------------------


@router.get("/matches")
@limiter.limit("60/minute")
async def public_matches(
    request: Request,
    limit: int = 25,
    api_key: ApiKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List recent pro matches (cached server-side)."""
    if "read:matches" not in api_key.scopes:
        raise HTTPException(status_code=403, detail="Missing scope: read:matches")

    from src.models.pro_match import ProMatch

    result = await db.execute(
        select(ProMatch).order_by(ProMatch.match_date.desc()).limit(min(limit, 100))
    )
    rows = result.scalars().all()
    return {
        "matches": [
            {
                "id": str(m.id),
                "team1": m.team1_name,
                "team2": m.team2_name,
                "map": m.map,
                "event": m.event_name,
                "match_date": m.match_date.isoformat() if m.match_date else None,
            }
            for m in rows
        ]
    }


@router.get("/players/{steam_id}")
@limiter.limit("60/minute")
async def public_player(
    request: Request,
    steam_id: str,
    api_key: ApiKey = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if "read:players" not in api_key.scopes:
        raise HTTPException(status_code=403, detail="Missing scope: read:players")

    from src.services.player_service import get_player_summary

    summary = await get_player_summary(db, steam_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return summary
