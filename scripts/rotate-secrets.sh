#!/usr/bin/env bash
# Rotate all runtime secrets stored in AWS Secrets Manager.
# external-secrets picks up the new version within refreshInterval (1h).

set -euo pipefail

ENV=${ENV:-production}
REGION=${AWS_REGION:-eu-west-1}

rotate() {
  local secret=$1
  local generator=$2
  local new_value
  new_value=$(eval "$generator")
  aws secretsmanager put-secret-value \
    --secret-id "cs2/${ENV}/${secret}" \
    --secret-string "$new_value" \
    --region "$REGION" >/dev/null
  echo "rotated cs2/${ENV}/${secret}"
}

rotate jwt 'jq -nc --arg s "$(openssl rand -hex 48)" "{secret:\$s}"'
rotate s3  'jq -nc --arg a "$(openssl rand -hex 16)" --arg k "$(openssl rand -hex 32)" "{access_key:\$a,secret_key:\$k}"'

echo "Secrets Manager rotations complete. external-secrets will roll in <= 1h."
echo "Force immediate rollout:"
echo "  kubectl -n cs2-analytics rollout restart deploy/backend deploy/frontend"
