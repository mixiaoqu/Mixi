# Agent Platform Backend

## Local database

Start PostgreSQL from the repository root:

```bash
docker compose up -d
```

Then create `backend/.env` from `backend/.env.example`. A working local example is:

```env
APP_ENV=development
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=agent_platform
POSTGRES_USER=root
POSTGRES_PASSWORD=123456
INIT_DB_ON_STARTUP=false
JWT_SECRET=replace-with-a-random-secret-of-at-least-32-characters
```

You can also use a single `DATABASE_URL`, but the backend now supports explicit database host, port, name, user, and password fields. If you already have an older `.env` that uses `POSTGRES_URL`, replace it.

## Migrations

Apply the initial schema:

```bash
cd backend
uv sync
uv run alembic upgrade head
```

Create a new migration after changing SQLAlchemy models:

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"
```

## API

Start the development server:

```bash
uv run uvicorn app.main:app --reload
```

OpenAPI documentation is available at `http://127.0.0.1:8000/docs`. The initial versioned API includes:

- `/api/v1/auth/register`
- `/api/v1/auth/login`
- `/api/v1/auth/refresh`
- `/api/v1/auth/logout`
- `/api/v1/auth/me`
- `/api/v1/users/{user_id}`
- `/api/v1/workspaces`
- `/api/v1/workspaces/{workspace_id}/agents`
- `/api/v1/agents/{agent_id}`

Collection endpoints return `{ items, total, limit, offset }` and accept validated `limit` and `offset` query parameters.

Access tokens are short-lived bearer tokens. Refresh tokens are rotated and stored in an HttpOnly cookie; the database stores only their SHA-256 hashes. Except for registration, login, refresh, health, and metadata, API routes require an `Authorization: Bearer <token>` header.

For frontend development, run `npm run dev` in `frontend`. Vite proxies `/api` requests to the backend at `http://127.0.0.1:8000`.
