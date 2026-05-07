#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <backup.dump> [target_db]"
  exit 1
fi

backup_file="$1"
if [[ ! -f "${backup_file}" ]]; then
  echo "Backup file not found: ${backup_file}"
  exit 1
fi

target_db="${2:-${POSTGRES_DB:-geoeye}}"
user="${POSTGRES_USER:-geoeye}"

echo "Restoring '${backup_file}' into db='${target_db}'"
echo "WARNING: This will drop/recreate objects in the target database."

# Safer restore using pg_restore. Requires custom-format dump from backup_db.sh.
docker compose exec -T postgres pg_restore \
  -U "${user}" \
  --dbname "${target_db}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  "${backup_file}"

echo "Database restore completed from ${backup_file}"
