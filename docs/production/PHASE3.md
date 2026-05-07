## Phase 3 — Database correctness, migrations, backup/restore (production-grade)

This repo already includes:
- PostGIS extension enablement (`infra/sql/init.sql`)
- Alembic-driven SQL migrations (`backend/alembic/versions/*.py` executing `backend/migrations/*.sql`)
- Core spatial indexes in initial schema (`backend/migrations/001_initial.sql`)
- Analytics views + a partition-mirroring strategy (`backend/migrations/002_analytics_and_partitioning.sql`)

Phase 3 production upgrades implemented in the repo:
- **Production-safe backups** via `pg_dump --format=custom`
- **Production-safe restores** via `pg_restore --clean --if-exists`
- **Restore drill (smoke test)** into a dedicated restore-test database

### Backups

- Create a backup:

```bash
./infra/scripts/backup_db.sh
```

- Output:
  - Custom-format dump under `./backups/` by default.
  - Override location with `BACKUP_DIR=/path`.

### Restores

**Warning**: restore performs a `--clean` restore (drops/recreates objects).

- Restore into the main DB:

```bash
./infra/scripts/restore_db.sh backups/geoeye_YYYYMMDD_HHMMSS.dump
```

- Restore into a specific DB:

```bash
./infra/scripts/restore_db.sh backups/geoeye_YYYYMMDD_HHMMSS.dump geoeye_staging
```

### Restore drill (recommended)

This creates a fresh database (default `geoeye_restore_test`), restores into it, then runs smoke queries.

```bash
./infra/scripts/restore_smoketest.sh backups/geoeye_YYYYMMDD_HHMMSS.dump
```

Override test DB name:

```bash
RESTORE_TEST_DB=my_restore_test ./infra/scripts/restore_smoketest.sh backups/...
```

### Migration policy (operational)

- Migrations are **forward-only**.
- Treat schema changes as **expand/contract** when you need zero-downtime:
  - add new column/table/index
  - deploy code that writes both / reads new
  - backfill
  - later remove old pieces in a separate change window

### What to do next (not yet automated here)

- Decide/record **RPO/RTO** and implement backup scheduling + off-host storage.
- Add DB monitoring/alerting (disk, connections, slow queries, backup failures).
- Add periodic “restore drill” to a staging environment.

