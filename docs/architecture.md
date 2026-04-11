# Architecture

High-level operational view of the **cs2-analytics** platform. For deep dives
on individual subsystems, see `docs/02-ml-architecture.md`,
`docs/04-database-schema.md`, `docs/05-api-design.md`,
`docs/06-frontend-architecture.md`, `docs/07-ml-training-pipeline.md`.

## 1. Component map

```
                                +-------------------------------+
                                |          End users            |
                                +---------------+---------------+
                                                |
                                          HTTPS / WSS
                                                |
                              +-----------------v-----------------+
                              |      NGINX Ingress + cert-mgr     |
                              +--+-------------------------------++
                                 |                               |
                                 | app.cs2.gg                    | api.cs2.gg
                                 v                               v
                       +---------+---------+         +-----------+-----------+
                       |    Frontend       |         |       Backend         |
                       |  (Next.js 16,     |         |  (FastAPI, Python     |
                       |   App Router,     |  REST   |   3.12, asyncpg,      |
                       |   SSR + RSC)      <---------+   Celery, slowapi)    |
                       +---------+---------+         +-----+-----------+-----+
                                                           |           |
                                                  read/write|         | jobs
                                                           |           |
                              +----------------------------+           |
                              |                                        |
                              v                                        v
                  +-----------+-----------+              +-------------+-------------+
                  |    PostgreSQL 16      |              |          Redis 7          |
                  |   (asyncpg + alembic) |              |  (cache, slowapi limiter, |
                  |   matches, players,   |              |   Celery broker, SSE      |
                  |   demos, ml meta...)  |              |   pub/sub)                |
                  +-----------+-----------+              +-------------+-------------+
                              ^                                         ^
                              |                                         |
                              | features                                | enqueue
                              |                                         |
            +-----------------+----------------+        +---------------+-----------------+
            |        Feature engine            |        |        Celery workers           |
            |  (packages/feature-engine,       |        |  (packages/backend/src/tasks)   |
            |   Polars + DuckDB transforms)    |        |  parse, train, score, ingest    |
            +-----------------+----------------+        +---------------+-----------------+
                              ^                                         |
                              |                                         |
                              |                                         v
                  +-----------+----------+              +---------------+----------------+
                  |   Demo parser        |              |   ML serving (BentoML +        |
                  | (packages/demo-      |              |   bundled artefacts in PVC)    |
                  |  parser, awpy 2.x)   |              |   - win-prob v2 (AUC 0.904)    |
                  +-----------+----------+              |   - player rating (R2 0.998)   |
                              ^                          |   - error detection            |
                              |                          |   - archetypes (UMAP+HDBSCAN)  |
                  +-----------+----------+              +--------------------------------+
                  |  pro-demo-ingester   |
                  |  (HLTV scrape →      |
                  |   download → .dem)   |
                  +----------------------+
                              ^
                              |
                  +-----------+----------+
                  |  S3 / MinIO (demos,  |
                  |  models, backups)    |
                  +----------------------+
```

## 2. Packages

| Package                       | Lang   | Role |
|-------------------------------|--------|------|
| `packages/frontend`           | TS/Next | User-facing web app, dashboards, replay |
| `packages/backend`            | Python | FastAPI HTTP API + Celery tasks |
| `packages/demo-parser`        | Python | Wraps awpy 2.x; emits parsed events to Polars/Parquet |
| `packages/feature-engine`     | Python | Per-round / per-player feature derivation |
| `packages/ml-models`          | Python | Training + inference; BentoML packaging |
| `packages/pro-demo-ingester`  | Python | HLTV scraper → demo downloader |

## 3. Request flow — interactive API call

```
user → Ingress → frontend (RSC fetch) → backend (FastAPI)
                                          |
                                          |-- JWT verify (jose)
                                          |-- slowapi rate limit (Redis backend)
                                          |-- DB query (asyncpg via SQLAlchemy 2.0)
                                          |-- Redis cache lookup / fill
                                          |-- (optional) ML inference call
                                          v
                                       JSON response
                                          |
                                          v
                                  frontend renders
```

`/api/sse/...` paths use Server-Sent Events for live match score updates;
backend maintains the connection and pushes events from a Redis pub/sub
channel populated by Celery tasks.

## 4. Demo ingestion flow

```
HLTV results page
        |
        v
pro-demo-ingester (scheduled by Celery Beat)
        |
        |-- scrape match list
        |-- download .rar / .dem
        |-- extract → object storage (S3/MinIO)
        |-- enqueue parse task
        v
Celery worker (parse_demo)
        |
        |-- demo-parser (awpy) → events (parquet)
        |-- feature-engine → per-round features
        |-- write match + rounds + events to Postgres
        |-- write parse cache (so re-runs are cheap)
        |-- enqueue ML scoring tasks
        v
Celery worker (score_match)
        |
        |-- run win-prob, error-detection, rating, archetype models
        |-- write predictions to Postgres
        |-- publish "match_ready" to Redis pub/sub
        v
SSE clients receive update; UI refreshes
```

## 5. ML training flow

```
Operator → CLI (`python -m cs2_ml.train ...`)
                 |
                 |-- pull labelled features from Postgres / parquet
                 |-- split train/val/test (time-aware)
                 |-- fit model (CatBoost / sklearn / torch)
                 |-- evaluate, write metrics + artefact to models dir
                 |-- (optional) BentoML build → push image
                 v
        Models PVC / object storage
                 |
                 v
        Backend hot-reloads bundle on next request,
        or new pod rollout pulls new image.
```

Training pipelines that exist today (per recent commits): smart labelling,
win-prob v2 (21 features, AUC 0.904), player rating (R2 0.998), Mamba
sequence regression, UMAP + HDBSCAN player archetypes, ML error detection
with heuristic baseline.

## 6. Storage

| Store        | Holds |
|--------------|-------|
| Postgres     | OLTP — users, demos, matches, rounds, players, predictions, billing |
| Redis        | Cache, rate-limit counters, Celery broker, SSE pub/sub |
| Object store | Raw `.dem` files, parsed parquet, model artefacts, backups |
| ML PVC       | Loaded model bundles for backend inference |

## 7. External integrations

- **Stripe** — billing (webhooks → backend)
- **HLTV** — pro match metadata (scrape only)
- **Steam (planned)** — auth, demo upload via OpenID
- **Sentry (planned)** — frontend + backend error tracking
