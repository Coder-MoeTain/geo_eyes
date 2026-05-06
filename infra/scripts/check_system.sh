#!/usr/bin/env bash
set -euo pipefail

echo "== Docker services =="
docker compose ps

echo "== Backend health =="
curl -fsS http://localhost:8000/health || true

echo "== Nginx root =="
curl -fsS http://localhost/ || true

echo "== TiTiler endpoint =="
curl -fsS http://localhost/titiler/healthz || true
