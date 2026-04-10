# 04 - Schema da Base de Dados

## Visão Geral

```
PostgreSQL 16 (Transacional)          ClickHouse (Analytics)
┌──────────────────────────┐          ┌──────────────────────┐
│ organizations            │          │ tick_data            │
│ users                    │          │ (15M rows/match)     │
│ teams / team_players     │          │                      │
│ demos                    │          │ events               │
│ matches / rounds         │          │ (5K rows/match)      │
│ detected_errors          │          │                      │
│ tactical_analysis        │          │ player_round_stats   │
│ player_ratings           │          │ (agregações)         │
│ player_weakness_profiles │          └──────────────────────┘
│ scout_reports            │
│ training_recommendations │
│ audit_log                │
└──────────────────────────┘
```

---

## Schema PostgreSQL

### Autenticação & Multi-Tenancy

```sql
-- Organizações (tenant principal)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    tier VARCHAR(20) NOT NULL DEFAULT 'free'
        CHECK (tier IN ('free', 'basic', 'premium')),
    max_demos_per_month INT NOT NULL DEFAULT 5,
    logo_url VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Utilizadores
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('admin', 'coach', 'analyst', 'player', 'viewer')),
    steam_id VARCHAR(50),
    avatar_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_steam_id ON users(steam_id) WHERE steam_id IS NOT NULL;

-- Refresh tokens
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Convites pendentes
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    invited_by UUID NOT NULL REFERENCES users(id),
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Equipas & Roster

```sql
-- Equipas dentro de uma organização
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    tag VARCHAR(10),
    game_team_name VARCHAR(255),  -- Nome in-game para matching automático
    logo_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_teams_org_id ON teams(org_id);

-- Jogadores numa equipa
CREATE TABLE team_players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    steam_id VARCHAR(50) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    role VARCHAR(20)
        CHECK (role IN ('entry', 'awp', 'support', 'lurk', 'igl', 'rifler')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    left_at TIMESTAMPTZ,

    UNIQUE(team_id, steam_id)
);

CREATE INDEX idx_team_players_team_id ON team_players(team_id);
CREATE INDEX idx_team_players_steam_id ON team_players(steam_id);
```

### Dados de Demo & Match

```sql
-- Ficheiros de demo carregados
CREATE TABLE demos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    s3_key VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255),
    file_size_bytes BIGINT NOT NULL,
    checksum_sha256 VARCHAR(64),
    status VARCHAR(30) NOT NULL DEFAULT 'uploaded'
        CHECK (status IN (
            'uploaded',
            'validating',
            'parsing',
            'parsed',
            'computing_features',
            'features_computed',
            'analyzing',
            'analysis_complete',
            'error'
        )),
    error_message TEXT,
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_demos_org_id ON demos(org_id);
CREATE INDEX idx_demos_status ON demos(status);
CREATE INDEX idx_demos_created_at ON demos(created_at DESC);

-- Partidas extraídas dos demos
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demo_id UUID NOT NULL REFERENCES demos(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    map VARCHAR(50) NOT NULL,
    match_date TIMESTAMPTZ,
    server VARCHAR(255),
    tickrate INT NOT NULL DEFAULT 64,

    -- Equipas (nomes)
    team1_name VARCHAR(255),
    team2_name VARCHAR(255),
    team1_score INT NOT NULL,
    team2_score INT NOT NULL,

    -- Ligação à nossa equipa
    our_team_id UUID REFERENCES teams(id),
    our_side_first VARCHAR(2) CHECK (our_side_first IN ('ct', 't')),

    -- Metadata
    match_type VARCHAR(20) DEFAULT 'unknown'
        CHECK (match_type IN ('scrim', 'official', 'pug', 'unknown')),
    total_rounds INT NOT NULL,
    overtime_rounds INT DEFAULT 0,
    duration_seconds INT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_matches_org_id ON matches(org_id);
CREATE INDEX idx_matches_map ON matches(map);
CREATE INDEX idx_matches_date ON matches(match_date DESC);
CREATE INDEX idx_matches_our_team ON matches(our_team_id);

-- Rounds
CREATE TABLE rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    round_number INT NOT NULL,

    -- Resultado do round
    winner_side VARCHAR(2) NOT NULL CHECK (winner_side IN ('ct', 't')),
    win_reason VARCHAR(30) NOT NULL
        CHECK (win_reason IN (
            'elimination', 'bomb_exploded', 'bomb_defused',
            'time_expired', 'surrender'
        )),

    -- Pontuação
    t_score INT NOT NULL,
    ct_score INT NOT NULL,

    -- Economia (freeze time)
    t_economy INT,
    ct_economy INT,
    t_equipment_value INT,
    ct_equipment_value INT,
    t_buy_type VARCHAR(20) CHECK (t_buy_type IN ('full', 'force', 'half', 'eco', 'pistol')),
    ct_buy_type VARCHAR(20) CHECK (ct_buy_type IN ('full', 'force', 'half', 'eco', 'pistol')),

    -- Dados da bomba
    bomb_planted BOOLEAN NOT NULL DEFAULT false,
    bomb_plant_tick INT,
    bomb_site VARCHAR(1) CHECK (bomb_site IN ('A', 'B')),

    -- Temporização
    start_tick INT NOT NULL,
    end_tick INT NOT NULL,
    freeze_end_tick INT NOT NULL,
    duration_seconds FLOAT,

    UNIQUE(match_id, round_number)
);

CREATE INDEX idx_rounds_match_id ON rounds(match_id);
```

### Resultados ML — Deteção de Erros

```sql
-- Erros detetados pelo ML
CREATE TABLE detected_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    round_id UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Dados do jogador
    player_steam_id VARCHAR(50) NOT NULL,
    player_name VARCHAR(255),

    -- Tipo de erro
    error_type VARCHAR(30) NOT NULL
        CHECK (error_type IN ('positioning', 'utility', 'timing')),
    error_subtype VARCHAR(50),  -- 'multi_angle_exposure', 'flash_no_blind', etc.
    severity VARCHAR(20) NOT NULL
        CHECK (severity IN ('critical', 'major', 'minor')),

    -- Localização no mapa
    tick INT NOT NULL,
    timestamp_seconds FLOAT NOT NULL,
    position_x FLOAT,
    position_y FLOAT,
    position_z FLOAT,
    map_area VARCHAR(50),  -- Callout name (e.g., "A-site", "mid", "banana")

    -- Detalhes do erro
    description TEXT NOT NULL,
    recommendation TEXT NOT NULL,

    -- Metadados do ML
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    shap_factors JSONB NOT NULL DEFAULT '[]',
    -- Formato: [{"feature": "angles_exposed", "value": 2, "impact": 0.45}, ...]

    -- Referência de jogador profissional
    pro_reference JSONB,
    -- Formato: {"player": "device", "match_id": "xxx", "round": 8, "description": "..."}

    -- Versão do modelo
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(50) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_errors_match_id ON detected_errors(match_id);
CREATE INDEX idx_errors_org_id ON detected_errors(org_id);
CREATE INDEX idx_errors_player ON detected_errors(player_steam_id);
CREATE INDEX idx_errors_type ON detected_errors(error_type);
CREATE INDEX idx_errors_severity ON detected_errors(severity);
CREATE INDEX idx_errors_created ON detected_errors(created_at DESC);
```

### Resultados ML — Análise Tática

```sql
-- Classificação tática por round (ronda)
CREATE TABLE tactical_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    round_id UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    team_side VARCHAR(2) NOT NULL CHECK (team_side IN ('ct', 't')),
    team_name VARCHAR(255),
    is_our_team BOOLEAN NOT NULL DEFAULT false,

    -- Estratégia classificada pelo modelo
    strategy_label VARCHAR(50) NOT NULL,
    strategy_confidence FLOAT NOT NULL,
    strategy_probabilities JSONB NOT NULL DEFAULT '{}',
    -- {"a_execute": 0.65, "mid_control_to_a": 0.20, ...}

    -- Detalhes da estratégia
    strategy_details JSONB,
    -- Posições iniciais, plano de utilitários, etc.

    model_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tactical_match ON tactical_analysis(match_id);
CREATE INDEX idx_tactical_org ON tactical_analysis(org_id);

-- Previsões de setup
CREATE TABLE setup_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    predicted_for_round INT NOT NULL,
    opponent_team_name VARCHAR(255),
    predicted_strategy VARCHAR(50) NOT NULL,
    prediction_confidence FLOAT NOT NULL,
    top_predictions JSONB NOT NULL DEFAULT '[]',
    -- [{"strategy": "b_execute", "probability": 0.35}, ...]

    counter_suggestion TEXT,
    reasoning TEXT,

    -- Resultado real (preenchido após o round)
    actual_strategy VARCHAR(50),
    prediction_correct BOOLEAN,

    model_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Resultados ML — Perfil de Jogador

```sql
-- Ratings por jogador por match
CREATE TABLE player_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_steam_id VARCHAR(50) NOT NULL,
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Rating geral
    overall_rating FLOAT NOT NULL CHECK (overall_rating >= 0 AND overall_rating <= 100),

    -- Sub-ratings
    aim_rating FLOAT CHECK (aim_rating >= 0 AND aim_rating <= 100),
    positioning_rating FLOAT CHECK (positioning_rating >= 0 AND positioning_rating <= 100),
    utility_rating FLOAT CHECK (utility_rating >= 0 AND utility_rating <= 100),
    game_sense_rating FLOAT CHECK (game_sense_rating >= 0 AND game_sense_rating <= 100),
    clutch_rating FLOAT CHECK (clutch_rating >= 0 AND clutch_rating <= 100),

    -- Raw stats usadas
    rating_factors JSONB NOT NULL DEFAULT '{}',
    -- {"kd_ratio": 1.2, "adr": 85, "kast": 72, ...}

    model_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(player_steam_id, match_id)
);

CREATE INDEX idx_ratings_player ON player_ratings(player_steam_id);
CREATE INDEX idx_ratings_org ON player_ratings(org_id);
CREATE INDEX idx_ratings_match ON player_ratings(match_id);

-- Perfis de fraqueza (atualizado periodicamente)
CREATE TABLE player_weakness_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_steam_id VARCHAR(50) NOT NULL,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Cluster de fraqueza principal
    primary_weakness_cluster VARCHAR(50) NOT NULL,
    primary_weakness_strength FLOAT NOT NULL,
    primary_weakness_description TEXT NOT NULL,

    -- Cluster secundário
    secondary_weakness_cluster VARCHAR(50),
    secondary_weakness_strength FLOAT,
    secondary_weakness_description TEXT,

    -- Todas as fraquezas detalhadas
    weakness_details JSONB NOT NULL DEFAULT '[]',
    -- [{"cluster": "...", "strength": 0.82, "features": {...}}, ...]

    -- Plano de treino
    training_recommendations JSONB NOT NULL DEFAULT '[]',
    -- [{"priority": 1, "area": "...", "description": "...", "drill": "...",
    --   "expected_impact": "...", "current_metric": 0.35, "target_metric": 0.20}, ...]

    -- Metadata
    computed_from_matches INT NOT NULL,  -- Número de matches analisados
    match_ids UUID[] NOT NULL,
    trend VARCHAR(20) DEFAULT 'stable'
        CHECK (trend IN ('improving', 'stable', 'declining')),
    improvement_rate FLOAT,  -- % change per month

    model_version VARCHAR(50) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_weakness_player ON player_weakness_profiles(player_steam_id);
CREATE INDEX idx_weakness_org ON player_weakness_profiles(org_id);
```

### Relatórios de Scouting

```sql
CREATE TABLE scout_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id),

    -- Oponente
    opponent_team_name VARCHAR(255) NOT NULL,
    opponent_team_hltv_id INT,

    -- Scope
    maps_analyzed VARCHAR(50)[] NOT NULL,
    matches_analyzed INT NOT NULL,
    date_range_start DATE,
    date_range_end DATE,
    demo_ids UUID[] NOT NULL,

    -- Relatório
    report_data JSONB NOT NULL,
    -- Estrutura:
    -- {
    --   "summary": "...",
    --   "map_veto_recommendation": {...},
    --   "maps": {
    --     "mirage": {
    --       "t_strategies": {"a_execute": 35%, "b_execute": 20%, ...},
    --       "ct_strategies": {"2_1_2": 60%, ...},
    --       "pistol_rounds": {...},
    --       "anti_eco": {...},
    --       "default_positions_heatmap_data": {...},
    --       "key_players": [...]
    --     }
    --   },
    --   "player_scouting": [...],
    --   "counter_strategies": [...],
    --   "exploitable_patterns": [...]
    -- }

    status VARCHAR(20) NOT NULL DEFAULT 'generating'
        CHECK (status IN ('generating', 'completed', 'error')),
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_scout_org ON scout_reports(org_id);
CREATE INDEX idx_scout_opponent ON scout_reports(opponent_team_name);
CREATE INDEX idx_scout_created ON scout_reports(created_at DESC);
```

### Auditoria & Sistema

```sql
-- Audit log
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    org_id UUID NOT NULL,
    user_id UUID,
    action VARCHAR(50) NOT NULL,  -- 'view_match', 'download_report', 'upload_demo'
    resource_type VARCHAR(50) NOT NULL,  -- 'match', 'scout_report', 'demo'
    resource_id UUID,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_org ON audit_log(org_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);

-- Usage tracking (para billing/limites)
CREATE TABLE usage_tracking (
    id BIGSERIAL PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES organizations(id),
    month DATE NOT NULL,  -- Primeiro dia do mês
    demos_uploaded INT NOT NULL DEFAULT 0,
    demos_analyzed INT NOT NULL DEFAULT 0,
    scout_reports_generated INT NOT NULL DEFAULT 0,
    api_calls INT NOT NULL DEFAULT 0,
    storage_bytes_used BIGINT NOT NULL DEFAULT 0,

    UNIQUE(org_id, month)
);
```

### Segurança ao Nível da Linha (RLS)

```sql
-- Ativar RLS em todas as tabelas com org_id
ALTER TABLE demos ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE rounds ENABLE ROW LEVEL SECURITY;
ALTER TABLE detected_errors ENABLE ROW LEVEL SECURITY;
ALTER TABLE tactical_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_weakness_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE scout_reports ENABLE ROW LEVEL SECURITY;

-- Policy padrão: isolamento por org_id
CREATE POLICY org_isolation ON demos
    USING (org_id = current_setting('app.current_org_id')::UUID);

CREATE POLICY org_isolation ON matches
    USING (org_id = current_setting('app.current_org_id')::UUID);

-- Repetir para todas as tabelas...
-- O middleware FastAPI faz SET app.current_org_id antes de cada query
```

---

## Schema ClickHouse

### Dados de Tick

```sql
CREATE TABLE tick_data (
    match_id UUID,
    round_number UInt8,
    tick UInt32,
    player_steam_id String,
    player_name String,
    team_side LowCardinality(String),  -- 'ct' ou 't'

    -- Posição
    x Float32,
    y Float32,
    z Float32,

    -- Orientação
    yaw Float32,
    pitch Float32,

    -- Movimento
    velocity_x Float32,
    velocity_y Float32,
    velocity_z Float32,

    -- Estado
    health UInt8,
    armor UInt8,
    is_alive UInt8,
    is_scoped UInt8,
    is_walking UInt8,
    is_ducking UInt8,

    -- Equipamento
    active_weapon LowCardinality(String),
    has_helmet UInt8,
    has_defuser UInt8,
    money UInt32,
    equipment_value UInt32,

    -- Flash
    flash_duration Float32,

    -- Metadata
    org_id UUID,
    inserted_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY match_id
ORDER BY (match_id, round_number, tick, player_steam_id)
TTL inserted_at + INTERVAL 365 DAY
SETTINGS index_granularity = 8192;
```

### Eventos

```sql
CREATE TABLE events (
    match_id UUID,
    round_number UInt8,
    tick UInt32,
    timestamp_seconds Float32,

    event_type LowCardinality(String),
    -- 'kill', 'damage', 'grenade_throw', 'grenade_detonate',
    -- 'bomb_plant', 'bomb_defuse', 'bomb_explode',
    -- 'flash_effect', 'weapon_fire'

    -- Actor
    actor_steam_id String,
    actor_name String,
    actor_team LowCardinality(String),
    actor_x Float32,
    actor_y Float32,
    actor_z Float32,

    -- Target (se aplicável)
    target_steam_id Nullable(String),
    target_name Nullable(String),
    target_team LowCardinality(Nullable(String)),
    target_x Nullable(Float32),
    target_y Nullable(Float32),
    target_z Nullable(Float32),

    -- Kill/Damage specific
    weapon LowCardinality(Nullable(String)),
    damage Nullable(UInt16),
    damage_armor Nullable(UInt16),
    hit_group Nullable(UInt8),
    is_headshot Nullable(UInt8),
    is_wallbang Nullable(UInt8),
    is_noscope Nullable(UInt8),
    is_through_smoke Nullable(UInt8),
    is_blind_kill Nullable(UInt8),
    penetration_count Nullable(UInt8),

    -- Grenade specific
    grenade_type LowCardinality(Nullable(String)),
    -- 'smoke', 'flash', 'he', 'molotov', 'incendiary', 'decoy'
    land_x Nullable(Float32),
    land_y Nullable(Float32),
    land_z Nullable(Float32),

    -- Flash specific
    players_blinded Array(String),
    blind_durations Array(Float32),

    -- Assisters
    assisters Array(String),

    -- Metadata
    org_id UUID,
    inserted_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY match_id
ORDER BY (match_id, round_number, tick, event_type);
```

### Vistas Materializadas (Performance)

```sql
-- Stats por jogador por round (pré-calculadas)
CREATE MATERIALIZED VIEW player_round_stats
ENGINE = SummingMergeTree()
ORDER BY (match_id, round_number, player_steam_id)
AS SELECT
    match_id,
    round_number,
    actor_steam_id AS player_steam_id,
    countIf(event_type = 'kill') AS kills,
    countIf(event_type = 'kill' AND is_headshot = 1) AS headshot_kills,
    countIf(event_type = 'damage') AS damage_events,
    sumIf(damage, event_type = 'damage') AS total_damage,
    countIf(event_type = 'grenade_throw') AS grenades_thrown,
    countIf(event_type = 'flash_effect' AND length(players_blinded) > 0) AS effective_flashes
FROM events
GROUP BY match_id, round_number, actor_steam_id;

-- Heatmap data (posições agregadas)
CREATE MATERIALIZED VIEW position_heatmap
ENGINE = SummingMergeTree()
ORDER BY (match_id, player_steam_id, grid_x, grid_y)
AS SELECT
    match_id,
    player_steam_id,
    team_side,
    -- Grid de 1x1 unidades para heatmap
    floor(x) AS grid_x,
    floor(y) AS grid_y,
    count() AS presence_count,
    avg(health) AS avg_health
FROM tick_data
WHERE is_alive = 1
GROUP BY match_id, player_steam_id, team_side, grid_x, grid_y;
```

---

## Diagrama de Relações

```
organizations ──┬── users
                ├── teams ──── team_players
                ├── demos ──── matches ──┬── rounds
                │                        ├── detected_errors
                │                        ├── tactical_analysis
                │                        ├── setup_predictions
                │                        └── player_ratings
                ├── player_weakness_profiles
                ├── scout_reports
                ├── usage_tracking
                └── audit_log

ClickHouse (sem FK, referência por match_id):
  tick_data ── (match_id) ── matches
  events ── (match_id) ── matches
```

---

## Estimativa de Volume

| Tabela | Rows/Match | Rows/Mês (30 matches) | Storage |
|--------|-----------|----------------------|---------|
| tick_data (CH) | ~15M | ~450M | ~6 GB (LZ4) |
| events (CH) | ~5K | ~150K | ~50 MB |
| rounds (PG) | ~30 | ~900 | <1 MB |
| detected_errors (PG) | ~50-200 | ~1.5-6K | ~5 MB |
| tactical_analysis (PG) | ~60 | ~1.8K | ~2 MB |
| player_ratings (PG) | ~10 | ~300 | <1 MB |

**Total por equipa/mês**: ~6 GB (dominado por tick_data no ClickHouse)
**100 equipas**: ~600 GB/mês em ClickHouse, ~1 GB/mês em PostgreSQL
