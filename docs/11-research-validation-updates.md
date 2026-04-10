# 11 - Validação de Pesquisa & Atualizações (Março 2026)

Este documento contém os resultados da pesquisa de validação profunda feita a todos os documentos do projeto. Inclui correções, melhorias e decisões atualizadas.

---

## MUDANÇAS CRÍTICAS vs Plano Original

### 1. ML: Substituir LSTM por Mamba (State Space Model)

**Decisão anterior**: LSTM bidirectional para deteção de erros de posicionamento e timing.

**Nova decisão**: **Mamba (MambaAD)** como modelo primário, TCN como ensemble.

**Justificação**:
- Mamba tem complexidade O(n) vs O(n²) do Transformer, sendo mais eficiente
- MambaAD (NeurIPS 2024) foi desenhado especificamente para anomaly detection
- Iguala a capacidade dos Transformers mantendo escalabilidade linear
- Papers de Março 2025 (ASSM, SP-Mamba) mostram Mamba a superar Transformers em deteção de anomalias
- TCN (Temporal Convolutional Networks) como ensemble: 84% mais rápido que LSTM, processamento paralelo

**Impacto nos ficheiros**:
- `02-ml-architecture.md`: Atualizar arquiteturas dos Modelos A e C (LSTM → Mamba)
- `07-ml-training-pipeline.md`: Ajustar configs de treino
- Código: `packages/ml-models/src/error_detection/positioning.py` e `timing.py`

```python
# Nova arquitetura recomendada (Mamba)
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
            nn.Linear(64, 3)
        )

    def forward(self, x):
        x = self.input_proj(x)   # (batch, 64, 128)
        x = self.mamba(x)         # (batch, 64, 128)
        x = x.mean(dim=1)         # (batch, 128) global avg pool
        return self.classifier(x)  # (batch, 3)
```

---

### 2. GNN: Substituir GAT por GraphSAGE

**Decisão anterior**: GATConv (Graph Attention Networks) para strategy classification.

**Nova decisão**: **GraphSAGE** como primário, Heterogeneous GNN como ensemble.

**Justificação**:
- GraphSAGE atinge 98.50% accuracy vs GAT em graph classification
- Mais rápido para treino e inferência
- Framework de aprendizagem indutiva adequado para estados de jogo dinâmicos
- Heterogeneous GNN como adição futura: modela roles de jogadores (IGL, AWP, support) como tipos de nós diferentes

---

### 3. Explicabilidade: Substituir SHAP por Integrated Gradients (para modelos neurais)

**Decisão anterior**: SHAP para todas as explicações.

**Nova decisão**: **Integrated Gradients** para modelos neurais (Mamba, Transformer), **FastTreeSHAP** apenas para modelos de árvore (XGBoost/LightGBM/CatBoost).

**Justificação**:
- SHAP KernelExplainer é demasiado lento para inferência real-time (50ms target)
- Integrated Gradients é 50-100x mais rápido que SHAP para redes neurais
- Requer apenas ~50 computações de gradiente vs centenas de avaliações do modelo
- Sub-10ms por explicação com PyTorch autograd
- FastTreeSHAP (TreeExplainer) é rápido o suficiente para modelos de árvore

**Impacto**:
- `packages/ml-models/src/error_detection/explainer.py` → usar `torch.autograd` para Integrated Gradients
- Manter SHAP apenas no `rating.py` e `utility.py` (XGBoost/LightGBM)

---

### 4. Gradient Boosting: LightGBM + CatBoost substituem XGBoost

**Decisão anterior**: XGBoost para utility errors e player rating.

**Nova decisão**:
- **LightGBM** para utility error model (velocidade de inferência)
- **CatBoost** para player rating model (handling nativo de categorias)
- **Ensemble** dos três para melhor accuracy

**Justificação**:
- LightGBM: 7x mais rápido que XGBoost em treino, leaf-wise growth
- CatBoost: Lida nativamente com features categóricas (player IDs, mapas, armas), menos tuning
- Ensemble (stacking) de XGBoost + LightGBM + CatBoost melhora accuracy

---

### 5. Semi-Supervised: FlexMatch em vez de pseudo-labeling simples

**Decisão anterior**: Pseudo-labeling com confidence threshold fixo (0.9).

**Nova decisão**: **FlexMatch** com Curriculum Pseudo Labeling (CPL).

**Justificação**:
- FlexMatch melhora +13.96% sobre FixMatch em datasets difíceis
- Thresholds dinâmicos por classe (erros de posicionamento vs timing têm perfis diferentes)
- 18.96% redução de erro em datasets com poucos labels
- Melhor com dados extremamente limitados (o nosso caso: 5,000 labels)

---

### 6. Infra: ECS Fargate substitui EKS

**Decisão anterior**: AWS EKS (Kubernetes).

**Nova decisão**: **AWS ECS Fargate** para MVP, migrar para EKS só se necessário.

**Justificação**:
- Elimina $73/mês de control plane
- Setup em 4 horas vs 1+ semana para EKS
- Muito menos overhead operacional para equipa de 2-5 devs
- Auto-scaling, SSL, load balancing incluído
- Migração para EKS é possível mais tarde se necessário

---

### 7. Custos: Estimativa reduzida de $1,380 para $200-300/mês

**Estimativa anterior**: ~$1,380/mês.

**Nova estimativa**: **$200-300/mês** (MVP com 50 equipas).

**Breakdown realista**:
| Componente | Custo |
|-----------|-------|
| ECS Fargate (API + Workers) | ~$60 |
| S3 (demos) | ~$10 |
| RDS PostgreSQL (t3.small) | ~$30 |
| ClickHouse Serverless | ~$50 |
| NAT/ALB/misc | ~$70 |
| ElastiCache Redis | ~$30 |
| **Total** | **~$250/mês** |

**Otimizações**:
- VPC Endpoints para S3/ECR (poupa $30-40/mês em NAT)
- Savings Plans se workload estável (30-50% desconto)
- GPU training: spot instances (~$200/mês adicional quando treinar)

---

### 8. Feature Store: PostgreSQL + Redis substitui Feast

**Decisão anterior**: Feast como feature store.

**Nova decisão**: **PostgreSQL + Redis direto** para MVP, Feast para escala futura.

**Justificação**:
- Menos overhead operacional (sem cluster Feast para gerir)
- Custo mais baixo ($20-50/mês vs $200+/mês)
- Iteração mais rápida (controlar o próprio schema)
- ~100 linhas de Python para sync batch → online
- Migrar para Feast quando ultrapassar limites (1000s de features)

---

## VALIDAÇÃO DO MERCADO (Atualizada)

### Concorrentes Atualizados (Março 2026)

| Plataforma | Tipo | Preço | Funcionalidades AI | Quota de Mercado |
|-----------|------|-------|------------|-------------|
| **Skybox EDGE** | Enterprise | €5.99-€1,299/mês | AI role detection, play detection | 85-90% pro |
| **Leetify** | Individual | ~€6/mês | AI coaching básico | Forte individual |
| **Scope.gg** | Mid-market | Subscription | Demo analysis, highlights | Moderado |
| **Stratmind** | AI-first (NOVO) | Desconhecido | Multi-pass tactical AI | Emergente |
| **StatTrak.xyz** | Free | €0 | AI coach, 47+ métricas, win probability | Crescente |
| **Rankacy** | AI coaching | Desconhecido | Neural network treinada em pro data | Novo |
| **CS2.CAM** | Team recording | Desconhecido | AI audio sync, 2D replay | Novo |
| **Noesis** | Visual analytics | Freemium | Heatmaps, round inspection | Estabelecido |

### Novos Concorrentes a Monitorizar

1. **Stratmind** - AI-first, análise tática multi-pass. Concorrente mais direto.
2. **StatTrak.xyz** - 47+ métricas GRÁTIS com AI coach. Pressiona no tier free.
3. **Rankacy** - Neural network treinada em dados pro. Foco em highlights.

### CS2 Ecosystem (Março 2026)

- **Prize pools**: $32.27M em 2025, 2026 será "ano recorde"
- **24 torneios** com $1M+ em 2026
- **Majors**: IEM Cologne (Junho), PGL Singapore (Novembro), $1.25M cada
- **Viewership**: 1.3M concurrent (IEM Katowice), superou LoL/Valorant/Dota2
- **CS2 ganhou "Esports Game of the Year"** nos Game Awards
- **Cena em crescimento forte** — investimento em analytics é "table-stakes"

### Validação de Preços

Skybox EDGE prova que equipas pagam até **€1,299/mês** por analytics enterprise. Os nossos tiers (€49-€149/mês) estão bem posicionados entre o free (StatTrak) e o enterprise (Skybox).

Salários de equipas pro: €120K-€260K/mês → analytics a €149/mês é investimento negligível.

---

## ATUALIZAÇÃO DO PARSER (CS2 Demo Format)

### TrueView System (Novembro 2025)

Valve introduziu sistema "TrueView" de playback de demos:
- Reconstrói a perspetiva original do jogador mais fielmente
- Limitações: recoil/muzzle flash podem ter 1-2 frames de atraso
- Mais intensivo em CPU/GPU

### Parser Status

- **demoparser2**: v0.41.1 (Fevereiro 2026) — ativamente mantido
- **Awpy**: Funcional com demoparser2 backend, documentação nota "increased error rates" em POV demos
- **Recomendação**: Manter Awpy como primário, monitorizar releases de demoparser2
- **Mitigação**: Abstraction layer sobre Awpy para poder trocar backend se necessário

---

## TABELA RESUMO: TECH STACK ATUALIZADO

| Componente | Plano Original | Atualização | Razão |
|-----------|---------------|------------|-------|
| Error Detection (Sequential) | LSTM | **Mamba (MambaAD)** | O(n) vs O(n²), melhor para anomaly detection |
| Strategy Classification | GATConv | **GraphSAGE** | 98.5% accuracy, mais rápido |
| Explainability (Neural) | SHAP | **Integrated Gradients** | 50-100x mais rápido, sub-10ms |
| Explainability (Trees) | SHAP | **FastTreeSHAP** | Rápido para XGBoost/LightGBM |
| Utility Error Model | XGBoost | **LightGBM** | 7x mais rápido em treino |
| Player Rating Model | XGBoost | **CatBoost** | Handling nativo de categorias |
| Semi-Supervised | Pseudo-labeling | **FlexMatch + CPL** | +14% com dados limitados |
| Container Orchestration | EKS | **ECS Fargate** | -$73/mês, setup 4h vs 1 semana |
| Feature Store | Feast | **PostgreSQL + Redis** | Mais simples, mais barato |
| Custo Mensal (50 equipas) | $1,380 | **$200-300** | Estimativa corrigida |
| Demo Parser | Awpy | **Awpy** (mantido) | Ativamente mantido, v0.41.1 |
| Backend | FastAPI | **FastAPI** (mantido) | 15-20K RPS, production-ready |
| Frontend | Next.js 15 | **Next.js 15** (mantido) | App Router estável, RSC maduro |

---

## AÇÕES NECESSÁRIAS NOS DOCS

| Doc | Ação |
|-----|------|
| `02-ml-architecture.md` | Substituir LSTM→Mamba, GAT→GraphSAGE, SHAP→Integrated Gradients, XGBoost→LightGBM/CatBoost |
| `03-tech-stack.md` | Atualizar tabela de stack, adicionar Mamba, LightGBM, CatBoost |
| `07-ml-training-pipeline.md` | Adicionar FlexMatch, atualizar pseudo-labeling pipeline |
| `09-infrastructure.md` | EKS→ECS Fargate, atualizar custos, remover Feast, simplificar |
| `10-business-model.md` | Adicionar Stratmind, StatTrak, Rankacy como concorrentes, atualizar dados CS2 2026 |

Todas as outras decisões (FastAPI, Next.js 15, PostgreSQL, ClickHouse, BentoML, Redis, D3.js) foram **validadas e confirmadas** como boas escolhas.
