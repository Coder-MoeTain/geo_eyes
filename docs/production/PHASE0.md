## Phase 0 — Production baseline (definition + readiness)

This document is the **contract** for what “production-grade” means for GeoEye-AI in your organization. Later phases implement and enforce these requirements.

### Scope

- **Primary workflows**
  - Upload GeoTIFF/COG → run detection asynchronously → review detections → export (GeoJSON/CSV).
  - Airport-centric intelligence: search airports, view nearby detections/activity.
  - Change detection workflows.
- **Non-goals (v1)**
  - Multi-tenant SaaS.
  - Guaranteed aircraft detection on medium/low-resolution imagery sources (e.g. Sentinel/Landsat).

### Deployment target (choose and record)

Record your initial production target and why:

- **Option A (recommended first step)**: Single VM + Docker Compose + Nginx reverse proxy
- **Option B**: Kubernetes (API/worker/frontend/titiler as separate deployments; managed Postgres/Redis preferred)

Also decide:
- Where **Postgres** runs (same host vs managed)
- Where **uploads** live (local disk vs object storage)
- Whether **GPU workers** are required (yes/no)

### Workload sizing (numbers that drive architecture)

Capture expected and peak:
- Concurrent analysts:
- Uploads/day:
- Average image size (MB):
- Peak upload size (MB):
- Detection jobs/day:
- Peak concurrent jobs:
- Typical job runtime p50/p95:
- Tile requests/sec peak:
- Storage growth/day:
- Retention windows (imagery/detections/logs):

### Reliability targets (SLOs)

Define measurable SLOs and error budget.

- **API availability**: e.g. 99.5% monthly
- **API latency** (p95)
  - `/api/v1/login`
  - `/api/v1/uploads` / signed upload
  - `/api/v1/detections`
  - `/api/v1/jobs/{task_id}`
- **Job SLOs**
  - Job enqueue time
  - Time-to-result p50/p95 for “typical” images
  - Max acceptable backlog delay
- **Data integrity**
  - “No silent corruption” requirement; errors must surface

### Security baseline (minimum bar)

- TLS required at the gateway
- Secrets never stored in git
- Strict CORS in production (no wildcard origins when credentials are enabled)
- Cookie security in production (Secure, SameSite policy)
- RBAC and audit logging for sensitive actions (model activation/deletion, user admin actions, exports)

### Data classification + retention + recoverability

- Define what is sensitive (uploads, detections, audit logs, user accounts)
- Define retention windows and deletion expectations
- Define recovery targets:
  - **RPO** (max data loss):
  - **RTO** (max downtime):

### Operating model

- On-call coverage (none / business hours / 24x7):
- Incident severity definitions (Sev1/2/3):
- Escalation path:
- Release policy (deploy window, approvals, rollback expectations):

### Go-live gate (Phase 0 output)

Before go-live, these must exist (implemented in later phases):
- Backups + restore drill completed at least once
- Monitoring/alerting for API/worker/DB/Redis/disk space
- Runbooks for deploy, rollback, restore, rotate secrets, scale workers
- Access control for hosts and secrets

