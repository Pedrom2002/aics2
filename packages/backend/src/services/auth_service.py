import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.organization import Organization
from src.models.refresh_token import RefreshToken
from src.models.user import User
from src.schemas.auth import AuthResponse, TokenResponse
from src.schemas.organization import OrgResponse
from src.schemas.user import UserResponse

ph = PasswordHasher()


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    return slug.replace(" ", "-")


def _hash_password(password: str) -> str:
    return ph.hash(password)


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _create_access_token(user: User) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "org_id": str(user.org_id),
        "role": user.role,
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _create_refresh_token_value() -> str:
    return secrets.token_urlsafe(64)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def register(
    db: AsyncSession,
    org_name: str,
    email: str,
    password: str,
    display_name: str,
) -> AuthResponse:
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail="Email already registered")

    # Create organization
    slug = _slugify(org_name)
    # Ensure unique slug
    slug_check = await db.execute(select(Organization).where(Organization.slug == slug))
    if slug_check.scalar_one_or_none():
        slug = f"{slug}-{secrets.token_hex(3)}"

    org = Organization(name=org_name, slug=slug)
    db.add(org)
    await db.flush()

    # Create admin user
    user = User(
        org_id=org.id,
        email=email,
        password_hash=_hash_password(password),
        display_name=display_name,
        role="admin",
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    await db.flush()

    # Generate tokens
    access_token = _create_access_token(user)
    refresh_token_value = _create_refresh_token_value()

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(refresh_token_value),
        expires_at=datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        organization=OrgResponse.model_validate(org),
        access_token=access_token,
        refresh_token=refresh_token_value,
    )


async def login(db: AsyncSession, email: str, password: str) -> AuthResponse:
    from fastapi import HTTPException

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not _verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Update last login
    user.last_login_at = datetime.now(UTC)

    # Load organization
    org_result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = org_result.scalar_one()

    # Generate tokens
    access_token = _create_access_token(user)
    refresh_token_value = _create_refresh_token_value()

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(refresh_token_value),
        expires_at=datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        organization=OrgResponse.model_validate(org),
        access_token=access_token,
        refresh_token=refresh_token_value,
    )


async def refresh(db: AsyncSession, refresh_token_value: str) -> TokenResponse:
    from fastapi import HTTPException
    from sqlalchemy import delete as sa_delete

    token_hash = _hash_token(refresh_token_value)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    now = datetime.now(UTC)
    expires = token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=UTC)
    if expires < now:
        await db.delete(token)
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Atomic rotation: DELETE ... WHERE token_hash=? returns rowcount.
    # If two requests race, only one sees rowcount==1 — the other 401s.
    deletion = await db.execute(
        sa_delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    await db.flush()
    if deletion.rowcount == 0:
        raise HTTPException(status_code=401, detail="Refresh token already used")

    # Load user
    user_result = await db.execute(select(User).where(User.id == token.user_id))
    user = user_result.scalar_one()

    new_access_token = _create_access_token(user)
    new_refresh_value = _create_refresh_token_value()

    new_refresh = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(new_refresh_value),
        expires_at=datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_refresh)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_value,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def logout(db: AsyncSession, refresh_token_value: str) -> None:
    token_hash = _hash_token(refresh_token_value)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token = result.scalar_one_or_none()
    if token:
        await db.delete(token)
