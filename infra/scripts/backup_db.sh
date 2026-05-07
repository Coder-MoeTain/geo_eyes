#!/usr/bin/env bash
set -euo pipefail

backup_dir="${BACKUP_DIR:-backups}"
mkdir -p "${backup_dir}"

timestamp="$(date +%Y%m%d_%H%M%S)"
db="${POSTGRES_DB:-geoeye}"
user="${POSTGRES_USER:-geoeye}"

# Prefer custom format so restores can be selective and safer (pg_restore).
outfile="${backup_dir}/${db}_${timestamp}.dump"

echo "Creating backup for db='${db}' into '${outfile}'"

# Notes:
# - --no-owner/--no-privileges makes the dump portable across environments.
# - --format=custom enables pg_restore features.
docker compose exec -T postgres pg_dump \
  -U "${user}" \
  --format=custom \
  --no-owner \
  --no-privileges \
  "${db}" > "${outfile}"

echo "Database backup written to ${outfile}"
