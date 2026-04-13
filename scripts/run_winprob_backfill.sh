#!/usr/bin/env bash
# One-shot backfill for win-probability on historical pro matches.
# Requires Celery worker + Redis running (docker compose up) and backend env vars set.
#
# Usage: PAGES=60 ./scripts/run_winprob_backfill.sh

set -euo pipefail

PAGES=${PAGES:-60}

cd "$(dirname "$0")/../packages/backend"

echo "[backfill] enqueuing backfill_hltv(pages=${PAGES})"
uv run python -c "
from src.tasks.pro_ingestion import backfill_hltv
task = backfill_hltv.delay(pages=${PAGES})
print(f'enqueued: {task.id}')
"

echo "[backfill] tail the celery worker logs to follow progress"
echo "[backfill] verify coverage:"
cat <<'SQL'
psql \$DATABASE_URL -c "
  SELECT
    COUNT(*) FILTER (WHERE win_prob IS NOT NULL) AS with_pred,
    COUNT(*) FILTER (WHERE win_prob IS NULL) AS missing,
    COUNT(*) AS total
  FROM rounds r
  JOIN matches m ON r.match_id = m.id
  WHERE m.source = 'hltv';
"
SQL
