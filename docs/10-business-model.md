# 10 - Modelo de Negócio & Análise Competitiva

## Mercado

### Dimensão do Mercado

| Métrica | Valor | Fonte |
|---------|-------|-------|
| Esports Coaching Services Market (2024) | $0.6B | FutureDataStats |
| Projeção 2032 | $3.5B (CAGR 20.5%) | FutureDataStats |
| AI in Sports Market (esports segment CAGR) | 24.5% (2026-2033) | Market.us |
| Uso por equipas profissionais | 43.6% das plataformas | Market.us |
| Preferência por modelo subscription | 72.4% | Market.us |

### CS2 Específico

- CS2 é o FPS competitivo mais jogado no mundo
- ~50,000 equipas ativas em competições (FACEIT, ESEA, torneiros regionais)
- ~500 equipas profissionais/semi-profissionais (Tier 1-3)
- 90% das equipas pro usam alguma ferramenta de análise
- Crescimento do esports em geral: ~15% ano
- **Prize pools 2025**: $32.27M em 2025; 2026 será "ano recorde"
- **2026**: 24 torneios com prize pool $1M+
- **Majors 2026**: IEM Cologne (Junho) e PGL Singapore (Novembro), $1.25M cada
- **Viewership**: 1.3M concurrent viewers no IEM Katowice — superou LoL, Valorant e Dota2
- CS2 ganhou **"Esports Game of the Year"** nos Game Awards
- Cena em crescimento forte — investimento em analytics é **"table-stakes"**

---

## Análise Competitiva

### Skybox EDGE

| Aspeto | Detalhe |
|--------|---------|
| **Market share** | ~90% equipas pro |
| **Foco** | Análise de equipa, prep de jogo |
| **Pontos fortes** | Standard da indústria, robusto, confiável |
| **Pontos fracos** | Sem AI profundo, focado em stats tradicionais |
| **Pricing** | €5.99-€1,299/mês; AI role detection, play detection |

### Leetify

| Aspeto | Detalhe |
|--------|---------|
| **Foco** | Melhoria individual de jogador, AI coach |
| **Pontos fortes** | UX excelente, freemium forte, AI coaching básico |
| **Pontos fracos** | Focado no individual, análise de equipa limitada |
| **Pricing** | ~€6/mês, AI coaching básico |

### Scope.gg

| Aspeto | Detalhe |
|--------|---------|
| **Foco** | Análise de demos, clips de destaques, lineups de granadas |
| **Pontos fortes** | Interface visual rica, boa biblioteca de granadas |
| **Pontos fracos** | Análise tática limitada, sem predição |
| **Pricing** | Subscription-based |

### Noesis.gg

| Aspeto | Detalhe |
|--------|---------|
| **Foco** | Visual analytics interativas |
| **Pontos fortes** | Visualizações bonitas, bom para pesquisa de oponentes |
| **Pontos fracos** | Menos funcionalidades de AI, mais manual |
| **Pricing** | Freemium |

### Bo3.gg

| Aspeto | Detalhe |
|--------|---------|
| **Foco** | Insights com AI, deteção de padrões |
| **Pontos fortes** | Emergente com AI, comparação de equipas |
| **Pontos fracos** | Novo no mercado, funcionalidades em desenvolvimento |

### Stratmind (NOVO - Concorrente Direto)

| Aspeto | Detalhe |
|--------|---------|
| **Foco** | AI-first, análise tática multi-pass |
| **Pontos fortes** | Multi-pass tactical AI, emergente |
| **Pontos fracos** | Novo, sem quota de mercado estabelecida |
| **Pricing** | Desconhecido |
| **Ameaça** | ALTA — concorrente mais direto ao nosso produto |

### StatTrak.xyz (NOVO - Pressão no Free Tier)

| Aspeto | Detalhe |
|--------|---------|
| **Foco** | Free AI analytics com 47+ métricas |
| **Pontos fortes** | GRÁTIS, AI coach, probabilidade de vitória |
| **Pontos fracos** | Modelo free limita investimento em funcionalidades avançadas |
| **Pricing** | €0 (free) |
| **Ameaça** | MÉDIA — pressiona o nosso tier free a ser mais generoso |

### Rankacy (NOVO)

| Aspeto | Detalhe |
|--------|---------|
| **Foco** | AI coaching com neural network |
| **Pontos fortes** | Rede neural treinada em dados pro, destaques |
| **Pontos fracos** | Novo, foco limitado |
| **Pricing** | Desconhecido |

### CS2.CAM (NOVO)

| Aspeto | Detalhe |
|--------|---------|
| **Foco** | Gravação de equipa e replay |
| **Pontos fortes** | AI audio sync, replay 2D |
| **Pontos fracos** | Foco estreito em gravação |
| **Pricing** | Desconhecido |

---

## Lacunas no Mercado (Nossa Oportunidade)

### 1. AI Error Detection com Explicações (NINGUÉM faz bem)

**Gap**: Plataformas existentes mostram STATS (headshot %, KD, ADR) mas não detetam ERROS específicos com explicação do PORQUÊ.

**Nossa solução**: ML deteta erros de posicionamento, utilidade e timing, com SHAP explanations que dizem exatamente o que correu mal e como corrigir.

**Exemplo de diferenciação**:
- Leetify: "Your positioning score is 65/100"
- Nós: "Round 14: Estavas exposto a A-main e palace simultaneamente. Segura de ticket booth para limitar a 1 ângulo. device fez isto na mesma situação vs Astralis."

### 2. Soluções Individuais por Jogador (NINGUÉM personaliza assim)

**Gap**: Plataformas dão stats genéricas. Nenhuma cria training plans personalizados baseados em padrões de fraqueza detetados por ML.

**Nossa solução**: Weakness clustering (UMAP + HDBSCAN) identifica o "archetype" de fraqueza de cada jogador e gera drills específicos com métricas de progresso.

### 3. Análise Tática Preditiva (MUITO limitado)

**Gap**: Nenhuma plataforma prediz o que o oponente vai fazer no próximo round baseado em padrões históricos.

**Nossa solução**: Transformer que analisa sequência de rounds e prediz estratégia provável, com sugestões de contra-estratégia.

### 4. Scout Reports Automáticos (Parcial)

**Gap**: Equipas gastam horas a preparar scout reports manualmente. Nenhuma plataforma gera reports completos automaticamente com ML.

**Nossa solução**: Pipeline automático que analisa últimos 3 meses de demos do oponente e gera report com tendências, fraquezas exploráveis e sugestões.

---

## Modelo de Preços

### Tiers

```
┌─────────────────────────────────────────────────────────────┐
│                        FREE                                  │
│  Para jogadores individuais e equipas a experimentar         │
├─────────────────────────────────────────────────────────────┤
│  ✓ 5 demos/mês                                              │
│  ✓ Stats básicas (KD, ADR, HS%)                             │
│  ✓ Scoreboard detalhado                                      │
│  ✓ Economy graph básico                                      │
│  ✗ Error detection                                           │
│  ✗ Tactical analysis                                         │
│  ✗ Scout reports                                             │
│  ✗ Training plans                                            │
│                                                              │
│  Preço: €0/mês                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       TEAM                                   │
│  Para equipas semi-profissionais e amateur                   │
├─────────────────────────────────────────────────────────────┤
│  ✓ 30 demos/mês                                              │
│  ✓ Tudo do Free                                              │
│  ✓ Error detection (positioning + utility + timing)          │
│  ✓ Recomendações personalizadas por jogador                  │
│  ✓ Player ratings + radar chart                              │
│  ✓ Heatmaps interativos                                      │
│  ✓ 2D Replayer                                               │
│  ✓ 1 scout report/mês                                        │
│  ✓ 5 user seats                                              │
│                                                              │
│  Preço: €49/mês (anual: €39/mês)                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     PRO                                      │
│  Para equipas profissionais e organizações                   │
├─────────────────────────────────────────────────────────────┤
│  ✓ Demos ilimitados                                          │
│  ✓ Tudo do Team                                              │
│  ✓ Análise tática preditiva (setup prediction)               │
│  ✓ Scout reports ilimitados                                  │
│  ✓ Training plans com tracking de progresso                  │
│  ✓ Weakness clustering avançado                              │
│  ✓ Processamento prioritário                                 │
│  ✓ Export PDF de reports                                     │
│  ✓ API access                                                │
│  ✓ 15 user seats                                             │
│  ✓ Suporte prioritário                                       │
│                                                              │
│  Preço: €149/mês (anual: €119/mês)                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   ENTERPRISE                                 │
│  Para organizações esports multi-equipa                      │
├─────────────────────────────────────────────────────────────┤
│  ✓ Tudo do Pro                                               │
│  ✓ Múltiplas equipas/rosters                                 │
│  ✓ Lugares de utilizador ilimitados                          │
│  ✓ Integrações personalizadas                                │
│  ✓ Suporte dedicado + onboarding                             │
│  ✓ Treino de modelos personalizado                           │
│  ✓ SLA (99.9% uptime)                                       │
│  ✓ SSO (SAML/OAuth)                                         │
│                                                              │
│  Preço: Custom (€500-2000/mês)                              │
└─────────────────────────────────────────────────────────────┘
```

> **Validação de pricing**: Skybox EDGE prova que equipas pagam até €1,299/mês por analytics enterprise. Os nossos tiers (€49-€149/mês) estão bem posicionados entre o free (StatTrak) e o enterprise (Skybox). Salários de equipas pro: €120K-€260K/mês → analytics a €149/mês é investimento negligível.

---

## Projeções de Receita

### Cenário Conservador (Ano 1)

```
Mês 1-3 (Beta):
  - 10 equipas free (testing)
  - 0 receita
  - Custo: ~$300/mês

Mês 4-6 (Soft Launch):
  - 50 free, 10 Team, 2 Pro
  - Receita: (10 × €49) + (2 × €149) = €788/mês
  - Custo: ~$300/mês

Mês 7-9 (Growth):
  - 150 free, 30 Team, 8 Pro, 1 Enterprise
  - Receita: (30 × €49) + (8 × €149) + (1 × €800) = €3,462/mês
  - Custo: ~$500/mês

Mês 10-12 (Scale):
  - 500 free, 80 Team, 20 Pro, 3 Enterprise
  - Receita: (80 × €49) + (20 × €149) + (3 × €800) = €8,300/mês
  - Custo: ~$800/mês

ARR fim do Ano 1: ~€100,000
```

### Cenário Otimista (Ano 2)

```
  - 2,000 free, 300 Team, 80 Pro, 10 Enterprise
  - MRR: (300 × €49) + (80 × €149) + (10 × €800) = €34,620/mês
  - ARR: ~€415,000
  - Custos: ~$1,500/mês infra + $15,000/mês equipa
```

---

## Estratégia de Entrada no Mercado

### Fase 1: Beta Fechada (Mês 1-3)

```
1. Recrutar 5-10 equipas semi-pro para beta testing
   - Oferecer acesso gratuito em troca de feedback
   - Contactar via Discord communities, FACEIT hubs
   - Foco em equipas portuguesas/brasileiras (mercado natural)

2. Iterar no produto baseado em feedback
   - Quais features são mais valiosas?
   - Que erros o ML deteta corretamente?
   - UX issues?

3. Começar content marketing
   - Blog posts: "Como a IA deteta erros de posicionamento"
   - Clips de análise partilhados no Twitter/X
```

### Fase 2: Soft Launch (Mês 4-6)

```
1. Launch público com tier free
   - Landing page com demo interativo
   - Partilhar em r/GlobalOffensive, r/cs2, HLTV forums

2. Content marketing agressivo
   - Análises de matches pro usando a plataforma
   - YouTube: "AI analysis of [Major Grand Final]"
   - Partnerships com criadores de conteúdo CS2

3. Converter free → paid
   - Email sequences mostrando value da análise de erros
   - In-app upsell: "Upgrade para ver recomendações detalhadas"
```

### Fase 3: Growth (Mês 7-12)

```
1. Partnerships com torneios
   - Oferecer analytics para participantes de torneios
   - Sponsorship de torneios regionais

2. Outreach a equipas pro
   - Cold outreach a coaches/analysts de equipas Tier 2-3
   - Case studies de equipas beta que melhoraram

3. Referral program
   - Equipas que referem ganham 1 mês grátis

4. Tournament prep packages
   - Pacotes one-off de scout reports para torneios
   - €299 por report completo de oponente
```

---

## Métricas de Negócio (KPIs)

### Produto

| KPI | Objetivo (Ano 1) |
|-----|----------------|
| Demos processados/dia | 100+ |
| Tempo médio de processamento | < 5 min |
| Error detection precision | > 85% |
| NPS (Net Promoter Score) | > 40 |
| DAU/MAU ratio | > 30% |
| Feature adoption (error tab) | > 60% dos users |

### Receita

| KPI | Objetivo (Ano 1) |
|-----|----------------|
| MRR (Monthly Recurring Revenue) | €8,000+ |
| ARR (Annual Recurring Revenue) | €100,000 |
| Free → Paid conversion rate | 5-8% |
| Monthly churn rate | < 5% |
| ARPU (Average Revenue Per User) | €70 |
| CAC (Customer Acquisition Cost) | < €50 |
| LTV (Lifetime Value) | > €500 |
| LTV/CAC ratio | > 3x |

### Envolvimento

| KPI | Objetivo |
|-----|--------|
| Demos uploaded/team/mês | > 10 |
| Time on platform/session | > 15 min |
| Return visits/week | > 3 |
| Scout reports generated/team/mês | > 2 |
| Training plan views/player/week | > 2 |

---

## Riscos de Negócio

| Risco | Probabilidade | Impacto | Mitigação |

|-------|-------------|---------|-----------|
| Skybox/Leetify/Stratmind adicionam AI similar | Alta | Alto | Ser primeiro, iterar rápido, foco no nicho |
| Stratmind/Rankacy como concorrentes AI diretos | Média | Alto | Mover rápido, foco em explicabilidade (SHAP/IG) como diferenciador |
| CS2 perde popularidade | Baixa | Muito Alto | Arquitetura extensível para outros jogos |
| Erro do ML causa análise errada | Média | Médio | Disclaimers, feedback loop, precision > recall |
| Valve muda formato de demos | Média | Alto | Parser abstraction layer, budget para fixes |
| Custo de GPU sobe | Baixa | Médio | Modelos otimizados, CPU inference onde possível |
| Dificuldade em adquirir clientes | Média | Alto | Content marketing forte, freemium generoso |
| Equipa pequena → burnout | Alta | Alto | Fases claras, scope controlado, priorizar |

---

## Extensões Futuras

### Ano 2+

1. **Outros jogos**: Valorant, Dota 2, League of Legends (requer novos parsers mas a arquitetura ML é reutilizável)
2. **Coaching ao vivo**: Análise em tempo real durante scrims (requer stream parsing)
3. **Insights para apostas**: Modelo de probabilidade de vitória para mercado de apostas (partilha de receita)
4. **Ferramentas para organizadores de torneios**: Dashboard para organizar torneios com analytics integradas
5. **Mercado de jogadores**: Conectar jogadores com equipas baseado em análise de compatibilidade
6. **Aplicação móvel**: Versão mobile do dashboard para consulta rápida
7. **Assistente AI**: Chatbot que responde perguntas sobre matches ("Como jogámos A-site em Mirage nos últimos 10 jogos?")
