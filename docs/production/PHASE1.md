## Phase 1 — Reproducible config + secrets (implemented)

### What Phase 1 adds to this repo

- Root `.env.example` that matches actual backend/frontend/docker-compose configuration.
- A backend config validator you can run locally and in CI to catch:
  - invalid JSON config values
  - unsafe production settings (CORS/cookies/JWT secret)
  - risky defaults for production
- CI wiring to run config validation on every push/PR.

### How to use

- Create runtime env:
  - Copy `.env.example` → `.env`
- Validate config without running services:
  - `python -m app.core.validate_config --env-file ../.env.example`

### Production guidance

- In production:
  - inject secrets via your deployment system (do not store `.env` in git)
  - set `ENV=production`
  - set `JWT_SECRET` to a strong value
  - set strict `CORS_ALLOWED_ORIGINS_JSON` (no `"*"`) especially when credentials are enabled
  - set `SECURE_COOKIES=true` when serving over HTTPS

