export type DemoStatus =
  | 'uploaded'
  | 'queued'
  | 'downloading'
  | 'parsing'
  | 'extracting_features'
  | 'running_models'
  | 'completed'
  | 'failed'
  | 'error'

export interface Demo {
  id: string
  original_filename: string
  file_size_bytes: number
  status: DemoStatus
  error_message: string | null
  created_at: string
  parsing_started_at: string | null
  processing_completed_at: string | null
}

export interface DemoDetail extends Demo {
  s3_key: string
  checksum_sha256: string
  parsing_completed_at: string | null
  processing_started_at: string | null
  match: MatchSummary | null
}

export interface MatchSummary {
  id: string
  map: string
  match_date: string | null
  team1_name: string | null
  team2_name: string | null
  team1_score: number
  team2_score: number
  total_rounds: number
  duration_seconds: number | null
}

export interface RoundData {
  id: string
  round_number: number
  winner_side: string | null
  win_reason: string | null
  team1_score: number
  team2_score: number
  t_economy: number | null
  ct_economy: number | null
  t_equipment_value: number | null
  ct_equipment_value: number | null
  t_buy_type: string | null
  ct_buy_type: string | null
  bomb_planted: boolean | null
  bomb_defused: boolean | null
  plant_site: string | null
  duration_seconds: number | null
}

export interface PlayerStats {
  id: string
  player_steam_id: string
  player_name: string
  team_side: string | null
  kills: number
  deaths: number
  assists: number
  headshot_kills: number
  damage: number
  adr: number | null
  flash_assists: number
  enemies_flashed: number
  utility_damage: number
  first_kills: number
  first_deaths: number
  trade_kills: number
  trade_deaths: number
  kast_rounds: number
  rounds_survived: number
  clutch_wins: number
  multi_kills_3k: number
  multi_kills_4k: number
  multi_kills_5k: number
  overall_rating: number | null
  aim_rating: number | null
  positioning_rating: number | null
  utility_rating: number | null
  game_sense_rating: number | null
  clutch_rating: number | null
}

export interface MatchDetail extends MatchSummary {
  match_type: string | null
  tickrate: number
  overtime_rounds: number
  rounds: RoundData[]
  player_stats: PlayerStats[]
}

export interface PlayerAggregatedStats {
  player_steam_id: string
  player_name: string
  total_matches: number
  total_rounds: number
  total_kills: number
  total_deaths: number
  total_assists: number
  total_headshot_kills: number
  total_damage: number
  total_flash_assists: number
  total_utility_damage: number
  total_first_kills: number
  total_first_deaths: number
  total_trade_kills: number
  total_trade_deaths: number
  total_clutch_wins: number
  total_multi_kills_3k: number
  total_multi_kills_4k: number
  total_multi_kills_5k: number
  total_kast_rounds: number
  total_rounds_survived: number
  avg_kills_per_round: number
  avg_deaths_per_round: number
  avg_kd_ratio: number
  avg_headshot_pct: number
  avg_adr: number
  avg_kast_pct: number
  avg_survival_rate: number
  avg_opening_duel_win_rate: number
  avg_trade_kill_rate: number
  avg_impact_rating: number
  avg_hltv_rating: number
  rating_std_deviation: number
  maps_played: Record<string, number>
  best_map: string | null
  worst_map: string | null
}

export interface MatchEconomyRound {
  round_number: number
  winner_side: string | null
  t_equipment_value: number | null
  ct_equipment_value: number | null
  t_buy_type: string | null
  ct_buy_type: string | null
  team1_score: number
  team2_score: number
}

export interface MatchEconomy {
  match_id: string
  map: string
  total_rounds: number
  rounds: MatchEconomyRound[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}
