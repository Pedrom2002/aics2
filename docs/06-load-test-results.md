# Load test — methodology

Run the k6 baseline against staging:

```bash
API_BASE=https://api.staging.cs2analytics.example.com \
API_KEY=csk_xxx_yyy \
MATCH_ID=<uuid-of-a-match-with-full-data> \
k6 run scripts/load-test/k6_baseline.js
```

Stages: 20 → 100 → 200 RPS over ~5 minutes. Thresholds:

- `http_req_duration` p95 < 2 s
- custom `win_prob_latency` p95 < 1.5 s
- `errors` rate < 5 %

## Expected first bottlenecks

Based on the architecture:

1. **ML inference** — win-prob + SHAP calls hit LightGBM + explainability
   engine. Model is loaded per-worker, so the first spike shows cold-start
   latency. Mitigation: pre-warm on container start, scale replicas.

2. **Postgres connection pool saturation** — asyncpg pool defaults to 10
   connections. Under ~150 concurrent RPS the pool queues. Mitigation:
   bump pool to 30, enable PgBouncer in-cluster.

3. **Heatmap aggregations** — per-match Polars aggregations over rounds.
   Cache the output in Redis with a 15-minute TTL.

Record real numbers here after the first staging run.
