# 01 - Fontes de Dados CS2

## 1. Ficheiros de Demo (.dem)

Os ficheiros de demo do  CS2 contêm toda a informação de uma partida, gravada tick-a-tick (64 ticks/segundo). São a fonte primária de dados da plataforma.

### Dados Disponíveis num Ficheiro de Demo

| Categoria | Dados | Granularidade |
|-----------|-------|---------------|
| Posição | x, y, z de cada jogador | Por tick (64/seg) |
| Orientação | yaw, pitch (direção do olhar) | Por tick |
| Velocidade | velocity_x, velocity_y, velocity_z | Por tick |
| Estado | health, armor, is_alive, is_scoped, is_walking, is_ducking | Por tick |
| Equipamento | active_weapon, has_helmet, has_defuser, money, equipment_value | Por tick |
| Flash | flash_duration (tempo cego) | Por tick |
| Kills | attacker, victim, weapon, headshot, wallbang, assisters | Por evento |
| Dano | attacker, victim, damage, hit_group, weapon | Por evento |
| Granadas | tipo, posição lançamento, posição impacto, trajetória | Por evento |
| Smokes | posição, duração, raio | Por evento |
| Incendiárias | posição, duração, dano por tick | Por evento |
| Bomba | posição de plant, defuse, explosão, site (A/B) | Por evento |
| Economia | dinheiro por jogador, valor do equipamento, tipo de compra | Por round |
| Rounds | vencedor, razão da vitória, pontuações, duração | Por round |

### Volume de Dados por Ficheiro de Demo

- Ficheiro bruto: ~50-150 MB
- Linhas de tick extraídas: ~5-15 milhões (10 jogadores × 64 ticks/seg × ~45 min)
- Eventos: ~2,000-5,000 (kills, danos, granadas, etc.)
- Após compressão ClickHouse (LZ4): ~200 MB por partida

---

## 2. Parsers de Demo CS2

### Awpy (Python) — Parser Principal

- **Repo**: github.com/pnxenopoulos/awpy
- **PyPI**: `pip install awpy` (requer Python >= 3.11)
- **Backend**: demoparser2 (Rust) — alta performance
- **Output**: DataFrames Pandas com header, rounds, kills, damages, grenades, weapon_fires, bomb_events, smokes, infernos, footsteps, tick data
- **Uso**:

```python
from awpy import Demo

demo = Demo("match.dem")

# Dados de alto nível
header = demo.header        # Mapa, servidor, data
kills = demo.kills          # Todas as eliminações com detalhes
damages = demo.damages      # Todos os danos
grenades = demo.grenades    # Todas as granadas
rounds = demo.rounds        # Resumo por round

# Dados de tick (posições de todos os jogadores)
ticks = demo.ticks          # DataFrame com posições tick-a-tick
```

### demoparser (Rust + Python/JS bindings)

- **Repo**: github.com/LaihoE/demoparser
- **Vantagem**: Computação pesada toda em Rust, ideal para processamento em lote
- **PyPI**: `pip install demoparser2`
- **Uso**: Ligações Python para extrair campos específicos

### demoinfocs-golang (Go)

- **Repo**: github.com/markus-wa/demoinfocs-golang
- **Vantagem**: Parser fundacional, registo de handlers de eventos
- **Uso**: Se precisarmos de microserviço Go para parsing de alta performance

### demofile-net (C#)

- **Repo**: github.com/saul/demofile-net
- **Desempenho**: Lê um jogo competitivo completo em ~1.3 segundos
- **Uso**: Alternativa se precisarmos de integração .NET

### Clarity (Java)

- **Repo**: github.com/skadistats/clarity
- **Vantagem**: "Comicamente rápido", suporta CS2, CSGO, Dota 2, Deadlock
- **Uso**: Alternativa para processamento massivo

### cs-demo-analyzer (CLI)

- **Repo**: github.com/akiver/cs-demo-analyzer
- **Output**: CSV, JSON, CSDM com dados de posição de entidades
- **Uso**: Ferramenta CLI para validação/debug

### Decisão: Usar Awpy como parser principal

**Justificação**:
1. Python nativo — integra diretamente com pipeline ML (PyTorch, scikit-learn)
2. Backend Rust (demoparser2) garante desempenho
3. Output em DataFrames Pandas — fácil transformação para features
4. Comunidade ativa, documentação completa
5. Extrai todos os tipos de dados necessários (ticks, eventos, economia)

---

## 3. Dados de Matches Profissionais

### HLTV (Fonte Principal de Dados Pro)

**APIs Disponíveis**:

| Recurso | URL / Biblioteca | Dados |
|---------|-----------|-------|
| hltv-async-api | PyPI: `hltv-async-api` | Resultados de partidas, rankings, stats de jogadores (async Python) |
| HLTV API (Vercel) | hltv-api.vercel.app | Resultados de partidas, partidas ao vivo, stats, rankings (REST) |
| hltv-scraper | github.com/jparedesDS/hltv-scraper | Stats individuais de jogadores (impact, KAST, opening kills) via Selenium |
| Apify HLTV Live | apify.com/paco_nassa/hltv-org-live-and-upcoming-matches | Partidas ao vivo + futuras + concluídas |
| Apify Rankings | apify.com/paco_nassa/hltv-org-team-ranking-api | Rankings de equipas |

**Dados do HLTV úteis para a plataforma**:
- Resultados de matches pro para calibrar ratings
- Stats de jogadores pro como baseline de comparação
- Rankings de equipas para contextualizar análises
- Ficheiros de demo de partidas pro (download direto do HLTV para partidas profissionais)

**Scraper de Demos Pro** (`scripts/download_pro_demos.py`):
```python
# Pipeline para recolha de dataset de treino:
# 1. Extrair IDs de partidas do HLTV (últimos 6 meses, Tier 1-2)
# 2. Descarregar ficheiros de demo de cada partida
# 3. Processar com Awpy → ClickHouse
# 4. Calcular features → PostgreSQL + Redis (feature store)
# Objetivo: ~5,000 demos pro para treino inicial dos modelos
```

### FACEIT / ESEA

**FACEIT CS2 Advanced Stats**:
- Stats detalhadas por match em páginas oficiais FACEIT
- API customizada para: últimos matches, elo, match stats, ladder info
- Limitação: FACEIT não guarda todos os demos

**Trackers de terceiros**:
- faceittracker.net — Stats e histórico FACEIT
- faceitanalyser.com — Análise de matches FACEIT
- csstats.gg — Tracker geral de stats CS2

### GameScorekeeper API

- **Docs**: docs.gamescorekeeper.com
- Fixture data CS2 com match URLs do HLTV desde Abril 2020
- Útil para cross-reference de dados

---

## 4. Datasets Públicos (Kaggle)

| Dataset | Descrição | Uso |
|---------|-----------|-----|
| CS2 HLTV Professional Match Statistics | Stats de matches pro históricas | Treino de modelo de rating, benchmark |
| Counter-Strike 2 Win Prediction (FACEIT) | Dados de matches FACEIT para predição | Features para win prediction model |

---

## 5. Estratégia de Recolha de Dados

### Para Treino dos Modelos ML

```
Fase 1 (Semanas 1-4): Bootstrap Dataset
├── Download 5,000 demos pro via HLTV scraper
├── Parse todos com Awpy pipeline
├── Armazenar em ClickHouse (tick data + events)
├── Armazenar metadata em PostgreSQL
└── Volume estimado: ~1 TB em ClickHouse (comprimido)

Fase 2 (Contínuo): Enrichment
├── Scrape novos matches pro semanalmente (~50-100/semana)
├── Integrar dados FACEIT para matches semi-pro
├── Adicionar dados de utilizadores da plataforma (com consentimento)
└── Target: 20,000+ demos ao fim de 6 meses
```

### Para Utilizadores da Plataforma

```
Upload Manual:
├── Utilizador faz upload de .dem via dashboard
├── Suportar bulk upload (múltiplos demos)
├── Validação: magic bytes, tamanho (<500 MB), formato CS2
└── Processamento assíncrono com status SSE

Integração Automática (futuro):
├── FACEIT API: sync automático de matches
├── Steam Game History: detetar novos demos
└── Folder watch: monitorizar pasta de demos local
```

---

## 6. Referências e Recursos

- **Awpy Docs**: awpy.readthedocs.io
- **Demo Parser Output Schema**: deepwiki.com/pnxenopoulos/awpy/2.3-demo-parser-output
- **PureSkill.gg Data Science**: docs.pureskill.gg/datascience/adx/cs2/csds/
- **SHAP for CS2**: journals.sagepub.com/doi/10.1177/17479541251388864
- **CS Demo Manager**: cs-demo-manager.com
