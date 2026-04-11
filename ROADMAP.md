# Roadmap

A short, realistic view of where cs2-analytics is and where it's going. Keep
this file honest — when something ships, move it to **Done**; when something
no longer makes sense, delete it.

Last updated: 2026-04-11

## Done

Shipped, in `master`, exercised by tests or manual verification.

### Foundations
- Monorepo (pnpm + turbo) with backend, frontend, ml-models, demo-parser,
  feature-engine, pro-demo-ingester packages
- FastAPI backend with auth (JWT), Stripe billing, slowapi rate limiting,
  Alembic migrations, asyncpg
- Next.js 16 frontend (App Router, RSC) with auth, dashboard shell, marketing
  pages, dark mode, onboarding, Stripe checkout
- Local dev stack via docker compose (Postgres, ClickHouse, Redis, MinIO)
- CI workflow (`.github/workflows/ci.yml`) running lint, typecheck, tests, build

### Demo pipeline
- awpy 2.x demo parser
- Feature engine (Polars-based per-round / per-player aggregations)
- HLTV scraper + auto demo downloader (`pro-demo-ingester`)
- Celery + Celery Beat for scheduled ingestion and parsing
- Parse cache (avoids reparsing the same demo)

### ML pipelines
- Smart labelling pipeline (win prob + 10 contextual variables)
- Win Probability v2 — 21 features, AUC 0.904
- Player Rating model — R² 0.998
- Mamba sequence regression
- Player archetypes via UMAP + HDBSCAN clustering
- ML error detection with heuristic baseline
- BentoML serving template
- One-command training entry point + synthetic data fallback
- Inference wired into backend (`/api/win-prob`, `/api/players/.../archetype`,
  rating prediction service)

### UX shipped
- Match detail, error analysis page, radar charts, economy chart, heatmap
- Advanced demo replayer (Phase 5)
- Player profile, comparison view, scout
- Responsive layouts + skeleton loaders
- E2E test scaffolding (Playwright)
- Settings page

## In progress

Code present but incomplete, behind feature flags, or carrying TODOs.

- **Production infrastructure** (this iteration): Kubernetes manifests,
  Helm chart, Terraform scaffolding, monitoring stack, backup scripts,
  deployment + architecture + contributing docs. Not yet exercised on a
  real cluster.
- **Win Prob v2 rollout** — model trained and integrated; backfill of
  predictions for historical matches still ongoing.
- **Player archetypes API** — service exists, but UI presentation and
  archetype taxonomy stability over time still need validation.
- **Test coverage gaps** — recent commit history shows tests being
  repeatedly broken/fixed by rate limiting and Next 16 upgrades; coverage
  on auth and billing edge cases is thin.
- **Security hardening pass** — `d8bec98` did one round; secret rotation,
  CSP, dependency scanning still open.

## Next (next 1–2 quarters)

Realistic, scoped, with clear value. Not a wishlist.

### Q2 2026
1. **Production deploy** — first staging environment on a real k8s cluster
   using the Helm chart in this iteration. Validate probes, HPA, ingress,
   cert-manager, backups.
2. **Observability stack** — kube-prometheus-stack + Loki + the dashboards
   in `infra/monitoring/grafana-dashboards/`. Wire alertmanager to Slack.
3. **Sentry** for backend + frontend errors.
4. **Steam OpenID auth** — let users connect their Steam account, upload
   their own demos.
5. **Drift detection on ML predictions** — track model output distribution
   per release; alert on shifts.
6. **Backfill historical pro matches** — ingest top N tournaments for
   richer demo / training corpus.

### Q3 2026
1. **Real-time match prediction** — use SSE infra already in place to stream
   live win-prob updates from in-progress matches (HLTV live page or demo
   relay).
2. **Coaching insights** — surface ML error detections in a coachable form
   (round X, player Y, suggested correction).
3. **Team-level dashboards** — extend player archetypes to team
   composition / map preference.
4. **Public API** — rate-limited, key-authenticated read API for the hosted
   data (matches, players, predictions).
5. **Cost/load test** — simulate 10x traffic, find the first bottleneck
   (likely ML inference latency or Postgres connection saturation).

### Beyond
- **Self-serve demo upload + parsing** for amateur teams
- **Tournament organiser tooling** — bracket overlays, prediction markets
- **Open-source the parser pieces** that don't depend on internal data
- **Mobile** — React Native / Expo client (already a referenced skill in
  the workspace tooling)

## Explicitly out of scope

- Other titles (Valorant, Dota, etc.) — focus is CS2.
- Bookmaking or gambling integrations.
- Hosting demos for users — we operate on demos uploaded or scraped, not
  as a long-term storage product.
