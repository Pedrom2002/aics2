# Contributing

Thanks for considering a contribution. This is a small, fast-moving codebase
— prefer small focused PRs.

## 1. Repository layout

```
cs2-analytics/
  packages/
    backend/            FastAPI + Celery (Python 3.12)
    frontend/           Next.js 16 (TypeScript, App Router)
    demo-parser/        awpy 2.x wrapper
    feature-engine/     Polars / DuckDB transforms
    ml-models/          training + inference + BentoML
    pro-demo-ingester/  HLTV demo downloader
  infra/
    docker-compose.yml  local data services
    docker/             Dockerfiles for backend + frontend
    k8s/                production manifests
    helm/               Helm chart
    terraform/          IaC scaffolding
    monitoring/         Prometheus, Grafana, Alertmanager
  scripts/
    backup/             pg_dump / restore / models tar
  docs/                 design + ops documentation
  .github/workflows/    CI
```

## 2. Local dev setup

```bash
# 1. Tooling
#   Node 20 + pnpm 10.32.1, Python 3.12, uv (or pip), Docker, kubectl, helm
corepack enable
corepack prepare pnpm@10.32.1 --activate

# 2. Install JS deps (workspaces)
pnpm install

# 3. Install Python deps
cd packages/backend && uv sync && cd ../..
cd packages/ml-models && uv sync && cd ../..

# 4. Bring up data services
docker compose -f infra/docker-compose.yml up -d

# 5. Pre-commit hooks
pip install pre-commit
pre-commit install

# 6. Run migrations + start backend
cd packages/backend
alembic upgrade head
uvicorn src.main:app --reload --port 8000

# 7. Start frontend
cd ../frontend
pnpm dev
```

## 3. Conventions

### Code style

- **Python**: ruff + mypy (config in `pyproject.toml`). 100-char lines.
- **TypeScript**: prettier + ESLint. The repo's `.prettierrc` and Tailwind
  plugin are authoritative.
- Run `pnpm format` before committing JS/TS changes.

### Commit messages

Looking at recent history (`git log --oneline`), the project uses short
sentence-style messages, often colon-prefixed by area. Examples:

```
ML pipeline complete: Player Rating (R² 0.998) + UMAP clustering + parse cache
Win Prob V2 inference integration + 4 new ML pipelines
Sprint 3: Feature engine, advanced parser stats, economy chart, player stats
Fix tests broken by auth rate limiting
Fix frontend build: Next 16 + force-dynamic + win-prob type fix
```

Patterns:

- Imperative present tense (`Fix`, `Add`, `Wire`)
- Optional area prefix with colon (`ML pipeline:`, `Phase 4:`, `Fix frontend build:`)
- One-line subject; body only when context is non-obvious
- Conventional Commits is **not** enforced — keep it descriptive

### Branches

- `master` is the default protected branch
- Feature branches: `feature/<short-desc>` or `fix/<short-desc>`
- Long-running experimental work: `experiment/<topic>`

## 4. Testing

### Backend

```bash
cd packages/backend
uv run pytest                       # full suite
uv run pytest -k auth -v            # filter
uv run pytest --cov=src --cov-report=term-missing
```

Tests use `aiosqlite` for the API layer; integration tests against real
Postgres run in CI.

### Frontend

```bash
cd packages/frontend
pnpm test                           # unit / component
pnpm test:e2e                       # Playwright (requires backend running)
pnpm typecheck
pnpm lint
```

### Repo-wide

```bash
pnpm -w build                       # turbo orchestrates per-package builds
pnpm -w test
```

## 5. Migrations

Schema changes go through Alembic in `packages/backend`:

```bash
cd packages/backend
alembic revision --autogenerate -m "add players archetype column"
# Inspect the generated file. autogenerate is a starting point, not gospel.
alembic upgrade head
```

Always verify the generated migration:

- Index creation should be `CREATE INDEX CONCURRENTLY` for hot tables
- Column additions on big tables: `ALTER TABLE ... ADD COLUMN ... NULL` then
  backfill, then set NOT NULL

## 6. Pull requests

1. Open PR against `master`.
2. CI must be green (`.github/workflows/ci.yml` runs lint + tests + build).
3. Description should cover: **what changed**, **why**, **how to test**.
4. Link relevant issues / docs.
5. Squash-merge unless commits are independently meaningful.
6. Reviewers: at least one approval from a maintainer.

### What to include in a PR description

```
## Summary
- bullet points of what changed

## Why
- one-paragraph rationale

## Test plan
- [ ] command 1
- [ ] command 2
```

## 7. Reporting issues

Use GitHub Issues. Include:

- Environment (local / staging / prod, OS, versions)
- Reproduction steps
- Expected vs actual behaviour
- Relevant logs (sanitised)

## 8. Security

Do **not** open public issues for security vulnerabilities. Email the
maintainers privately and allow time for a fix before disclosure.
