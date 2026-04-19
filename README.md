# TheVault

TheVault is a secure secrets and credentials manager scaffolded around the architecture you sketched:

- `frontend/`: React + TypeScript client built with Next.js
- `backend/`: FastAPI backend with JWT auth, RBAC, rate limiting, AES encryption, and audit logging
- `docker-compose.yml`: local Postgres + Redis dependencies

## Architecture

```text
React + TypeScript client
        |
    FastAPI API
        |
Auth service | Secrets service | Audit log
        |
   Postgres + Redis
```

## Current MVP capabilities

- User registration and login
- JWT bearer auth with Redis-backed token revocation on logout
- Redis-backed fixed-window rate limiting with in-memory fallback
- AES encryption before secret values are persisted
- Secret create, list, reveal, update, and delete flows
- Audit events for auth and secret operations
- Role bootstrap: the first registered user becomes `admin`

## Local setup

### 1. Start infrastructure

```bash
docker compose up -d
```

This starts:

- Postgres on `localhost:5432`
- Redis on `localhost:6379`

### 2. Configure the backend

```bash
cd backend
copy .env.example .env
python -m venv .venv
<activate the virtual environment in your shell>
python -m pip install --upgrade pip
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

API base URL: `http://localhost:8000/api/v1`

### 3. Configure the frontend

```bash
cd frontend
copy .env.local.example .env.local
npm install
npm run dev
```

Frontend URL: `http://localhost:3000`

## Important environment variables

Backend:

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `ENCRYPTION_KEY`
- `FRONTEND_ORIGIN`
- `RATE_LIMIT_PER_MINUTE`

Frontend:

- `NEXT_PUBLIC_API_URL`

## API surface

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/secrets`
- `POST /api/v1/secrets`
- `GET /api/v1/secrets/{secret_id}`
- `PATCH /api/v1/secrets/{secret_id}`
- `DELETE /api/v1/secrets/{secret_id}`
- `GET /api/v1/audit`
- `GET /api/v1/health`

## Notes

- This scaffold bootstraps tables with direct Postgres DDL on startup instead of migrations.
- The encryption key is derived from `ENCRYPTION_KEY`; use a strong dedicated value outside development.
- The frontend stores the bearer token in `localStorage` for speed of setup. For production, move to a stricter session strategy.
