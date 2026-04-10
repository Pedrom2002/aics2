# 07 - Pipeline de Treino ML

## Visão Geral do Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    ML TRAINING PIPELINE                         │
├─────────────┬──────────────┬──────────────┬────────────────────┤
│  1. Data    │  2. Labeling │  3. Training │  4. Evaluation     │
│  Collection │              │              │                    │
├─────────────┼──────────────┼──────────────┼────────────────────┤
│ HLTV demos  │ Heurísticas  │ GPU EC2      │ Test set holdout   │
│ FACEIT demos│ Expert annot.│ Hydra configs│ Precision/Recall   │
│ User demos  │ Active learn.│ MLflow track │ Confusion matrix   │
│    ↓        │    ↓         │    ↓         │    ↓               │
│ Awpy parse  │ Label store  │ Model ckpt   │ Metrics gates      │
│ ClickHouse  │ (PostgreSQL) │ (MLflow)     │ (auto pass/fail)   │
│ PostgreSQL + Redis │       │              │                    │
├─────────────┴──────────────┴──────────────┼────────────────────┤
│  5. Registry & Deployment                 │  6. Monitoring     │
├───────────────────────────────────────────┼────────────────────┤
│ MLflow Model Registry                     │ Prediction drift   │
│ BentoML packaging                         │ Latency tracking   │
│ Docker → ECR → ECS Fargate               │ User feedback loop │
│ Canary rollout (10% → 100%)              │ Monthly retrain    │
└───────────────────────────────────────────┴────────────────────┘
```

---

## 1. Recolha de Dados

### Fase 1: Bootstrap Dataset (Semanas 1-4)

```python
# scripts/download_pro_demos.py

"""
Pipeline de recolha de demos profissionais:
1. Scrape match IDs do HLTV (últimos 6 meses, Tier 1-2)
2. Download demo files (.dem) de cada match
3. Validar integridade dos ficheiros
4. Armazenar em S3 com metadata

Target: ~5,000 demos profissionais
Volume: ~500 GB de demos raw
Tempo estimado: 2-3 dias (rate-limited)
"""

import asyncio
from hltv_async_api import Hltv

async def collect_pro_demos():
    hltv = Hltv()

    # 1. Obter matches dos últimos 6 meses
    matches = await hltv.get_results(
        max_results=5000,
        start_date="2025-09-01",
        end_date="2026-03-01"
    )

    # 2. Filtrar por tier (top 30 teams only)
    top_teams = await hltv.get_team_ranking()
    top_team_ids = {t['id'] for t in top_teams[:30]}

    pro_matches = [
        m for m in matches
        if m['team1_id'] in top_team_ids or m['team2_id'] in top_team_ids
    ]

    # 3. Download demos (com rate limiting)
    for match in pro_matches:
        demo_url = await get_demo_url(match['id'])
        if demo_url:
            await download_and_store(demo_url, match)
            await asyncio.sleep(2)  # Rate limit: 1 demo / 2 seg

    # 4. Parse todos os demos
    # (executado como batch job separado)
```

### Fase 2: Parsing em Batch

```python
# scripts/batch_parse.py

"""
Parse batch de todos os demos recolhidos.
Executa em paralelo com Celery workers.

Por demo (~30 seg de parse):
  - ~15M tick rows → ClickHouse
  - ~5K events → ClickHouse
  - Match/round metadata → PostgreSQL
  - 200+ features → PostgreSQL + Redis
"""

from awpy import Demo
from celery import group

def parse_demo_batch(demo_paths: list[str]):
    tasks = group(
        parse_single_demo.s(path) for path in demo_paths
    )
    result = tasks.apply_async()
    return result

@celery_app.task(bind=True, max_retries=3)
def parse_single_demo(self, demo_path: str):
    try:
        demo = Demo(demo_path)

        # Extrair dados
        ticks = demo.ticks        # DataFrame: posições tick-a-tick
        kills = demo.kills        # DataFrame: todos os kills
        damages = demo.damages    # DataFrame: todos os danos
        grenades = demo.grenades  # DataFrame: granadas
        rounds = demo.rounds      # DataFrame: resumo por round

        # Inserir em ClickHouse (bulk insert)
        insert_ticks_clickhouse(ticks, match_id)
        insert_events_clickhouse(kills, damages, grenades, match_id)

        # Inserir metadata em PostgreSQL
        insert_match_metadata(demo.header, rounds, match_id)

        # Computar features
        compute_and_store_features(ticks, kills, damages, grenades, match_id)

    except Exception as e:
        self.retry(exc=e, countdown=60)
```

### Fase 3: Feature Engineering

```python
# packages/feature-engine/src/player_features.py

"""
200+ features computadas por jogador por match.
Organizadas em 7 categorias.
"""

def compute_player_features(match_data: MatchData) -> dict:
    features = {}

    # === AIM & MECÂNICA (20 features) ===
    features['kills_per_round'] = total_kills / total_rounds
    features['deaths_per_round'] = total_deaths / total_rounds
    features['kd_ratio'] = total_kills / max(total_deaths, 1)
    features['headshot_pct'] = headshot_kills / max(total_kills, 1)
    features['adr'] = total_damage / total_rounds
    features['first_bullet_accuracy'] = first_shots_hit / first_shots_fired
    features['spray_transfer_success'] = successful_transfers / transfer_attempts
    features['time_to_kill_avg'] = avg(kill_times)
    features['flick_shot_rate'] = flick_kills / total_kills
    # ... mais 11 features

    # === POSICIONAMENTO (30 features) ===
    features['avg_angles_exposed'] = mean(angles_exposed_per_death)
    features['avg_cover_distance'] = mean(cover_distances)
    features['survival_rate_open_area'] = survived_open / total_open_fights
    features['crosshair_placement_score'] = compute_crosshair_discipline(ticks)
    features['positioning_error_rate'] = positioning_errors / total_situations
    features['time_exposed_to_multiple_angles'] = sum(multi_angle_ticks) / total_alive_ticks
    # ... mais 24 features

    # === UTILIDADE (25 features) ===
    features['flash_assists'] = total_flash_assists
    features['enemies_flashed_per_flash'] = enemies_flashed / flashes_thrown
    features['avg_flash_blind_duration'] = mean(blind_durations)
    features['smoke_effective_rate'] = effective_smokes / smokes_thrown
    features['utility_damage_per_round'] = utility_damage / total_rounds
    features['utility_used_before_death_rate'] = used_before_death / total_deaths
    features['lineup_accuracy'] = compute_lineup_accuracy(grenades)
    # ... mais 18 features

    # === GAME SENSE (30 features) ===
    features['opening_duel_attempts'] = opening_duels
    features['opening_duel_win_rate'] = opening_wins / max(opening_duels, 1)
    features['trade_kill_rate'] = trade_kills / tradeable_situations
    features['trade_death_rate'] = was_traded / total_deaths
    features['clutch_win_rate_1v1'] = clutch_wins_1v1 / clutch_attempts_1v1
    features['clutch_win_rate_1v2'] = clutch_wins_1v2 / clutch_attempts_1v2
    features['clutch_win_rate_1v3plus'] = clutch_wins_1v3 / clutch_attempts_1v3
    features['info_gathering_efficiency'] = info_gained / time_alive
    features['timing_error_rate'] = timing_errors / timed_actions
    # ... mais 21 features

    # === IMPACTO (20 features) ===
    features['rounds_with_kill'] = rwk / total_rounds
    features['multi_kill_rounds'] = multi_kill_rounds / total_rounds
    features['round_win_share'] = compute_win_share(player_actions, round_outcomes)
    features['impact_rating'] = compute_impact(kills, damages, assists, traded_deaths)
    features['entry_success_rate'] = successful_entries / entry_attempts
    features['kast_pct'] = kast_rounds / total_rounds
    # ... mais 14 features

    # === ECONOMIA (15 features) ===
    features['eco_kills'] = kills_on_eco_rounds
    features['anti_eco_efficiency'] = kills_vs_eco / rounds_vs_eco
    features['buy_accuracy'] = correct_buys / total_buy_decisions
    features['save_success_rate'] = successful_saves / save_rounds
    features['equipment_value_efficiency'] = kills / avg_equipment_value
    features['force_buy_win_rate'] = force_wins / force_rounds
    # ... mais 9 features

    # === CONSISTÊNCIA (10 features) ===
    features['rating_std_deviation'] = std(round_ratings)
    features['performance_vs_team_avg'] = player_rating / team_avg_rating
    features['first_half_vs_second_half'] = first_half_rating / second_half_rating
    features['ct_vs_t_performance'] = ct_rating / t_rating
    # ... mais 6 features

    return features  # dict com 200+ features
```

---

## 2. Labeling Pipeline

### Strategy Labels (Semi-Automático)

```python
# packages/ml-models/src/labeling/strategy_labeler.py

"""
Pipeline de labeling de estratégias em 3 fases:
1. Rule-based initial labels (automático)
2. Model-assisted active learning
3. Human review of uncertain cases
"""

class StrategyLabeler:
    def label_round_heuristic(self, round_data: RoundData) -> str:
        """Fase 1: Regras heurísticas para label inicial."""
        positions = round_data.player_positions_at_15s  # 15 seg após freeze
        bomb_carrier_pos = round_data.bomb_carrier_position

        if round_data.side == 't':
            # Detetar executes (4+ jogadores no mesmo site)
            a_site_count = count_players_in_area(positions, 'a_site_approach')
            b_site_count = count_players_in_area(positions, 'b_site_approach')

            if a_site_count >= 4:
                if round_data.time_of_first_kill < 20:
                    return 'fast_a'
                return 'a_execute'
            elif b_site_count >= 4:
                if round_data.time_of_first_kill < 20:
                    return 'fast_b'
                return 'b_execute'
            elif count_players_in_area(positions, 'mid') >= 2:
                if a_site_count >= 2:
                    return 'mid_control_to_a'
                elif b_site_count >= 2:
                    return 'mid_control_to_b'
                return 'split_a'  # ou split_b baseado em movimento posterior

            # Default ou eco
            if round_data.buy_type in ('eco', 'force'):
                return 'eco_rush' if round_data.time_of_first_contact < 25 else 'force_buy_execute'

            spread = compute_spread(positions)
            if spread > SPREAD_THRESHOLD:
                return 'default_spread'
            return 'slow_default'

        else:  # CT side
            # Contar jogadores por zona
            a_count = count_players_in_area(positions, 'a_site')
            b_count = count_players_in_area(positions, 'b_site')
            mid_count = count_players_in_area(positions, 'mid')

            if a_count >= 3: return 'stack_a'
            if b_count >= 3: return 'stack_b'
            if a_count == 2 and b_count == 2: return 'standard_2_1_2'
            # ... mais regras

    def active_learning_phase(self, model, unlabeled_data):
        """Fase 2: Modelo prediz, humanos corrigem casos incertos."""
        predictions = model.predict_proba(unlabeled_data)

        # Selecionar os 500 mais incertos para review humano
        uncertainty = 1 - predictions.max(axis=1)
        most_uncertain_idx = uncertainty.argsort()[-500:]

        review_queue = [
            {
                'round_data': unlabeled_data[i],
                'model_prediction': predictions[i].argmax(),
                'confidence': predictions[i].max(),
                'top_3': get_top_3(predictions[i])
            }
            for i in most_uncertain_idx
        ]

        return review_queue  # Enviado para interface de review
```

### Error Labels (Mais Complexo)

```python
# packages/ml-models/src/labeling/error_labeler.py

"""
Pipeline de labeling de erros em 3 rounds:
Round 1: Pseudo-labels heurísticos
Round 2: Expert annotation (2-3 high-rank players)
Round 3: Semi-supervised expansion
"""

class ErrorLabeler:
    def generate_pseudo_labels(self, round_data: RoundData) -> list[ErrorCandidate]:
        """Round 1: Gerar candidatos a erro usando heurísticas."""
        candidates = []

        for death in round_data.deaths:
            player_state = get_player_state_at_tick(death.tick)

            # === Positioning Error Candidates ===
            angles_exposed = count_exposed_angles(
                player_state.position,
                round_data.map,
                COMMON_ANGLE_POSITIONS[round_data.map]
            )
            cover_dist = distance_to_nearest_cover(
                player_state.position,
                COVER_POSITIONS[round_data.map]
            )
            teammate_dist = nearest_teammate_distance(
                player_state.position,
                round_data.alive_teammates_positions(death.tick)
            )

            if angles_exposed >= 2 and cover_dist > 5.0:
                candidates.append(ErrorCandidate(
                    type='positioning',
                    severity='critical' if angles_exposed >= 3 else 'major',
                    tick=death.tick,
                    player=death.victim,
                    features={
                        'angles_exposed': angles_exposed,
                        'cover_distance': cover_dist,
                        'teammate_distance': teammate_dist
                    }
                ))
            elif angles_exposed >= 2 or cover_dist > 8.0:
                candidates.append(ErrorCandidate(
                    type='positioning',
                    severity='minor',
                    tick=death.tick,
                    player=death.victim,
                    features={...}
                ))

            # === Utility Error Candidates ===
            utility_remaining = player_state.utility_count
            if utility_remaining >= 2:
                candidates.append(ErrorCandidate(
                    type='utility',
                    severity='major',
                    tick=death.tick,
                    player=death.victim,
                    features={
                        'utility_remaining': utility_remaining,
                        'utility_types': player_state.utility_types
                    }
                ))

            # === Timing Error Candidates ===
            if death.tick - round_data.last_teammate_death_tick < 32:  # 0.5s
                # Peeked immediately after teammate died (no trade potential)
                candidates.append(ErrorCandidate(
                    type='timing',
                    severity='major',
                    tick=death.tick,
                    player=death.victim,
                    features={
                        'time_after_teammate_death': (death.tick - round_data.last_teammate_death_tick) / 64
                    }
                ))

        # Filtro: Verificar se jogadores pro na mesma posição/contexto
        # não morrem (reduz false positives)
        filtered = self.filter_with_pro_baseline(candidates)

        return filtered

    def expert_review_interface(self, candidates: list[ErrorCandidate]):
        """
        Round 2: Interface para experts reviewarem candidatos.
        Exportar para CSV/Google Sheets ou custom web UI.

        Colunas:
        - match_id, round, tick, player
        - heuristic_type, heuristic_severity
        - 2D map screenshot at tick
        - kill feed context
        - CONFIRM (yes/no)
        - CORRECTED_TYPE
        - CORRECTED_SEVERITY
        - NOTES

        Target: 5,000 reviewed candidates
        Estimativa: 2-3 experts, ~2 semanas, ~100 reviews/hora
        """
        pass

    def semi_supervised_expansion(self, model, labeled_data, unlabeled_data):
        """
        Round 3: FlexMatch com Curriculum Pseudo Labeling (CPL).
        Em vez de threshold fixo (0.9), usa thresholds dinâmicos por classe.
        Melhora +13.96% sobre FixMatch em datasets difíceis.
        18.96% redução de erro com dados limitados.
        """
        from torch.utils.data import DataLoader

        # FlexMatch: thresholds dinâmicos por classe
        num_classes = model.num_classes
        class_thresholds = np.ones(num_classes) * 0.95  # threshold inicial alto
        class_counts = np.zeros(num_classes)

        # Treinar com labeled data
        model.fit(labeled_data.X, labeled_data.y)

        # Curriculum Pseudo Labeling: iterar em múltiplas rondas
        expanded_X = labeled_data.X.copy()
        expanded_y = labeled_data.y.copy()

        for iteration in range(5):  # 5 rondas de curriculum
            predictions = model.predict_proba(unlabeled_data.X)
            max_probs = predictions.max(axis=1)
            pred_classes = predictions.argmax(axis=1)

            # FlexMatch: threshold adaptativo por classe
            # Classes com menos exemplos pseudo-labeled têm threshold mais baixo
            selected_mask = np.zeros(len(predictions), dtype=bool)
            for c in range(num_classes):
                class_mask = pred_classes == c
                # Threshold adaptativo: reduz para classes sub-representadas
                adaptive_threshold = class_thresholds[c] * (
                    class_counts[c] / max(class_counts.max(), 1)
                ) if class_counts.max() > 0 else class_thresholds[c]
                adaptive_threshold = max(adaptive_threshold, 0.7)  # mínimo 0.7

                selected_mask |= (class_mask & (max_probs > adaptive_threshold))
                class_counts[c] += (class_mask & (max_probs > adaptive_threshold)).sum()

            if selected_mask.sum() == 0:
                break

            new_X = unlabeled_data.X[selected_mask]
            new_y = pred_classes[selected_mask]

            expanded_X = np.concatenate([expanded_X, new_X])
            expanded_y = np.concatenate([expanded_y, new_y])

            # Remover do unlabeled
            unlabeled_data.X = unlabeled_data.X[~selected_mask]

            # Re-treinar com dados expandidos
            model.fit(expanded_X, expanded_y)

            # Atualizar thresholds (curriculum: relaxar gradualmente)
            class_thresholds *= 0.95  # Reduzir thresholds 5% por iteração

            print(f"Iteration {iteration+1}: {len(expanded_y)} total labels "
                  f"({selected_mask.sum()} new)")

        return expanded_X, expanded_y
```

---

## 3. Fluxo de Treino

### Configuração com Hydra

```yaml
# packages/ml-models/src/training/configs/positioning_mamba.yaml
model:
  name: positioning_mamba
  type: mamba
  d_model: 128
  d_state: 16
  d_conv: 4
  expand: 2
  input_size: 18
  num_classes: 3

training:
  batch_size: 256
  learning_rate: 0.001
  weight_decay: 0.0001
  max_epochs: 100
  early_stopping_patience: 10
  optimizer: adam
  scheduler: cosine_annealing
  gradient_clip_norm: 1.0

data:
  train_split: 0.7
  val_split: 0.15
  test_split: 0.15
  window_size: 64  # ticks
  features: 18
  augmentation:
    noise_std: 0.01
    time_shift_max: 8  # ticks

mlflow:
  experiment_name: "positioning_error_detection"
  tracking_uri: "http://mlflow.internal:5000"

compute:
  gpu: true
  instance_type: "g5.xlarge"  # A10G
  spot: true
```

### Script de Treino

```python
# packages/ml-models/src/training/train_error_detection.py

import hydra
from omegaconf import DictConfig
import mlflow
import torch
from torch.utils.data import DataLoader

@hydra.main(config_path="configs", config_name="positioning_lstm")
def train(cfg: DictConfig):
    # MLflow tracking
    mlflow.set_tracking_uri(cfg.mlflow.tracking_uri)
    mlflow.set_experiment(cfg.mlflow.experiment_name)

    with mlflow.start_run():
        # Log hyperparameters
        mlflow.log_params({
            "model_type": cfg.model.type,
            "hidden_size": cfg.model.hidden_size,
            "num_layers": cfg.model.num_layers,
            "batch_size": cfg.training.batch_size,
            "learning_rate": cfg.training.learning_rate,
            "window_size": cfg.data.window_size,
        })

        # Data loading
        train_dataset = PositioningDataset(split='train', cfg=cfg.data)
        val_dataset = PositioningDataset(split='val', cfg=cfg.data)

        train_loader = DataLoader(train_dataset, batch_size=cfg.training.batch_size,
                                  shuffle=True, num_workers=4, pin_memory=True)
        val_loader = DataLoader(val_dataset, batch_size=cfg.training.batch_size,
                                num_workers=4, pin_memory=True)

        # Model
        model = PositioningErrorModel(cfg.model).cuda()
        optimizer = torch.optim.Adam(model.parameters(),
                                     lr=cfg.training.learning_rate,
                                     weight_decay=cfg.training.weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=cfg.training.max_epochs
        )
        criterion = torch.nn.CrossEntropyLoss(
            weight=torch.tensor([1.0, 2.0, 5.0]).cuda()  # Peso maior para critical errors
        )

        # Training loop
        best_val_f1 = 0
        patience_counter = 0

        for epoch in range(cfg.training.max_epochs):
            # Train
            model.train()
            train_loss = 0
            for batch_x, batch_y in train_loader:
                batch_x, batch_y = batch_x.cuda(), batch_y.cuda()
                optimizer.zero_grad()
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.training.gradient_clip_norm)
                optimizer.step()
                train_loss += loss.item()

            # Validate
            model.eval()
            val_preds, val_targets = [], []
            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_x = batch_x.cuda()
                    outputs = model(batch_x)
                    val_preds.extend(outputs.argmax(dim=1).cpu().numpy())
                    val_targets.extend(batch_y.numpy())

            # Metrics
            precision = precision_score(val_targets, val_preds, average='weighted')
            recall = recall_score(val_targets, val_preds, average='weighted')
            f1 = f1_score(val_targets, val_preds, average='weighted')

            mlflow.log_metrics({
                "train_loss": train_loss / len(train_loader),
                "val_precision": precision,
                "val_recall": recall,
                "val_f1": f1,
                "learning_rate": scheduler.get_last_lr()[0]
            }, step=epoch)

            # Early stopping
            if f1 > best_val_f1:
                best_val_f1 = f1
                patience_counter = 0
                torch.save(model.state_dict(), "best_model.pt")
                mlflow.pytorch.log_model(model, "model")
            else:
                patience_counter += 1
                if patience_counter >= cfg.training.early_stopping_patience:
                    break

            scheduler.step()

        # Final evaluation on test set
        test_dataset = PositioningDataset(split='test', cfg=cfg.data)
        test_metrics = evaluate_model(model, test_dataset)
        mlflow.log_metrics({f"test_{k}": v for k, v in test_metrics.items()})

        # Log confusion matrix
        mlflow.log_figure(
            plot_confusion_matrix(test_metrics['confusion_matrix'],
                                  labels=['no_error', 'minor', 'critical']),
            "confusion_matrix.png"
        )

if __name__ == "__main__":
    train()
```

### Pipeline ML com GitHub Actions

```yaml
# .github/workflows/ml-pipeline.yml
name: ML Training Pipeline

on:
  workflow_dispatch:
    inputs:
      model:
        description: 'Model to train'
        required: true
        type: choice
        options:
          - positioning_mamba
          - utility_lightgbm
          - timing_mamba
          - strategy_graphsage
          - setup_transformer
          - rating_catboost
          - all
  schedule:
    - cron: '0 2 1 * *'  # Primeiro dia de cada mês às 2h

jobs:
  train:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-west-1

      - name: Start GPU instance
        id: gpu
        run: |
          INSTANCE_ID=$(aws ec2 run-instances \
            --image-id ami-xxx \
            --instance-type g5.xlarge \
            --spot \
            --key-name ml-training \
            --output text --query 'Instances[0].InstanceId')
          echo "instance_id=$INSTANCE_ID" >> $GITHUB_OUTPUT

      - name: Run training
        run: |
          ssh ec2-user@${{ steps.gpu.outputs.ip }} << 'EOF'
            cd /workspace
            git pull
            pip install -e packages/ml-models
            python -m training.train_error_detection \
              --config-name=${{ inputs.model }}
          EOF

      - name: Evaluate model
        run: |
          # Check metrics gates
          python scripts/check_model_metrics.py \
            --model=${{ inputs.model }} \
            --min-precision=0.85 \
            --min-recall=0.70

      - name: Register model
        if: success()
        run: |
          python scripts/register_model.py \
            --model=${{ inputs.model }} \
            --stage=staging

      - name: Terminate GPU instance
        if: always()
        run: |
          aws ec2 terminate-instances \
            --instance-ids ${{ steps.gpu.outputs.instance_id }}
```

---

## 4. Avaliação & Portas de Métricas

### Critérios por Modelo

| Modelo | Métrica Principal | Gate | Secundária | Gate |
|--------|------------------|------|------------|------|
| Positioning Mamba | Precision (weighted) | > 0.85 | Recall (weighted) | > 0.70 |
| Utility LightGBM | Precision (weighted) | > 0.85 | F1 (weighted) | > 0.77 |
| Timing Mamba | Precision (weighted) | > 0.85 | Recall (weighted) | > 0.70 |
| Strategy GraphSAGE | Accuracy (top-1) | > 0.80 | Top-3 accuracy | > 0.95 |
| Setup Transformer | Top-3 accuracy | > 0.75 | Top-1 accuracy | > 0.50 |
| Rating CatBoost | Correlation vs HLTV | > 0.85 | MAE | < 5.0 |
| Weakness HDBSCAN | Silhouette score | > 0.40 | Cluster stability | > 0.80 |

### Script de Avaliação

```python
# scripts/check_model_metrics.py

def check_metrics(model_name: str, run_id: str):
    """Verificar se modelo passa os gates de qualidade."""
    client = mlflow.tracking.MlflowClient()
    run = client.get_run(run_id)
    metrics = run.data.metrics

    gates = METRIC_GATES[model_name]

    passed = True
    for metric_name, threshold in gates.items():
        actual = metrics.get(f"test_{metric_name}")
        if actual is None or actual < threshold:
            print(f"FAIL: {metric_name} = {actual} < {threshold}")
            passed = False
        else:
            print(f"PASS: {metric_name} = {actual} >= {threshold}")

    # Comparar com modelo em produção
    production_model = client.get_latest_versions(model_name, stages=["production"])
    if production_model:
        prod_metrics = client.get_run(production_model[0].run_id).data.metrics
        for key in gates:
            improvement = metrics.get(f"test_{key}", 0) - prod_metrics.get(f"test_{key}", 0)
            print(f"vs production: {key} {'improved' if improvement > 0 else 'regressed'} by {improvement:.4f}")

    return passed
```

---

## 5. Registo de Modelos & Deploy

### Registo de Modelos MLflow

```
Ciclo de Vida do Modelo:
  Nenhum → Staging → Produção → Arquivado

Staging:
  - Modelo passa portas de métricas
  - Registado automaticamente pelo pipeline
  - Executar testes de integração

Produção:
  - Aprovação manual OU automática (se métricas > produção + 1%)
  - Deploy via BentoML → Docker → ECS Fargate

Arquivado:
  - Versão anterior quando nova entra em Produção
  - Mantida 6 meses para rollback
```

### Empacotamento BentoML

```python
# packages/ml-models/src/serving/bentoml_service.py

import bentoml

# Registar modelo no BentoML a partir do MLflow
def register_from_mlflow(model_name: str, mlflow_run_id: str):
    """Importar modelo do MLflow para BentoML."""
    if 'mamba' in model_name or 'graphsage' in model_name or 'transformer' in model_name:
        model = mlflow.pytorch.load_model(f"runs:/{mlflow_run_id}/model")
        bentoml.pytorch.save_model(model_name, model)
    elif 'lightgbm' in model_name:
        model = mlflow.lightgbm.load_model(f"runs:/{mlflow_run_id}/model")
        bentoml.lightgbm.save_model(model_name, model)
    elif 'catboost' in model_name:
        model = mlflow.catboost.load_model(f"runs:/{mlflow_run_id}/model")
        bentoml.catboost.save_model(model_name, model)
```

### Deploy Canário

```yaml
# infra/ecs/canary-deployment.yaml
# 1. Deploy nova versão com 10% do tráfego
# 2. Monitorizar métricas durante 1 hora
# 3. Se OK: aumentar para 50% durante 2 horas
# 4. Se OK: rollout completo (100%)
# 5. Se problemas: rollback automático
```

---

## 6. Monitorização

### Deteção de Drift nas Predições

```python
# packages/ml-models/src/monitoring/drift_detector.py

"""
Monitorizar mudanças na distribuição de predições.
Se drift significativo → alertar e agendar retrain.
"""

from evidently.metrics import DataDriftMetric
from evidently.report import Report

def check_prediction_drift(reference_data, current_data):
    report = Report(metrics=[DataDriftMetric()])
    report.run(reference_data=reference_data, current_data=current_data)

    drift_score = report.as_dict()['metrics'][0]['result']['drift_score']

    if drift_score > 0.15:  # 15% drift threshold
        send_alert("Prediction drift detected", drift_score)
        schedule_retrain()

    return drift_score
```

### Ciclo de Feedback do Utilizador

```python
# Backend endpoint para analysts flaggarem predições erradas

@app.post("/api/v1/errors/{error_id}/feedback")
async def submit_error_feedback(
    error_id: UUID,
    feedback: ErrorFeedback,
    user: User = Depends(get_current_user)
):
    """
    feedback.correct: bool  — O erro está correto?
    feedback.corrected_type: str  — Se errado, qual deveria ser?
    feedback.corrected_severity: str
    feedback.notes: str

    Este feedback é armazenado e usado no próximo ciclo de treino
    para melhorar o modelo.
    """
    await store_feedback(error_id, feedback, user.id)

    # Se acumulou 100+ feedbacks negativos → agendar retrain
    negative_count = await count_negative_feedbacks_since_last_train()
    if negative_count >= 100:
        schedule_retrain(priority="high")
```

---

## Cronograma de Treino

| Atividade | Frequência | Trigger |
|-----------|-----------|---------|
| Feature extraction | Diário (novos demos) | Novo demo processado |
| Positioning Mamba | Mensal | Schedule + dados novos |
| Utility LightGBM | Mensal | Schedule |
| Timing Mamba | Mensal | Schedule |
| Strategy GraphSAGE | Mensal | Schedule |
| Setup Transformer | Mensal | Schedule |
| Rating CatBoost | Semanal | Novos matches processados |
| Weakness Clustering | Semanal | Novos ratings calculados |
| Drift check | Diário | Automático |
| Emergency retrain | Ad-hoc | 100+ negative feedbacks |
