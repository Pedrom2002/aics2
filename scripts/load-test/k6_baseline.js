// k6 load-test for cs2-analytics.
// Usage:
//   API_BASE=https://api.staging.cs2analytics.example.com \
//   API_KEY=csk_xxx_yyy \
//   k6 run scripts/load-test/k6_baseline.js

import http from 'k6/http'
import { check, sleep } from 'k6'
import { Trend, Rate } from 'k6/metrics'

const errorRate = new Rate('errors')
const winProbLatency = new Trend('win_prob_latency', true)
const heatmapLatency = new Trend('heatmap_latency', true)

const API = __ENV.API_BASE || 'http://localhost:8000/api/v1'
const API_KEY = __ENV.API_KEY || ''
const MATCH_ID = __ENV.MATCH_ID || '00000000-0000-0000-0000-000000000000'

export const options = {
  stages: [
    { duration: '30s', target: 20 },   // baseline
    { duration: '2m',  target: 100 },  // 5x
    { duration: '2m',  target: 200 },  // 10x
    { duration: '1m',  target: 0 },    // cooldown
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    errors: ['rate<0.05'],
    win_prob_latency: ['p(95)<1500'],
  },
}

const authHeaders = API_KEY
  ? { 'X-API-Key': API_KEY }
  : {}

export default function () {
  const matches = http.get(`${API}/public/matches?limit=25`, { headers: authHeaders })
  check(matches, { 'matches 200': (r) => r.status === 200 })
  errorRate.add(matches.status !== 200)

  const wp = http.get(`${API}/win-prob/${MATCH_ID}`, { headers: authHeaders })
  winProbLatency.add(wp.timings.duration)
  errorRate.add(wp.status >= 500)

  const heat = http.get(`${API}/matches/${MATCH_ID}/heatmap?type=positions`, {
    headers: authHeaders,
  })
  heatmapLatency.add(heat.timings.duration)
  errorRate.add(heat.status >= 500)

  sleep(1)
}
