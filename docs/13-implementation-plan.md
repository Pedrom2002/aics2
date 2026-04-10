# 13 - Plano de Implementação Completo

> **Projeto**: AI CS2 Analytics Platform
> **Data**: Março 2026
> **Estado**: Documentação completa (docs 01-12), zero código implementado
> **Objetivo**: Plano detalhado sprint-a-sprint para ir de documentação a produto em produção
> **Contexto competitivo**: Skybox EDGE domina 90% do mercado pro; entramos pelo segmento semi-pro/amador com AI superior e preços 7x mais baixos

---

## Índice

1. [Visão Estratégica](#1-visão-estratégica)
2. [Fases de Implementação](#2-fases-de-implementação)
3. [Fase 0 — Validação de Mercado](#3-fase-0--validação-de-mercado-semanas-1-4)
4. [Fase 1 — Fundação Técnica](#4-fase-1--fundação-técnica-semanas-5-8)
5. [Fase 2 — MVP Core](#5-fase-2--mvp-core-semanas-9-16)
6. [Fase 3 — Pipeline de Demos Pro](#6-fase-3--pipeline-de-demos-pro-semanas-13-18)
7. [Fase 4 — ML Error Detection](#7-fase-4--ml-error-detection-semanas-14-20)
8. [Fase 5 — Frontend Completo](#8-fase-5--frontend-completo-semanas-17-22)
9. [Fase 6 — Beta Fechado](#9-fase-6--beta-fechado-semanas-23-26)
10. [Fase 7 — Soft Launch](#10-fase-7--soft-launch-semanas-27-30)
11. [Fase 8 — Crescimento & Features Avançadas](#11-fase-8--crescimento--features-avançadas-meses-8-12)
12. [Dependências Técnicas](#12-dependências-técnicas)
13. [Riscos & Mitigações](#13-riscos--mitigações)
14. [Métricas de Sucesso por Fase](#14-métricas-de-sucesso-por-fase)
15. [Orçamento & Recursos](#15-orçamento--recursos)

---

## 1. Visão Estratégica

### Posicionamento vs. Concorrência

```
                    Individual ←─────────────────→ Equipa
                         │                            │
  Leetify (€6/mês) ●    │                            │
                         │                            │
  Scope.gg ●             │                            │
             Stats       │        ● NÓS              │
             simples     │     (AI + €39-129/mês)     │
                         │                            │
  StatTrak.xyz (€0) ●   │                  ● Skybox   │
                         │               (€350-1299/mês)
                    ─────┼────────────────────────────
                    Descritivo              Preditivo
```

### Vantagens Competitivas a Implementar (por ordem de prioridade)

| # | Vantagem | Skybox Tem? | Impacto | Esforço |
|---|----------|-------------|---------|---------|
| 1 | Error detection com explicações SHAP | Não | Crítico | Alto |
| 2 | Preço 7x inferior para equipas | N/A | Alto | Baixo |
| 3 | Demos pro pré-carregadas + já analisadas | Sim (sem AI) | Alto | Médio |
| 4 | Planos de treino personalizados | Não | Alto | Alto |
| 5 | Previsão tática (próximo round) | Não | Muito Alto | Muito Alto |
| 6 | Scout reports automáticos | Parcial (manual) | Alto | Alto |
| 7 | Explicabilidade transparente (SHAP/IG) | Não | Médio | Médio |

### Princípio Orientador

**Lançar rápido com 1 modelo ML (positioning errors) + demos pro pré-carregadas.**
Iterar com base em feedback real. Não construir os 7 modelos ML antes de ter utilizadores pagantes.

---

## 2. Fases de Implementação

```
Sem 1-4     ████ Fase 0: Validação (landing page + entrevistas)
Sem 5-8     ████ Fase 1: Fundação técnica (infra + DB + auth)
Sem 9-16    ████████ Fase 2: MVP Core (upload + parse + stats)
Sem 13-18   ██████ Fase 3: Pipeline demos pro (paralelo)
Sem 14-20   ███████ Fase 4: ML Error Detection (paralelo)
Sem 17-22   ██████ Fase 5: Frontend completo
Sem 23-26   ████ Fase 6: Beta fechado (10-20 equipas)
Sem 27-30   ████ Fase 7: Soft launch (durante Major)
Mês 8-12    ████████████████ Fase 8: Crescimento + features avançadas
```

**Timeline total**: ~12 meses (validação → escala)
**Tempo até MVP funcional**: ~5 meses (20 semanas)
**Tempo até primeiro utilizador pagante**: ~6.5 meses (26 semanas)

---

## 3. Fase 0 — Validação de Mercado (Semanas 1-4)

### Objetivo
Confirmar que alguém quer pagar ANTES de escrever código.

### Sprint 0.1 (Semana 1-2): Landing Page

**Deliverables:**
- Landing page em Next.js + Vercel (ou Framer/Carrd)
- Mockups/screenshots do produto (Figma)
- Formulário "Join Beta" (email capture)
- Página de pricing com tiers visíveis

**Conteúdo da landing page:**
```
Hero: "AI que deteta os teus erros em CS2 — e explica como corrigir"
Secção 1: Exemplo visual de error detection (mockup)
  → "Round 14: Exposto a 2 ângulos em A-site. device segura de ticket booth."
Secção 2: Features (error detection, heatmaps, scout reports)
Secção 3: Pricing (Free €0 / Solo €9 / Team €39 / Pro €129)
Secção 4: "Join Beta" CTA
Footer: Stack técnico (builds credibility)
```

**Tech stack landing:**
- Next.js 15 + Tailwind CSS + shadcn/ui (reutilizável para o produto)
- Vercel hosting (free tier)
- Resend ou SendGrid para email capture
- Plausible/Umami para analytics (privacy-first)

### Sprint 0.2 (Semana 3-4): Distribuição & Entrevistas

**Canais de distribuição:**
| Canal | Ação | Meta |
|-------|------|------|
| Reddit r/cs2 | Post: "Building AI that explains WHY you lose rounds" | 50+ upvotes |
| Reddit r/LearnCSGO | Post educativo sobre análise de posicionamento | 30+ upvotes |
| HLTV forums | Thread sobre ferramenta de AI analytics | Engagement |
| Discord FACEIT PT/BR | Partilha direta nos hubs | 20+ signups |
| Discord GamersClub | Comunidade brasileira | 20+ signups |
| Twitter/X | Clips de mockups de análise AI | 10+ retweets |

**Entrevistas (10-15 pessoas):**
- Coaches de equipas semi-pro (FACEIT Level 8-10)
- Analistas de equipas Tier 2-3
- IGL (In-Game Leaders) de equipas amadoras
- Perguntas-chave:
  1. "Que ferramentas de análise usas? Quanto pagas?"
  2. "Quanto tempo gastas a rever demos por semana?"
  3. "O que falta nas ferramentas atuais?"
  4. "Pagarias €39/mês por error detection com explicações?"
  5. "O que te faria mudar do Skybox/Leetify?"

### Critério Go/No-Go

| Sinal | Go ✅ | Repensar ⚠️ | No-Go ❌ |
|-------|-------|-------------|----------|
| Emails recolhidos | >200 | 50-200 | <50 |
| "Pagaria €39/mês?" | >40% sim | 20-40% | <20% |
| Entrevistas positivas | >70% | 40-70% | <40% |
| Reddit engagement | >100 upvotes total | 30-100 | <30 |

### Custo Fase 0: ~€0 (apenas tempo)

---

## 4. Fase 1 — Fundação Técnica (Semanas 5-8)

### Objetivo
Setup completo de infraestrutura, CI/CD, base de dados, e autenticação.

### Sprint 1.1 (Semana 5-6): Infraestrutura Base

**4.1.1 Monorepo Setup**

```
cs2-analytics/
├── packages/
│   ├── backend/          # FastAPI (Python 3.12+)
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── models/          # SQLAlchemy models
│   │   │   ├── schemas/         # Pydantic schemas
│   │   │   ├── routers/         # API endpoints
│   │   │   ├── services/        # Business logic
│   │   │   ├── tasks/           # Celery tasks
│   │   │   └── middleware/      # Auth, CORS, RLS
│   │   ├── tests/
│   │   ├── alembic/             # DB migrations
│   │   └── pyproject.toml
│   │
│   ├── frontend/         # Next.js 15
│   │   ├── src/
│   │   │   ├── app/             # App Router pages
│   │   │   ├── components/      # React components
│   │   │   ├── lib/             # Utilities, API client
│   │   │   └── hooks/           # Custom hooks
│   │   ├── public/
│   │   └── package.json
│   │
│   ├── demo-parser/      # Awpy wrapper
│   │   ├── src/
│   │   └── pyproject.toml
│   │
│   ├── ml-models/        # PyTorch models
│   │   ├── src/
│   │   │   ├── positioning/     # Modelo A: Mamba
│   │   │   ├── utility/         # Modelo B: LightGBM
│   │   │   ├── timing/          # Modelo C: Mamba
│   │   │   ├── strategy/        # Modelo D: GraphSAGE
│   │   │   ├── prediction/      # Modelo E: Transformer
│   │   │   ├── rating/          # Modelo F: CatBoost
│   │   │   ├── weakness/        # Modelo G: HDBSCAN
│   │   │   └── explainability/  # SHAP + IG
│   │   └── pyproject.toml
│   │
│   ├── feature-engine/   # Feature extraction
│   │   ├── src/
│   │   └── pyproject.toml
│   │
│   └── pro-demo-ingester/ # Pipeline demos pro (Fase 3)
│       ├── src/
│       └── pyproject.toml
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   ├── Dockerfile.ml-serving
│   │   └── Dockerfile.demo-ingester
│   ├── terraform/           # IaC AWS
│   └── docker-compose.yml   # Dev local
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── turbo.json              # Turborepo config
├── pnpm-workspace.yaml
└── README.md
```

**Tarefas:**

| Tarefa | Descrição | Tempo |
|--------|-----------|-------|
| Monorepo init | pnpm workspace + Turborepo + uv | 2h |
| Docker Compose | PostgreSQL 16 + ClickHouse 24 + Redis 7 + MinIO | 3h |
| Backend skeleton | FastAPI app + config + health endpoint | 4h |
| Frontend skeleton | Next.js 15 App Router + Tailwind + shadcn/ui | 4h |
| CI pipeline | GitHub Actions (lint + type-check + test) | 4h |
| Linting/formatting | Ruff (Python) + ESLint + Prettier (TS) | 2h |

**4.1.2 Bases de Dados (Setup Local)**

PostgreSQL 16:
```sql
-- Executar schema do doc 04-database-schema.md
-- Tabelas prioritárias para MVP:
-- organizations, users, refresh_tokens, invitations
-- teams, team_players
-- demos, matches, rounds
-- detected_errors (para Fase 4)
```

ClickHouse:
```sql
-- Tabelas para dados de tick e eventos
-- tick_data (15M rows/match)
-- events (5K rows/match)
-- player_round_stats (materialized view)
```

Redis 7:
```
-- Celery broker
-- Session cache
-- Rate limiting
-- Feature store (futuro)
```

### Sprint 1.2 (Semana 7-8): Autenticação & Multi-Tenancy

**4.2.1 Sistema de Auth (conforme doc 05 e 08)**

| Endpoint | Descrição |
|----------|-----------|
| `POST /auth/register` | Criar org + admin user |
| `POST /auth/login` | Login → JWT access + refresh tokens |
| `POST /auth/refresh` | Renovar access token |
| `POST /auth/logout` | Invalidar refresh token |
| `POST /auth/invite` | Convidar membro para org |
| `POST /auth/accept-invite/:token` | Aceitar convite |

**Implementação:**
- JWT (access token: 1h, refresh: 30d)
- Password hashing: argon2
- Rate limiting: 5 tentativas login/min
- CORS configurado para frontend domain

**4.2.2 Row-Level Security (RLS)**

```sql
-- Cada query filtrada por org_id do utilizador autenticado
-- Middleware FastAPI injeta org_id no contexto
-- Previne acesso cross-tenant

ALTER TABLE demos ENABLE ROW LEVEL SECURITY;
CREATE POLICY demos_org_isolation ON demos
    USING (org_id = current_setting('app.current_org_id')::uuid);
```

**4.2.3 Frontend Auth**

| Componente | Descrição |
|-----------|-----------|
| Login page | Email + password form |
| Register page | Org name + admin credentials |
| Auth context | Zustand store com tokens + user info |
| Protected routes | Middleware Next.js para rotas autenticadas |
| API client | Fetch wrapper com auto-refresh de tokens |

### Deliverables Fase 1
- [ ] Monorepo funcional com dev environment local
- [ ] PostgreSQL + ClickHouse + Redis a correr via Docker Compose
- [ ] Backend FastAPI com health check + auth completo
- [ ] Frontend Next.js com login/register/dashboard skeleton
- [ ] CI pipeline verde (lint + types + testes unitários básicos)
- [ ] Deploy pipeline para staging (AWS ECS Fargate)

### Custo Fase 1: ~€50 (domínio + staging AWS mínimo)

---

## 5. Fase 2 — MVP Core (Semanas 9-16)

### Objetivo
Upload de demos, parsing, stats básicas, e dashboard funcional.

### Sprint 2.1 (Semana 9-10): Upload & Parsing Pipeline

**5.1.1 Upload de Demos**

```
Utilizador → Upload .dem → Validação → S3 → Celery Task → Awpy Parse → DB
                                                    │
                                                    ├→ PostgreSQL (metadata, rounds, kills)
                                                    ├→ ClickHouse (tick data, events)
                                                    └→ SSE update (status ao frontend)
```

| Endpoint | Descrição |
|----------|-----------|
| `POST /api/v1/demos/upload` | Upload demo file (multipart) |
| `GET /api/v1/demos/:id/status` | SSE stream de status de processamento |
| `GET /api/v1/demos` | Listar demos da org (paginado) |
| `DELETE /api/v1/demos/:id` | Remover demo |

**Validações no upload:**
- Magic bytes: verifica que é ficheiro .dem válido
- Tamanho: <500 MB
- Formato: CS2 (não CS:GO)
- Quota: verifica limite de demos/mês do tier
- Duplicação: hash SHA256 para evitar duplicados

**5.1.2 Celery Task — Demo Processing**

```python
# packages/backend/src/tasks/demo_processing.py

@celery.task(bind=True, max_retries=3)
def process_demo(self, demo_id: str, s3_key: str):
    """
    Pipeline completo de processamento de demo.

    Etapas:
    1. Download do S3
    2. Parse com Awpy
    3. Extrair metadata (mapa, equipas, jogadores)
    4. Armazenar rounds + kills + damages em PostgreSQL
    5. Armazenar tick data + events em ClickHouse
    6. Calcular stats agregadas (KD, ADR, HS%, KAST)
    7. Atualizar status → "completed"
    8. Enviar SSE notification

    Se ML models disponíveis (Fase 4+):
    9. Extrair features para ML
    10. Executar inferência (error detection)
    11. Armazenar resultados em detected_errors
    """
```

**5.1.3 Wrapper Awpy**

```python
# packages/demo-parser/src/parser.py

from awpy import Demo

class DemoParser:
    def parse(self, file_path: str) -> ParsedDemo:
        demo = Demo(file_path)
        return ParsedDemo(
            header=demo.header,       # mapa, servidor, data
            rounds=demo.rounds,       # resumo por round
            kills=demo.kills,         # todas as eliminações
            damages=demo.damages,     # todos os danos
            grenades=demo.grenades,   # todas as granadas
            ticks=demo.ticks,         # posições tick-a-tick (15M rows)
        )
```

### Sprint 2.2 (Semana 11-12): Stats & Scoreboard

**5.2.1 Stats Calculadas por Match**

| Stat | Fórmula | Granularidade |
|------|---------|---------------|
| KD Ratio | kills / deaths | Por jogador, por match |
| ADR | total_damage / rounds_played | Por jogador, por match |
| HS% | headshot_kills / total_kills × 100 | Por jogador, por match |
| KAST% | rounds com (Kill OR Assist OR Survived OR Traded) / total | Por jogador, por match |
| Opening Duel Win% | opening_kills / (opening_kills + opening_deaths) × 100 | Por jogador |
| Clutch Win% | clutches_won / clutches_attempted × 100 | Por jogador |
| Flash Assists | assists via flash blindness | Por jogador |
| Utility Damage | dano de granadas (HE + molotov) | Por jogador |
| Economy Rating | equipment_value efficiency | Por round |

**5.2.2 Endpoints Stats**

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/v1/matches/:id` | Match overview (mapa, score, equipas) |
| `GET /api/v1/matches/:id/scoreboard` | Scoreboard detalhado |
| `GET /api/v1/matches/:id/rounds` | Round-by-round breakdown |
| `GET /api/v1/matches/:id/economy` | Economia por round |
| `GET /api/v1/matches/:id/kills` | Feed de kills com detalhes |
| `GET /api/v1/players/:steamId/stats` | Stats agregadas do jogador |

### Sprint 2.3 (Semana 13-14): Dashboard Frontend

**5.3.1 Páginas do MVP**

| Página | Rota | Componentes |
|--------|------|-------------|
| Dashboard | `/` | Resumo: últimos demos, stats rápidas, equipa |
| Upload | `/upload` | Drag & drop zone, progress bar, status SSE |
| Match List | `/matches` | Tabela paginada, filtros (mapa, data, resultado) |
| Match Overview | `/matches/:id` | Tabs: Overview, Scoreboard, Economy, Rounds |
| Match Scoreboard | `/matches/:id/scoreboard` | Tabela com todas as stats |
| Match Economy | `/matches/:id/economy` | Gráfico Recharts de economia por round |
| Match Rounds | `/matches/:id/rounds` | Timeline de rounds com resultado e compra |

**5.3.2 Componentes UI Core**

```
components/
├── ui/                    # shadcn/ui (button, card, table, tabs, badge, skeleton)
├── layout/
│   ├── sidebar.tsx        # Navegação principal
│   ├── header.tsx         # Barra superior + user menu
│   └── processing-queue.tsx # Bottom bar: demos em processamento
├── matches/
│   ├── match-card.tsx     # Card de match na lista
│   ├── scoreboard.tsx     # Tabela de scoreboard
│   ├── economy-chart.tsx  # Gráfico de economia (Recharts)
│   └── round-timeline.tsx # Timeline visual de rounds
├── upload/
│   ├── dropzone.tsx       # Drag & drop upload
│   └── progress.tsx       # Barra de progresso com SSE
└── players/
    └── player-stats.tsx   # Stats card de jogador
```

### Sprint 2.4 (Semana 15-16): Heatmaps & 2D Replayer (Básico)

**5.4.1 Heatmaps**

```
Endpoint: GET /api/v1/matches/:id/heatmap?type=kills&player=steamId&side=ct

Tipos:
- kills: onde os kills acontecem
- deaths: onde os jogadores morrem
- positions: density de posicionamento

Implementação:
- Backend: query ClickHouse aggregada por zonas do mapa
- Frontend: Canvas overlay sobre imagem do mapa (D3.js)
- Filtros: por jogador, por lado (T/CT), por round type
```

**5.4.2 2D Replayer (Versão Básica)**

```
Endpoint: GET /api/v1/matches/:id/replay?round=14

Dados: tick data filtrado por round (64 ticks/seg × 10 jogadores)

Implementação:
- Canvas API para rendering (mais performante que SVG)
- 10 player dots com cores T/CT
- Posições tick-a-tick com interpolação
- Play/pause/speed controls
- Timeline scrub bar
- Ícones de granadas e kills

Nota: Versão avançada (smokes, flashes, tracers) na Fase 8
```

### Deliverables Fase 2
- [ ] Upload de demos funcional (drag & drop → S3 → parse)
- [ ] Parsing automático com Awpy (tick data → ClickHouse)
- [ ] Stats completas por match (KD, ADR, HS%, KAST, etc.)
- [ ] Dashboard com lista de matches + scoreboard + economy chart
- [ ] Heatmaps básicos (kills, deaths)
- [ ] 2D Replayer básico (posições, play/pause)
- [ ] SSE para status de processamento em tempo real
- [ ] Testes de integração para pipeline completo

### Custo Fase 2: ~€300/mês (AWS staging)

---

## 6. Fase 3 — Pipeline de Demos Pro (Semanas 13-18)

### Objetivo
Ter todas as demos profissionais pré-carregadas e analisadas na plataforma, eliminando a maior desvantagem face ao Skybox.

> **NOTA**: Esta fase corre em paralelo com a Fase 2 (sprints 2.3-2.4) e Fase 4.

### 6.1 Fontes de Demos & Estratégia Legal

| Fonte | Tipo de Demos | Método | Legalidade |
|-------|--------------|--------|------------|
| **HLTV.org** | Pro Tier 1-3 (~95%) | Scraper | ToS proíbem scraping; parceria formal ideal |
| **FACEIT API** | Semi-pro ranked | Downloads API oficial | Legal (requer aplicação, ~30 dias) |
| **Steam GC** | Valve MM (dos nossos users) | cs-demo-downloader | Legal (conta própria) |
| **Torneios** | Demos de eventos | Via HLTV | Mesmo que HLTV |

### 6.2 Ações Legais Imediatas

**Semana 13:**
1. **Enviar email ao HLTV** pedindo parceria/licença de acesso a demos
   - Proposta: "Creditamos HLTV em todos os demos, linkamos de volta, trazemos tráfego"
   - Contacto: business@hltv.org
   - Modelo: similar ao que Skybox tem (demo sponsorship)

2. **Submeter aplicação FACEIT Downloads API**
   - URL: https://fce.gg/downloads-api-application
   - Tempo de aprovação: ~30 dias
   - Contacto urgente: partnerships@faceit.com

3. **Enquanto aguardamos**: implementar scraper HLTV com rate limiting conservador

### 6.3 Implementação Técnica

**6.3.1 HLTV Scraper**

```python
# packages/pro-demo-ingester/src/hltv_scraper.py

class HLTVScraper:
    """
    Scraper de demos profissionais do HLTV.

    Rate limiting: 1 request cada 5 segundos
    User-Agent: header real de browser
    Retry: exponential backoff em 429/503
    Cloudflare: rotate user agents, respeitar rate limits
    """

    BASE_URL = "https://www.hltv.org"

    async def get_recent_matches(self, pages: int = 5) -> list[MatchInfo]:
        """Scrape match list das últimas páginas de resultados."""

    async def get_match_demo_id(self, match_id: int) -> int | None:
        """Extrair demo_id da página de match."""

    async def download_demo(self, demo_id: int, output_dir: str) -> str:
        """Download demo file (RAR/ZIP) → extrair .dem."""
```

**6.3.2 FACEIT Integration**

```python
# packages/pro-demo-ingester/src/faceit_client.py

class FACEITClient:
    """
    Cliente oficial FACEIT Downloads API.
    Requer bearer token com Downloads API scope.
    """

    async def get_match_demo_url(self, match_id: str) -> str:
        """POST /download/v2/demos/download → signed URL."""

    async def setup_webhook(self, callback_url: str):
        """Registar webhook 'Match Demo Ready'."""
```

**6.3.3 Pipeline de Ingestão Automática**

```
┌─────────────────┐
│  Celery Beat     │  Cron: cada 30 min
│  Scheduler       │
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
    ▼          ▼
┌────────┐ ┌────────┐
│ HLTV   │ │ FACEIT │
│Scraper │ │ API    │
└───┬────┘ └───┬────┘
    │          │
    ▼          ▼
┌──────────────────┐
│  Dedup Check     │  SHA256 hash + match_id
│  (PostgreSQL)    │
└────────┬─────────┘
         │ (novo demo)
         ▼
┌──────────────────┐
│  Download Worker │
│  - Download file │
│  - Validate .dem │
│  - Upload S3     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Parse Worker    │  (reutiliza pipeline Fase 2)
│  - Awpy parse    │
│  - ClickHouse    │
│  - PostgreSQL    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  ML Inference    │  (quando disponível, Fase 4+)
│  - Error detect  │
│  - Stats avançadas│
└──────────────────┘
```

**6.3.4 Schema para Demos Pro**

```sql
-- Nova tabela para metadata de demos pro
CREATE TABLE pro_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(20) NOT NULL CHECK (source IN ('hltv', 'faceit', 'valve')),
    source_match_id VARCHAR(100) NOT NULL,

    -- Match info
    team1_name VARCHAR(255) NOT NULL,
    team2_name VARCHAR(255) NOT NULL,
    team1_score INT,
    team2_score INT,
    map VARCHAR(50) NOT NULL,
    event_name VARCHAR(255),
    event_tier VARCHAR(10) CHECK (event_tier IN ('tier1', 'tier2', 'tier3', 'regional')),
    match_date TIMESTAMPTZ NOT NULL,

    -- Demo info
    demo_id UUID REFERENCES demos(id),
    demo_s3_key VARCHAR(500),
    demo_file_hash VARCHAR(64),  -- SHA256 dedup

    -- Processing status
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'downloading', 'parsing', 'analyzing', 'completed', 'failed')),
    error_message TEXT,

    -- ML analysis status
    ml_analyzed BOOLEAN NOT NULL DEFAULT false,
    ml_analyzed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (source, source_match_id)
);

CREATE INDEX idx_pro_matches_teams ON pro_matches(team1_name, team2_name);
CREATE INDEX idx_pro_matches_event ON pro_matches(event_name);
CREATE INDEX idx_pro_matches_date ON pro_matches(match_date DESC);
CREATE INDEX idx_pro_matches_status ON pro_matches(status);
```

**6.3.5 Frontend — Browse Pro Demos**

| Página | Rota | Funcionalidade |
|--------|------|----------------|
| Pro Matches | `/pro` | Lista de matches pro com filtros |
| Pro Match Detail | `/pro/:id` | Stats + análise AI (se disponível) |
| Team Browser | `/pro/teams/:name` | Todos os matches de uma equipa |
| Event Browser | `/pro/events/:name` | Todos os matches de um evento |

**Filtros disponíveis:**
- Por equipa (search autocomplete)
- Por evento/torneio
- Por mapa
- Por tier (1, 2, 3)
- Por data (range picker)
- Por estado de análise AI (analisado / pendente)

### 6.4 Volume & Custos

| Métrica | Valor |
|---------|-------|
| Matches pro/semana | ~50-100 |
| Tamanho médio demo | ~100 MB |
| Storage mensal (S3) | ~40 GB |
| ClickHouse (parsed) | ~800 GB/mês |
| Custo S3 | ~€1/mês |
| Custo ClickHouse extra | ~€50-100/mês |
| Bandwidth download | ~€5/mês |
| **Total adicional** | **~€55-105/mês** |

### 6.5 Diferenciação vs. Skybox

| Aspeto | Skybox | Nós |
|--------|--------|-----|
| Demos pro disponíveis | Sim | Sim (após Fase 3) |
| Delay no free tier | 1 mês | Sem delay (todos os tiers) |
| Análise AI dos demos pro | Não | **Sim** — error detection, stats avançadas |
| Scout data pré-processada | Manual | **Automático** — base para scout reports |

**Killer feature**: Quando o utilizador abre um demo pro, já tem **análise AI completa** — erros detetados, stats avançadas, heatmaps. O Skybox só mostra o replay e stats básicas.

### Deliverables Fase 3
- [ ] HLTV scraper funcional com rate limiting
- [ ] FACEIT API integration (quando aprovada)
- [ ] Pipeline automático: scrape → download → parse → store
- [ ] Scheduler Celery Beat (cada 30 min)
- [ ] Schema pro_matches com deduplicação
- [ ] Frontend: browse pro matches com filtros
- [ ] Backfill: últimos 3 meses de demos Tier 1-2 (~600 demos)
- [ ] Email enviado ao HLTV para parceria
- [ ] Aplicação FACEIT submetida

---

## 7. Fase 4 — ML Error Detection (Semanas 14-20)

### Objetivo
Implementar o primeiro modelo ML: deteção de erros de posicionamento com explicações SHAP. Este é o **principal diferenciador** face a toda a concorrência.

> **NOTA**: Corre em paralelo com Fases 2-3. Requer dataset de treino (demos pro da Fase 3).

### 7.1 Dataset de Treino

**Fonte:** Demos pro processados na Fase 3 + dados públicos

| Dataset | Demos | Uso |
|---------|-------|-----|
| Demos pro (Fase 3 backfill) | ~600 | Treino principal |
| PureSkill.gg CSDS (Kaggle) | ~1,000+ | Suplementar |
| Demos da beta (Fase 6) | ~100-200 | Validação |

**Labeling Strategy:**
```
Semi-supervised approach:
1. Regras heurísticas para gerar labels automáticos:
   - angles_exposed > 2 AND distance_to_cover > threshold → positioning_error
   - Morte em <2s após peek sem info → bad_peek
   - Flash thrown with 0 enemies flashed → utility_error

2. Validação manual de ~500 exemplos por analista CS2
   - Contratar 2-3 analistas FACEIT level 10 (freelance)
   - Interface de labeling: Streamlit app simples
   - Budget: ~€500-1000

3. Pro player data como "ground truth positivo"
   - Posições de jogadores pro = exemplos de "bom posicionamento"
   - Desvios significativos = potenciais erros
```

### 7.2 Modelo A: Positioning Errors (Mamba)

**Arquitetura (conforme doc 02):**

```
Input: (batch, 64 ticks, 18 features)
         │
         ▼
┌─────────────────┐
│   Mamba Block    │  d_model=64, d_state=16, d_conv=4
│   (SSM Layer)    │  Complexidade: O(n) vs O(n²) LSTM
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Mamba Block    │  d_model=64
│   (SSM Layer)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Global Pool     │  Average pooling temporal
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   MLP Head       │  64 → 32 → 3 classes
│   + Softmax      │  (safe, minor_error, critical_error)
└────────┬────────┘
         │
         ▼
Output: {class, confidence, severity}
```

**Features de input (18 dimensões):**
```
Posição:        x, y, z                           (3)
Orientação:     yaw, pitch                         (2)
Movimento:      velocity                           (1)
Estado:         health, armor, weapon_id, is_scoped (4)
Contexto:       teammates_alive, enemies_alive,    (4)
                bomb_state, round_time_remaining
Posicionamento: nearest_teammate_dist,             (2)
                nearest_enemy_dist_estimated
Qualidade:      angles_exposed_count,              (2)
                distance_to_nearest_cover
```

**Hyperparameters:**
```python
config = {
    "d_model": 64,
    "d_state": 16,
    "d_conv": 4,
    "n_layers": 2,
    "dropout": 0.1,
    "learning_rate": 1e-3,
    "batch_size": 256,
    "epochs": 50,
    "optimizer": "AdamW",
    "scheduler": "CosineAnnealing",
    "loss": "FocalLoss",  # class imbalance (muito mais "safe" que "error")
}
```

### 7.3 Motor de Explicabilidade

**Para Mamba (neural network) → Integrated Gradients:**

```python
# packages/ml-models/src/explainability/integrated_gradients.py

from captum.attr import IntegratedGradients

class PositioningExplainer:
    """
    Gera explicações para cada erro detetado.
    Latência target: <10ms por explicação.

    Output: top-5 features mais influentes + magnitude + direção
    Exemplo: "angles_exposed_count (+0.42), distance_to_cover (+0.31), ..."
    """

    def explain(self, model, input_tensor) -> Explanation:
        ig = IntegratedGradients(model)
        attributions = ig.attribute(input_tensor, n_steps=50)
        # Agregar attributions temporais → feature importance
        return self._format_explanation(attributions)
```

**Template de Recomendação:**

```python
# Mapear explicação ML → texto actionable para o jogador

RECOMMENDATION_TEMPLATES = {
    "angles_exposed": {
        "high": "Estavas exposto a {n} ângulos simultaneamente em {position}. "
                "Move para {nearest_cover} para limitar a 1-2 ângulos.",
        "pro_reference": "{pro_player} segura esta posição de {safe_position} "
                        "nesta mesma situação.",
    },
    "distance_to_cover": {
        "high": "Estavas a {distance}m da cover mais próxima em {position}. "
                "Joga mais perto de {nearest_cover} para ter retreat option.",
    },
    "isolated_position": {
        "high": "Sem teammate a menos de {distance}m. "
                "Coordena com {nearest_teammate} para crossfire.",
    },
}
```

### 7.4 Pipeline de Inferência

```
Demo processado (Fase 2)
         │
         ▼
┌─────────────────────┐
│  Feature Extraction  │  Extrair janelas de 64 ticks
│  (feature-engine)    │  por jogador, por round
└────────┬────────────┘
         │ ~3000 janelas/match
         ▼
┌─────────────────────┐
│  Mamba Inference     │  Batch inference via BentoML
│  (ml-models)         │  GPU ou CPU (Fargate)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Explanation Gen     │  Integrated Gradients
│  (explainability)    │  <10ms por erro
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Recommendation Gen  │  Template matching
│  (recommendations)   │  + pro player reference
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Store Results       │  PostgreSQL: detected_errors
│  (database)          │  + error_explanations
└─────────────────────┘
```

**Latência target (match completo):**
- Feature extraction: ~30s
- Mamba inference (3000 windows): ~60s (GPU), ~180s (CPU)
- Explanations: ~30s
- **Total: <5 min** (dentro do tempo de parsing)

### 7.5 Treino & MLflow

```python
# packages/ml-models/src/positioning/train.py

import mlflow
import torch

def train_positioning_model(config: dict):
    mlflow.set_experiment("positioning-errors-v1")

    with mlflow.start_run():
        mlflow.log_params(config)

        model = MambaPositioningModel(config)
        trainer = Trainer(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            loss_fn=FocalLoss(alpha=0.25, gamma=2.0),
            optimizer=AdamW(model.parameters(), lr=config["lr"]),
        )

        metrics = trainer.train(epochs=config["epochs"])

        mlflow.log_metrics({
            "val_precision": metrics.precision,
            "val_recall": metrics.recall,
            "val_f1": metrics.f1,
            "val_auc": metrics.auc,
        })

        # Target: precision > 85%, recall > 70%
        mlflow.pytorch.log_model(model, "model")
```

**Treino em AWS:**
- Instance: g5.xlarge spot (~€0.50/hora)
- Tempo estimado: ~4-6 horas por treino completo
- Budget: ~€50-100 total para experimentação

### Deliverables Fase 4
- [ ] Dataset de treino preparado (~5000 demos parsed)
- [ ] Labels semi-automáticos + ~500 labels manuais validados
- [ ] Modelo Mamba treinado (precision >85%)
- [ ] Motor de explicabilidade (Integrated Gradients)
- [ ] Sistema de recomendações (templates)
- [ ] Pipeline de inferência integrado no processing pipeline
- [ ] MLflow tracking de experiências
- [ ] Testes unitários + integration tests para ML pipeline
- [ ] BentoML serving configurado

---

## 8. Fase 5 — Frontend Completo (Semanas 17-22)

### Objetivo
Interface completa com error analysis, heatmaps interativos, e experiência polida para beta.

### Sprint 5.1 (Semana 17-18): Error Analysis UI

**8.1.1 Página de Erros (`/matches/:id/errors`)**

```
┌─────────────────────────────────────────────────────┐
│  Match: Team A vs Team B — Mirage                    │
│  Tabs: Overview | Errors ← | Tactics | Economy | Replay │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐  ┌──────────────────────────────┐  │
│  │  MAPA 2D    │  │  Error Details               │  │
│  │             │  │                              │  │
│  │  ● erro #1  │  │  Round 14 — 1:23            │  │
│  │  ● erro #2  │  │  Player: s1mple             │  │
│  │  ● erro #3  │  │  Type: Positioning Error     │  │
│  │             │  │  Severity: Critical ⬤        │  │
│  │  [filtros]  │  │                              │  │
│  │  □ Critical │  │  "Exposto a 3 ângulos em     │  │
│  │  □ Major    │  │  A-ramp. Move para ticket    │  │
│  │  □ Minor    │  │  booth para limitar a 1."    │  │
│  │             │  │                              │  │
│  └─────────────┘  │  ┌─── SHAP Waterfall ─────┐ │  │
│                    │  │ angles_exposed ████ +0.42│ │  │
│  Round filter:     │  │ dist_to_cover  ███ +0.31│ │  │
│  [All ▼]          │  │ teammate_dist  ██ +0.18 │ │  │
│                    │  │ velocity       █ -0.08  │ │  │
│  Player filter:    │  └─────────────────────────┘ │  │
│  [All ▼]          │                              │  │
│                    │  Pro Reference:              │  │
│  Summary:          │  "device segura de behind    │  │
│  12 errors found   │  boxes nesta situação"       │  │
│  5 critical        │  [Ver clip ▶]               │  │
│  4 major           │                              │  │
│  3 minor           │                              │  │
│                    └──────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Componentes:**

| Componente | Descrição | Lib |
|-----------|-----------|-----|
| `ErrorMap` | Mapa 2D com markers de erros clicáveis | Canvas + D3 |
| `ErrorDetail` | Painel lateral com detalhes do erro | shadcn/ui |
| `ShapWaterfall` | Gráfico waterfall de feature importance | D3.js custom |
| `ErrorSummary` | Cards resumo (total, por severidade) | shadcn/ui |
| `ErrorFilters` | Filtros por round, jogador, severidade, tipo | shadcn/ui |
| `ProReference` | Card com referência a jogador pro | shadcn/ui |

### Sprint 5.2 (Semana 19-20): Heatmaps Interativos & Replayer Avançado

**8.2.1 Heatmaps Interativos**

```
Melhorias sobre o básico da Fase 2:
- Toggle entre kill/death/position heatmaps
- Filtro por jogador individual
- Filtro por lado (T/CT)
- Filtro por round type (eco, force, full buy)
- Overlay de erros detetados
- Animação temporal (evolução por round)
- Export como imagem PNG
```

**8.2.2 2D Replayer Avançado**

```
Melhorias sobre o básico da Fase 2:
- Rendering de smokes (circles com fade)
- Rendering de flashes (flash indicator)
- Rendering de molotovs (fire area)
- Kill feed lateral
- Player names + health bars
- Weapon icons
- Bomb plant/defuse indicators
- Speed controls (0.25x, 0.5x, 1x, 2x, 4x)
- Round selector dropdown
- Minimap awareness indicators
- Click em jogador → highlight path
```

### Sprint 5.3 (Semana 21-22): Player Profiles & Settings

**8.3.1 Player Profile (`/players/:steamId`)**

```
┌──────────────────────────────────────┐
│  Player: NiKo                         │
│  Team: G2 Esports                     │
├──────────────────────────────────────┤
│                                       │
│  ┌──── Radar Chart ─────┐  Stats:    │
│  │     Aim: 87          │  KD: 1.23  │
│  │   /        \         │  ADR: 82.1 │
│  │  Util    Positioning │  HS%: 54%  │
│  │   \        /         │  KAST: 71% │
│  │    Game Sense        │            │
│  └──────────────────────┘            │
│                                       │
│  Recent Matches:                      │
│  [Match cards with individual stats]  │
│                                       │
│  Error Trends (últimos 10 matches):   │
│  [Line chart: errors over time]       │
│                                       │
│  Common Errors:                       │
│  1. Positioning on A-site (34%)       │
│  2. Aggressive peeks without info (28%)│
│  3. Late rotations (18%)              │
└──────────────────────────────────────┘
```

**8.3.2 Settings**

| Página | Funcionalidade |
|--------|----------------|
| `/settings` | Nome da org, logo, timezone |
| `/settings/team` | Roster management, convites |
| `/settings/billing` | Tier atual, upgrade (Stripe Checkout) |

**Stripe Integration:**
- Stripe Checkout para upgrade de tier
- Stripe Customer Portal para gestão de subscription
- Webhook handler para eventos de pagamento
- Proration automática em upgrades/downgrades

### Deliverables Fase 5
- [ ] Error analysis page completa com SHAP waterfall
- [ ] Heatmaps interativos com todos os filtros
- [ ] 2D Replayer avançado (smokes, flashes, molotovs, kill feed)
- [ ] Player profiles com radar chart e error trends
- [ ] Settings com team management
- [ ] Stripe integration para billing
- [ ] Responsive design (tablet-friendly para coaches)
- [ ] Loading states, error boundaries, empty states
- [ ] Testes E2E (Playwright) para fluxos críticos

---

## 9. Fase 6 — Beta Fechado (Semanas 23-26)

### Objetivo
Validar o produto com 10-20 equipas reais. Recolher feedback. Corrigir bugs. Confirmar product-market fit.

### 9.1 Recrutamento de Beta Testers

**Target: 10-20 equipas, maioritariamente PT/BR**

| Canal | Ação | Target |
|-------|------|--------|
| Discord FACEIT PT | "Procuramos equipas para beta de AI analytics grátis" | 5 equipas |
| Discord GamersClub | Mesmo approach, comunidade BR | 5 equipas |
| Lista de emails (Fase 0) | Email a top signups | 5 equipas |
| Contacto direto | DMs a coaches conhecidos | 3-5 equipas |
| Reddit r/cs2 | Update post sobre o produto | 2-3 equipas |

**Critérios de seleção:**
- Equipa organizada (5 jogadores + coach ou IGL)
- Jogam pelo menos 3-4 matches/semana
- Dispostos a dar feedback regular (1 call/semana de 15 min)
- Mix de níveis: FACEIT Level 5-7 (amateur) e 8-10 (semi-pro)

**Incentivo:**
- Acesso grátis ao tier Team durante beta
- 3 meses grátis de tier Team após launch se derem feedback útil
- Crédito no site como "Beta Testers"

### 9.2 Processo de Beta

**Semana 23-24: Onboarding**
```
1. Setup de conta + equipa para cada beta tester
2. Call individual de onboarding (30 min)
3. Guia de "getting started" (upload primeiro demo)
4. Canal Discord privado para beta testers
5. Formulário de feedback inicial (expectations)
```

**Semana 24-25: Uso Ativo**
```
1. Beta testers usam a plataforma normalmente
2. Monitorizar métricas de uso (Mixpanel/PostHog):
   - Demos uploaded/equipa/semana
   - Páginas mais visitadas
   - Tempo por sessão
   - Features mais usadas
   - Erros/crashes
3. Bug reports via Discord + form
4. Call semanal de feedback (15 min/equipa)
```

**Semana 25-26: Iteração**
```
1. Compilar feedback → priorizar fixes/features
2. Sprint de correções (bugs críticos + UX issues)
3. Implementar top 3 pedidos dos beta testers
4. Survey final de NPS + willingness-to-pay
5. Decisão go/no-go para launch
```

### 9.3 Métricas da Beta

| Métrica | Bom Sinal ✅ | Red Flag ❌ |
|---------|-------------|------------|
| Demos uploaded/equipa/semana | >2 | <1 |
| Return visits/semana | >2 | 0-1 |
| Tempo por sessão | >10 min | <3 min |
| Error analysis page views | >60% dos users | <20% |
| "Isto ajudou a melhorar?" | >60% sim | <30% |
| "Pagariam €39/mês?" | >40% sim | <15% |
| NPS | >40 | <10 |
| Bugs críticos encontrados | <10 | >30 |

### 9.4 Critério Go/No-Go para Launch

| Critério | Go ✅ | Delay ⚠️ | Pivot ❌ |
|----------|-------|----------|---------|
| NPS beta | >30 | 10-30 | <10 |
| "Pagaria €39?" | >40% | 20-40% | <20% |
| Demos/equipa/semana | >2 | 1-2 | <1 |
| Bugs críticos restantes | 0 | 1-3 | >5 |
| Error detection useful? | >50% | 30-50% | <30% |

### Deliverables Fase 6
- [ ] 10-20 equipas onboarded e ativas
- [ ] Canal Discord de beta com comunicação regular
- [ ] Relatório de métricas da beta
- [ ] Top bugs corrigidos
- [ ] Top 3 feature requests implementados
- [ ] Survey NPS + willingness-to-pay completado
- [ ] Decisão go/no-go documentada

---

## 10. Fase 7 — Soft Launch (Semanas 27-30)

### Objetivo
Lançamento público. Primeiros utilizadores pagantes. Timing: durante Major CS2 (IEM Cologne Junho 2026 ou PGL Singapore Novembro 2026).

### 10.1 Pre-Launch Checklist

**Infraestrutura:**
- [ ] Produção AWS estável (ECS Fargate, RDS, ClickHouse Cloud)
- [ ] CDN (CloudFront) configurado
- [ ] WAF com regras OWASP
- [ ] Monitoring: Sentry + CloudWatch + Grafana
- [ ] Alertas PagerDuty para incidentes críticos
- [ ] Backup automático PostgreSQL + ClickHouse
- [ ] Load testing: suporta 50 uploads simultâneos
- [ ] SSL/TLS em todos os endpoints

**Produto:**
- [ ] Onboarding flow polido (register → upload → primeiro resultado)
- [ ] Email transacional (welcome, demo processed, weekly digest)
- [ ] Stripe billing funcional (upgrade/downgrade/cancel)
- [ ] Legal: Terms of Service, Privacy Policy, Cookie consent
- [ ] Help center / FAQ (Notion ou GitBook)
- [ ] Página de pricing pública

**Marketing:**
- [ ] Landing page atualizada com screenshots reais
- [ ] 3 posts preparados (Reddit, HLTV, Twitter)
- [ ] 1 vídeo demo (2-3 min) no YouTube
- [ ] 2-3 clips curtos (30-60s) para TikTok/Twitter
- [ ] Product Hunt listing preparado

### 10.2 Estratégia de Launch

**Timing óptimo: durante Major CS2**
- Máximo interesse da comunidade em CS2
- Análise AI do Grand Final como content viral
- "AI detected 47 positioning errors in NaVi vs FaZe Grand Final"

**Semana 27: Soft launch (silencioso)**
```
1. Abrir registo público
2. Convidar lista de emails da Fase 0 (200+ pessoas)
3. Monitorizar onboarding flow + bugs
4. Fix imediato de qualquer issue
```

**Semana 28: Content launch**
```
1. Publicar análise AI de match pro recente
2. Post Reddit r/cs2: "We built AI that explains your CS2 mistakes"
3. Post HLTV forums
4. Twitter thread com clips de análise
```

**Semana 29: Product Hunt + comunidades**
```
1. Product Hunt launch (preparar 1 semana antes)
2. Partilhar em Discord communities
3. Contactar criadores de conteúdo CS2 para reviews
```

**Semana 30: Post-launch iteration**
```
1. Analisar métricas de aquisição + ativação
2. Identificar drop-off points no funnel
3. A/B test na landing page
4. Responder a todo o feedback público
```

### 10.3 Funnel de Conversão Target

```
Visitante landing page        1,000/semana
         │ (30% signup)
         ▼
Registo free                  300/semana
         │ (60% upload 1 demo)
         ▼
Demo uploaded                 180/semana
         │ (50% return next week)
         ▼
Utilizador ativo              90/semana
         │ (5-8% upgrade)
         ▼
Pagante (Solo/Team/Pro)       5-7/semana
```

### 10.4 Pricing em Produção

| Tier | Preço | Features |
|------|-------|----------|
| **Free** | €0 | 10 demos/mês, error detection básico (sem explicações), stats |
| **Solo** | €9/mês | 15 demos, ratings, heatmaps, treino básico |
| **Team** | €39/mês | 30 demos, error detection completo + SHAP, 2D replayer, 1 scout/mês, 5 seats |
| **Pro** | €129/mês | Ilimitado, prediction, scouts ilimitados, API, 15 seats |

### Deliverables Fase 7
- [ ] Produção estável com monitoring
- [ ] 50+ registos na primeira semana
- [ ] Primeiros utilizadores pagantes (target: 5-10)
- [ ] Content launch executado (Reddit + HLTV + Twitter)
- [ ] Funnel de conversão medido e otimizado
- [ ] Zero downtime durante launch

---

## 11. Fase 8 — Crescimento & Features Avançadas (Meses 8-12)

### Objetivo
Adicionar features avançadas por ordem de impacto. Crescer para €2,000-4,000 MRR.

### 11.1 Roadmap de Features (por prioridade)

#### Q3 (Meses 8-9): Utilidade & Ratings

**Modelo B: Utility Errors (LightGBM)**
```
Prioridade: Alta
Esforço: 2-3 semanas
Descrição: Classificar granadas como effective/suboptimal/wasted/harmful
Input: tipo granade, posição lançamento, posição impacto,
       enemies_flashed, damage_dealt, smoke_coverage_score
Output: classificação + SHAP explanation
Integração: adicionar tab "Utility" na página de erros
```

**Modelo F: Player Ratings (CatBoost)**
```
Prioridade: Alta
Esforço: 2 semanas
Descrição: Rating 0-100 multi-dimensional por jogador
Sub-ratings: aim, positioning, utility, game sense, clutch
Input: stats agregadas + error counts + context features
Output: overall rating + 5 sub-ratings + radar chart
Integração: player profile page, team dashboard
```

#### Q3 (Meses 9-10): Timing Errors & Scout Reports

**Modelo C: Timing Errors (Mamba)**
```
Prioridade: Média
Esforço: 2-3 semanas
Descrição: Detetar peeks, rotações, e ações em momentos errados
Input: sequência temporal (como Modelo A) + game state context
Output: timing_error classification + explanation
```

**Scout Reports v1 (Rule-based + ML)**
```
Prioridade: Alta
Esforço: 3-4 semanas
Descrição: Relatório automático analisando últimos demos do oponente
Conteúdo:
  - Strategy distribution por mapa e economia
  - Pistol round tendencies
  - Key player profiles
  - Exploitable patterns
  - Map veto recommendations
Implementação:
  - Queries agregadas ao ClickHouse
  - Templates Jinja2 para gerar report
  - PDF export via weasyprint
  - Sem modelo ML dedicado (usa dados dos outros modelos)
```

#### Q4 (Meses 10-12): Tactical Analysis & Training Plans

**Modelo D: Strategy Classifier (GraphSAGE)**
```
Prioridade: Média
Esforço: 4-5 semanas (mais complexo)
Descrição: Classificar estratégia de cada round
Categories: 15 T-side + 10 CT-side por mapa
Input: grafo de jogadores (posições + ações) → GraphSAGE
Output: strategy label + confidence
```

**Modelo E: Setup Prediction (Transformer)**
```
Prioridade: Média-Alta
Esforço: 4-5 semanas
Descrição: Prever setup do oponente no próximo round
Input: sequência de rounds anteriores + economy + score
Output: probabilidade de cada estratégia + counter-suggestion
Diferenciador CRÍTICO vs. Skybox
```

**Modelo G: Weakness Clustering (HDBSCAN)**
```
Prioridade: Média
Esforço: 2 semanas
Descrição: Identificar padrões recorrentes de fraquezas
Pipeline: erros acumulados → UMAP → HDBSCAN → archetypes
Output: weakness archetype + custom training drills
Integração: training plan page por jogador
```

### 11.2 Features Não-ML

| Feature | Prioridade | Esforço | Descrição |
|---------|-----------|---------|-----------|
| Voice comms sync | Média | 2 sem | Upload MP3 → sync com replay timeline |
| Referral program | Alta | 1 sem | 1 mês grátis por referral que pague |
| Weekly email digest | Alta | 0.5 sem | Resumo semanal de stats + erros |
| API pública | Média | 2 sem | REST API para integrações (tier Pro) |
| Team comparison | Média | 1 sem | Comparar stats entre 2 equipas |
| Bookmark rounds | Baixa | 0.5 sem | Guardar rounds importantes |
| Export clips | Baixa | 2 sem | Exportar replay de round como vídeo |

### 11.3 Growth Targets

| Mês | Free Users | Pagantes | MRR | Ação Principal |
|-----|-----------|----------|-----|----------------|
| 8 | 200 | 15 | €500 | Utility errors + ratings lançados |
| 9 | 350 | 30 | €1,000 | Scout reports v1 lançados |
| 10 | 500 | 50 | €1,800 | Timing errors + content marketing |
| 11 | 700 | 70 | €2,500 | Strategy classifier + referrals |
| 12 | 1,000 | 100 | €3,500 | Setup prediction (killer feature) |

---

## 12. Dependências Técnicas

### Diagrama de Dependências entre Fases

```
Fase 0 (Validação)
    │
    ▼ (go/no-go)
Fase 1 (Fundação) ──────────────────────────────────┐
    │                                                 │
    ▼                                                 │
Fase 2 (MVP Core) ──────────────┐                   │
    │                            │                   │
    ├──→ Fase 3 (Demos Pro)      │                   │
    │    [paralelo, precisa       │                   │
    │     pipeline de parse]      │                   │
    │                            │                   │
    ├──→ Fase 4 (ML)             │                   │
    │    [paralelo, precisa       │                   │
    │     dataset da Fase 3]      │                   │
    │                            │                   │
    ▼                            ▼                   │
Fase 5 (Frontend) ◄── Depende de Fases 2+3+4       │
    │                                                 │
    ▼                                                 │
Fase 6 (Beta) ◄── Depende de todas as anteriores    │
    │                                                 │
    ▼                                                 │
Fase 7 (Launch)                                      │
    │                                                 │
    ▼                                                 │
Fase 8 (Growth) ◄── infra da Fase 1 escala aqui ────┘
```

### Dependências Críticas Externas

| Dependência | Risco | Mitigação | Deadline |
|-------------|-------|-----------|----------|
| Resposta HLTV (parceria) | Médio — podem ignorar | Scraper como fallback | Semana 13 (enviar), esperar 4 sem |
| Aprovação FACEIT API | Baixo — processo formal | Submeter cedo, followup | Semana 13 (submeter), ~30 dias |
| Awpy compatibilidade CS2 | Baixo — lib ativa | demoparser2 como fallback | Semana 9 (validar) |
| Valve update formato demo | Baixo — raro | Parser abstraction layer | Contínuo |
| Stripe approval | Muito baixo | Processo standard | Semana 20 (aplicar) |
| AWS account + limits | Muito baixo | Pedir increase cedo | Semana 5 |

### Dependências entre Pacotes (Monorepo)

```
frontend ──→ (HTTP) ──→ backend
                           │
                           ├──→ demo-parser (Awpy)
                           ├──→ feature-engine
                           ├──→ ml-models (via BentoML)
                           └──→ pro-demo-ingester
                                    │
                                    ├──→ demo-parser (reutiliza)
                                    └──→ feature-engine (reutiliza)
```

---

## 13. Riscos & Mitigações

### Riscos Técnicos

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Mamba não converge para positioning errors | Média | Alto | Fallback: LSTM clássico; dataset maior |
| ClickHouse lento com volume (15M ticks × 1000 matches) | Baixa | Alto | Materialized views pré-agregadas; partitioning por mês |
| Awpy não suporta novo update CS2 | Média | Médio | demoparser2 direto; community fix rápido |
| Celery bottleneck em pico | Média | Médio | Auto-scaling workers; prioridade por tier |
| Explicações SHAP não fazem sentido para coaches | Média | Alto | Validar com beta testers; simplificar UI |
| 2D Replayer lento com 15M ticks | Baixa | Médio | Downsample para 16 ticks/seg; Canvas otimizado |

### Riscos de Negócio

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Ninguém quer pagar (€39 parece caro) | Média | Fatal | Fase 0 valida; ajustar pricing |
| Skybox adiciona AI features | Alta | Alto | Mover rápido; explicabilidade como moat |
| Stratmind lança primeiro | Média | Alto | Foco em PT/BR primeiro; nicho geográfico |
| StatTrak grátis mata conversão free→paid | Média | Médio | Free tier mais generoso; valor único no paid |
| HLTV bloqueia scraper | Média | Médio | Parceria formal; FACEIT como alternativa |
| Burnout (solo dev) | Alta | Alto | Scope controlado; Fase 0 valida antes de investir |
| CS2 perde popularidade | Baixa | Muito Alto | Arquitetura extensível (Valorant, Deadlock) |

### Planos de Contingência

**Se Fase 0 falha (no-go):**
→ Pivotar para tool individual (competir com Leetify em vez de Skybox)
→ Ou pivotar para API/B2B (vender análise como serviço a outras plataformas)

**Se ML precision <70% após 2 meses:**
→ Simplificar: usar regras heurísticas em vez de ML
→ Adicionar mais dados de treino (labels manuais)
→ Consultar especialista ML (freelance, 1-2 semanas)

**Se MRR <€500 após 3 meses de launch:**
→ Entrevistas urgentes com churned users
→ Testar preço mais baixo (€19/mês team)
→ Pivotar para modelo B2B (menos clientes, preço mais alto)
→ Considerar Valorant como mercado alternativo

---

## 14. Métricas de Sucesso por Fase

| Fase | Métrica Principal | Target | Red Flag |
|------|------------------|--------|----------|
| **0 — Validação** | Emails recolhidos | >200 | <50 |
| **1 — Fundação** | CI pipeline verde | 100% | Qualquer falha |
| **2 — MVP Core** | Demo: upload → stats em <5min | <5 min | >15 min |
| **3 — Demos Pro** | Demos pro disponíveis | >500 | <100 |
| **4 — ML** | Positioning error precision | >85% | <70% |
| **5 — Frontend** | Lighthouse performance score | >80 | <50 |
| **6 — Beta** | NPS beta testers | >30 | <10 |
| **7 — Launch** | Primeiros pagantes semana 1 | >5 | 0 |
| **8 — Growth** | MRR mês 12 | >€3,000 | <€1,000 |

### KPIs Contínuos (após launch)

| Categoria | KPI | Target |
|-----------|-----|--------|
| **Produto** | Tempo processamento demo | <5 min |
| | Error detection precision | >85% |
| | Uptime | >99.5% |
| | Error rate (5xx) | <0.1% |
| **Engagement** | Demos/equipa/mês | >10 |
| | Sessão média | >15 min |
| | Return visits/semana | >3 |
| | Feature adoption (errors tab) | >60% |
| **Revenue** | MRR growth | >15%/mês |
| | Free→Paid conversion | 5-8% |
| | Monthly churn | <5% |
| | ARPU | ~€50-70 |
| | LTV/CAC | >3x |

---

## 15. Orçamento & Recursos

### Cenário: Solo Dev

| Período | Custo Infra | Custo Externo | Total/Mês |
|---------|-------------|---------------|-----------|
| Fase 0 (Sem 1-4) | €0 | €0 | **€0** |
| Fase 1 (Sem 5-8) | €50 | €0 | **€50** |
| Fase 2-4 (Sem 9-20) | €300 | €500-1000 (labeling) | **€400-500** |
| Fase 5-6 (Sem 17-26) | €350 | €0 | **€350** |
| Fase 7+ (Sem 27+) | €400-600 | €100 (marketing) | **€500-700** |

**Custo total até launch: ~€3,000-4,000**
**Custo mensal em produção: ~€500-700**

### Cenário: Solo Dev + 1 Freelancer ML (part-time)

| Item | Custo |
|------|-------|
| Freelancer ML (20h/semana, 4 meses) | €8,000-12,000 |
| Infra (6 meses) | €2,000 |
| Labeling dataset | €1,000 |
| Marketing | €500 |
| **Total até launch** | **€12,000-16,000** |

### Break-Even Analysis

```
Custos fixos mensais (produção): ~€600
Margem por cliente pagante (ARPU €50): ~€48.50 (após Stripe 3%)

Break-even: €600 / €48.50 = ~13 clientes pagantes

Timeline estimado para break-even: Mês 8-10 (2-3 meses após launch)
```

---

## Apêndice A: Stack Técnico Completo

| Camada | Tecnologia | Versão | Fase |
|--------|-----------|--------|------|
| **Frontend** | Next.js (App Router, RSC) | 15+ | 1 |
| | React | 19+ | 1 |
| | TypeScript | 5.5+ | 1 |
| | Tailwind CSS | 4+ | 1 |
| | shadcn/ui | latest | 1 |
| | Recharts | 2.x | 2 |
| | D3.js | 7+ | 5 |
| | Canvas API | - | 2 |
| | TanStack Query | 5+ | 2 |
| | Zustand | 5+ | 1 |
| **Backend** | FastAPI | 0.110+ | 1 |
| | Python | 3.12+ | 1 |
| | Pydantic v2 | 2.5+ | 1 |
| | SQLAlchemy | 2.0+ | 1 |
| | Alembic | 1.13+ | 1 |
| | Celery | 5.3+ | 2 |
| **ML** | PyTorch | 2.2+ | 4 |
| | Mamba (mamba-ssm) | latest | 4 |
| | LightGBM | 4.0+ | 8 |
| | CatBoost | 1.2+ | 8 |
| | PyTorch Geometric | 2.5+ | 8 |
| | scikit-learn | 1.5+ | 4 |
| | Captum (Integrated Gradients) | latest | 4 |
| | FastTreeSHAP | latest | 8 |
| | MLflow | 2.10+ | 4 |
| | BentoML | 1.2+ | 4 |
| **Demo Parsing** | Awpy | latest | 2 |
| | demoparser2 (Rust) | latest | 2 |
| **Databases** | PostgreSQL | 16 | 1 |
| | ClickHouse | 24+ | 1 |
| | Redis | 7+ | 1 |
| **Infra** | AWS ECS Fargate | - | 1 |
| | AWS RDS | - | 1 |
| | AWS S3 | - | 2 |
| | AWS CloudFront | - | 7 |
| | ClickHouse Cloud | - | 1 |
| | Docker | 24+ | 1 |
| | Terraform | 1.6+ | 7 |
| | GitHub Actions | - | 1 |
| **Monorepo** | pnpm | 9+ | 1 |
| | Turborepo | latest | 1 |
| | uv | latest | 1 |
| **Monitoring** | Sentry | latest | 2 |
| | CloudWatch | - | 1 |
| | Prometheus + Grafana | - | 7 |
| **Payments** | Stripe | latest | 5 |

---

## Apêndice B: Comparação Detalhada Skybox vs. Nós (Pós-Implementação)

| Feature | Skybox EDGE | Nós (após Fase 8) | Vantagem |
|---------|-------------|-------------------|----------|
| **Demos pro pré-carregadas** | Sim | Sim + análise AI | Nós |
| **2D Replayer** | Sim (hardware accel.) | Sim (Canvas) | Empate |
| **3D Replayer** | Sim (mas sem CS2) | Não | Skybox* |
| **Player stats** | Sim | Sim + ratings ML | Nós |
| **Team stats** | Sim (€350+) | Sim (€39) | Nós (preço) |
| **Error detection AI** | Não | Sim + SHAP | Nós |
| **Tactic-spotter AI** | Sim (€1,299) | Sim (€129) | Nós (preço) |
| **Setup prediction** | Não | Sim | Nós |
| **Scout reports** | Manual | Automático | Nós |
| **Training plans** | Não | Sim (ML-based) | Nós |
| **Veto simulator** | Sim (€1,299) | Sim (via scout) | Empate |
| **Voice comms sync** | Sim (€350+) | Sim (€39) | Nós (preço) |
| **Broadcast tools** | Sim | Não | Skybox |
| **Adoção pro** | 90% | 0% → crescendo | Skybox |
| **Licença Valve** | Sim | Não | Skybox |
| **Explicabilidade** | Não | Sim (SHAP/IG) | Nós |
| **Preço equipa** | €350/mês | €39/mês | Nós (9x) |
| **Preço enterprise** | €1,299/mês | €129/mês | Nós (10x) |

*Skybox 3D não suporta CS2 atualmente

### Conclusão Estratégica

Após implementação completa (12 meses), teremos **superioridade técnica** em AI e explicabilidade, **preços 7-10x mais baixos**, e **funcionalidades que o Skybox não oferece** (error detection, prediction, training plans). A principal desvantagem — adoção e brand — só se resolve com tempo, tração, e execução consistente.

**O plano está desenhado para maximizar a probabilidade de sucesso**: validar antes de construir, lançar rápido com 1 modelo, e iterar com base em feedback real.
