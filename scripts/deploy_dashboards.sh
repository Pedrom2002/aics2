#!/usr/bin/env bash
# Ship Grafana dashboards as ConfigMaps in the monitoring namespace.
# Requires kubectl configured against the target cluster.

set -euo pipefail

NS=${NS:-monitoring}
cd "$(dirname "$0")/../infra/monitoring/grafana-dashboards"

for f in *.json; do
  name="grafana-dashboard-$(basename "$f" .json)"
  kubectl -n "$NS" create configmap "$name" \
    --from-file="$f" \
    --dry-run=client -o yaml \
    | kubectl label --local -f - grafana_dashboard=1 --dry-run=client -o yaml \
    | kubectl apply -f -
  echo "deployed $name"
done

# PrometheusRule from alert-rules.yml
kubectl -n "$NS" apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cs2-analytics
  labels:
    release: kube-prometheus-stack
spec:
$(sed 's/^/  /' ../alert-rules.yml)
EOF
