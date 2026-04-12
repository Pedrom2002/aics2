# CS2 Analytics Platform

AI-powered analytics platform for Counter-Strike 2 demos. Upload demos, get win probability predictions, player ratings, error detection, tactical breakdowns, and scouting reports — all driven by ML models trained on professional match data.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui, Recharts, D3.js, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic 2, Celery, Redis, Stripe |
| ML | PyTorch, LightGBM, CatBoost, scikit-learn, SHAP, Mamba SSM |
| Database | PostgreSQL 16, Redis 7 |
| Infra | Docker Compose, Kubernetes, Helm, Terraform, Prometheus, Grafana |

## Features

- **Match Analysis** — Upload `.dem` files, parse rounds/events, replay on interactive canvas
- **Win Probability** — Round-by-round predictions (LightGBM v2, AUC 0.904, 21 features)
- **Player Rating** — CatBoost regression (R² 0.998) with SHAP explainability
- **Player Archetypes** — UMAP + HDBSCAN clustering into 8 playstyle archetypes
- **Error Detection** — Utility/timing mistakes via Mamba SSM classifier (81% accuracy)
- **Tactical Insights** — Economy charts, heatmaps, radar comparisons, strategy classification
- **Scout Reports** — Generate scouting profiles with strengths, weaknesses, training plans
- **Pro Match Pipeline** — Auto-ingest HLTV pro demos via scraper + Celery Beat
- **Billing** — Stripe integration (Solo/Team/Pro tiers) with webhook handling
- **Real-Time** — SSE for live parsing progress and match status updates

## Project Structure

```
cs2-analytics/
├── packages/
│   ├── frontend/           # Next.js 16 App Router
│   ├── backend/            # FastAPI + Celery workers
│   ├── ml-models/          # Training scripts + model registry
│   ├── feature-engine/     # Round/player/team feature extractors
│   ├── demo-parser/        # CS2 .dem parsing (Awpy)
│   └── pro-demo-ingester/  # HLTV scraper + demo downloader
├── infra/
│   ├── docker-compose.yml  # Postgres, Redis (local dev)
│   ├── k8s/                # Kubernetes manifests
│   ├── helm/               # Helm chart
│   ├── terraform/          # AWS IaC scaffolding
│   └── monitoring/         # Prometheus, Grafana, Alertmanager
├── scripts/backup/         # DB + model backup/restore
├── docs/                   # Architecture, deployment, contributing
├── .github/workflows/      # CI (lint, test, build, e2e)
└── turbo.json              # Monorepo orchestration
```

## Prerequisites

- Node.js 20+
- Python 3.12+
- pnpm 10+
- uv (Python package manager)
- Docker + Docker Compose

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/Pedrom2002/aics2.git
cd aics2
cp .env.example .env        # edit with your secrets

# 2. Start infrastructure
docker compose -f infra/docker-compose.yml up -d

# 3. Backend
cd packages/backend
uv sync --extra dev --extra test
alembic upgrade head
uvicorn src.main:app --reload --port 8000

# 4. Frontend (new terminal)
cd packages/frontend
pnpm install
pnpm dev                    # http://localhost:3000
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis connection (`redis://localhost:6379/0`) |
| `JWT_SECRET` | Signing secret for auth tokens (min 64 chars) |
| `STRIPE_SECRET_KEY` | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend (`http://localhost:8000/api/v1`) |
| `CORS_ORIGINS` | Allowed origins (comma-separated) |

See `.env.example` for the full list.

## API Endpoints

| Router | Prefix | Description |
|--------|--------|-------------|
| health | `/api/v1/health` | Liveness + readiness (DB/Redis probes) |
| auth | `/api/v1/auth` | Register, login, refresh, logout |
| demos | `/api/v1/demos` | Upload, list, parse demos |
| players | `/api/v1/players` | Stats, archetypes, comparisons |
| tactics | `/api/v1/tactics` | Team strategy analysis per match |
| scout | `/api/v1/scout` | CRUD for scouting reports |
| win-prob | `/api/v1/win-prob` | Round win probability predictions |
| ml | `/api/v1/ml` | Model registry, SHAP explainability |
| billing | `/api/v1/billing` | Stripe checkout, webhooks, plans |
| pro | `/api/v1/pro` | Pro match ingestion pipeline |
| heatmap | `/api/v1/heatmap` | Positional heat data |
| sse | `/api/v1/demos/.../sse` | Server-Sent Events (live updates) |

Interactive docs at `http://localhost:8000/docs` (dev only).

## ML Models

| Model | Task | Framework | Key Metric |
|-------|------|-----------|------------|
| Win Probability v2 | Classification | LightGBM | AUC 0.904 |
| Player Rating v1 | Regression | CatBoost | R² 0.998 |
| Player Archetypes v1 | Clustering | UMAP + HDBSCAN | 8 clusters |
| Positioning v2 | Regression | Mamba SSM | MAE 0.067 |
| Timing v1 | Classification | Mamba SSM | Acc 0.81 |
| Strategy GNN v1 | Classification | GraphSAGE | Heuristic fallback |

Model registry at `packages/ml-models/models_registry.json`. SHAP explainability available via `POST /api/v1/ml/explain`.

## Scripts

```bash
# Monorepo (root)
pnpm dev                    # Start all packages
pnpm build                  # Build all
pnpm lint                   # Lint all
pnpm test                   # Test all

# Backend
uv run ruff check src/      # Lint
uv run pytest tests/ -v     # Unit + integration tests
alembic upgrade head        # Run migrations
alembic revision --autogenerate -m "description"

# Frontend
pnpm type-check             # TypeScript
pnpm test                   # Vitest
pnpm exec playwright test   # E2E (requires running backend)

# ML
cd packages/ml-models
python -m src.training.train_win_prob
python -m src.training.train_player_rating

# Backup
scripts/backup/backup-postgres.sh
scripts/backup/backup-models.sh
```

## Deployment

**Local**: Docker Compose (see Quick Start)

**Production** (Kubernetes):
```bash
helm upgrade --install cs2 ./infra/helm/cs2-analytics \
  --set backend.image=your-registry/cs2-backend:latest \
  --set frontend.image=your-registry/cs2-frontend:latest \
  -f values-production.yaml
```

See [docs/deployment.md](docs/deployment.md) for full staging/production guide, [docs/architecture.md](docs/architecture.md) for system design, and [docs/contributing.md](docs/contributing.md) for development workflow.

## CI/CD

GitHub Actions runs on every push and PR:
- **Backend**: ruff lint + format, pytest with Postgres + Redis services
- **Frontend**: ESLint, TypeScript check, Next.js build
- **ML Models**: pytest model tests
- **E2E**: Playwright golden-path tests (on PR)

## Roadmap

See [ROADMAP.md](ROADMAP.md) for current status and planned features.
