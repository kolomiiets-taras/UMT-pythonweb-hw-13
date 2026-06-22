# Contacts REST API

A REST API for storing and managing contacts, with JWT auth (access + refresh
token pair), email verification, password reset, per-user data isolation,
role-based access (`user` / `admin`), Redis caching, rate limiting, CORS, and
Cloudinary avatar uploads.

Built with **FastAPI**, **async SQLAlchemy 2.0**, **PostgreSQL**, **Redis**.
Tested with **pytest** (>75% coverage) and documented with **Sphinx**.

## Features

### Contacts (per authenticated user)
- Full CRUD, scoped to the current user
- Search by first name / last name / email (query params)
- Birthdays in the next N days (default 7)

### Auth & users
- **Signup** — bcrypt-hashed password, `201`; duplicate email → `409`
- **Login** — OAuth2 form (email + password); issues **access + refresh** tokens;
  bad creds or unconfirmed email → `401`
- **Refresh** (`GET /api/auth/refresh_token`) — rotate the token pair
- **Email verification** — tokenized confirmation link
- **Password reset** — `forgot_password` emails a reset token; `reset_password`
  sets the new password
- **Roles** — `user` / `admin`; only **admins** may change the default avatar
- **`/api/users/me`** — current user, **rate limited** (10/min)
- **Redis cache** — `get_current_user` reads from Redis, falling back to the DB
  on a miss; cache is invalidated on any user change
- **CORS** enabled

## Models

**User**: `id`, `username`, `email` (unique), `password` (hashed), `avatar`,
`refresh_token`, `confirmed`, `role` (`user`/`admin`), `created_at`.

**Contact**: `id`, `first_name`, `last_name`, `email`, `phone`, `birthday`,
`additional_data` (optional), `user_id` (FK → users).

## Run everything in Docker

```bash
cp .env.example .env          # fill in real JWT/SMTP/Cloudinary secrets
docker compose up -d --build  # postgres + redis + api (migrations run on boot)
```

API at http://localhost:8000/docs. The `api` service reaches `postgres` and
`redis` by their compose service names.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

docker compose up -d postgres redis
alembic upgrade head
uvicorn main:app --reload
```

## Tests & coverage

```bash
pytest --cov=src --cov-report=term-missing
```

- Unit tests: `tests/test_repository_*.py`, `tests/test_cache.py`, `tests/test_email.py`
- Integration tests (routes): `tests/test_routes_*.py`
- Tests run against an in-memory SQLite DB; Redis, email and Cloudinary are stubbed.
- Current coverage: **~82%** (requirement: >75%).

## Documentation (Sphinx)

```bash
cd docs && python -m sphinx -b html . _build/html
# open docs/_build/html/index.html
```

All main functions/methods carry docstrings (Google/NumPy style via
`sphinx.ext.napoleon`).

## Environment variables (`.env`)

| Var | Purpose |
|-----|---------|
| `DB_URL` | async SQLAlchemy Postgres URL |
| `JWT_SECRET`, `JWT_ALGORITHM` | JWT signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | token lifetimes |
| `EMAIL_TOKEN_EXPIRE_HOURS`, `RESET_TOKEN_EXPIRE_HOURS` | verification / reset token lifetimes |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `USER_CACHE_TTL` | Redis cache |
| `MAIL_*` | SMTP config (fastapi-mail) |
| `CLD_NAME`, `CLD_API_KEY`, `CLD_API_SECRET` | Cloudinary |

No secrets are hardcoded — all read from the environment.

## Endpoints

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/api/auth/signup` | – | 201 / 409 on dup |
| POST | `/api/auth/login` | – | access + refresh tokens |
| GET | `/api/auth/refresh_token` | refresh | rotate tokens |
| GET | `/api/auth/confirmed_email/{token}` | – | confirm email |
| POST | `/api/auth/request_email` | – | resend confirmation |
| POST | `/api/auth/forgot_password` | – | email reset token |
| POST | `/api/auth/reset_password` | – | set new password |
| GET | `/api/users/me` | ✅ | rate limited, cached |
| PATCH | `/api/users/avatar` | admin | Cloudinary upload |
| GET/POST | `/api/contacts/` | ✅ | list-search / create |
| GET/PUT/DELETE | `/api/contacts/{id}` | ✅ | own contacts only |
| GET | `/api/contacts/birthdays` | ✅ | upcoming birthdays |

## Project structure

```
main.py                    # app: CORS, rate limiter, routers, lifespan
Dockerfile, docker-compose.yml
src/
  conf/config.py           # pydantic-settings (DB, JWT, redis, mail, cloudinary)
  database/db.py           # async engine + session + get_db
  entity/models.py         # User (+Role), Contact
  schemas/                 # Pydantic
  repository/              # DB layer: contacts.py, users.py
  routes/                  # auth.py, users.py, contacts.py
  services/                # auth.py, cache.py (Redis), email.py, limiter.py
migrations/                # Alembic
tests/                     # pytest unit + integration
docs/                      # Sphinx
```

## Cloud deployment

The app is fully containerized (`docker compose up`), so it can be deployed to
any Docker-capable host (Fly.io, Render, Koyeb, a VPS, etc.). Set the production
`.env` values (Postgres + Redis URLs, real SMTP and Cloudinary credentials) on
the target platform.
