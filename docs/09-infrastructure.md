# 09 - Infraestrutura

## Arquitetura na Cloud (AWS)

```
                    ┌─────────────────┐
                    │   CloudFront    │
                    │   (CDN + WAF)   │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │   ALB (Load     │
                    │   Balancer)     │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
   ┌────────┴───────┐ ┌─────┴──────┐ ┌──────┴───────┐
   │   Frontend     │ │  Backend   │ │  ML Serving  │
   │   (Next.js)    │ │  (FastAPI) │ │  (BentoML)   │
   │  ECS Fargate   │ │ECS Fargate │ │ ECS Fargate  │
   └────────────────┘ │  (2-4)     │ │  (2-3)       │
                      └─────┬──────┘ └──────┬───────┘
                            │               │
            ┌───────────────┼───────────────┤
            │               │               │
   ┌────────┴───────┐ ┌────┴─────┐ ┌──────┴───────┐
   │   PostgreSQL   │ │  Redis   │ │  ClickHouse  │
   │   (RDS)        │ │ (Elasti- │ │  (Cloud)     │
   │                │ │  Cache)  │ │              │
   └────────────────┘ └──────────┘ └──────────────┘
            │
   ┌────────┴───────┐
   │   S3           │
   │   (Demos +     │
   │    Static)     │
   └────────────────┘
```

---

## Serviços AWS

| Serviço | Utilização | Configuração |
|---------|-----|--------|
| **ECS Fargate** | Orquestração de containers | Serverless, auto-scaling |
| **EC2** | Treino GPU apenas | g5.xlarge (spot instances) |
| **RDS** | PostgreSQL 16 | db.t3.small |
| **ElastiCache** | Redis 7 | cache.r6g.large, 1 node |
| **S3** | Armazenamento de demos + assets estáticos | Standard tier |
| **CloudFront** | CDN para frontend + cache API | Localizações globais |
| **ECR** | Registo de imagens Docker | Políticas de ciclo de vida |
| **Secrets Manager** | Credenciais e chaves API | Rotação automática |
| **CloudWatch** | Logs + métricas | 30 dias de retenção |
| **WAF** | Firewall de Aplicação Web | Regras OWASP |
| **Route 53** | DNS | Gestão de domínio |
| **ACM** | Certificados TLS | Renovação automática |
| **SES** | Email (convites, notificações) | Domínio verificado |

### ClickHouse Cloud

Utilizar ClickHouse Cloud (gerido) em vez de auto-alojado:
- Menos overhead operacional para equipa pequena
- Auto-scaling baseado em queries
- Backups automáticos
- Região: eu-west-1 (Irlanda) ou eu-central-1 (Frankfurt)

---

## ECS Fargate

### Porquê ECS Fargate em vez de EKS

- Elimina $73/mês de EKS control plane
- Setup em 4 horas vs 1+ semana para EKS
- Muito menos overhead operacional para equipa de 2-5 devs
- Auto-scaling, SSL, load balancing incluído
- Migração para EKS possível mais tarde se necessário

### Definições de Tarefas (Task Definitions)

```json
// Definição de Tarefa da API Backend
{
  "family": "cs2-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "${ECR_REGISTRY}/cs2-backend:latest",
      "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
      "environment": [
        {"name": "DATABASE_URL", "value": "from-secrets"},
        {"name": "REDIS_URL", "value": "from-secrets"},
        {"name": "CLICKHOUSE_URL", "value": "from-secrets"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/cs2-backend",
          "awslogs-region": "eu-west-1"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

```json
// Definição de Tarefa do Celery Worker
{
  "family": "cs2-celery",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "celery",
      "image": "${ECR_REGISTRY}/cs2-backend:latest",
      "command": ["celery", "-A", "src.tasks", "worker", "--loglevel=info", "--concurrency=4"]
    }
  ]
}
```

```json
// Definição de Tarefa do Serviço ML
{
  "family": "cs2-ml-serving",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "bentoml",
      "image": "${ECR_REGISTRY}/cs2-ml-serving:latest",
      "portMappings": [{"containerPort": 3000, "protocol": "tcp"}]
    }
  ]
}
```

### Auto-Scaling (Application Auto Scaling)

```json
{
  "ServiceNamespace": "ecs",
  "ScalableDimension": "ecs:service:DesiredCount",
  "MinCapacity": 1,
  "MaxCapacity": 8,
  "TargetTrackingScalingPolicy": {
    "TargetValue": 70,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    }
  }
}
```

---

## Docker

### Ficheiros Docker

```dockerfile
# infra/docker/Dockerfile.backend

FROM python:3.12-slim AS base
WORKDIR /app

# Instalar dependências de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY packages/backend/pyproject.toml packages/backend/
COPY packages/demo-parser/pyproject.toml packages/demo-parser/
COPY packages/feature-engine/pyproject.toml packages/feature-engine/
RUN pip install --no-cache-dir \
    -e packages/backend \
    -e packages/demo-parser \
    -e packages/feature-engine

# Copiar código fonte
COPY packages/backend/src /app/packages/backend/src
COPY packages/demo-parser/src /app/packages/demo-parser/src
COPY packages/feature-engine/src /app/packages/feature-engine/src

# Executar
EXPOSE 8000
CMD ["uvicorn", "packages.backend.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# infra/docker/Dockerfile.frontend

FROM node:20-alpine AS builder
WORKDIR /app

COPY packages/frontend/package.json packages/frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY packages/frontend/ .
RUN pnpm build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

### Docker Compose (Desenvolvimento Local)

```yaml
# docker-compose.yml

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: cs2analytics
      POSTGRES_USER: cs2user
      POSTGRES_PASSWORD: localdev123
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  clickhouse:
    image: clickhouse/clickhouse-server:24
    ports:
      - "8123:8123"   # HTTP
      - "9000:9000"   # Native
    volumes:
      - chdata:/var/lib/clickhouse

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  mlflow:
    image: ghcr.io/mlflow/mlflow:2.10
    command: mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri postgresql://cs2user:localdev123@postgres/mlflow
    ports:
      - "5000:5000"
    depends_on:
      - postgres

  backend:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://cs2user:localdev123@postgres/cs2analytics
      REDIS_URL: redis://redis:6379
      CLICKHOUSE_URL: http://clickhouse:8123
      S3_ENDPOINT: http://minio:9000
    depends_on:
      - postgres
      - redis
      - clickhouse
    volumes:
      - ./packages/backend/src:/app/packages/backend/src  # Hot reload

  celery:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.backend
    command: celery -A src.tasks worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://cs2user:localdev123@postgres/cs2analytics
      REDIS_URL: redis://redis:6379
      CLICKHOUSE_URL: http://clickhouse:8123
    depends_on:
      - postgres
      - redis

  frontend:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      BACKEND_URL: http://backend:8000
    volumes:
      - ./packages/frontend/src:/app/src  # Hot reload

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - miniodata:/data

volumes:
  pgdata:
  chdata:
  miniodata:
```

---

## CI/CD (GitHub Actions)

### Pipeline de CI

```yaml
# .github/workflows/ci.yml

name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_cs2
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
      redis:
        image: redis:7
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }

      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -e "packages/backend[test]"
          uv pip install -e packages/demo-parser
          uv pip install -e packages/feature-engine

      - name: Lint
        run: ruff check packages/

      - name: Type check
        run: mypy packages/backend/src/

      - name: Test
        run: pytest packages/backend/tests/ -v --cov=src --cov-report=xml
        env:
          DATABASE_URL: postgresql://test:test@localhost/test_cs2
          REDIS_URL: redis://localhost:6379

      - name: Upload coverage
        uses: codecov/codecov-action@v4

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "pnpm" }

      - name: Install
        run: cd packages/frontend && pnpm install --frozen-lockfile

      - name: Lint
        run: cd packages/frontend && pnpm lint

      - name: Type check
        run: cd packages/frontend && pnpm tsc --noEmit

      - name: Test
        run: cd packages/frontend && pnpm test

      - name: Build
        run: cd packages/frontend && pnpm build

  ml-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }

      - name: Install
        run: |
          pip install uv
          uv pip install -e "packages/ml-models[test]"

      - name: Test
        run: pytest packages/ml-models/tests/ -v
```

### Pipeline de Deploy

```yaml
# .github/workflows/deploy.yml

name: Deploy

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-west-1

      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push images
        run: |
          docker build -f infra/docker/Dockerfile.backend -t $ECR/cs2-backend:$SHA .
          docker build -f infra/docker/Dockerfile.frontend -t $ECR/cs2-frontend:$SHA .
          docker build -f infra/docker/Dockerfile.ml-serving -t $ECR/cs2-ml-serving:$SHA .
          docker push $ECR/cs2-backend:$SHA
          docker push $ECR/cs2-frontend:$SHA
          docker push $ECR/cs2-ml-serving:$SHA

      - name: Deploy to ECS Fargate
        run: |
          aws ecs update-service --cluster cs2-analytics --service backend --force-new-deployment
          aws ecs update-service --cluster cs2-analytics --service celery-worker --force-new-deployment
          aws ecs update-service --cluster cs2-analytics --service ml-serving --force-new-deployment
          aws ecs update-service --cluster cs2-analytics --service frontend --force-new-deployment
          aws ecs wait services-stable --cluster cs2-analytics --services backend

      - name: Run DB migrations
        run: |
          aws ecs run-task \
            --cluster cs2-analytics \
            --task-definition cs2-backend \
            --overrides '{"containerOverrides":[{"name":"backend","command":["alembic","upgrade","head"]}]}' \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SG_ID]}"

      - name: Smoke test
        run: |
          curl -f https://api.cs2analytics.com/health || exit 1
```

---

## Monitorização & Observabilidade

### Stack de Monitorização

| Ferramenta | Utilização |
|-----------|-----|
| **Prometheus** | Métricas (CPU, memória, personalizadas) |
| **Grafana** | Dashboards de monitorização |
| **CloudWatch Logs** | Centralização de logs |
| **Sentry** | Rastreamento de erros (backend + frontend) |
| **PagerDuty** | Alertas de chamada |

### Métricas Críticas

```
Aplicação:
  - Tempo de resposta da API (p50, p95, p99)
  - Taxa de erros (5xx por minuto)
  - Tempo de processamento de demo (upload → análise completa)
  - Utilizadores concorrentes ativos

ML:
  - Latência de inferência dos modelos
  - Drift na distribuição de predições
  - Frescura do feature store

Infraestrutura:
  - Utilização CPU/Memória por container
  - Uso de disco (PostgreSQL, ClickHouse, S3)
  - Throughput de rede

Negócio:
  - Demos enviados por dia
  - Organizações ativas
  - Distribuição de tiers
  - Scout reports gerados
```

### Regras de Alerta

```yaml
# Regras de alerta Prometheus

groups:
- name: critical
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status="5xx"}[5m]) > 0.05
    for: 5m
    labels: { severity: critical }

  - alert: DemoProcessingStuck
    expr: demo_processing_duration_seconds > 600  # > 10 min
    for: 10m
    labels: { severity: warning }

  - alert: DatabaseConnectionPoolExhausted
    expr: db_pool_available_connections < 2
    for: 2m
    labels: { severity: critical }

  - alert: MLServingDown
    expr: up{job="ml-serving"} == 0
    for: 1m
    labels: { severity: critical }

  - alert: DiskSpaceClickHouse
    expr: disk_used_percent{instance="clickhouse"} > 85
    for: 30m
    labels: { severity: warning }
```

---

## Estimativa de Custos (Mensal)

### Cenário: 50 equipas, 1.500 demos/mês

| Componente | Custo |
|-----------|-------|
| ECS Fargate (API + Workers) | ~$60 |
| S3 (demos) | ~$10 |
| RDS PostgreSQL (t3.small) | ~$30 |
| ClickHouse Serverless | ~$50 |
| NAT/ALB/misc | ~$70 |
| ElastiCache Redis | ~$30 |
| Treino GPU (spot, quando necessário) | ~$50 |
| **Total** | **~$300/mês** |

Otimizações:
- VPC Endpoints para S3/ECR (poupa $30-40/mês em NAT)
- Planos de poupança se carga de trabalho estável (30-50% desconto)

### Cenário: 200 equipas

| Componente | Estimativa |
|-----------|-----------|
| ECS Fargate (scale up) | ~$200 |
| RDS PostgreSQL (scale up) | ~$100 |
| ClickHouse Cloud | ~$200 |
| Outros | ~$200 |
| Treino GPU | ~$100 |
| **Total** | **~$800/mês** |

---

## Backup & Recuperação de Desastres

```
PostgreSQL (RDS):
  - Backups automáticos: diários, 30 dias de retenção
  - Recuperação point-in-time: últimos 5 minutos
  - Multi-AZ: failover automático
  - Snapshots manuais antes de migrações

ClickHouse Cloud:
  - Backups automáticos incluídos no serviço
  - Retenção: 30 dias

S3:
  - Versionamento ativado (demos são imutáveis)
  - Ciclo de vida: demos > 1 ano → Glacier
  - Replicação cross-region (opcional)

MLflow / Modelos:
  - Artefactos em S3 (versionados)
  - Registo de modelos com histórico completo

Objetivos de Recuperação:
  - RTO (tempo para restaurar): < 1 hora
  - RPO (perda de dados máxima): < 5 minutos (PG), < 1 hora (CH)
```
