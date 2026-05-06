#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups
timestamp="$(date +%Y%m%d_%H%M%S)"
outfile="backups/geoeye_${timestamp}.sql.gz"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-geoeye}" "${POSTGRES_DB:-geoeye}" | gzip > "${outfile}"
echo "Database backup written to ${outfile}"
