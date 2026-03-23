from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.exceptions import http_exception_handler, validation_exception_handler
from src.routers import auth, beta, demos, health, heatmap, ml, players, pro_matches, sse


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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(beta.router, prefix="/api/v1")
app.include_router(demos.router, prefix="/api/v1")
app.include_router(players.router, prefix="/api/v1")
app.include_router(ml.router, prefix="/api/v1")
app.include_router(sse.router, prefix="/api/v1")
app.include_router(heatmap.router, prefix="/api/v1")
app.include_router(pro_matches.router, prefix="/api/v1")
