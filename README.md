# RealWorld Lite

Scoped **RealWorld-style publishing API** — JWT auth, ownership-checked CRUD, tags, favorites, pagination/search, rate limits, Alembic migrations, and CI.

Built as a resume-ready backend for software engineering interviews: clear layers, explicit authorization, and production habits without shipping an entire multi-frontend clone.

[![CI](https://github.com/ssk525/realworld-lite/actions/workflows/ci.yml/badge.svg)](https://github.com/ssk525/realworld-lite/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

**Repo:** https://github.com/ssk525/realworld-lite

---

## Why this project exists

Full RealWorld demos try to cover every client stack. Recruiters screening for **backend / full-stack SWE** care more about whether you can:

1. Model relational data and migrate it safely
2. Authenticate users and **authorize** mutations (403, not “hope”)
3. Expose a predictable REST surface (pagination, filters, OpenAPI)
4. Ship with tests, Docker, and CI

This repo is that subset — intentionally scoped, interview-explainable end to end.

---

## Features

| Area | What shipped |
|------|----------------|
| Auth | Register / login / JWT Bearer / profile update |
| Articles | Create, read, update, delete with **author ownership** |
| Tags | Many-to-many tags, filter feed by tag |
| Favorites | Favorite / unfavorite; filter by who favorited |
| Comments | Create, read, update, delete; threaded replies via `parent_id`; author-only edit/delete |
| Query API | `page`, `page_size`, `author`, `tag`, `favorited`, `q` |
| Hardening | Rate limit (SlowAPI, stricter on login), request IDs, bcrypt + JWT expiry |
| Data | SQLAlchemy 2.x models, **Alembic** migrations |
| Ops | Pytest, GitHub Actions CI (Python 3.11/3.12, PostgreSQL 16, Docker), Docker Compose + Postgres |

---

## Architecture

```
Client ── JSON + JWT ──▶ FastAPI (/api)
                           │
           ┌───────────────┼───────────────┐
           │               │               │
        Auth API      Articles API    Comments/Tags
           │               │               │
           └─────── services/ (domain) ────┘
                           │
                    SQLAlchemy ORM
                           │
              ┌────────────┴────────────┐
              │ SQLite (dev / tests)    │
              │ PostgreSQL (Compose)    │
              └────────────┬────────────┘
                           │
                     Alembic migrations
```

**Request path:** router → dependency (auth/db) → service helper → model → DB.  
**Mutations:** load resource → compare `author_id` to `current_user.id` → 403 or proceed.

---

## Quick start

### Local (SQLite)

```bash
git clone https://github.com/ssk525/realworld-lite.git
cd realworld-lite
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run_api.py
# optional demo data
python -m scripts.seed
```

- OpenAPI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

### Docker (PostgreSQL)

```bash
docker compose up --build
```

API runs migrations on boot, then serves on port `8000`.

---

## REST API

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/health` | — | Liveness + version |
| POST | `/api/users` | — | Register → token |
| POST | `/api/users/login` | — | Login → token |
| GET / PUT | `/api/user` | JWT | Current user |
| GET | `/api/profiles/{username}` | — | Public profile |
| GET | `/api/articles` | optional | Paginated list + filters |
| POST | `/api/articles` | JWT | Create (`tag_list` optional) |
| GET / PUT / DELETE | `/api/articles/{slug}` | JWT on mutate | Author-only mutate |
| POST / DELETE | `/api/articles/{slug}/favorite` | JWT | Favorite toggle |
| GET / POST | `/api/articles/{slug}/comments` | JWT on POST | Flat list; POST takes optional `parent_id` to reply |
| GET | `/api/articles/{slug}/comments/thread` | — | Comments as a reply tree |
| PUT / DELETE | `/api/articles/{slug}/comments/{id}` | JWT | Comment author only; deleting a comment removes its replies |
| GET | `/api/tags` | — | All tag names |

### List query params

`page`, `page_size` (max 100), `author`, `tag`, `favorited` (username), `q` (title/description/body).

Response shape:

```json
{
  "items": [ /* ArticleOut */ ],
  "meta": { "total": 3, "page": 1, "page_size": 20, "pages": 1 }
}
```

### Example

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","username":"you","password":"secret12"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://127.0.0.1:8000/api/articles \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"First Post","description":"demo","body":"hello","tag_list":["fastapi","sql"]}'
```

---

## Tests & quality

```bash
pytest -q
# or
make test
```

Pytest covers register/login, ownership (403), tags, favorites, pagination, comment edit and threaded replies, the login rate limit (429), and token expiry (401).

CI has three jobs:

1. **test** — Pytest on Python 3.11 and 3.12, then Alembic upgrade on SQLite.
2. **postgres** — Alembic upgrade, downgrade, upgrade on a PostgreSQL 16 service, then a smoke test (register, create article, filter by tag) against it.
3. **docker** — builds the image and runs `docker compose up` until `/health` answers.

---

## Project layout

```
app/
  api/           auth, articles, comments, tags routers
  core/          config, db, security, deps, middleware, logging
  models/        User, Article, Comment, Tag + association tables
  services/      slug, users, articles (domain logic)
  schemas.py     Pydantic contracts
  main.py        App factory, CORS, rate limit, lifespan
alembic/         Schema migrations
scripts/seed.py  Demo users + articles
tests/           Auth, ownership, tags, favorites, pagination
.github/workflows/ci.yml
```

---

## Design decisions (interview talking points)

1. **Ownership in the API layer** — JWT proves identity; comparing `author_id` proves permission. Missing that check is how “authenticated” apps still leak writes.
2. **Services over fat routes** — Slug uniqueness, tag normalization, and serialization live in `services/` so routers stay thin and testable.
3. **Pagination envelope** — Clients need `total`/`pages`, not a bare array, once feeds grow.
4. **Alembic even with `create_all`** — Local DX stays fast; Compose/CI prove migration-first deploys.
5. **Scoped RealWorld** — Enough product surface to discuss tradeoffs; not a kitchen-sink clone.

### Resume one-liner

Built a FastAPI publishing API with JWT auth, author-owned article and comment CRUD, threaded replies, tags/favorites, pagination & search, Alembic migrations, Pytest, rate limits, GitHub Actions CI, and Dockerized PostgreSQL.

---

## License

MIT — see [LICENSE](LICENSE).
