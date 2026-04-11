# cs2-analytics Helm Chart

Minimum-viable Helm chart for deploying the AI CS2 Analytics platform on Kubernetes.

## What it deploys

- `backend` Deployment + Service + HPA (FastAPI)
- `frontend` Deployment + Service (Next.js)
- `Ingress` for `app.*` and `api.*` hosts (NGINX + cert-manager)
- `ConfigMap` for non-secret env vars
- References an existing `Secret` for credentials

Postgres and Redis are intentionally **not** in the chart by default — use a managed
service (RDS / Cloud SQL / ElastiCache) in production. For dev clusters, the raw
manifests under `infra/k8s/postgres` and `infra/k8s/redis` work fine.

## Install

```bash
# 1. Create namespace + secrets out-of-band
kubectl create namespace cs2-analytics
kubectl -n cs2-analytics apply -f ../../k8s/secret.yaml.example   # edit values first

# 2. Install / upgrade
helm upgrade --install cs2 ./infra/helm/cs2-analytics \
  --namespace cs2-analytics \
  --set global.imageRegistry=ghcr.io/your-org \
  --set backend.image.tag=v1.2.3 \
  --set frontend.image.tag=v1.2.3 \
  --set ingress.hosts.app=app.example.com \
  --set ingress.hosts.api=api.example.com
```

## Custom values example

```yaml
# my-values.yaml
global:
  imageRegistry: registry.gitlab.com/cs2

backend:
  replicaCount: 4
  resources:
    requests:
      cpu: 1000m
      memory: 1Gi
  autoscaling:
    minReplicas: 4
    maxReplicas: 20

ingress:
  hosts:
    app: app.cs2.gg
    api: api.cs2.gg
```

Then: `helm upgrade --install cs2 ./infra/helm/cs2-analytics -f my-values.yaml`

## Uninstall

```bash
helm uninstall cs2 -n cs2-analytics
```

## Notes

- The chart references `secrets.existingSecret` rather than embedding sensitive values.
  Use sealed-secrets, external-secrets-operator, or your platform's secret manager.
- HPA is CPU+memory based; add custom metrics via Prometheus adapter for request-rate
  scaling.
- Probes hit `/health` (backend) and `/api/health` (frontend) — ensure those endpoints
  exist (they're implemented in `packages/backend/src/routers/health.py`).
