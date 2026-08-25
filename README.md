# RealWorld Lite

> Scoped RealWorld-style backend: **JWT auth, article CRUD, comments, SQLAlchemy, Pytest, Docker Compose (PostgreSQL)**.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

**GitHub** · **[Architecture](#architecture)** · **[REST API](#rest-api)**

---

## What This Is

A clean **product backend** for campus / SDE screens — not a full RealWorld multi-stack clone:

- User register / login with JWT (Bearer)
- Articles: create, list, get, update, delete (author-owned)
- Comments nested under articles (author-owned delete)
- SQLAlchemy models + PostgreSQL in Docker (SQLite for local/tests)
- Ownership checks (403 when another user mutates your resource)
- Automated Pytest coverage for auth + CRUD flows

---

## Architecture

```
Client ──JSON/JWT──▶ FastAPI (/api)
                         │
                         ├─ Auth (register / login /me)
                         ├─ Articles CRUD
                         └─ Comments CRUD
                         │
                         ▼
                   SQLAlchemy ORM
                         │
              ┌──────────┴──────────┐
              │ SQLite (dev/tests)  │
              │ PostgreSQL (Docker) │
              └─────────────────────┘
```

| Layer | Tech | Responsibility |
|-------|------|----------------|
| API | FastAPI | Routes, validation, OpenAPI |
| Auth | JWT + bcrypt | Register, login, protected routes |
| Domain | SQLAlchemy models | User, Article, Comment |
| Persist | SQLite / PostgreSQL | Local vs Compose |
| Quality | Pytest | Auth, ownership, CRUD |

---

## Quick Start

### Local (SQLite)

```bash
git clone https://github.com/ssk525/realworld-lite.git
cd realworld-lite
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run_api.py
```

Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Docker (PostgreSQL)

```bash
docker compose up --build
```

---

## REST API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | no | Liveness |
| POST | `/api/users` | no | Register → token |
| POST | `/api/users/login` | no | Login → token |
| GET | `/api/user` | yes | Current user |
| GET | `/api/articles` | no | List articles |
| POST | `/api/articles` | yes | Create article |
| GET | `/api/articles/{slug}` | no | Get article |
| PUT | `/api/articles/{slug}` | yes (author) | Update |
| DELETE | `/api/articles/{slug}` | yes (author) | Delete |
| GET | `/api/articles/{slug}/comments` | no | List comments |
| POST | `/api/articles/{slug}/comments` | yes | Add comment |
| DELETE | `/api/articles/{slug}/comments/{id}` | yes (author) | Delete comment |

### Example flow

```bash
# register
curl -s -X POST http://127.0.0.1:8000/api/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","username":"you","password":"secret12"}'

# create article (paste token)
curl -s -X POST http://127.0.0.1:8000/api/articles \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"First Post","description":"demo","body":"hello backend"}'
```

---

## Tests

```bash
pytest -q
```

---

## Layout

```
app/main.py           FastAPI app + lifespan DB init
app/api/routes.py     Auth, articles, comments
app/models/           User, Article, Comment
app/schemas.py        Pydantic request/response models
app/core/             config, database, security, deps
app/services/slug.py  Title → unique slug
tests/                Auth + CRUD + ownership tests
Dockerfile / compose  PostgreSQL deploy
```

---

## License

MIT — see [LICENSE](LICENSE).
