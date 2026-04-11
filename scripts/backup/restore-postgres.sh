#!/usr/bin/env bash
# restore-postgres.sh — fetch backup from S3 and restore into Postgres.
#
# Usage:
#   ./restore-postgres.sh <s3-key>
#   ./restore-postgres.sh postgres/postgres-cs2analytics-20260411T031500Z.sql.gz
#
# Required env vars:
#   PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
#   S3_BUCKET, S3_ENDPOINT
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# Optional:
#   STAGING_DIR (default /var/backups/cs2)
#   FORCE_DROP=1 to drop the target DB before restore (DANGEROUS)

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <s3-key>" >&2
  exit 1
fi

: "${PGHOST:?PGHOST required}"
: "${PGUSER:?PGUSER required}"
: "${PGDATABASE:?PGDATABASE required}"
: "${S3_BUCKET:?S3_BUCKET required}"
: "${S3_ENDPOINT:?S3_ENDPOINT required}"

S3_KEY="$1"
STAGING_DIR="${STAGING_DIR:-/var/backups/cs2}"
FILENAME="$(basename "${S3_KEY}")"
LOCAL_PATH="${STAGING_DIR}/${FILENAME}"

mkdir -p "${STAGING_DIR}"

echo "[$(date -Iseconds)] Downloading s3://${S3_BUCKET}/${S3_KEY} ..."
aws --endpoint-url "${S3_ENDPOINT}" s3 cp \
  "s3://${S3_BUCKET}/${S3_KEY}" \
  "${LOCAL_PATH}"

if [[ "${FORCE_DROP:-0}" == "1" ]]; then
  echo "[$(date -Iseconds)] FORCE_DROP=1 — dropping and recreating ${PGDATABASE}..."
  PGPASSWORD="${PGPASSWORD:-}" psql \
    --host="${PGHOST}" --port="${PGPORT:-5432}" --username="${PGUSER}" \
    --dbname=postgres \
    -c "DROP DATABASE IF EXISTS ${PGDATABASE};" \
    -c "CREATE DATABASE ${PGDATABASE};"
fi

echo "[$(date -Iseconds)] Restoring into ${PGDATABASE}..."
gunzip -c "${LOCAL_PATH}" | pg_restore \
  --host="${PGHOST}" \
  --port="${PGPORT:-5432}" \
  --username="${PGUSER}" \
  --dbname="${PGDATABASE}" \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  --verbose

echo "[$(date -Iseconds)] Restore complete."
