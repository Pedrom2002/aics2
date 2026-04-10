# 02 - Arquitetura de Machine Learning

## Visão Geral dos Modelos

A plataforma utiliza 7 modelos ML organizados em 3 sistemas:

```
┌─────────────────────────────────────────────────────────────┐
│                    SISTEMA DE ML                            │
├─────────────────────┬──────────────────┬────────────────────┤
│  Deteção de Erros   │  IA Tática       │  Perfil de Jogador │
│  (3 modelos)        │  (2 modelos)     │  (2 modelos)       │
├─────────────────────┼──────────────────┼────────────────────┤
│ A. Positioning Mamba│ D. Strategy GNN  │ F. Rating CatBoost │
│ B. Utility LightGBM │ E. Setup Transf. │ G. Weakness HDBSCAN│
│ C. Timing Mamba     │                  │                    │
└─────────────────────┴──────────────────┴────────────────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │ Motor de          │
                    │ Explicabilidade   │
                    │ · Integrated      │
                    │   Gradients       │
                    │   (neural models) │
                    │ · FastTreeSHAP    │
                    │   (tree models)   │
                    └───────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  Motor de         │
                    │  Recomendações    │
                    │  (regras+templates)│
                    └───────────────────┘
```

---

## Modelo A: Erros de Posicionamento (Mamba — State Space Model)

### Objetivo
Detetar quando um jogador está numa posição perigosa — exposto a múltiplos ângulos, longe de cover, sem crossfire de teammates.

### Input

```
Janela temporal: 64 ticks (1 segundo)
Features por tick (18 dimensões):
  Posição:
    - x, y, z                          (3)
  Orientação:
    - yaw, pitch                        (2)
  Movimento:
    - velocity (magnitude)              (1)
  Estado:
    - health (normalizado 0-1)          (1)
    - armor (normalizado 0-1)           (1)
    - weapon_id (encoded)               (1)
    - is_scoped (0/1)                   (1)
  Contexto de round:
    - teammates_alive (0-4)             (1)
    - enemies_alive (0-5)               (1)
    - bomb_state (0=none,1=carried,     (1)
      2=planted,3=defusing)
    - round_time_remaining (norm.)      (1)
  Posicionamento relativo:
    - nearest_teammate_dist (norm.)     (1)
    - nearest_enemy_dist_estimated      (1)
      (baseado em última posição conhecida)
  Qualidade de posição:
    - angles_exposed_count              (1)
      (quantos ângulos comuns o jogador
       está exposto, calculado via raycast
       contra posições comuns do mapa)
    - distance_to_nearest_cover (norm.) (1)

Shape final: (batch_size, 64, 18)
```

### Arquitetura

Utiliza **Mamba (MambaAD)**, State Space Model com complexidade O(n) vs O(n²) dos Transformers. MambaAD foi desenhado especificamente para anomaly detection (NeurIPS 2024) e iguala a capacidade dos Transformers mantendo escalabilidade linear.

```python
class PositioningErrorModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.mamba = MambaBlock(
            d_model=128,
            d_state=16,
            d_conv=4,
            expand=2
        )
        self.input_proj = nn.Linear(18, 128)
        self.classifier = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 3)    # sem_erro, menor, critico
        )

    def forward(self, x):
        # x: (batch, 64, 18)
        x = self.input_proj(x)   # (batch, 64, 128)
        x = self.mamba(x)         # (batch, 64, 128)
        x = x.mean(dim=1)         # (batch, 128) global avg pool
        return self.classifier(x)  # (batch, 3)
```

### Labels de Treino

```
Classe 0 - sem_erro:
  - Posições de jogadores pro em contextos similares
  - Jogador sobreviveu o engagement ou ganhou o duel

Classe 1 - erro_menor:
  - Posição subótima mas não diretamente causou morte
  - Exposto a 1 ângulo extra sem necessidade
  - Ligeiramente longe de cover

Classe 2 - erro_critico:
  - Morte diretamente causada por má posição
  - Exposto a 2+ ângulos simultaneamente
  - Sem possibilidade de trade pelo teammate
  - Muito longe de qualquer cover
```

### Estratégia de Labeling

```
Round 1: Pseudo-labels heurísticos
  - SE morreu E angles_exposed >= 2 E cover_dist > threshold
    → candidato a erro_critico
  - SE morreu E (angles_exposed >= 2 OU cover_dist > threshold)
    → candidato a erro_menor
  - SE jogador pro na mesma posição no mesmo contexto → sem_erro
  - Filtro: ignorar mortes por headshot 1-tap (skill, não posição)

Round 2: Expert annotation (2-3 analistas high-rank)
  - Revisar 5,000 candidatos
  - Corrigir false positives/negatives
  - Adicionar severidade

Round 3: Semi-supervised expansion
  - Treinar modelo inicial nos 5,000 exemplos
  - Aplicar ao dataset completo
  - Aceitar predições com confidence > 0.9 como labels
  - Target: 20,000 exemplos labeled
```

### Métricas de Avaliação

- **Precision > 0.85**: Minimizar false positives (não queremos dizer que há erro quando não há)
- **Recall > 0.70**: Queremos apanhar a maioria dos erros reais
- **F1 > 0.77**: Balanço geral
- **Confusion matrix por classe**: Verificar que critical errors são bem identificados

---

## Modelo B: Erros de Utilidade (LightGBM)

### Objetivo
Classificar cada utilização de granada (smoke, flash, HE, molotov) como eficaz, subótima, desperdiçada ou prejudicial.

### Input

```
Features por granada (25 dimensões):

Contexto da granada:
  - grenade_type (one-hot: smoke/flash/he/molly)  (4)
  - map_id (encoded)                                (1)

Posição:
  - throw_x, throw_y, throw_z                      (3)
  - land_x, land_y, land_z                          (3)
  - distance_to_pro_lineup                          (1)
    (distância ao lineup pro mais próximo conhecido)

Timing:
  - round_time_remaining (normalizado)              (1)
  - time_since_round_start                          (1)
  - phase (early_round/mid_round/execute/post_plant)(1)

Contexto de round:
  - score_diff (normalizado)                        (1)
  - teammates_alive                                 (1)
  - enemies_alive                                   (1)
  - buy_type (eco/force/full)                       (1)

Resultado (calculado pós-evento):
  - enemies_flashed_count (para flash)              (1)
  - flash_duration_avg (para flash)                 (1)
  - smoke_blocks_los_count                          (1)
  - molly_damage_dealt                              (1)
  - he_damage_dealt                                 (1)
  - time_to_site_take_after (para T-side)           (1)
  - was_round_won                                   (1)

Shape: (batch_size, 25)
```

### Arquitetura

Utiliza **LightGBM**, 7x mais rápido que XGBoost em treino graças ao leaf-wise growth (em vez de level-wise). Melhor adequado para inferência em lote com baixa latência.

```python
import lightgbm as lgb

model = lgb.LGBMClassifier(
    n_estimators=500,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective='multiclass',
    num_class=4,
    metric='multi_logloss',
    num_leaves=127,       # leaf-wise growth (LightGBM advantage)
    min_child_samples=20,
    verbose=-1
)

# Classes:
# 0 - eficaz: granada cumpriu objetivo (flash cegou, smoke bloqueou LOS, etc.)
# 1 - subótima: teve algum efeito mas podia ser melhor
# 2 - desperdiçada: sem efeito útil (flash sem cegar, smoke mal posicionada)
# 3 - prejudicial: flash cegou teammates, smoke bloqueou própria equipa
```

### Explicabilidade

Para modelos de árvore como LightGBM utiliza-se **FastTreeSHAP** (TreeExplainer), rápido o suficiente para inferência real-time. Modelos neurais (Mamba) usam **Integrated Gradients** — 50-100x mais rápido que SHAP KernelExplainer, com latência sub-10ms via PyTorch autograd.

```python
import shap

# FastTreeSHAP para LightGBM (tree model)
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_single)

# Output exemplo:
# "Esta flash foi classificada como 'desperdiçada' porque:
#  - enemies_flashed_count = 0 (impacto +0.45 para 'desperdiçada')
#  - round_time_remaining era baixo (impacto +0.22)
#  - distance_to_pro_lineup = 15.3m (impacto +0.18)"
```

---

## Modelo C: Erros de Timing (Mamba — State Space Model)

### Objetivo
Detetar quando um jogador fez peek, rotação ou ação num momento errado.

### Input

```
Janela: 5 segundos centrada no momento-chave (320 ticks a 64/seg)

Momentos-chave detetados automaticamente:
  - Peek (mudança de posição atrás de cover para exposed)
  - Rotação (mudança de site/área)
  - Plant attempt
  - Defuse attempt
  - Aggressive push

Features por tick (14 dimensões):
  - player_state (moving/holding/peeking)           (1)
  - round_clock (normalizado)                        (1)
  - recent_kills_own_team (últimos 3 seg)            (1)
  - recent_kills_enemy_team (últimos 3 seg)          (1)
  - teammates_alive                                  (1)
  - enemies_alive                                    (1)
  - teammate_1_relative_pos (dist + angle)           (2)
  - teammate_2_relative_pos                          (2)
  - info_level (quanta info tem: radar, sound cues)  (1)
  - economy_advantage (normalizado -1 a 1)           (1)
  - bomb_state                                       (1)
  - has_flash_available                               (1)

Shape: (batch_size, 320, 14)
```

### Arquitetura

Utiliza **Mamba** como backbone sequencial, parte de um ensemble Mamba + TCN (Temporal Convolutional Networks). O TCN processa em paralelo (84% mais rápido que LSTM) e complementa o Mamba na captura de padrões locais.

```python
class TimingErrorModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.input_proj = nn.Linear(14, 96)
        self.mamba = MambaBlock(
            d_model=96,
            d_state=16,
            d_conv=4,
            expand=2
        )
        self.classifier = nn.Sequential(
            nn.Linear(96, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 4)  # bom, demasiado_cedo, demasiado_tarde, desnecessário
        )

    def forward(self, x):
        x = self.input_proj(x)        # (batch, 320, 96)
        x = self.mamba(x)              # (batch, 320, 96)
        pooled = x.mean(dim=1)         # (batch, 96)
        return self.classifier(pooled)  # (batch, 4)
```

### Classes

```
0 - bom_timing: ação no momento correto dado o contexto
1 - demasiado_cedo: peek/push antes de ter info ou flash
2 - demasiado_tarde: rotação atrasada, peek depois de oportunidade passar
3 - desnecessário: ação sem necessidade (peek quando já tem controlo)
```

---

## Modelo D: Strategy Classifier (GraphSAGE GNN com PyG)

### Objetivo
Classificar a estratégia de uma equipa em cada round (15-25 labels por mapa).

### Input: Grafo por Round

```
Snapshot nos primeiros 15 segundos do round (após freeze time)

Nós (5 por equipa):
  - Cada jogador é um nó
  Node features (16 dimensões):
    - position_x, position_y (normalizadas para mapa)  (2)
    - velocity (magnitude)                               (1)
    - weapon_category (rifle/smg/awp/pistol/shotgun)     (1)
    - utility_remaining (flash/smoke/molly/he counts)    (4)
    - health (normalizado)                               (1)
    - armor (normalizado)                                (1)
    - role_encoding (entry/awp/support/lurk/igl)         (1)
    - area_id (zona do mapa encoded)                     (1)
    - movement_direction (angle normalizado)             (1)
    - is_in_site (0/1)                                   (1)
    - time_in_current_area                               (1)
    - equipment_value (normalizado)                      (1)

Edges (conexões entre jogadores):
  - Edge se distância < threshold (próximos o suficiente para trade)
  - Edge se line-of-sight (podem ver-se)
  Edge features (3 dimensões):
    - distance (normalizada)                             (1)
    - can_trade (0/1, baseado em distância e ângulo)     (1)
    - can_flash_for (0/1, baseado em posição relativa)   (1)
```

### Arquitetura

Utiliza **GraphSAGE** (inductive learning framework), que atinge **98.5% de accuracy** em graph classification vs GAT. A aprendizagem indutiva é adequada para estados de jogo dinâmicos onde novos grafos surgem a cada round. Mais rápido para treino e inferência que GATConv.

```python
from torch_geometric.nn import SAGEConv, global_mean_pool

class StrategyClassifier(nn.Module):
    def __init__(self, num_strategies):
        super().__init__()
        self.conv1 = SAGEConv(
            in_channels=16,
            out_channels=64
        )
        self.conv2 = SAGEConv(
            in_channels=64,
            out_channels=128
        )
        self.classifier = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_strategies)
        )

    def forward(self, data):
        x, edge_index, batch = (
            data.x, data.edge_index, data.batch
        )
        x = F.elu(self.conv1(x, edge_index))
        x = F.elu(self.conv2(x, edge_index))
        x = global_mean_pool(x, batch)    # (batch, 128)
        return self.classifier(x)          # (batch, num_strategies)
```

### Labels de Estratégia (Exemplo Mirage)

```
T-Side (15 estratégias):
  - a_execute           (execute A com utility completa)
  - b_execute           (execute B com utility completa)
  - mid_control_to_a    (tomar mid, depois rodar A)
  - mid_control_to_b    (tomar mid, depois rodar B)
  - split_a             (dividir por mid + ramp)
  - split_b             (dividir por mid + apartments)
  - fast_b              (rush B rápido)
  - fast_a              (rush A rápido)
  - a_fake_b            (fake A, ir B)
  - b_fake_a            (fake B, ir A)
  - default_spread      (default, espalhar para info)
  - slow_default        (default lento, esperar erros CT)
  - eco_rush            (eco round rush)
  - force_buy_execute   (force buy com execute simples)
  - save                (save round)

CT-Side (10 estratégias):
  - standard_2_1_2      (2A, 1mid, 2B)
  - stack_a             (3+ jogadores A)
  - stack_b             (3+ jogadores B)
  - aggressive_mid      (push mid agressivo)
  - aggressive_a        (push A-main agressivo)
  - passive_default     (todos passivos, esperar info)
  - retake_setup        (setup para retake, poucos no site)
  - anti_eco_push       (push agressivo contra eco)
  - save                (save round)
  - mixed               (setup não standard)
```

---

## Modelo E: Setup Predictor (Transformer)

### Objetivo
Prever a estratégia que o oponente vai usar no próximo round, baseado no histórico do match.

### Input

```
Sequência de rounds anteriores do oponente (max 30 rounds):

Features por round (12 dimensões):
  - strategy_label (encoded)                         (1)
  - economy_state (eco/force/full/save)              (1)
  - score_own (normalizado)                          (1)
  - score_opponent (normalizado)                     (1)
  - side (ct=0, t=1)                                 (1)
  - round_result (won/lost)                          (1)
  - players_alive_at_end (0-5)                       (1)
  - was_bomb_planted (0/1)                           (1)
  - opening_kill_won (0/1)                           (1)
  - equipment_value_ratio (vs opponent, normalizado) (1)
  - round_duration (normalizado)                     (1)
  - consecutive_losses (0-5+)                        (1)

Shape: (batch_size, max_rounds, 12)
Padding: rounds futuros são mascarados
```

### Arquitetura

```python
class SetupPredictor(nn.Module):
    def __init__(self, num_strategies, d_model=64, nhead=4, num_layers=3):
        super().__init__()
        self.input_proj = nn.Linear(12, d_model)
        self.pos_encoding = nn.Embedding(30, d_model)  # max 30 rounds
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=256,
            dropout=0.1,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer, num_layers=num_layers
        )
        self.classifier = nn.Linear(d_model, num_strategies)

    def forward(self, x, mask=None):
        # x: (batch, seq_len, 12)
        batch_size, seq_len, _ = x.shape
        positions = torch.arange(seq_len, device=x.device)
        x = self.input_proj(x) + self.pos_encoding(positions)
        x = self.transformer(x, src_key_padding_mask=mask)
        # Usar output do último round como predição
        last_valid = x[:, -1, :]  # (batch, d_model)
        return self.classifier(last_valid)  # (batch, num_strategies)
```

### Output

```json
{
  "predictions": [
    {"strategy": "b_execute", "probability": 0.35},
    {"strategy": "mid_control_to_a", "probability": 0.25},
    {"strategy": "default_spread", "probability": 0.20},
    {"strategy": "split_a", "probability": 0.12},
    {"strategy": "other", "probability": 0.08}
  ],
  "reasoning": "Após 2 rounds perdidos em A, equipas neste cluster tendem a mudar para B execute (65% histórico). Economia permite full buy.",
  "counter_suggestion": "Considerar stack B com 3 jogadores. AWP em window para cobrir mid rotation."
}
```

---

## Modelo F: Player Rating (CatBoost)

### Objetivo
Rating 0-100 para cada jogador por match, mais granular que HLTV Rating 2.0.

### Input

```
200+ features agregadas por match:

Aim & Mecânica (20 features):
  - kills_per_round, deaths_per_round, kd_ratio
  - headshot_pct, first_bullet_accuracy
  - adr (average damage per round)
  - time_to_kill_avg, spray_accuracy
  - flick_shot_success_rate
  - ...

Posicionamento (30 features):
  - positioning_error_rate (do Modelo A)
  - avg_angles_exposed, avg_cover_distance
  - survival_rate_by_position
  - crosshair_placement_score
  - ...

Utilidade (25 features):
  - flash_assists, enemies_flashed_per_flash
  - smoke_effectiveness_rate (do Modelo B)
  - utility_damage_per_round
  - utility_wasted_rate
  - ...

Game Sense (30 features):
  - opening_duel_win_rate, trade_kill_rate
  - clutch_win_rates (1v1, 1v2, 1v3)
  - timing_error_rate (do Modelo C)
  - info_gathering_efficiency
  - ...

Impacto (20 features):
  - rounds_with_kill, multi_kill_rounds
  - round_win_share, impact_rating
  - entry_success_rate
  - kast_pct
  - ...

Economia (15 features):
  - eco_kills, anti_eco_efficiency
  - buy_accuracy, save_success_rate
  - equipment_value_efficiency
  - ...

Consistência (10 features):
  - rating_std_deviation, clutch_consistency
  - performance_vs_team_avg
  - ...

Sub-ratings calculados (5 outputs):
  - aim_rating (0-100)
  - positioning_rating (0-100)
  - utility_rating (0-100)
  - game_sense_rating (0-100)
  - clutch_rating (0-100)
  - OVERALL_RATING (0-100) — média ponderada
```

### Modelo de Rating

Utiliza **CatBoost**, que lida nativamente com features categóricas como player IDs, mapas e armas sem necessidade de encoding manual. Menos tuning necessário vs XGBoost para dados mistos (numéricos + categóricos).

### Calibração

```
1. Treinar com jogadores pro como referência (rating 70-100)
2. Calibrar contra HLTV Rating 2.0 (correlation target > 0.85)
3. Normalizar para que a média de jogadores semi-pro seja ~50
4. Sub-ratings independentes permitem radar chart
```

---

## Modelo G: Weakness Pattern Detection (UMAP + HDBSCAN)

### Objetivo
Identificar padrões de fraqueza recorrentes e agrupar jogadores em "archetypes" de fraqueza.

### Pipeline

```python
# 1. Computar error vectors por jogador (agregado de vários matches)
error_features = [
    positioning_error_rate_by_map,      # (7 mapas)
    positioning_error_rate_by_side,     # (CT, T)
    utility_waste_rate_by_type,         # (4 tipos granada)
    timing_error_rate_by_situation,     # (peek, rotate, push)
    economy_error_rate,
    trade_failure_rate,
    rotation_speed_percentile,
    crosshair_discipline_score,
    # ... ~50 features totais
]

# 2. Dimensionality reduction
from umap import UMAP
reducer = UMAP(n_components=10, n_neighbors=15, min_dist=0.1)
embedding = reducer.fit_transform(error_features)

# 3. Clustering
from hdbscan import HDBSCAN
clusterer = HDBSCAN(min_cluster_size=50, min_samples=10)
clusters = clusterer.fit_predict(embedding)

# 4. Cluster interpretation (manual + automated)
cluster_profiles = {
    0: "Overaggressive Peeker",    # timing errors: too_early, peek sem flash
    1: "Utility Hoarder",          # morre com utility não usada
    2: "Poor Rotator",             # timing errors em rotações, positioning errors pós-rotate
    3: "Economy Mismanager",       # force buys errados, saves tardios
    4: "Crosshair Discipline",     # crosshair placement baixo, perde first duels
    5: "Site Anchor Issues",       # positioning errors em CT-side holds
    # ... mais clusters emergem dos dados
}
```

### Output: Training Plan Personalizado

```json
{
  "player": "Player1",
  "primary_weakness": {
    "cluster": "Overaggressive Peeker",
    "strength": 0.82,
    "description": "Tendência a fazer peek sem flash e demasiado cedo"
  },
  "secondary_weakness": {
    "cluster": "Utility Hoarder",
    "strength": 0.45,
    "description": "Morre frequentemente com granadas não utilizadas"
  },
  "training_recommendations": [
    {
      "priority": 1,
      "area": "Peek Discipline",
      "description": "Praticar jiggle peeks e shoulder peeks antes de commit",
      "drill": "Deathmatch com regra: só fazer peek com flash ou info prévia",
      "expected_impact": "Redução de 30% em timing errors",
      "current_metric": 0.35,
      "target_metric": 0.20,
      "pro_benchmark": 0.12
    },
    {
      "priority": 2,
      "area": "Utility Usage",
      "description": "Usar granadas antes de morrer, integrar no gameplay",
      "drill": "Praticar 3 lineups por mapa. Em scrims, objetivo: 0 mortes com 2+ granadas",
      "expected_impact": "Redução de 25% em utility waste",
      "current_metric": 0.28,
      "target_metric": 0.15,
      "pro_benchmark": 0.08
    }
  ],
  "progress_tracking": {
    "matches_analyzed": 45,
    "trend": "improving",
    "improvement_rate": "-5% error rate per month"
  }
}
```

---

## Motor de Recomendações

### Arquitetura

```
Output da Deteção de Erros
        │
        ▼
┌───────────────────────────┐
│ Correspondência de        │
│ Templates                 │
│ (200+ templates)          │
│                           │
│ Input: tipo_erro,         │
│   contexto, mapa,         │
│   posição, SHAP           │
│                           │
│ Encontrar template mais   │
│   próximo por contexto    │
└──────────┬────────────────┘
           │
           ▼
┌───────────────────────────┐
│ Preenchimento de Contexto │
│                           │
│ Preencher template com:   │
│ - Posição específica      │
│ - Nomes de callout do mapa│
│ - Nome do jogador         │
│ - Contexto do round       │
│ - Fatores SHAP principais │
└──────────┬────────────────┘
           │
           ▼
┌───────────────────────────┐
│ Referência de Jogadores   │
│ Profissionais             │
│                           │
│ Encontrar situação similar│
│ na base de dados de matchs│
│ pro onde o pro fez bem    │
└──────────┬────────────────┘
           │
           ▼
Output Final de Recomendações
```

### Template Database (Exemplos)

```yaml
# templates/positioning/exposed_multiple_angles.yaml
template_id: "pos_multi_angle_001"
error_type: "positioning"
context_match:
  angles_exposed: ">= 2"
  had_cover_nearby: true
severity: "critical"
description_template: >
  Exposto a {angles} ângulos simultaneamente ({angle_names})
  enquanto segurava {position_callout} em {map}.
  Cover disponível a {cover_distance}m em {cover_callout}.
recommendation_template: >
  Segurar de {cover_callout} para limitar exposição a {max_safe_angles} ângulo(s).
  {conditional: if enemies > 2: "Com {enemies} inimigos vivos, considerar
  reposicionar para {alternative_position} para garantir trade do teammate."}
pro_reference_query:
  map: "{map}"
  position_area: "{position_area}"
  situation: "similar_hold"
  outcome: "survived_or_won_duel"
```

---

## Computação e Custos de Treino

| Modelo | Tipo | GPU | Tempo Treino | Frequência | Custo/Mês |
|--------|------|-----|-------------|------------|-----------|
| A. Positioning Mamba | PyTorch | 1x A10G | ~4h | Mensal | ~$8 |
| B. Utility LightGBM | LightGBM | CPU | ~4min (7x mais rápido) | Mensal | ~$1 |
| C. Timing Mamba | PyTorch | 1x A10G | ~3h | Mensal | ~$6 |
| D. Strategy GraphSAGE GNN | PyG | 1x A10G | ~6h | Mensal | ~$12 |
| E. Setup Transformer | PyTorch | 1x A10G | ~8h | Mensal | ~$16 |
| F. Rating CatBoost | CatBoost | CPU | ~1h | Semanal | ~$4 |
| G. Weakness HDBSCAN | scikit | CPU | ~20min | Semanal | ~$2 |
| **Total** | | | | | **~$50-100** |

*Usando spot instances AWS (g5.xlarge ~$0.50/h spot para A10G)*
*Custo real com overhead (data loading, eval): ~$200-400/mês*

---

## Inferência (Produção)

### BentoML Service

```python
import bentoml
from bentoml.io import JSON

# Cada modelo é um runner separado
positioning_runner = bentoml.pytorch.get("positioning_mamba:latest").to_runner()
utility_runner = bentoml.lightgbm.get("utility_lgbm:latest").to_runner()
timing_runner = bentoml.pytorch.get("timing_mamba:latest").to_runner()
strategy_runner = bentoml.pytorch.get("strategy_gnn:latest").to_runner()
setup_runner = bentoml.pytorch.get("setup_transformer:latest").to_runner()
rating_runner = bentoml.catboost.get("rating_catboost:latest").to_runner()

svc = bentoml.Service("cs2_analytics", runners=[
    positioning_runner, utility_runner, timing_runner,
    strategy_runner, setup_runner, rating_runner
])

@svc.api(input=JSON(), output=JSON())
async def analyze_match(input_data):
    # Executa todos os modelos em paralelo
    errors, tactics, rating = await asyncio.gather(
        detect_errors(input_data),
        classify_tactics(input_data),
        compute_rating(input_data)
    )
    return {"errors": errors, "tactics": tactics, "rating": rating}
```

### Latência Esperada

| Endpoint | Latência (p50) | Latência (p99) |
|----------|---------------|---------------|
| Error detection (por round) | ~50ms | ~150ms |
| Strategy classification | ~30ms | ~100ms |
| Setup prediction | ~20ms | ~80ms |
| Player rating | ~10ms | ~30ms |
| Full match analysis | ~30-60s | ~120s |
