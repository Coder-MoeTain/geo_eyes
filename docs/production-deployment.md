# Production Deployment

- Use Alembic migrations (`alembic upgrade head`) before starting API workers.
- Run services with Docker Compose, including `migrate`, `backend`, `worker`, `worker-gpu`, `titiler`, `nginx`.
- Configure strict CORS allow-list and secure cookie settings.
- Use non-default JWT secret and rotate credentials regularly.
