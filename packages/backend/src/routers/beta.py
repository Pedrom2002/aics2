from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.beta_signup import BetaSignup
from src.schemas.auth import BetaSignupRequest, BetaSignupResponse

router = APIRouter(prefix="/beta", tags=["beta"])


@router.post("/signup", response_model=BetaSignupResponse, status_code=201)
async def beta_signup(body: BetaSignupRequest, db: AsyncSession = Depends(get_db)):
    # Check for existing signup
    existing = await db.execute(select(BetaSignup).where(BetaSignup.email == body.email))
    if existing.scalar_one_or_none():
        return BetaSignupResponse(message="You're already on the list!")

    signup = BetaSignup(email=body.email, source=body.source)
    db.add(signup)
    return BetaSignupResponse()
