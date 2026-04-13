#!/usr/bin/env bash
# Smoke-test a freshly deployed staging cluster.
# Requires: API_BASE and FRONTEND_BASE env vars pointing at the staging hostnames.

set -euo pipefail

API=${API_BASE:-https://api.staging.cs2analytics.example.com}
FRONT=${FRONTEND_BASE:-https://app.staging.cs2analytics.example.com}

echo "[smoke] API root ($API/api/v1/health/live)"
curl -fsS "$API/api/v1/health/live" >/dev/null && echo "  ok"

echo "[smoke] API Prometheus metrics"
curl -fsS "$API/metrics" | head -5

echo "[smoke] Register + login round-trip"
EMAIL="smoke-$(date +%s)@test.com"
PAYLOAD=$(jq -n --arg e "$EMAIL" '{org_name:"Smoke",email:$e,password:"smokepassword123",display_name:"Smoke"}')
TOKEN=$(curl -fsS -H 'content-type: application/json' -d "$PAYLOAD" "$API/api/v1/auth/register" | jq -r .access_token)
[ -n "$TOKEN" ] && [ "$TOKEN" != "null" ] && echo "  token acquired"

echo "[smoke] Authenticated demos list"
curl -fsS -H "authorization: Bearer $TOKEN" "$API/api/v1/demos" | jq '.page,.total'

echo "[smoke] Security headers"
curl -fsS -I "$FRONT" | grep -iE 'content-security-policy|strict-transport|x-frame' || true

echo "[smoke] Force a backend error to check Sentry capture"
curl -sS -o /dev/null -w "status=%{http_code}\n" "$API/api/v1/demos/00000000-0000-0000-0000-000000000000" \
  -H "authorization: Bearer $TOKEN"

echo "[smoke] done — check Grafana + Sentry dashboards for the new events"
