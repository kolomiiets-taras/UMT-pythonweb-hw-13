# Contacts REST API (with Auth)

REST API for storing and managing contacts, with JWT authentication, email
verification, per-user data isolation, rate limiting, CORS, and Cloudinary
avatar uploads. Built with **FastAPI**, **async SQLAlchemy 2.0**, **PostgreSQL**.

## Features

### Contacts (per authenticated user)
- Full CRUD (create / list / get / update / delete) — scoped to the current user
- Search by first name, last name, or email (query params)
- Birthdays in the next N days (default 7)

### Auth & users
- **Signup** (`POST /api/auth/signup`) — hashes password (bcrypt), returns `201` + user;
  duplicate email → `409 Conflict`
- **Login** (`POST /api/auth/login`) — OAuth2 password form (`username`=email, `password`);
  wrong credentials or unconfirmed email → `401`; returns JWT `access_token`
- **Email verification** — signup sends a tokenized confirmation link
  (`GET /api/auth/confirmed_email/{token}`); resend via `POST /api/auth/request_email`
- **`/api/users/me`** — current user, **rate limited** (10 req/min)
- **`/api/users/avatar`** — upload avatar to **Cloudinary** (`PATCH`)
- **CORS** enabled for all origins

JWT authorization protects all contact routes — only registered, confirmed users
can access contacts, and each user sees only their own.

## Models

**User**: `id`, `username`, `email` (unique), `password` (hashed), `avatar`,
`confirmed`, `created_at`.

**Contact**: `id`, `first_name`, `last_name`, `email`, `phone`, `birthday` (date),
`additional_data` (optional), `user_id` (FK → users).

## Setup (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in real JWT/SMTP/Cloudinary secrets

docker compose up -d postgres # start DB only
alembic upgrade head          # apply migrations
uvicorn main:app --reload
```

Swagger: http://localhost:8000/docs

## Run everything in Docker

```bash
cp .env.example .env          # adjust secrets
docker compose up -d --build  # starts postgres + api (runs migrations on boot)
```

API at http://localhost:8000 (the `api` service overrides `DB_URL` to reach the
`postgres` service by name). Migrations run automatically on container start.

## Environment variables (`.env`)

| Var | Purpose |
|-----|---------|
| `DB_URL` | async SQLAlchemy Postgres URL |
| `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT config |
| `EMAIL_TOKEN_EXPIRE_HOURS` | email-verification token lifetime |
| `MAIL_*` | SMTP config for fastapi-mail |
| `CLD_NAME`, `CLD_API_KEY`, `CLD_API_SECRET` | Cloudinary credentials |

No secrets are hardcoded — all read from environment.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/signup` | – | Register (201, 409 on dup) |
| POST | `/api/auth/login` | – | Get access_token (401 on fail) |
| GET | `/api/auth/confirmed_email/{token}` | – | Confirm email |
| POST | `/api/auth/request_email` | – | Resend confirmation |
| GET | `/api/users/me` | ✅ | Current user (rate limited) |
| PATCH | `/api/users/avatar` | ✅ | Upload avatar (Cloudinary) |
| GET | `/api/contacts/` | ✅ | List/search own contacts |
| POST | `/api/contacts/` | ✅ | Create contact (201) |
| GET | `/api/contacts/{id}` | ✅ | Get own contact |
| PUT | `/api/contacts/{id}` | ✅ | Update own contact |
| DELETE | `/api/contacts/{id}` | ✅ | Delete own contact |
| GET | `/api/contacts/birthdays` | ✅ | Upcoming birthdays |

## Project structure

```
main.py                    # FastAPI app: CORS, rate limiter, routers, lifespan
Dockerfile                 # api image (migrate + uvicorn)
docker-compose.yml         # postgres + api
src/
  conf/config.py           # pydantic-settings (DB, JWT, mail, cloudinary)
  database/db.py           # async engine + session + get_db
  entity/models.py         # User, Contact
  schemas/                 # Pydantic: contacts.py, users.py
  repository/              # DB layer: contacts.py, users.py
  routes/                  # auth.py, users.py, contacts.py
  services/
    auth.py                # hashing, JWT, get_current_user
    email.py               # fastapi-mail verification
    limiter.py             # slowapi limiter
    templates/             # verify_email.html
migrations/                # Alembic
```
