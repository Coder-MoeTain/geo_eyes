# Testing

## Backend

```bash
cd backend
pytest
```

## Frontend

```bash
cd frontend
npm install
npm run typecheck
npm test
npm run build
```

## CI

CI runs backend lint/tests, frontend typecheck/tests/build, and Docker Compose config validation.
