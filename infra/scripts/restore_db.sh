#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backup.sql.gz>"
  exit 1
fi

backup_file="$1"
if [[ ! -f "${backup_file}" ]]; then
  echo "Backup file not found: ${backup_file}"
  exit 1
fi

gunzip -c "${backup_file}" | docker compose exec -T postgres psql -U "${POSTGRES_USER:-geoeye}" "${POSTGRES_DB:-geoeye}"
echo "Database restore completed from ${backup_file}"
