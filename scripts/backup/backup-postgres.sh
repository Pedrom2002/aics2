#!/usr/bin/env bash
# backup-postgres.sh — pg_dump → gzip → S3-compatible upload.
#
# Required env vars:
#   PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
#   S3_BUCKET           e.g. cs2-analytics-backups
#   S3_ENDPOINT         e.g. https://s3.amazonaws.com (or MinIO endpoint)
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# Optional:
#   BACKUP_PREFIX       default: postgres
#   RETENTION_DAYS      default: 30 (only for local staging dir)
#   STAGING_DIR         default: /var/backups/cs2
#
# Usage:
#   ./backup-postgres.sh
#
# Cron example (daily 03:15 UTC):
#   15 3 * * * /opt/cs2/scripts/backup/backup-postgres.sh >> /var/log/cs2-backup.log 2>&1

set -euo pipefail

: "${PGHOST:?PGHOST required}"
: "${PGUSER:?PGUSER required}"
: "${PGDATABASE:?PGDATABASE required}"
: "${S3_BUCKET:?S3_BUCKET required}"
: "${S3_ENDPOINT:?S3_ENDPOINT required}"

BACKUP_PREFIX="${BACKUP_PREFIX:-postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
STAGING_DIR="${STAGING_DIR:-/var/backups/cs2}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILENAME="${BACKUP_PREFIX}-${PGDATABASE}-${TIMESTAMP}.sql.gz"
LOCAL_PATH="${STAGING_DIR}/${FILENAME}"

mkdir -p "${STAGING_DIR}"

echo "[$(date -Iseconds)] Dumping ${PGDATABASE} from ${PGHOST}..."
pg_dump \
  --host="${PGHOST}" \
  --port="${PGPORT:-5432}" \
  --username="${PGUSER}" \
  --dbname="${PGDATABASE}" \
  --format=custom \
  --no-owner \
  --no-privileges \
  --verbose \
  | gzip -9 > "${LOCAL_PATH}"

SIZE=$(du -h "${LOCAL_PATH}" | cut -f1)
echo "[$(date -Iseconds)] Dump complete: ${LOCAL_PATH} (${SIZE})"

echo "[$(date -Iseconds)] Uploading to s3://${S3_BUCKET}/${BACKUP_PREFIX}/${FILENAME}..."
aws --endpoint-url "${S3_ENDPOINT}" s3 cp \
  "${LOCAL_PATH}" \
  "s3://${S3_BUCKET}/${BACKUP_PREFIX}/${FILENAME}" \
  --storage-class STANDARD_IA

echo "[$(date -Iseconds)] Upload complete."

# Local retention
find "${STAGING_DIR}" -name "${BACKUP_PREFIX}-*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete
echo "[$(date -Iseconds)] Local retention applied (>${RETENTION_DAYS} days removed)."

echo "[$(date -Iseconds)] Backup OK: ${FILENAME}"
