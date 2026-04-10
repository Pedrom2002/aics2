# 06 - Arquitetura Frontend

## Stack

| Tecnologia | Versão | Uso |
|-----------|--------|-----|
| Next.js | 15+ | Framework (App Router, RSC) |
| React | 19+ | UI library |
| TypeScript | 5.5+ | Type safety |
| Tailwind CSS | 4+ | Styling |
| shadcn/ui | latest | UI components |
| Recharts | 2.x | Standard charts |
| D3.js | 7+ | Custom map visualizations |
| TanStack Query | 5+ | Client data fetching |
| Zustand | 5+ | Client state (minimal) |
| pnpm | 9+ | Package manager |

---

## Estrutura de Ficheiros

```
packages/frontend/
├── src/
│   ├── app/                              # App Router
│   │   ├── layout.tsx                    # Root layout (fonts, providers)
│   │   ├── (auth)/                       # Auth group (sem sidebar)
│   │   │   ├── layout.tsx
│   │   │   ├── login/page.tsx
│   │   │   ├── register/page.tsx
│   │   │   └── invite/[token]/page.tsx
│   │   ├── (dashboard)/                  # Dashboard group (com sidebar)
│   │   │   ├── layout.tsx                # Sidebar + Header + TeamSwitcher
│   │   │   ├── page.tsx                  # Dashboard home
│   │   │   ├── upload/page.tsx
│   │   │   ├── matches/
│   │   │   │   ├── page.tsx              # Match list
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx          # Match overview (redirect to overview tab)
│   │   │   │       ├── overview/page.tsx
│   │   │   │       ├── errors/page.tsx   # Error analysis
│   │   │   │       ├── tactics/page.tsx
│   │   │   │       ├── economy/page.tsx
│   │   │   │       └── replay/page.tsx   # 2D replayer
│   │   │   ├── players/
│   │   │   │   ├── page.tsx              # Team roster
│   │   │   │   └── [steamId]/
│   │   │   │       ├── page.tsx          # Player profile
│   │   │   │       └── training/page.tsx # Training plan
│   │   │   ├── scout/
│   │   │   │   ├── page.tsx              # Scout report list
│   │   │   │   ├── new/page.tsx          # Generate new report
│   │   │   │   └── [id]/page.tsx         # View report
│   │   │   └── settings/
│   │   │       ├── page.tsx              # Org settings
│   │   │       ├── team/page.tsx
│   │   │       └── billing/page.tsx
│   │   └── api/                          # Rotas API Next.js (BFF proxy)
│   │       └── [...proxy]/route.ts       # Proxy para backend FastAPI
│   │
│   ├── components/
│   │   ├── ui/                           # Componentes shadcn/ui
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── table.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── skeleton.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/
│   │   │   ├── sidebar.tsx               # Sidebar de navegação principal
│   │   │   ├── header.tsx                # Barra superior com pesquisa + utilizador
│   │   │   ├── team-switcher.tsx         # Dropdown para trocar de equipa
│   │   │   └── processing-queue.tsx      # Bottom bar: demos em processamento
│   │   │
│   │   ├── maps/                         # Visualizações de mapas CS2
│   │   │   ├── map-canvas.tsx            # Renderer base D3/Canvas do mapa
│   │   │   ├── heatmap-layer.tsx         # Overlay de heatmap (kills, deaths, etc.)
│   │   │   ├── trajectory-layer.tsx      # Trajectórias de movimento dos jogadores
│   │   │   ├── replayer-engine.tsx       # Replayer 2D completo
│   │   │   ├── replayer-controls.tsx     # Play/pause/velocidade/slider de ticks
│   │   │   ├── player-dots.tsx           # Ícones dos jogadores no mapa
│   │   │   ├── grenade-effects.tsx       # Rendering de smoke, flash, molly
│   │   │   └── map-utils.ts             # Transformações de coordenadas
│   │   │
│   │   ├── charts/                       # Gráficos Recharts + D3
│   │   │   ├── radar-chart.tsx           # Radar de performance do jogador
│   │   │   ├── economy-graph.tsx         # Economia ronda a ronda
│   │   │   ├── timeline-chart.tsx        # Timeline de eventos do match
│   │   │   ├── error-distribution.tsx    # Gráficos de distribuição de erros
│   │   │   ├── rating-history.tsx        # Rating ao longo do tempo
│   │   │   ├── strategy-distribution.tsx # Pie/bar de estratégias
│   │   │   ├── shap-waterfall.tsx        # Gráfico de explicação SHAP (D3)
│   │   │   └── win-rate-chart.tsx        # Win rate por mapa/estratégia
│   │   │
│   │   ├── analytics/                    # Componentes específicos de funcionalidades
│   │   │   ├── error-card.tsx            # Erro individual com SHAP + recomendação
│   │   │   ├── error-list.tsx            # Lista de erros filtrável
│   │   │   ├── error-filters.tsx         # Filtrar por jogador, tipo, severidade
│   │   │   ├── error-minimap.tsx         # Mini-mapa com posição do erro
│   │   │   ├── tactical-breakdown.tsx    # Vista de estratégias por ronda
│   │   │   ├── prediction-panel.tsx      # Card de "previsão da próxima ronda"
│   │   │   ├── scout-report-view.tsx     # Relatório de scouting completo
│   │   │   ├── training-plan-card.tsx    # Recomendação de treino
│   │   │   ├── weakness-profile.tsx      # Visualização de fraquezas do jogador
│   │   │   ├── scoreboard.tsx            # Scoreboard melhorado do match
│   │   │   └── match-card.tsx            # Card de resumo do match
│   │   │
│   │   └── common/
│   │       ├── page-header.tsx
│   │       ├── empty-state.tsx
│   │       ├── loading-skeleton.tsx
│   │       └── file-upload.tsx           # Drag-and-drop .dem upload
│   │
│   ├── lib/
│   │   ├── api-client.ts                # Wrapper tipado de fetch para API backend
│   │   ├── sse.ts                       # Hook SSE (useSSE)
│   │   ├── map-coordinates.ts           # Sistemas de coordenadas de mapas CS2
│   │   ├── map-data.ts                  # Nomes de mapas, limites, imagens radar
│   │   ├── utils.ts                     # Utilitários gerais
│   │   └── constants.ts                 # Armas CS2, mapas, etc.
│   │
│   ├── hooks/
│   │   ├── use-match.ts                 # Buscar dados de match
│   │   ├── use-errors.ts                # Buscar dados de erros
│   │   ├── use-player.ts                # Buscar perfil de jogador
│   │   ├── use-demo-status.ts           # Estado de processamento via SSE
│   │   └── use-replayer.ts              # Gestão de estado do replayer
│   │
│   └── types/
│       ├── match.ts                     # Tipos Match, Round, Event
│       ├── player.ts                    # Tipos Player, Rating, Weakness
│       ├── error.ts                     # Tipos DetectedError, ShapFactor
│       ├── tactical.ts                  # Tipos Strategy, Prediction
│       └── scout.ts                     # Tipos ScoutReport
│
├── public/
│   └── maps/                            # CS2 radar images
│       ├── de_mirage_radar.png
│       ├── de_inferno_radar.png
│       ├── de_dust2_radar.png
│       ├── de_anubis_radar.png
│       ├── de_nuke_radar.png
│       ├── de_overpass_radar.png
│       └── de_vertigo_radar.png
│
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## Padrões de Rendering

### Server Components (RSC) — Data Fetching

Usar para todas as páginas que carregam dados iniciais:

```tsx
// app/(dashboard)/matches/[id]/overview/page.tsx
// Este é um componente SERVER — fetch direto no servidor
export default async function MatchOverviewPage({
  params,
}: {
  params: { id: string }
}) {
  const match = await fetchMatch(params.id)
  const rounds = await fetchRounds(params.id)

  return (
    <div>
      <Scoreboard players={match.scoreboard} />     {/* Server */}
      <RoundScores rounds={rounds} />                {/* Server */}
      <MatchTimeline events={match.timeline} />      {/* Client - interativo */}
      <KillHeatmap map={match.map} data={match.kills} /> {/* Client - D3 */}
    </div>
  )
}
```

### Client Components — Interatividade

Usar `"use client"` apenas para componentes que precisam de:
- Interação do utilizador (clicks, filters, hover)
- D3.js / Canvas rendering
- SSE / real-time updates
- Estado local (useState, useReducer)

```tsx
// components/maps/replayer-engine.tsx
"use client"

import { useRef, useEffect, useState } from 'react'
import { useReplayer } from '@/hooks/use-replayer'

export function ReplayerEngine({ matchId, roundNumber }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { ticks, currentTick, play, pause, setSpeed } = useReplayer(matchId, roundNumber)

  useEffect(() => {
    const ctx = canvasRef.current?.getContext('2d')
    if (!ctx || !ticks) return
    // Renderizar frame no tick atual
    renderFrame(ctx, ticks, currentTick)
  }, [currentTick, ticks])

  return (
    <div>
      <canvas ref={canvasRef} width={1024} height={1024} />
      <ReplayerControls
        tick={currentTick}
        onPlay={play}
        onPause={pause}
        onSpeedChange={setSpeed}
      />
    </div>
  )
}
```

---

## Páginas Principais

### Dashboard Home (`/`)

```
┌─────────────────────────────────────────────────────────┐
│  Dashboard                                    Mar 2026  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │ Matches │ │ Win Rate│ │ Errors/ │ │ Rating  │      │
│  │   25    │ │  64%    │ │ Match   │ │  72.5   │      │
│  │ este mês│ │  ▲ +5%  │ │  11.2   │ │  ▲ +3   │      │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │
│                                                         │
│  Team Performance Trend (últimos 3 meses)               │
│  ┌─────────────────────────────────────────────┐        │
│  │  [Recharts line chart: rating over time]    │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  Matches Recentes                   Top Erros            │
│  ┌────────────────────┐  ┌────────────────────┐        │
│  │ Mirage  16-12  W   │  │ Multi-angle pos.   │        │
│  │ Inferno 10-16  L   │  │ Flash sem cegar    │        │
│  │ Anubis  16-14  W   │  │ Peek sem flash     │        │
│  │ Dust2   16-8   W   │  │ Rotação atrasada   │        │
│  └────────────────────┘  └────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Match Detail — Errors Tab (Diferenciador)

```
┌─────────────────────────────────────────────────────────┐
│  Mirage | Our Team 16-12 Opponent | 2026-03-08          │
│  [Overview] [ERRORS] [Tactics] [Economy] [Replay]       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Filters: [All Players ▼] [All Types ▼] [All Sev. ▼]  │
│                                                         │
│  45 erros detetados (8 critical, 20 major, 17 minor)   │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ERROR #1                           🔴 Critical    │  │
│  │ Player1 | Round 14 | 11:46                        │  │
│  │                                                    │  │
│  │ Exposto a A-main e palace simultaneamente          │  │
│  │ enquanto segurava A-site                           │  │
│  │                                                    │  │
│  │ ┌──────────────┐  ┌────────────────────────────┐  │  │
│  │ │  Mini-mapa   │  │  SHAP Waterfall            │  │  │
│  │ │  [posição do │  │  angles_exposed ████ +0.45 │  │  │
│  │ │   jogador    │  │  cover_dist     ███  +0.31 │  │  │
│  │ │   marcada]   │  │  teammate_dist  ██   +0.15 │  │  │
│  │ └──────────────┘  └────────────────────────────┘  │  │
│  │                                                    │  │
│  │ 💡 Recomendação: Segurar de ticket booth ou       │  │
│  │    stairs para limitar exposição a 1 ângulo.       │  │
│  │                                                    │  │
│  │ 🎯 Referência Pro: device fez hold similar de     │  │
│  │    stairs em match vs Astralis (round 8)           │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ERROR #2                           🟡 Major       │  │
│  │ Player3 | Round 7 | 05:23                         │  │
│  │ ...                                                │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Distribuição de Erros                                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │ [Recharts: bar chart by type + by player]         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Perfil de Jogador

```
┌─────────────────────────────────────────────────────────┐
│  Player1 | Entry Fragger | Rating: 78.5 ▲              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────────────┐  ┌────────────────────────┐    │
│  │  Performance Radar │  │  Rating History         │    │
│  │                    │  │  ┌──────────────────┐   │    │
│  │    Aim: 82         │  │  │ [line chart      │   │    │
│  │   /    \           │  │  │  over 3 months]  │   │    │
│  │ Clutch  Pos: 65    │  │  └──────────────────┘   │    │
│  │   \    /           │  │                          │    │
│  │  Sense  Utility    │  │                          │    │
│  │   80     71        │  │                          │    │
│  └────────────────────┘  └────────────────────────┘    │
│                                                         │
│  Perfil de Fraquezas                                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Primary: Overaggressive Peeker (82%)              │  │
│  │ - Peek sem flash, timing demasiado cedo           │  │
│  │ Secondary: Utility Hoarder (45%)                  │  │
│  │ - Morre com granadas não utilizadas               │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Plano de Treino                                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 1. Peek Discipline (Priority HIGH)                │  │
│  │    Current: 0.35 | Target: 0.20 | Pro: 0.12       │  │
│  │    [████████░░░░] 55% to target                    │  │
│  │    Drill: DM com flash obrigatória antes de peek   │  │
│  │                                                    │  │
│  │ 2. Utility Usage (Priority MEDIUM)                │  │
│  │    Current: 0.28 | Target: 0.15 | Pro: 0.08       │  │
│  │    [██████░░░░░░] 40% to target                    │  │
│  │    Drill: 3 lineups/mapa, 0 mortes com 2+ nades    │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Performance por Mapa                                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Mirage: 82.0 | Inferno: 75.5 | Anubis: 70.2      │  │
│  │ Dust2: 80.1  | Nuke: 68.0   | Overpass: 73.8     │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 2D Replayer

```
┌─────────────────────────────────────────────────────────┐
│  Round 14 | 1:46 remaining | Score: 8-6                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │                                                    │  │
│  │              CS2 MAP (Canvas)                      │  │
│  │                                                    │  │
│  │    🔵 CT1          🔵 CT2                          │  │
│  │         🟠 T1                                      │  │
│  │                    💨 smoke                         │  │
│  │    🔵 CT3     🟠 T2     🟠 T3                     │  │
│  │                         🔥 molotov                 │  │
│  │              🟠 T4         🟠 T5                   │  │
│  │                                                    │  │
│  │    💀 death marker    ─── trajectory               │  │
│  │                                                    │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  [⏮] [⏪] [▶ Play] [⏩] [⏭]  Speed: [1x ▼]          │
│  Tick: [███████████░░░░░░░░░] 45230/64000              │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ CT1: 100hp AK  | CT2: 85hp M4  | CT3: 100hp AWP│    │
│  │ T1: 100hp AK   | T2: 72hp M4   | T3: 💀        │    │
│  │ T4: 100hp AK   | T5: 100hp AK  |               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  Kill Feed:                                              │
│  │ CT1 🔫 T3 (AK-47, headshot)                        │
│  │ T2 🔫 CT2 (M4A1-S)                                 │
└─────────────────────────────────────────────────────────┘
```

---

## Padrões de Data Fetching

### Lado do Servidor (RSC)

```tsx
// lib/api-client.ts
const API_BASE = process.env.BACKEND_URL || 'http://localhost:8000/api/v1'

export async function fetchMatch(id: string) {
  const res = await fetch(`${API_BASE}/matches/${id}`, {
    headers: { Authorization: `Bearer ${getServerToken()}` },
    next: { revalidate: 60 } // Cache 60 seconds
  })
  if (!res.ok) throw new Error('Failed to fetch match')
  return res.json() as Promise<Match>
}
```

### Lado do Cliente (TanStack Query)

```tsx
// hooks/use-errors.ts
"use client"

import { useQuery } from '@tanstack/react-query'

export function useErrors(matchId: string, filters: ErrorFilters) {
  return useQuery({
    queryKey: ['errors', matchId, filters],
    queryFn: () => fetchErrors(matchId, filters),
    staleTime: 5 * 60 * 1000, // 5 min
  })
}
```

### SSE (Tempo Real)

```tsx
// hooks/use-demo-status.ts
"use client"

import { useEffect, useState } from 'react'

export function useDemoStatus(demoId: string) {
  const [status, setStatus] = useState<DemoStatus>({ status: 'uploaded', progress: 0 })

  useEffect(() => {
    const eventSource = new EventSource(`/api/v1/demos/${demoId}/status`)
    eventSource.onmessage = (event) => {
      setStatus(JSON.parse(event.data))
    }
    eventSource.onerror = () => eventSource.close()
    return () => eventSource.close()
  }, [demoId])

  return status
}
```

---

## Sistema de Coordenadas (CS2 Maps)

Cada mapa CS2 tem o seu sistema de coordenadas. O frontend precisa de converter coordenadas do jogo para pixels no radar image.

```typescript
// lib/map-coordinates.ts
interface MapConfig {
  name: string
  displayName: string
  radarImage: string
  // Mapeamento: game coords → pixel coords
  pos_x: number      // X offset
  pos_y: number      // Y offset
  scale: number       // Scale factor
  image_width: number  // Radar image width in pixels
  image_height: number
}

const MAP_CONFIGS: Record<string, MapConfig> = {
  de_mirage: {
    name: 'de_mirage',
    displayName: 'Mirage',
    radarImage: '/maps/de_mirage_radar.png',
    pos_x: -3230,
    pos_y: 1713,
    scale: 5.00,
    image_width: 1024,
    image_height: 1024
  },
  // ... outros mapas
}

export function gameToPixel(gameX: number, gameY: number, map: string): { px: number, py: number } {
  const config = MAP_CONFIGS[map]
  return {
    px: (gameX - config.pos_x) / config.scale,
    py: (config.pos_y - gameY) / config.scale  // Y invertido
  }
}
```

---

## Considerações de Performance

1. **RSC para initial load**: Scoreboard, stats, metadata carregados no servidor — zero JS enviado
2. **Dynamic imports**: Replayer e D3 charts carregados lazily (`next/dynamic`)
3. **Canvas sobre SVG**: Replayer usa Canvas (10 jogadores × 64fps = 640 updates/seg)
4. **Tick data pagination**: Replayer pede ticks em chunks (1 round de cada vez)
5. **Image optimization**: Radar images servidas via `next/image` com WebP
6. **Memoization**: D3 scales e calculations memoizados com `useMemo`
7. **Virtual scrolling**: Error list com virtualization para matches com 200+ erros
