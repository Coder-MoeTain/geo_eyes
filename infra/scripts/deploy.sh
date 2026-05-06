#!/usr/bin/env bash
set -euo pipefail

cp -n .env.example .env || true
docker compose up --build -d
echo "GeoEye-AI deployed. Frontend: http://localhost:5173 API: http://localhost:8000/docs"
