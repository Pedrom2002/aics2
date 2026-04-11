# Backup scripts

Three POSIX shell scripts for snapshotting Postgres and trained ML models to
any S3-compatible bucket (AWS S3, MinIO, Backblaze B2, R2, Wasabi).

## Scripts

| Script | Purpose |
|---|---|
| `backup-postgres.sh` | `pg_dump --format=custom` → gzip → S3 |
| `restore-postgres.sh` | Pull a dump from S3 and `pg_restore` it |
| `backup-models.sh` | tar+gzip the ML models directory → S3 |

## Required tools

- `pg_dump` / `pg_restore` (matching the server major version, 16+)
- `gzip`, `tar`, `find`
- `aws` CLI (works with any S3-compatible endpoint via `--endpoint-url`)

## Environment

Common to all scripts:

```bash
export PGHOST=postgres.cs2.svc.cluster.local
export PGPORT=5432
export PGUSER=cs2user
export PGPASSWORD=...               # or use ~/.pgpass
export PGDATABASE=cs2analytics

export S3_BUCKET=cs2-analytics-backups
export S3_ENDPOINT=https://s3.eu-west-1.amazonaws.com
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

For models:

```bash
export MODELS_DIR=/var/lib/cs2/models
```

## Local cron

```cron
# /etc/cron.d/cs2-backup
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

# Daily Postgres dump at 03:15 UTC
15 3 * * * cs2 /opt/cs2/scripts/backup/backup-postgres.sh >> /var/log/cs2-backup.log 2>&1

# Weekly model archive Sunday 04:00 UTC
0 4 * * 0 cs2 /opt/cs2/scripts/backup/backup-models.sh >> /var/log/cs2-models-backup.log 2>&1
```

## Kubernetes CronJob (preferred)

Run the same scripts inside a small image (`postgres:16-alpine` + `awscli`)
as a `CronJob` in the `cs2-analytics` namespace. Mount env from the secret
already used by the backend (`cs2-analytics-secrets`).

## Restore example

```bash
S3_KEY=postgres/postgres-cs2analytics-20260411T031500Z.sql.gz \
  ./restore-postgres.sh "$S3_KEY"

# Destructive variant:
FORCE_DROP=1 ./restore-postgres.sh "$S3_KEY"
```

## Notes

- All scripts are idempotent w.r.t. naming (timestamps in filenames).
- `backup-postgres.sh` uses `--format=custom` so `pg_restore` can do parallel
  restores and selective object recovery.
- `backup-models.sh` keeps the **last 4 local archives** as a hot cache; S3
  retention is delegated to bucket lifecycle rules.
