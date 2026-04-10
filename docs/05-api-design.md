# 05 - Design da API

## Convenções

- Base URL: `/api/v1/`
- Auth: JWT Bearer token em header `Authorization: Bearer <token>`
- Formato: JSON (pedido e resposta)
- Paginação: `?page=1&page_size=20` (padrão 20, máx 100)
- Filtros: parâmetros de query
- Erros: formato RFC 7807 Problem Details
- Versionamento: caminho URL (`/v1/`, `/v2/`)

```json
// Erro padrão
{
  "type": "validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "field 'map' must be one of: mirage, inferno, ...",
  "instance": "/api/v1/matches"
}
```

---

## Endpoints de Autenticação

### POST /auth/register
Criar organização + utilizador admin.

```json
// Request
{
  "org_name": "Team Exemplo",
  "email": "admin@teamexemplo.com",
  "password": "securepassword123",
  "display_name": "Admin"
}

// Response 201
{
  "user": {
    "id": "uuid",
    "email": "admin@teamexemplo.com",
    "display_name": "Admin",
    "role": "admin"
  },
  "organization": {
    "id": "uuid",
    "name": "Team Exemplo",
    "slug": "team-exemplo",
    "tier": "free"
  },
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

### POST /auth/login

```json
// Request
{ "email": "admin@teamexemplo.com", "password": "securepassword123" }

// Response 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 3600,
  "user": { "id": "uuid", "email": "...", "role": "admin", "org_id": "uuid" }
}
```

### POST /auth/refresh

```json
// Request
{ "refresh_token": "eyJ..." }

// Response 200
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "expires_in": 3600 }
```

### POST /auth/invite
Permissões: admin, coach

```json
// Request
{ "email": "analyst@team.com", "role": "analyst" }

// Response 201
{ "invitation_id": "uuid", "email": "analyst@team.com", "expires_at": "..." }
```

---

## Endpoints de Demo

### POST /demos/upload
Permissões: admin, coach, analyst

```
Content-Type: multipart/form-data
Fields:
  - file: .dem file (max 500MB)
  - match_type: "scrim" | "official" | "pug" (optional)
  - our_team_id: UUID (optional)

Response 202:
{
  "demo_id": "uuid",
  "status": "uploaded",
  "message": "Demo queued for processing"
}
```

### POST /demos/bulk-upload
Permissões: admin, coach

```
Content-Type: multipart/form-data
Fields:
  - files[]: multiple .dem files
  - match_type: string (optional, applies to all)

Response 202:
{
  "demos": [
    { "demo_id": "uuid", "filename": "match1.dem", "status": "uploaded" },
    { "demo_id": "uuid", "filename": "match2.dem", "status": "uploaded" }
  ]
}
```

### GET /demos
Permissões: todos

```
Query params: ?status=analysis_complete&page=1&page_size=20

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "filename": "match1.dem",
      "status": "analysis_complete",
      "file_size_bytes": 85000000,
      "match": { "map": "mirage", "score": "16-12" },
      "uploaded_by": "Admin",
      "created_at": "2026-03-10T14:30:00Z",
      "processed_at": "2026-03-10T14:35:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20
}
```

### GET /demos/{id}/status (SSE)
Estado de processamento em tempo real via Server-Sent Events.

```
Event stream:
data: {"status": "parsing", "progress": 30, "message": "Extracting tick data..."}

data: {"status": "computing_features", "progress": 60, "message": "Computing 200+ features..."}

data: {"status": "analyzing", "progress": 85, "message": "Running error detection..."}

data: {"status": "analysis_complete", "progress": 100, "match_id": "uuid"}
```

---

## Endpoints de Match

### GET /matches

```
Query params:
  ?map=mirage
  &date_from=2026-01-01
  &date_to=2026-03-10
  &team_id=uuid
  &match_type=official
  &page=1

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "map": "mirage",
      "match_date": "2026-03-08T20:00:00Z",
      "team1": { "name": "Our Team", "score": 16 },
      "team2": { "name": "Opponent", "score": 12 },
      "match_type": "scrim",
      "total_rounds": 28,
      "our_result": "win"
    }
  ],
  "total": 30,
  "page": 1
}
```

### GET /matches/{id}

```json
// Response 200
{
  "id": "uuid",
  "map": "mirage",
  "match_date": "2026-03-08T20:00:00Z",
  "team1": {
    "name": "Our Team",
    "score": 16,
    "first_half_score": 9,
    "second_half_score": 7,
    "side_first": "ct"
  },
  "team2": {
    "name": "Opponent",
    "score": 12,
    "first_half_score": 6,
    "second_half_score": 6,
    "side_first": "t"
  },
  "total_rounds": 28,
  "scoreboard": [
    {
      "player_name": "Player1",
      "steam_id": "76561...",
      "team": "Our Team",
      "kills": 25, "deaths": 18, "assists": 5,
      "adr": 85.3, "kast": 72.5, "headshot_pct": 48.0,
      "rating": 78.5,
      "flash_assists": 3, "utility_damage": 120
    }
  ],
  "analysis_status": "complete",
  "errors_count": 45,
  "errors_critical": 8
}
```

### GET /matches/{id}/rounds

```json
// Response 200
{
  "rounds": [
    {
      "round_number": 1,
      "winner_side": "ct",
      "win_reason": "elimination",
      "t_score": 0, "ct_score": 1,
      "t_economy": 800, "ct_economy": 800,
      "t_buy_type": "pistol", "ct_buy_type": "pistol",
      "bomb_planted": false,
      "our_strategy": "a_execute",
      "opponent_strategy": "standard_2_1_2",
      "errors_count": 2,
      "duration_seconds": 85.5
    }
  ]
}
```

### GET /matches/{id}/rounds/{n}/ticks

```
Query params: ?tick_start=0&tick_end=6400&step=4 (every 4th tick)

Response 200:
{
  "round_number": 5,
  "tick_range": [12800, 19200],
  "players": [
    {
      "steam_id": "76561...",
      "name": "Player1",
      "team": "ct",
      "ticks": [
        {
          "tick": 12800,
          "x": 150.5, "y": -230.2, "z": 64.0,
          "yaw": 180.0, "health": 100, "armor": 100,
          "weapon": "ak47", "is_alive": true
        }
      ]
    }
  ],
  "events": [
    {
      "tick": 15200, "type": "kill",
      "actor": "Player1", "target": "Enemy1",
      "weapon": "ak47", "headshot": true,
      "position": { "x": 155.0, "y": -228.0 }
    }
  ]
}
```

### GET /matches/{id}/timeline

```json
// Response 200
{
  "events": [
    {
      "tick": 3200, "time_seconds": 50.0, "round": 1,
      "type": "kill", "description": "Player1 killed Enemy3 (AK-47, headshot)",
      "impact": "first_kill",
      "actor_team": "our"
    },
    {
      "tick": 3400, "time_seconds": 53.1, "round": 1,
      "type": "trade_kill", "description": "Enemy2 traded Player1",
      "actor_team": "opponent"
    },
    {
      "tick": 4800, "time_seconds": 75.0, "round": 1,
      "type": "bomb_plant", "site": "A",
      "actor_team": "our"
    }
  ]
}
```

### GET /matches/{id}/economy

```json
// Response 200
{
  "rounds": [
    {
      "round": 1,
      "our_team": {
        "total_money": 4000, "equipment_value": 3500,
        "buy_type": "pistol", "loss_bonus": 0
      },
      "opponent": {
        "total_money": 4000, "equipment_value": 3200,
        "buy_type": "pistol", "loss_bonus": 0
      }
    }
  ]
}
```

---

## Endpoints de Deteção de Erros

### GET /matches/{id}/errors

```
Query params:
  ?player=76561...
  &error_type=positioning
  &severity=critical
  &page=1

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "round": 14,
      "tick": 45230,
      "timestamp_seconds": 706.7,
      "player": {
        "steam_id": "76561...",
        "name": "Player1"
      },
      "error_type": "positioning",
      "error_subtype": "multi_angle_exposure",
      "severity": "critical",
      "map_area": "A-site",
      "description": "Exposto a A-main e palace simultaneamente enquanto segurava A-site em Mirage",
      "recommendation": "Segurar de ticket booth ou stairs para limitar exposição a 1 ângulo",
      "confidence": 0.92,
      "shap_factors": [
        { "feature": "angles_exposed", "value": 2, "impact": 0.45 },
        { "feature": "cover_distance", "value": 12.5, "impact": 0.31 },
        { "feature": "nearest_teammate_dist", "value": 25.0, "impact": 0.15 }
      ],
      "pro_reference": {
        "player": "device",
        "description": "Similar situation, held from stairs",
        "match_id": "xxx",
        "round": 8
      },
      "position": { "x": 150.5, "y": -230.2 }
    }
  ],
  "summary": {
    "total_errors": 45,
    "critical": 8, "major": 20, "minor": 17,
    "by_type": { "positioning": 20, "utility": 15, "timing": 10 },
    "by_player": {
      "Player1": 12, "Player2": 10, "Player3": 8,
      "Player4": 8, "Player5": 7
    }
  }
}
```

### GET /players/{steamId}/errors/summary

```json
// Response 200
{
  "player": { "steam_id": "76561...", "name": "Player1" },
  "matches_analyzed": 45,
  "total_errors": 520,
  "errors_per_match_avg": 11.5,
  "by_type": {
    "positioning": { "count": 230, "pct": 44.2, "critical_pct": 15.0 },
    "utility": { "count": 180, "pct": 34.6, "critical_pct": 8.0 },
    "timing": { "count": 110, "pct": 21.2, "critical_pct": 12.0 }
  },
  "most_common_errors": [
    { "subtype": "multi_angle_exposure", "count": 85, "maps": ["mirage", "inferno"] },
    { "subtype": "flash_no_blind", "count": 62, "maps": ["dust2", "mirage"] },
    { "subtype": "peek_without_flash", "count": 45, "maps": ["overpass", "anubis"] }
  ],
  "comparison_to_avg": {
    "positioning_error_rate": { "player": 0.35, "team_avg": 0.28, "pro_avg": 0.12 },
    "utility_error_rate": { "player": 0.22, "team_avg": 0.25, "pro_avg": 0.08 },
    "timing_error_rate": { "player": 0.18, "team_avg": 0.20, "pro_avg": 0.10 }
  }
}
```

### GET /players/{steamId}/errors/trends

```json
// Response 200
{
  "period": "last_3_months",
  "data_points": [
    {
      "week": "2026-01-06",
      "matches": 4,
      "errors_per_match": 14.5,
      "positioning_rate": 0.40,
      "utility_rate": 0.25,
      "timing_rate": 0.22
    },
    {
      "week": "2026-01-13",
      "matches": 3,
      "errors_per_match": 12.0,
      "positioning_rate": 0.35,
      "utility_rate": 0.23,
      "timing_rate": 0.20
    }
  ],
  "trend": "improving",
  "improvement_rate": "-5% per month"
}
```

---

## Endpoints Táticos

### GET /matches/{id}/tactics

```json
// Response 200
{
  "rounds": [
    {
      "round": 1,
      "our_team": {
        "side": "t",
        "strategy": "a_execute",
        "confidence": 0.85,
        "details": "Full A execute with 3 smokes, 2 flashes"
      },
      "opponent": {
        "side": "ct",
        "strategy": "standard_2_1_2",
        "confidence": 0.78,
        "details": "Standard setup: 2 A, 1 mid, 2 B"
      }
    }
  ],
  "summary": {
    "our_strategies": {
      "t_side": { "a_execute": 5, "b_execute": 3, "default": 4, "mid_control": 3 },
      "ct_side": { "standard_2_1_2": 8, "stack_a": 2, "aggressive_mid": 3 }
    }
  }
}
```

### GET /tactics/predict

```
Query params:
  ?opponent=TeamName
  &map=mirage
  &rounds_history=[encoded JSON of previous rounds]

Response 200:
{
  "predicted_round": 16,
  "predictions": [
    { "strategy": "b_execute", "probability": 0.35 },
    { "strategy": "mid_control_to_a", "probability": 0.25 },
    { "strategy": "default_spread", "probability": 0.20 }
  ],
  "reasoning": "After 2 lost A rounds, this opponent shifts to B 65% of the time",
  "counter_suggestion": {
    "recommendation": "Stack B with 3 players, AWP in window for mid",
    "expected_success_rate": 0.72
  }
}
```

---

## Endpoints de Perfil de Jogador

### GET /players/{steamId}/profile

```json
// Response 200
{
  "player": {
    "steam_id": "76561...",
    "name": "Player1",
    "role": "entry",
    "team": "Our Team"
  },
  "overall_rating": 78.5,
  "sub_ratings": {
    "aim": 82.0,
    "positioning": 65.0,
    "utility": 71.0,
    "game_sense": 80.0,
    "clutch": 75.0
  },
  "stats_last_30_days": {
    "matches": 25,
    "kd_ratio": 1.15,
    "adr": 82.3,
    "kast": 71.5,
    "headshot_pct": 48.2,
    "opening_duel_win_rate": 0.55,
    "clutch_win_rate": 0.38,
    "flash_assists_per_match": 2.8,
    "utility_damage_per_match": 45.2
  },
  "weakness_profile": {
    "primary": {
      "cluster": "Overaggressive Peeker",
      "strength": 0.82,
      "description": "Tendência a fazer peek sem flash e demasiado cedo"
    },
    "secondary": {
      "cluster": "Utility Hoarder",
      "strength": 0.45,
      "description": "Morre frequentemente com granadas não utilizadas"
    }
  },
  "trend": "improving"
}
```

### GET /players/{steamId}/training-plan

```json
// Response 200
{
  "player": { "steam_id": "76561...", "name": "Player1" },
  "recommendations": [
    {
      "priority": 1,
      "area": "Peek Discipline",
      "description": "Praticar jiggle peeks e shoulder peeks antes de commit",
      "drill": "Deathmatch: só fazer peek com flash ou info prévia",
      "expected_impact": "Redução de 30% em timing errors",
      "current_metric": 0.35,
      "target_metric": 0.20,
      "pro_benchmark": 0.12,
      "progress": {
        "started_at": "2026-01-15",
        "initial_metric": 0.42,
        "current_metric": 0.35,
        "trend": "improving"
      }
    },
    {
      "priority": 2,
      "area": "Utility Usage",
      "description": "Usar granadas antes de morrer, integrar no gameplay",
      "drill": "Em scrims: objetivo de 0 mortes com 2+ granadas restantes",
      "expected_impact": "Redução de 25% em utility waste",
      "current_metric": 0.28,
      "target_metric": 0.15,
      "pro_benchmark": 0.08
    }
  ],
  "overall_progress": {
    "errors_per_match_trend": [14.5, 13.2, 12.0, 11.5],
    "months": ["Dec", "Jan", "Feb", "Mar"],
    "improvement_rate": "-8% per month"
  }
}
```

### GET /players/{steamId}/heatmaps

```
Query params: ?map=mirage&side=ct&type=kills

Response 200:
{
  "map": "mirage",
  "side": "ct",
  "type": "kills",
  "matches_included": 15,
  "data": [
    { "x": 150.5, "y": -230.2, "count": 8, "headshot_pct": 62.5 },
    { "x": 200.1, "y": -180.5, "count": 5, "headshot_pct": 40.0 }
  ],
  "map_bounds": {
    "x_min": -3230, "x_max": 1820,
    "y_min": -3490, "y_max": 1710
  }
}
```

---

## Endpoints de Relatório de Scouting

### POST /scout/generate
Permissões: admin, coach, analyst

```json
// Request
{
  "opponent_name": "Enemy Team",
  "maps": ["mirage", "inferno", "anubis"],
  "date_range": { "from": "2025-12-01", "to": "2026-03-10" },
  "demo_ids": ["uuid1", "uuid2", "uuid3"]
}

// Response 202
{
  "report_id": "uuid",
  "status": "generating",
  "estimated_time_seconds": 120
}
```

### GET /scout/reports/{id}

```json
// Response 200
{
  "id": "uuid",
  "opponent": "Enemy Team",
  "matches_analyzed": 12,
  "maps_analyzed": ["mirage", "inferno", "anubis"],
  "created_at": "2026-03-10T15:00:00Z",
  "map_veto_recommendation": {
    "ban": ["nuke", "vertigo"],
    "pick": ["mirage"],
    "reasoning": "Enemy has 35% win rate on Mirage vs 68% on Nuke"
  },
  "maps": {
    "mirage": {
      "matches": 5,
      "win_rate": 0.40,
      "t_strategies": {
        "a_execute": { "pct": 35, "success_rate": 0.55 },
        "b_execute": { "pct": 20, "success_rate": 0.60 },
        "mid_control_to_a": { "pct": 15, "success_rate": 0.45 },
        "default": { "pct": 20, "success_rate": 0.50 },
        "fast_b": { "pct": 10, "success_rate": 0.30 }
      },
      "ct_strategies": {
        "standard_2_1_2": { "pct": 60, "success_rate": 0.55 },
        "stack_a": { "pct": 15, "success_rate": 0.40 },
        "aggressive_mid": { "pct": 25, "success_rate": 0.35 }
      },
      "pistol_rounds": {
        "t_tendency": "rush B (60%)",
        "ct_tendency": "passive hold (80%)"
      },
      "exploitable_patterns": [
        "After losing 2 A rounds, switch to B 70% of the time",
        "AWPer always positions mid on CT first 3 rounds",
        "Rarely use mid control before round 20s mark"
      ]
    }
  },
  "key_players": [
    {
      "name": "EnemyPlayer1",
      "role": "awp",
      "tendencies": "Aggressive AWP, pushes mid early on CT. Weak on retakes.",
      "opening_duel_rate": 0.58,
      "positions_preferred": ["mid window", "top mid"]
    }
  ],
  "counter_strategies": [
    {
      "against": "a_execute (35% of T rounds)",
      "suggestion": "Stack A with 3 players when economy allows full buy",
      "expected_improvement": "+15% round win rate"
    }
  ]
}
```

---

## Endpoints de Visualizações

### GET /viz/heatmap

```
Query params:
  ?match_id=uuid (ou ?player=76561...&last_n_matches=10)
  &map=mirage
  &type=kills|deaths|positions|utility
  &side=ct|t
  &player=76561... (opcional, filtrar por jogador)

Response 200:
{
  "type": "kills",
  "grid_resolution": 50,
  "data": [
    [0, 0, 0, 1, 3, 5, 2, ...],  // row 0
    [0, 1, 2, 4, 8, 12, 5, ...], // row 1
    ...
  ],
  "bounds": { "x_min": -3230, "x_max": 1820, "y_min": -3490, "y_max": 1710 }
}
```

### GET /viz/trajectories

```
Query params: ?match_id=uuid&round=5

Response 200:
{
  "round": 5,
  "trajectories": [
    {
      "player": "Player1",
      "team": "ct",
      "path": [
        { "tick": 0, "x": 150.5, "y": -230.2, "alive": true },
        { "tick": 64, "x": 155.0, "y": -228.0, "alive": true },
        { "tick": 128, "x": 160.2, "y": -225.5, "alive": true }
      ]
    }
  ]
}
```

---

## Endpoints de Gestão de Equipa

### GET /teams

```json
// Response 200
{
  "teams": [
    {
      "id": "uuid",
      "name": "Main Roster",
      "tag": "EX",
      "players_count": 5,
      "matches_count": 45,
      "is_active": true
    }
  ]
}
```

### POST /teams

```json
// Request
{
  "name": "Main Roster",
  "tag": "EX",
  "game_team_name": "Team Exemplo"
}

// Response 201
{ "id": "uuid", "name": "Main Roster", "tag": "EX" }
```

### POST /teams/{id}/players

```json
// Request
{ "steam_id": "76561...", "display_name": "Player1", "role": "entry" }

// Response 201
{ "id": "uuid", "steam_id": "76561...", "display_name": "Player1", "role": "entry" }
```

### GET /teams/{id}/stats

```json
// Response 200
{
  "team": "Main Roster",
  "period": "last_30_days",
  "matches": 25,
  "win_rate": 0.64,
  "map_stats": {
    "mirage": { "played": 8, "won": 6, "win_rate": 0.75 },
    "inferno": { "played": 6, "won": 3, "win_rate": 0.50 }
  },
  "avg_errors_per_match": 11.2,
  "error_trend": "improving",
  "avg_rating": 72.5,
  "top_performer": { "name": "Player3", "rating": 82.0 }
}
```
