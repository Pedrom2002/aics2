# 03 - Tech Stack Completo

## Resumo Visual

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│  Next.js 15 (App Router, RSC) + shadcn/ui + Tailwind           │
│  Recharts (gráficos) + D3.js (mapas CS2) + Canvas (replayer)   │
│  TanStack Query (client state) + SSE (real-time)               │
├─────────────────────────────────────────────────────────────────┤
│                         BACKEND API                             │
│  FastAPI (Python 3.12+) + Pydantic v2                          │
│  JWT Auth + Multi-tenancy Middleware                            │
├───────────────┬──────────────────┬──────────────────────────────┤
│ FILA DE TAREFAS│   SERVIÇO ML     │   TEMPO REAL                 │
│  Celery       │   BentoML        │   SSE endpoints              │
│  Redis broker │   (containerized)│                              │
├───────────────┴──────────────────┴──────────────────────────────┤
│                      CAMADA DE DADOS                             │
│  PostgreSQL 16    │  ClickHouse     │  Redis        │  S3       │
│  (transacional)   │  (analytics)    │  (cache+queue)│  (demos)  │
├───────────────────┴─────────────────┴───────────────┴───────────┤
│                      ML PIPELINE                                │
│  PyTorch + scikit-learn + LightGBM + CatBoost + PyG            │
│  Integrated Gradients + FastTreeSHAP (interpretabilidade) + MLflow (experiment tracking) │
│  PostgreSQL + Redis (feature store) + Awpy (demo parsing)      │
├─────────────────────────────────────────────────────────────────┤
│                      INFRAESTRUTURA                              │
│  AWS (ECS Fargate, EC2 GPU, RDS, S3, CloudFront)              │
│  Docker + ECS Fargate + Terraform                               │
│  GitHub Actions (CI/CD)                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Parsing de Demos

### Awpy + demoparser2

| Aspeto | Detalhe |
|--------|---------|
| **Lib** | `awpy` (PyPI) |
| **Backend** | demoparser2 (Rust) — alta performance |
| **Python** | >= 3.11 |
| **Output** | DataFrames Pandas |
| **Dados** | Header, ticks, kills, damages, grenades, rounds, economy |

**Porquê Awpy**:
- Python nativo → integra com PyTorch, pandas, scikit-learn sem friction
- Backend Rust garante parsing rápido (~10-30 seg por demo)
- DataFrame output → transformação direta para features
- Comunidade ativa, lib mais usada para CS2 analytics em Python
- Extrai TODOS os dados que precisamos (tick-level + events)

**Alternativas avaliadas**:
- demoinfocs-golang: Requer Go, não integra com stack Python
- Clarity (Java): Muito rápido mas requer JVM, overkill
- demofile-net (C#): 1.3s parse mas ecossistema .NET

---

## Aprendizagem Automática

### PyTorch (Deep Learning)

| Aspeto | Detalhe |
|--------|---------|
| **Versão** | >= 2.2 |
| **Uso** | Mamba (error detection), Transformer (setup prediction) |
| **GPU** | CUDA support para treino |

**Porquê PyTorch**:
- Dominante em ML research e produção (2025-2026)
- 29% mais rápido em treino GPU vs TensorFlow
- Ecossistema imenso (torchvision, torchaudio, PyG)
- Melhor debugging (eager execution)
- Comunidade maior, mais tutorials e suporte

**Não TensorFlow**: Overhead de produção, curva de aprendizagem maior
**Não JAX**: Excelente para research mas falta tooling de produção

### scikit-learn + LightGBM + CatBoost (ML Clássico)

| Aspeto | Detalhe |
|--------|---------|
| **scikit-learn** | >= 1.5, clustering (HDBSCAN), preprocessing, evaluation |
| **LightGBM** | >= 4.0, utility error classification (7x mais rápido que XGBoost, leaf-wise growth) |
| **CatBoost** | >= 1.2, player rating model (tratamento nativo de features categóricas para player IDs, maps, weapons) |
| **XGBoost** | Disponível como componente de ensemble |
| **UMAP** | umap-learn, dimensionality reduction para weakness patterns |

**Porquê**:
- Testado em produção para ML tabular, não precisamos de deep learning para tudo
- LightGBM 7x mais rápido que XGBoost com leaf-wise growth — ideal para utility error classification
- CatBoost com tratamento nativo de features categóricas — ideal para player IDs, maps e weapons no rating model
- scikit-learn v1.8+ suporta GPU via Array API

### PyG - PyTorch Geometric (Graph Neural Networks)

| Aspeto | Detalhe |
|--------|---------|
| **Versão** | >= 2.5 |
| **Uso** | Strategy classifier (jogadores como grafos) |
| **Layers** | SAGEConv (GraphSAGE) |

**Porquê PyG sobre DGL**:
- 98.5% accuracy com inductive learning framework
- SAGEConv suporta inductive learning — generaliza para novos jogadores/grafos não vistos
- 30% melhor performance que DGL
- Mais datasets integrados (80 vs 40)
- Recomendado oficialmente pela NVIDIA
- Integração nativa com PyTorch

### Integrated Gradients + FastTreeSHAP (Interpretabilidade)

| Aspeto | Detalhe |
|--------|---------|
| **Integrated Gradients** | Para modelos neurais (Mamba, Transformer) — 50-100x mais rápido que SHAP, sub-10ms |
| **FastTreeSHAP** | Para modelos de árvore (LightGBM, CatBoost) — TreeExplainer nativo e rápido |
| **Uso** | Explicar cada predição dos modelos de erro |

**Porquê abordagem dual**:
- Integrated Gradients é o método de referência para redes neurais (Mamba, Transformer) — 50-100x mais rápido que DeepSHAP, latência sub-10ms
- FastTreeSHAP usa o TreeExplainer nativo do SHAP, optimizado para LightGBM e CatBoost
- Cada tipo de modelo tem o método de interpretabilidade mais adequado
- Permite gerar explicações humanas: "Este erro aconteceu porque X"
- Waterfall plots para visualização no frontend

### MLflow (Experiment Tracking)

| Aspeto | Detalhe |
|--------|---------|
| **Versão** | >= 2.10 |
| **Uso** | Tracking de experiências, model registry, comparação |
| **Deploy** | Model Registry → BentoML → Docker |

### BentoML (Model Serving)

| Aspeto | Detalhe |
|--------|---------|
| **Versão** | >= 1.2 |
| **Uso** | Servir modelos em produção |
| **Vantagem** | Multi-modelo, batching, containerização automática |

**Porquê BentoML sobre TorchServe**:
- Mais simples para equipas pequenas
- Suporta PyTorch + scikit-learn + XGBoost nativamente
- Docker containers gerados automaticamente
- Batching e async out-of-box

### PostgreSQL + Redis (Feature Store - MVP)

| Aspeto | Detalhe |
|--------|---------|
| **Offline Store** | PostgreSQL direto — armazenamento de features para treino |
| **Online Store** | Redis — features em tempo real para inferência |
| **Sync** | ~100 linhas de Python para batch→online sync |
| **Custo** | $20-50/mês vs $200+/mês para Feast managed |

**Porquê não Feast (por agora)**:
- PostgreSQL + Redis cobre 100% das necessidades de MVP sem overhead operacional
- ~100 linhas de Python para sincronização batch→online — simples e controlável
- $20-50/mês vs $200+/mês para Feast com infra dedicada
- Migrar para Feast quando exceder limites (1000s de features, múltiplas equipas de ML)

---

## Backend

### FastAPI

| Aspeto | Detalhe |
|--------|---------|
| **Versão** | >= 0.110 |
| **Python** | 3.12+ |
| **Validação** | Pydantic v2 |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Migrations** | Alembic |
| **Docs** | Auto-generated Swagger/OpenAPI |

**Porquê FastAPI**:
- Performance igual a Node.js, muito superior a Django REST
- Async nativo — crítico para servir analytics em tempo real
- Pydantic v2 — validação automática de request/response
- Auto-documentação Swagger — reduz overhead de docs
- Integração natural com ecossistema Python ML

**Não Django**: Overhead desnecessário, REST framework mais lento
**Não Node.js**: Separaria backend do ML stack (tudo Python é vantagem)
**Não Go**: Performance superior mas equipa pequena em Python é mais produtiva

### Celery + Redis (Task Queue)

| Aspeto | Detalhe |
|--------|---------|
| **Celery** | >= 5.3 |
| **Broker** | Redis |
| **Uso** | parse_demo, compute_features, run_inference |

**Porquê Celery**:
- Testado em produção, bem documentado
- Python nativo, integra com FastAPI
- Demo processing é o caso de uso clássico de task queue
- Retry logic, monitoring (Flower), prioridades

---

## Bases de Dados

### PostgreSQL 16 (Transacional)

| Aspeto | Detalhe |
|--------|---------|
| **Uso** | Auth, teams, match metadata, resultados ML, scout reports |
| **Multi-tenancy** | Row-Level Security (RLS) por org_id |
| **AWS** | RDS PostgreSQL |

**Porquê PostgreSQL**:
- ACID compliance para dados sensíveis
- RLS nativo para multi-tenancy sem complexidade
- JSONB para dados flexíveis (SHAP factors, report data)
- Ecossistema maduro (Alembic, SQLAlchemy)

### ClickHouse (Analytics)

| Aspeto | Detalhe |
|--------|---------|
| **Uso** | Tick data, events (milhões de rows por match) |
| **Compressão** | LZ4 (6x menos disco que PostgreSQL) |
| **Performance** | 100-9000x mais rápido que PG para queries analíticas |
| **Deploy** | ClickHouse Cloud (managed) |

**Porquê ClickHouse**:
- Tick data é append-only, nunca atualizada — perfeito para columnar store
- Uma match gera ~15M tick rows — PG seria muito lento
- Queries agregadas (heatmaps, stats) em milissegundos
- Compressão excelente para dados repetitivos

**Não TimescaleDB**: Bom compromisso mas ClickHouse é significativamente mais rápido para o nosso volume

### Redis

| Aspeto | Detalhe |
|--------|---------|
| **Uso** | Cache de queries, broker Celery, online feature store |
| **AWS** | ElastiCache |

---

## Frontend

### Next.js 15

| Aspeto | Detalhe |
|--------|---------|
| **Router** | App Router com React Server Components |
| **React** | 19+ |
| **Rendering** | RSC para data fetching, Client Components para interatividade |

**Porquê Next.js**:
- 2-3x initial load mais rápido que React SPA
- 40% bundle menor com React Server Components
- Data fetching no servidor — dashboard sidebar, tables, stats em RSC
- Image/font optimization, code splitting automático
- Turbopack: HMR <100ms

### Recharts (Gráficos Standard)

| Aspeto | Detalhe |
|--------|---------|
| **Uso** | Economy graphs, radar charts, bar charts, line charts |
| **Porquê** | API simples, integração React nativa, cobre 95% dos gráficos |

### D3.js (Mapas CS2 Custom)

| Aspeto | Detalhe |
|--------|---------|
| **Uso** | Map renderer, heatmaps, SHAP waterfall plots |
| **Porquê** | Flexibilidade total para visualizações custom de mapas CS2 |

### Canvas API (Replayer 2D)

| Aspeto | Detalhe |
|--------|---------|
| **Uso** | Replayer em tempo real (10 jogadores, 64 updates/seg) |
| **Porquê** | Performance superior a SVG para animações contínuas |

### shadcn/ui + Tailwind

| Aspeto | Detalhe |
|--------|---------|
| **Uso** | Componentes UI (buttons, cards, tables, modals, forms) |
| **Porquê** | Acessíveis, customizáveis, copy-paste (não dependency) |

### TanStack Query (React Query)

| Aspeto | Detalhe |
|--------|---------|
| **Uso** | Client-side data fetching para dados dinâmicos |
| **Porquê** | Cache, refetch, optimistic updates para UI interativa |

### SSE (Server-Sent Events)

| Aspeto | Detalhe |
|--------|---------|
| **Uso** | Status de processamento de demos, notificações |
| **Porquê** | Mais simples que WebSocket para updates unidirecionais |

---

## Infraestrutura

### AWS

| Serviço | Uso |
|---------|-----|
| **ECS Fargate** | Orquestração de containers (backend, ML serving, workers) — auto-scaling sem gerir nodes |
| **EC2 g5.xlarge** | GPU instances para treino ML (A10G, spot) |
| **RDS** | PostgreSQL managed |
| **S3** | Demo file storage |
| **ElastiCache** | Redis managed |
| **CloudFront** | CDN para frontend |
| **ECR** | Docker image registry |
| **Secrets Manager** | Credenciais e API keys |

### Docker + ECS Fargate

| Aspeto | Detalhe |
|--------|---------|
| **Containers** | Backend, ML Serving, Parser Worker, Frontend |
| **Orchestration** | ECS Fargate com auto-scaling — poupa $73/mês control plane vs EKS, 4h setup vs 1 semana |
| **Manifests** | ECS Task Definitions + Service definitions via Terraform |
| **Migração** | Migrar para EKS apenas se necessário (multi-cluster, custom networking avançado) |

### GitHub Actions (CI/CD)

| Pipeline | Trigger | Ações |
|----------|---------|-------|
| CI | Push/PR | Lint, test, type-check, build |
| ML Pipeline | Novo data threshold / manual | Train, evaluate, register |
| Deploy | Merge to main | Build images, push ECR, deploy ECS Fargate |

### Terraform

| Aspeto | Detalhe |
|--------|---------|
| **Uso** | Provisioning de toda a infraestrutura AWS |
| **State** | S3 backend com DynamoDB lock |

---

## Versões e Compatibilidade

```
Python:          3.12+
Node.js:         20 LTS
PostgreSQL:      16
ClickHouse:      24+
Redis:           7+
Docker:          24+
LightGBM:        4.0+
CatBoost:        1.2+
Terraform:       1.6+
```

## Gestores de Pacotes

```
Python:    uv (rápido, substitui pip + virtualenv)
Node.js:   pnpm (rápido, eficiente em disco)
Monorepo:  turborepo (builds frontend) + uv workspaces (Python)
```
