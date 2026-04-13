import logging
import uuid
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=False,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            AsyncioIntegration(),
        ],
    )
from src.exceptions import http_exception_handler, validation_exception_handler
from src.middleware.metrics import metrics_response, prometheus_middleware
from src.routers import (
    archetypes,
    auth,
    beta,
    billing,
    demos,
    health,
    heatmap,
    live,
    ml,
    players,
    pro_matches,
    public_api,
    scout,
    sse,
    steam_auth,
    tactics,
    teams,
    win_prob,
)

# Structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
    if settings.LOG_FORMAT == "text"
    else '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    from src.database import _get_engine

    await _get_engine().dispose()


app = FastAPI(
    title="AI CS2 Analytics",
    description="AI-powered CS2 esports analytics platform",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "dev" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "dev" else None,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Security headers
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
}


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    for header, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response


# Prometheus metrics middleware
app.middleware("http")(prometheus_middleware)


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Prometheus metrics exposition endpoint."""
    return metrics_response()


# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(steam_auth.router, prefix="/api/v1")
app.include_router(beta.router, prefix="/api/v1")
app.include_router(demos.router, prefix="/api/v1")
app.include_router(players.router, prefix="/api/v1")
app.include_router(ml.router, prefix="/api/v1")
app.include_router(sse.router, prefix="/api/v1")
app.include_router(heatmap.router, prefix="/api/v1")
app.include_router(live.router, prefix="/api/v1")
app.include_router(public_api.router, prefix="/api/v1")
app.include_router(public_api.admin_router, prefix="/api/v1")
app.include_router(pro_matches.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(win_prob.router, prefix="/api/v1")
app.include_router(archetypes.router, prefix="/api/v1")
app.include_router(tactics.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(scout.router, prefix="/api/v1")
