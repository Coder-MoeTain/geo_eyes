# GeoEye-AI Intelligence Portal

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-42b883?logo=vuedotjs&logoColor=white)
![PostGIS](https://img.shields.io/badge/PostGIS-Enabled-336791?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

GeoEye-AI is a local-first GEOINT platform for aircraft intelligence workflows. It combines geospatial ingestion, asynchronous ML inference, change analysis, and analyst-facing map UI in a single stack.

## Table of Contents

- [What It Does](#what-it-does)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Core Workflows](#core-workflows)
- [API Highlights](#api-highlights)
- [Testing](#testing)
- [Operational Docs](#operational-docs)
- [Security Notes](#security-notes)
- [Known Constraints](#known-constraints)

## What It Does

- Upload and validate imagery (GeoTIFF/COG preferred for precise geospatial workflows)
- Run aircraft detection jobs asynchronously through Celery workers
- Manage model lifecycle (upload, activate, disable, delete)
- Visualize detections and heatmaps in map-centric analyst UI
- Support airport-centric intelligence views and historical comparisons
- Generate tile overlays via TiTiler for interactive map rendering

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, Alembic, Celery, Redis
- **Data/Geo:** PostgreSQL + PostGIS, GeoPandas, Rasterio, Shapely, GDAL, TiTiler
- **ML:** PyTorch, Ultralytics YOLOv8, Transformers (auxiliary workflows)
- **Frontend:** Vue 3, TypeScript, Pinia, Vite, Leaflet, Cesium
- **Infra:** Docker Compose, Nginx, CI workflow via GitHub Actions

## Repository Structure

```text
.
|-- backend/         # FastAPI app, DB models, migrations, Celery worker/tasks
|-- frontend/        # Vue + TypeScript web app
|-- ai/              # Dataset preparation and training utilities
|-- data/            # Runtime data, models, datasets
|-- docs/            # Operational and engineering documentation
|-- infra/           # Nginx config and operational scripts
|-- docker-compose.yml
`-- .env.example
```

## Getting Started

### Prerequisites

- Docker + Docker Compose
- Git

### 1) Clone and enter repository

```bash
git clone <your-repo-url>
cd "geo intelligence"
```

### 2) Create environment file

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### 3) Launch full stack

```bash
docker compose up --build
```

This starts PostGIS, Redis, migrations, API, worker, frontend, Nginx, and TiTiler.

### 4) Access services

- Frontend: [http://localhost:5173](http://localhost:5173)
- API docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Nginx gateway: [http://localhost](http://localhost)
- TiTiler proxy: [http://localhost/titiler](http://localhost/titiler)
- Health endpoint: [http://localhost:8000/health](http://localhost:8000/health)

### Optional: GPU worker profile

```bash
docker compose --profile gpu up --build
```

## Configuration

Base configuration is in `.env.example`. Copy into `.env` and update values for your environment.

Key settings:

- **Auth/security:** `JWT_SECRET`, `DEFAULT_ADMIN_ENABLED`, `DEFAULT_ADMIN_*`, `SECURE_COOKIES`, `COOKIE_SAMESITE`
- **CORS:** `CORS_ALLOWED_ORIGINS_JSON`, `CORS_ALLOW_CREDENTIALS`
- **Database/cache:** `POSTGRES_*`, `DATABASE_URL`, `REDIS_URL`
- **Task queue:** `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- **ML/modeling:** `YOLO_MODEL_PATH`, `MODEL_DIR`, `DETECTION_THRESHOLDS_JSON`
- **Uploads/tiles:** `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `TITILER_BASE_URL`

## Core Workflows

### Upload -> Detect -> Review

1. Upload an image using `/api/v1/uploads` (or signed upload flow).
2. Start inference with `/api/v1/uploads/{image_id}/detect`.
3. Poll completion via `/api/v1/jobs/{task_id}`.
4. Inspect detections from `/api/v1/detections` or `/api/v1/detections/geojson`.
5. Review QA status via `/api/v1/detections/{id}/review`.

### Model Management

- Upload model: `/api/v1/models/upload`
- Activate model: `/api/v1/models/{model_id}/activate`
- Disable model: `/api/v1/models/{model_id}/disable`
- Delete inactive model: `/api/v1/models/{model_id}`

### Airport Intelligence

- Search airports: `/api/v1/airports/search`
- Airport summary: `/api/v1/airports/{airport_id}`
- Activity near airport: `/api/v1/airports/{airport_id}/activity`
- Nearby detections: `/api/v1/airports/{airport_id}/detections`

## API Highlights

Representative endpoints:

- `POST /api/v1/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/uploads`
- `POST /api/v1/uploads/sign`
- `POST /api/v1/uploads/signed/{token}`
- `POST /api/v1/uploads/{image_id}/detect`
- `POST /api/v1/detect/coordinate`
- `GET /api/v1/jobs/{task_id}`
- `GET /api/v1/satellite-image`
- `GET /api/v1/detections`
- `GET /api/v1/heatmap`
- `POST /api/v1/change-detection`

Full interactive API docs are available at `/docs` when backend is running.

## Testing

### Backend

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run typecheck
npm test
npm run build
```

CI validates backend tests, frontend type checks/tests/build, and Docker Compose config.

## Quick Sample Dataset (Real Data Subset)

Build a small training subset from your real converted datasets (no synthetic/demo images):

```bash
python ai/prepare_dataset.py --include-xview --include-dota --include-dior --include-rareplanes --max-samples 600 --output data/datasets/sample_training
```

Then train:

```bash
python ai/training.py --data-yaml data/datasets/sample_training/data.yaml --model yolov8m.pt --epochs 20 --imgsz 1024 --batch 8 --device 0
```

## Operational Docs

- `docs/geospatial-correctness.md`
- `docs/model-management.md`
- `docs/imagery-workflow.md`
- `docs/production-deployment.md`
- `docs/security-hardening.md`
- `docs/testing.md`

## Security Notes

- Access + refresh token model with rotation/revocation
- Login brute-force protection and API rate limiting
- HTTP-only cookie support for auth flows
- Security response headers enabled in middleware
- Audit logging for sensitive actions

## Known Constraints

- Medium/low-resolution imagery (for example Sentinel-2/Landsat) is typically unsuitable for reliable aircraft detection.
- For best results, use high-resolution imagery (commonly 0.3m to 1m GSD), preferably uploaded GeoTIFF/COG.
- Validate external dataset licensing before training or redistribution.
