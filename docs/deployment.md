# Deployment Guide

This document covers deploying **cs2-analytics** across local, staging, and
production environments.

> The repo already has architecture detail in `docs/09-infrastructure.md` and
> `docs/03-tech-stack.md`. This file is the operational complement: prerequisites,
> commands, rollback, troubleshooting.

## Environments at a glance

| Env        | Stack                              | Where                   |
|------------|------------------------------------|-------------------------|
| Local      | docker compose                     | developer laptop        |
| Staging    | docker compose with prod-ish vars  | single VM               |
| Production | Kubernetes (Helm)                  | EKS / GKE / on-prem k8s |

## 1. Prerequisites

| Tool        | Min version | Required for |
|-------------|-------------|--------------|
| Docker      | 24.x        | local + staging |
| docker compose v2 | bundled with Docker | local + staging |
| Node + pnpm | Node 20, pnpm 10.32.1 | frontend dev |
| Python      | 3.12        | backend / ML dev |
| uv (or pip) | latest      | backend deps |
| kubectl     | 1.30+       | production |
| helm        | 3.14+       | production |
| terraform   | 1.6+        | infra provisioning (optional) |
| awscli      | 2.x         | backups, S3 |

## 2. Local development (docker compose)

```bash
# 1. Copy env template
cp .env.example .env
# fill in JWT_SECRET_KEY, STRIPE keys, etc.

# 2. Start data services
docker compose -f infra/docker-compose.yml up -d

# 3. Run the backend
cd packages/backend
uv sync                                # or: pip install -e .[test,dev,parser]
alembic upgrade head
uvicorn src.main:app --reload --port 8000

# 4. Run the frontend
cd packages/frontend
pnpm install
pnpm dev                               # localhost:3000
```

Verify: open http://localhost:8000/health and http://localhost:3000.

## 3. Staging (docker compose with prod env)

```bash
# On the staging VM:
git clone https://github.com/cs2-analytics/cs2-analytics.git
cd cs2-analytics
cp .env.example .env.staging
# Set ENVIRONMENT=staging, real DB password, real S3, real Stripe test keys

docker compose --env-file .env.staging -f infra/docker-compose.yml up -d
docker compose exec backend alembic upgrade head
```

Use a reverse proxy (Caddy / Traefik / nginx) for TLS in front of the
compose stack on staging.

## 4. Production (Kubernetes + Helm)

### 4.1 One-time bootstrap

```bash
# Cluster prerequisites: ingress-nginx + cert-manager + metrics-server installed.
kubectl create namespace cs2-analytics

# Create secrets (or use sealed-secrets / external-secrets-operator)
cp infra/k8s/secret.yaml.example secret.yaml
# edit values
kubectl -n cs2-analytics apply -f secret.yaml
rm secret.yaml
```

### 4.2 First install

```bash
helm upgrade --install cs2 ./infra/helm/cs2-analytics \
  --namespace cs2-analytics \
  --set global.imageRegistry=ghcr.io/your-org \
  --set backend.image.tag=v0.1.0 \
  --set frontend.image.tag=v0.1.0 \
  --set ingress.hosts.app=app.example.com \
  --set ingress.hosts.api=api.example.com
```

Or apply the raw manifests:

```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/configmap.yaml
kubectl apply -R -f infra/k8s/postgres
kubectl apply -R -f infra/k8s/redis
kubectl apply -R -f infra/k8s/backend
kubectl apply -R -f infra/k8s/frontend
kubectl apply -f infra/k8s/ingress.yaml
```

### 4.3 Run migrations

Migrations are NOT part of the regular pod boot — run them as a one-off Job
on each release:

```bash
kubectl -n cs2-analytics run alembic-upgrade \
  --rm -it --restart=Never \
  --image=ghcr.io/your-org/backend:v0.1.0 \
  --env-from=secret/cs2-analytics-secrets \
  --env-from=configmap/cs2-analytics-config \
  --command -- alembic upgrade head
```

### 4.4 Subsequent releases

```bash
helm upgrade cs2 ./infra/helm/cs2-analytics \
  --namespace cs2-analytics \
  --reuse-values \
  --set backend.image.tag=v0.2.0 \
  --set frontend.image.tag=v0.2.0
```

Watch the rollout:

```bash
kubectl -n cs2-analytics rollout status deploy/backend --timeout=5m
kubectl -n cs2-analytics rollout status deploy/frontend --timeout=5m
```

## 5. Rollback strategy

### Application rollback

```bash
# List Helm history
helm -n cs2-analytics history cs2

# Roll back to revision N (use the previous good one)
helm -n cs2-analytics rollback cs2 N

# Or per-deployment with kubectl
kubectl -n cs2-analytics rollout undo deploy/backend
```

### Database rollback

Schema changes are managed by Alembic. Roll **forward** with a new revision
unless the change has not yet shipped to production.

```bash
# Inspect history
alembic history --verbose
# Roll back exactly one revision
alembic downgrade -1
```

If a destructive migration shipped, restore from backup:

```bash
S3_KEY=postgres/postgres-cs2analytics-20260411T031500Z.sql.gz \
  ./scripts/backup/restore-postgres.sh "$S3_KEY"
```

## 6. Backups

See `scripts/backup/README.md`. Run as a Kubernetes `CronJob` against the
postgres service. ML model artefacts are tar'd weekly via `backup-models.sh`.

## 7. Observability

- Prometheus scrapes `/metrics` on the backend (config: `infra/monitoring/prometheus.yml`)
- Grafana dashboards: `infra/monitoring/grafana-dashboards/*.json`
- Alerts: `infra/monitoring/alert-rules.yml` + `alertmanager.yml`

## 8. Troubleshooting

| Symptom                                 | First check |
|-----------------------------------------|-------------|
| Backend pods CrashLoopBackOff           | `kubectl logs` — usually missing env var or DB unreachable |
| Frontend 502 from ingress               | Check pod readiness; check `NEXT_PUBLIC_API_URL` ConfigMap value |
| `alembic upgrade head` hangs            | Long-running query holding lock — `pg_stat_activity` |
| HPA not scaling                         | `metrics-server` installed? `kubectl top pods` works? |
| `pg_isready` fails                      | StatefulSet PVC mounted? Look at `kubectl describe pvc` |
| Cert-manager TLS pending                | `kubectl describe certificate -n cs2-analytics` — DNS / HTTP-01 challenge issue |
| ML inference 500s                       | Models PVC mounted at `ML_MODELS_PATH`? Bundle present? |
| Demo ingestion stuck                    | Celery worker logs; verify Redis broker reachable |

### Useful commands

```bash
# Tail backend logs
kubectl -n cs2-analytics logs -f deploy/backend --max-log-requests=10

# Shell into a pod
kubectl -n cs2-analytics exec -it deploy/backend -- sh

# Port-forward Postgres for inspection
kubectl -n cs2-analytics port-forward svc/postgres 15432:5432

# Force a re-roll (useful after secret update)
kubectl -n cs2-analytics rollout restart deploy/backend
```
