#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backup.dump>"
  exit 1
fi

backup_file="$1"
if [[ ! -f "${backup_file}" ]]; then
  echo "Backup file not found: ${backup_file}"
  exit 1
fi

user="${POSTGRES_USER:-geoeye}"
test_db="${RESTORE_TEST_DB:-geoeye_restore_test}"

echo "Creating restore test database '${test_db}' (if needed)"
docker compose exec -T postgres psql -U "${user}" -d postgres -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = current_setting('RESTORE_TEST_DB', true)) THEN
    -- no-op: variable not set
  END IF;
END $$;
SQL

# We can't reliably read env vars inside the container via SQL above in a portable way.
# Create/drop using psql commands from the host-side env.
docker compose exec -T postgres psql -U "${user}" -d postgres -v ON_ERROR_STOP=1 \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${test_db}' AND pid <> pg_backend_pid();" || true
docker compose exec -T postgres psql -U "${user}" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS \"${test_db}\";"
docker compose exec -T postgres psql -U "${user}" -d postgres -v ON_ERROR_STOP=1 \
  -c "CREATE DATABASE \"${test_db}\";"

echo "Restoring backup into '${test_db}'"
docker compose exec -T postgres pg_restore \
  -U "${user}" \
  --dbname "${test_db}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  "${backup_file}"

echo "Running smoke queries"
docker compose exec -T postgres psql -U "${user}" -d "${test_db}" -v ON_ERROR_STOP=1 <<'SQL'
SELECT current_database() AS db, now() AS now;
SELECT COUNT(*) AS users FROM users;
SELECT COUNT(*) AS satellite_images FROM satellite_images;
SELECT COUNT(*) AS detections FROM detections;
SELECT postgis_full_version() AS postgis_version;
SQL

echo "OK: restore smoke test passed."

