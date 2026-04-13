from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    ENVIRONMENT: str = "dev"
    APP_VERSION: str = "0.1.0"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "text"

    # Database (PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://cs2user:localdev123@localhost:5432/cs2analytics"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # seconds

    # ClickHouse
    CLICKHOUSE_URL: str = "http://localhost:8123"

    # JWT
    JWT_SECRET: str = "change-me-in-production-use-64-chars-minimum-random-string-here"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # MinIO (S3)
    MINIO_ENDPOINT: str = "http://localhost:9002"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "cs2-demos"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_SOLO: str = "price_solo_placeholder"
    STRIPE_PRICE_TEAM: str = "price_team_placeholder"
    STRIPE_PRICE_PRO: str = "price_pro_placeholder"
    FRONTEND_URL: str = "http://localhost:3000"

    # FACEIT
    FACEIT_API_KEY: str = ""
    FACEIT_HUB_IDS: str = ""  # comma-separated

    # Rate limiting
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_UPLOAD: str = "5/minute"
    RATE_LIMIT_DEFAULT: str = "60/minute"

    # File upload
    MAX_DEMO_SIZE_MB: int = 200

    # SSE
    SSE_TIMEOUT_ITERATIONS: int = 120

    # Sentry
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.0


settings = Settings()
