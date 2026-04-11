#!/usr/bin/env bash
# backup-models.sh — tar + gzip ML models dir, upload to S3.
#
# Required env vars:
#   MODELS_DIR          e.g. /var/lib/cs2/models
#   S3_BUCKET, S3_ENDPOINT
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# Optional:
#   BACKUP_PREFIX (default: models)
#   STAGING_DIR (default: /var/backups/cs2)
#
# Cron example (weekly Sunday 04:00 UTC):
#   0 4 * * 0 /opt/cs2/scripts/backup/backup-models.sh >> /var/log/cs2-models-backup.log 2>&1

set -euo pipefail

: "${MODELS_DIR:?MODELS_DIR required}"
: "${S3_BUCKET:?S3_BUCKET required}"
: "${S3_ENDPOINT:?S3_ENDPOINT required}"

if [[ ! -d "${MODELS_DIR}" ]]; then
  echo "MODELS_DIR ${MODELS_DIR} not found" >&2
  exit 1
fi

BACKUP_PREFIX="${BACKUP_PREFIX:-models}"
STAGING_DIR="${STAGING_DIR:-/var/backups/cs2}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILENAME="${BACKUP_PREFIX}-${TIMESTAMP}.tar.gz"
LOCAL_PATH="${STAGING_DIR}/${FILENAME}"

mkdir -p "${STAGING_DIR}"

echo "[$(date -Iseconds)] Archiving ${MODELS_DIR}..."
tar --create --gzip \
  --file "${LOCAL_PATH}" \
  --directory "$(dirname "${MODELS_DIR}")" \
  "$(basename "${MODELS_DIR}")"

SIZE=$(du -h "${LOCAL_PATH}" | cut -f1)
echo "[$(date -Iseconds)] Archive complete: ${LOCAL_PATH} (${SIZE})"

echo "[$(date -Iseconds)] Uploading to s3://${S3_BUCKET}/${BACKUP_PREFIX}/${FILENAME}..."
aws --endpoint-url "${S3_ENDPOINT}" s3 cp \
  "${LOCAL_PATH}" \
  "s3://${S3_BUCKET}/${BACKUP_PREFIX}/${FILENAME}" \
  --storage-class STANDARD_IA

echo "[$(date -Iseconds)] Models backup OK: ${FILENAME}"

# Keep only latest 4 local archives
ls -1t "${STAGING_DIR}/${BACKUP_PREFIX}-"*.tar.gz 2>/dev/null | tail -n +5 | xargs -r rm -f
