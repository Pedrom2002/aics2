# CS2 Analytics Platform

Full-stack analytics platform for Counter-Strike 2. Upload match demos, get win probability predictions, player ratings, error detection, and tactical analysis powered by trained ML models.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui, Recharts, D3.js |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic 2, Celery, Redis |
| ML | PyTorch (Mamba SSM), LightGBM, CatBoost, UMAP, SHAP |
| Database | PostgreSQL 16, Redis 7 |
| Infra | Docker Compose (dev), Kubernetes manifests + Helm (scaffolded) |

## What Works

**Core pipeline (functional):**
- JWT auth (register/login/refresh/logout) with org isolation
- Demo upload to MinIO, parsing via Awpy, feature extraction
- Match detail with round stats, economy breakdown, win probability impacts
- Player stats with aggregated KD, ADR, rating, headshot %
- Scout reports (CRUD) with weakness/strength profiles
- Stripe billing (checkout, portal, webhook signature verification)
- Pro match data from HLTV (manual CLI ingestion, not automated)

**ML models (5/6 trained):**

| Model | Framework | Metric | Status |
|-------|-----------|--------|--------|
| Win Probability v2 | LightGBM | AUC 0.904 | Trained, real inference |
| Player Rating v1 | CatBoost | R² 0.998 | Trained, real inference |
| Player Archetypes v1 | UMAP + HDBSCAN | 8 clusters | Trained |
| Positioning v2 | Mamba SSM | MAE 0.067 | Trained |
| Timing v1 | Mamba SSM | Acc 0.81 | Trained |
| Strategy GNN v1 | GraphSAGE | Coarse (6T/5CT) | Weak-supervision pipeline in `ml-models/src/training/train_strategy_gnn.py` (heuristic fallback still active until checkpoints are committed) |

SHAP explainability for win_prob and player_rating via `POST /api/v1/ml/explain`.

**Shipped in this iteration:**
- Sentry integration (backend + frontend) + CSP / HSTS headers
- Dependency scanning (pip-audit + pnpm audit) in CI, Dependabot config
- Auth edge-case tests (expired/forged JWT, refresh reuse, concurrent rotation)
- Stripe webhook idempotency via Redis dedup
- Strategy GNN training pipeline (weak supervision, coarse taxonomy)
- ML feature-drift middleware + daily Celery job + Prometheus alert rules
- Real radar-asset loading in the replay canvas
- Coaching insights page (`/matches/[id]/coaching`)
- Terraform modules filled out (VPC, RDS, EKS + cert-manager/external-secrets/kube-prometheus-stack/loki)
- K8s NetworkPolicy, RBAC, External-Secrets, cert-manager ClusterIssuers
- Steam OpenID sign-in (`/auth/steam/login` + callback, "Sign in with Steam" button)
- Real-time SSE win-prob stream (`/live/{match_id}/win-prob/sse`)
- Public API with API keys (`/public/*`, `/api-keys`) + migration `008_add_api_keys`
- Team overview endpoint + dashboard page
- k6 baseline load-test script + staging smoke-test + secret rotation script

**Still partial:**
- Replay: real Valve radar PNGs need to be dropped into `packages/frontend/public/radars/`
- GNN checkpoints are produced by the training script but not committed — run `python -m src.training.train_strategy_gnn` to populate
- Terraform has not yet been applied to a real AWS account

## Project Structure

```
packages/
  frontend/           Next.js 16 App Router, shadcn/ui, TanStack Query
  backend/            FastAPI REST API, Alembic migrations (7), Celery
  ml-models/          Training scripts, model registry, SHAP API
  feature-engine/     Round/player/team feature extractors
  demo-parser/        CS2 .dem parsing via Awpy
  pro-demo-ingester/  HLTV scraper (Playwright) + demo downloader
infra/
  docker-compose.yml  PostgreSQL 16, Redis 7, MinIO
  k8s/                Kubernetes manifests (scaffolded)
  helm/               Helm chart (scaffolded)
  monitoring/         Prometheus, Grafana dashboards, Alertmanager configs
scripts/backup/       Postgres + model backup/restore scripts
docs/                 Architecture, deployment, contributing guides
.github/workflows/    CI: lint, test, build, e2e
```

## Quick Start

```bash
git clone https://github.com/Pedrom2002/aics2.git
cd aics2
cp .env.example .env

# Infrastructure
docker compose -f infra/docker-compose.yml up -d

# Backend
cd packages/backend
uv sync --extra dev --extra test
alembic upgrade head
uvicorn src.main:app --reload --port 8000

# Frontend
cd packages/frontend
pnpm install
pnpm dev    # http://localhost:3000
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost:5432/cs2analytics` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `JWT_SECRET` | Auth signing secret (min 64 chars) |
| `STRIPE_SECRET_KEY` | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend |
| `CORS_ORIGINS` | Allowed origins (comma-separated) |

Full list in `.env.example`.

## API

| Router | Prefix | Status |
|--------|--------|--------|
| auth | `/api/v1/auth` | Register, login, refresh, logout |
| demos | `/api/v1/demos` | Upload, list, parse, delete |
| players | `/api/v1/players` | Stats, archetypes |
| win-prob | `/api/v1/win-prob` | Round win probability + impacts |
| tactics | `/api/v1/tactics` | Strategy analysis (heuristic) |
| scout | `/api/v1/scout` | CRUD scouting reports |
| ml | `/api/v1/ml` | Model registry, SHAP explain |
| billing | `/api/v1/billing` | Stripe checkout, webhooks |
| pro | `/api/v1/pro` | Pro match metadata |
| health | `/api/v1/health` | DB + Redis probes |
| heatmap | `/api/v1/heatmap` | Stub |
| sse | `/api/v1/demos/.../sse` | Stub |

Swagger docs at `http://localhost:8000/docs` (dev only).

## Scripts

```bash
# Root (Turborepo)
pnpm dev / build / lint / test

# Backend
uv run ruff check src/ tests/
uv run pytest tests/ -v
alembic upgrade head

# Frontend
pnpm type-check
pnpm exec playwright test   # needs running backend

# ML training
cd packages/ml-models
python -m src.training.train_win_prob
python -m src.training.train_player_rating

# Pro demo ingestion (manual)
cd packages/pro-demo-ingester
python src/download_demos.py
```

## CI

GitHub Actions on push/PR:
- Backend: ruff lint + format, pytest (Postgres + Redis services)
- Frontend: ESLint, TypeScript, Next.js build
- ML: pytest model tests
- E2E: Playwright (on PR)

## Roadmap

See [ROADMAP.md](ROADMAP.md).
