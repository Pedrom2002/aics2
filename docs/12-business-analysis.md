# Análise de Negócio & Estratégia — AI CS2 Analytics

> Documento gerado a partir da análise completa do projeto (11 docs técnicos, ~200KB).
> Estado atual: documentação completa, zero código implementado.
> Data: Março 2026

---

## 1. Valorização do Projeto

### Estado atual vs. potencial

| Estado do Projeto | Valor Estimado |
|-------------------|---------------|
| Só documentação (hoje) | €0 - €3K |
| MVP funcional (3-4 features core) | €15K - €40K |
| Produto com 50 clientes pagantes | €100K - €250K |
| Produto com 200+ clientes e crescimento | €500K - €1.5M |
| Cenário otimista (raro, tração forte) | €2M - €5M |

### Custo de desenvolvimento estimado

| Cenário | Custo | Duração |
|---------|-------|---------|
| Dev solo (tempo próprio) | €0 (custo de oportunidade) | 6-9 meses |
| 1 freelancer ML part-time | €2,000-4,000/mês | 6-9 meses |
| Equipa pequena (2-3 devs) | €8,000-15,000/mês | 3-5 meses |
| Freelancers projeto completo | €80K-150K total | 6-9 meses |

### Nota importante

A documentação em si vale muito pouco comercialmente — qualquer dev sénior pode pesquisar e documentar o mesmo em 2-3 semanas. O valor real só aparece com código funcional + clientes pagantes + métricas de retenção. A maioria dos projetos indie/solo nunca ultrapassa €1K-5K/mês de revenue, o que coloca o valor do negócio em €50K-200K no cenário mais provável.

---

## 2. Estrutura de Preços

### Tiers (revistos)

| Tier | Preço | Demos/mês | Features Principais | Target |
|------|-------|-----------|-------------------|--------|
| **Free** | €0 | 10 | Error detection básico (sem explicações), stats básicas | Trial, jogadores casuais |
| **Solo** | €9/mês | 15 | Ratings, treino personalizado, heatmaps | Jogadores individuais |
| **Team** | €39/mês | 30 | Error detection completo com explicações, 2D replayer, 5 seats | Equipas semi-pro |
| **Pro** | €99-129/mês | Ilimitado | Scout reports, prediction, API access, 15 seats | Equipas profissionais |
| **Enterprise** | €300-800/mês | Ilimitado | Multi-team, SSO, SLA, custom integrations, seats ilimitados | Organizações esports |

### Decisões de pricing

- **Tier Solo (€9) adicionado** — preenche o gap entre Free (€0) e Team (€39), aumenta o funil de conversão
- **Preços reduzidos vs. documentação original** (Team era €49, Pro era €149) — priorizar volume e tração no início
- **Desconto anual**: ~20% (ex: Team €39/mês → €31/mês anual)
- Preços podem subir depois de tração comprovada

### Referência da concorrência

| Concorrente | Preço | Posicionamento |
|------------|-------|---------------|
| Leetify | ~€6/mês | Individual, AI coach básico |
| Skybox EDGE | €5.99-€1,299/mês | Individual a enterprise, líder de mercado |
| StatTrak.xyz | €0 (grátis) | 47+ métricas AI — pressiona free tiers |
| Stratmind | Desconhecido | AI-first, concorrente direto |
| Scope.gg | Subscription | Visual analytics, grenades |

---

## 3. Custos Operacionais

### Infraestrutura MVP (50 equipas)

| Componente | Custo/mês |
|-----------|-----------|
| ECS Fargate (API + Workers) | ~$60 |
| RDS PostgreSQL (t3.small) | ~$30 |
| ClickHouse Serverless | ~$50 |
| ElastiCache Redis | ~$30 |
| S3 (demos storage) | ~$10 |
| NAT/ALB/networking | ~$70 |
| **Subtotal AWS** | **~$250** |
| Stripe fees (3% revenue) | variável |
| Email transacional (SendGrid) | ~$20 |
| Monitoring (Sentry/Datadog) | ~$30-50 |
| MLflow hosting | ~$50-100 |
| GPU treino mensal (spot g5.xlarge) | ~$200 (quando ativo) |
| Domínio + SSL | ~$1 |
| **Total real MVP** | **~$400-600/mês** |

### Infraestrutura Scale (200 equipas)

| Componente | Custo/mês |
|-----------|-----------|
| ECS Fargate (scaled) | ~$200 |
| RDS PostgreSQL (scaled) | ~$100 |
| ClickHouse Cloud | ~$200 |
| Outros serviços AWS | ~$200 |
| GPU training (spot) | ~$100 |
| Serviços terceiros | ~$150-200 |
| **Total** | **~$1,200-1,500/mês** |

### Otimizações possíveis

- VPC Endpoints para S3/ECR: poupa $30-40/mês em NAT
- AWS Savings Plans: 30-50% desconto em workloads estáveis
- GPU spot instances: ~70% mais barato que on-demand

---

## 4. Modelo Financeiro

### Projeção de revenue — cenário realista

#### Mês 6 (após soft launch)

| Tier | Clientes | MRR |
|------|----------|-----|
| Free | 100 | €0 |
| Solo | 30 | €270 |
| Team | 8 | €312 |
| Pro | 1 | €129 |
| **Total** | **139** | **€711** |
| Custos infra | | -€500 |
| **Margem** | | **€211** |

#### Mês 12

| Tier | Clientes | MRR |
|------|----------|-----|
| Free | 500 | €0 |
| Solo | 100 | €900 |
| Team | 30 | €1,170 |
| Pro | 8 | €1,032 |
| Enterprise | 1 | €500 |
| **Total** | **639** | **€3,602** |
| Custos infra | | -€800 |
| **Margem** | | **€2,802** |

#### Resumo anual

| Período | Revenue Realista | Revenue Otimista |
|---------|-----------------|-----------------|
| Ano 1 | €15K-25K | €50K |
| Ano 2 | €50K-100K | €200K |

### Break-even

- **Infraestrutura**: Mês 4-5 (revenue cobre custos AWS)
- **Com equipa**: Provavelmente nunca no Ano 1 se tiveres devs a pagar
- **Solo dev**: Positivo a partir do mês 5-6

### KPIs target

| Métrica | Target |
|---------|--------|
| Free → Paid conversão | 5-8% |
| Churn mensal | < 5% |
| CAC (Customer Acquisition Cost) | < €50 |
| LTV (Lifetime Value) | > €500 |
| LTV/CAC ratio | > 3x |
| ARPU | ~€70 |

---

## 5. Análise de Concorrência

### Concorrentes detalhados

#### Skybox EDGE — Líder de mercado
- **Market share**: ~90% das equipas pro
- **Preço**: €5.99-€1,299/mês
- **Forças**: Standard da indústria, robusto, anos de confiança
- **Fraquezas**: Sem AI profunda, foco em stats tradicionais
- **Ameaça**: ALTA (distribuição e marca)

#### Leetify — Individual focus
- **Preço**: ~€6/mês
- **Forças**: UX excelente, forte freemium, AI coaching básico
- **Fraquezas**: Foco individual, análise de equipa limitada
- **Ameaça**: MÉDIA

#### StatTrak.xyz — Free tier pressure
- **Preço**: €0 (completamente grátis)
- **Forças**: 47+ métricas AI, AI coach, win probability — tudo grátis
- **Fraquezas**: Modelo grátis limita investimento em features avançadas
- **Ameaça**: MÉDIA (pressiona o nosso free tier)

#### Stratmind — Concorrente direto
- **Preço**: Desconhecido
- **Forças**: AI-first, análise tática multi-pass
- **Fraquezas**: Novo, sem market share estabelecido
- **Ameaça**: ALTA (mesmo posicionamento que nós)

#### Outros
- **Scope.gg**: Visual analytics, grenade lineups — ameaça baixa
- **Noesis.gg**: Visualizações bonitas, mais manual — ameaça baixa
- **Rankacy**: Neural networks em dados pro — nicho
- **Bo3.gg**: AI insights emergente — em desenvolvimento

### Nossos diferenciadores

| Gap no mercado | O que oferecemos |
|---------------|-----------------|
| **Explicabilidade** | Ninguém mostra PORQUÊ um erro aconteceu com evidência ML (SHAP/Integrated Gradients) |
| **Treino personalizado** | Clustering de fraquezas (UMAP + HDBSCAN) com planos específicos por jogador |
| **Scout reports auto** | Análise automática de 3 meses de demos → relatório completo |
| **Prediction** | Previsão da estratégia do próximo round com contra-sugestões |

### Janela competitiva

~12 meses antes de Skybox/Leetify adicionarem features AI similares. Se Stratmind ganhar tração primeiro, a janela fecha mais rápido.

---

## 6. Marketing & Aquisição de Clientes

### Canais por ordem de eficácia (custo zero/baixo)

| Canal | Potencial | Exemplo de ação |
|-------|-----------|----------------|
| **Reddit r/cs2** | Alto (viral) | "AI detected 47 positioning errors in NaVi vs FaZe Grand Final" |
| **YouTube/TikTok** | Alto | Clips 30-60s de análise AI de rounds famosos |
| **Discord FACEIT/ESEA** | Médio-Alto | Presença direta nos hubs onde as equipas estão |
| **HLTV forums** | Médio | Posts na comunidade mais hardcore de CS |
| **Twitter/X** | Médio | Análises ao vivo durante Majors |
| **Product Hunt** | Médio (1x) | Launch day para tráfego tech |

### O que NÃO funciona neste nicho

- **Paid ads** — CAC demasiado alto para €9-39/mês
- **Cold email a pro teams** — ignoram, já estão com Skybox
- **Blog SEO genérico** — tráfego lento, conversão baixa

### Estratégia de aquisição

- **Mês 1-4**: Beta PT/BR (mercado natural, língua) via Discord/FACEIT
- **Mês 4-6**: Posts virais durante Major CS2 (IEM Cologne Jun 2026)
- **Mês 6-12**: Referral program (1 mês grátis por referral que pague)
- **Ongoing**: 1 análise AI de jogo pro por semana (Reddit + Twitter)

---

## 7. Estratégia de Lançamento

### Fase 0: Validação (Semanas 1-4) — CRÍTICO

**Objetivo: Confirmar que alguém quer pagar ANTES de escrever código.**

1. **Landing page simples** (1-2 dias)
   - Explica o produto com mockups/screenshots fictícios
   - Botão "Join Beta" que recolhe email
   - Ferramentas: Vercel + Next.js ou Carrd/Framer

2. **Distribuir nos canais:**
   - Reddit r/cs2: "Building an AI tool that explains WHY you lose rounds — would you use it?"
   - HLTV forums, Discord FACEIT PT/BR

3. **Entrevistar 10-15 potenciais clientes** (DMs Discord/Twitter)
   - Coaches de equipas semi-pro
   - Perguntas: "Quanto pagas por analytics? O que falta?"

4. **Critério de go/no-go:**
   - ✅ 200+ emails recolhidos = sinal verde
   - ❌ <50 emails = repensar o produto

### Fase 1: MVP Mínimo (Meses 1-3)

**Scope reduzido — NÃO construir os 7 modelos ML:**

| Incluir no MVP | Deixar para depois |
|---------------|-------------------|
| Upload + parsing demo (Awpy) | Timing errors (Mamba) |
| Stats básicas (KD, ADR, HS%) | Strategy classifier (GraphSAGE) |
| 1 modelo: positioning errors (simplificado) | Setup prediction (Transformer) |
| Heatmaps simples | Weakness clustering (HDBSCAN) |
| Dashboard Next.js | Scout reports automáticos |
| Stripe billing (Solo + Team) | Enterprise tier |

### Fase 2: Beta Fechado (Meses 3-4)

- **Target**: 10-20 equipas, todas grátis
- **Foco**: Equipas PT/BR (FACEIT hubs, GamersClub, Discord)
- **Métricas a monitorar:**

| Métrica | Bom sinal | Red flag |
|---------|-----------|----------|
| Demos uploaded/equipa/semana | >2 | <1 |
| Return visits/semana | >2 | 0-1 |
| "Isto ajudou a melhorar?" | >60% sim | <30% |
| "Pagariam €39/mês?" | >40% sim | <15% |

### Fase 3: Soft Launch (Meses 4-6)

- **Timing**: Lançar durante Major CS2 (IEM Cologne Junho 2026)
- **Ações**: Post Reddit com análise AI do Grand Final, clip viral YouTube/TikTok
- **Target MRR**: €500-1,000

### Fase 4: Crescimento (Meses 6-12)

- Adicionar features por impacto: utility errors → player ratings → scout reports
- Referral program ativo
- Parcerias com torneios regionais (analytics grátis para participantes)
- Content marketing semanal (1 análise AI de jogo pro)
- **Target MRR mês 12**: €2,000-4,000

### Fase 5: Escalar ou Pivotar (Ano 2)

- **Se MRR > €3,000**: Continuar, considerar seed funding (€100-200K)
- **Se MRR < €1,000**: Pivotar (Valorant? Dota 2?) ou vender codebase
- **Alternativa**: Modelo B2B puro (só enterprise, preço alto, menos clientes)

### Cronograma visual

```
Sem 1-4     ████ Validação (landing page + entrevistas)
Mês 1-3     ████████████ MVP (1 modelo ML + dashboard)
Mês 3-4     ████ Beta fechado (10-20 equipas PT/BR)
Mês 4-6     ████████ Soft launch (durante Major CS2)
Mês 6-12    ████████████████████████ Crescimento + novas features
Ano 2       ████████████████████████████████ Escalar ou pivotar
```

---

## 8. Fatores de Risco

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Ninguém quer pagar | Média | Fatal | Fase 0 de validação antes de construir |
| Concorrentes copiam AI | Alta | Alto | Janela de 12 meses, mover rápido |
| Stratmind ganha tração primeiro | Média | Alto | Lançar durante Major, foco PT/BR |
| StatTrak.xyz grátis mata free tier | Média | Médio | Free tier mais generoso, valor no paid |
| 7 modelos ML difíceis de manter | Alta | Médio | MVP com 1 modelo, adicionar gradualmente |
| CS2 perde popularidade | Baixa | Muito alto | Arquitetura reutilizável para Valorant/Dota 2 |
| Valve muda formato de demo | Média | Alto | Camada de abstração no parser |
| Burnout (solo dev) | Alta | Alto | Scope controlado, fases claras |

---

## 9. Dados de Mercado

| Métrica | Valor |
|---------|-------|
| Esports Coaching Market (2024) | $0.6B |
| Projeção 2032 | $3.5B (CAGR 20.5%) |
| AI in Sports CAGR | 24.5% (2026-2033) |
| Equipas CS2 ativas em competições | ~50,000 |
| Equipas pro/semi-pro (Tier 1-3) | ~500 |
| Equipas que usam analytics | 90% dos pro |
| Prize pools CS2 2025 | $32.27M |
| Torneios $1M+ em 2026 | 24 |
| Pico viewership (IEM Katowice) | 1.3M simultâneos |
| Salários equipas pro | €120K-€260K/mês |
| Preferência por subscription | 72.4% |

---

## 10. Decisões Tomadas

| Decisão | Escolha | Razão |
|---------|---------|-------|
| Adicionar tier Solo | ✅ €9/mês | Preencher gap Free→Team, aumentar funil |
| Reduzir preços vs. docs originais | ✅ Team €39, Pro €99-129 | Priorizar volume e tração no início |
| MVP com 1 modelo ML | ✅ Só positioning errors | Reduzir scope, lançar mais rápido |
| Validação antes de código | ✅ Landing page + emails | Evitar 6 meses de trabalho sem mercado |
| Foco inicial PT/BR | ✅ Beta em português | Mercado natural, vantagem linguística |
| Lançamento durante Major | ✅ IEM Cologne Jun 2026 | Máximo interesse e tráfego CS2 |
