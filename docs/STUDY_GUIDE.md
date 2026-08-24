# Study guide — RealWorld Lite

## One-minute pitch

"I built a scoped product backend the way campus SDE screens expect: users with JWT, articles with full CRUD, comments, SQL models, ownership checks, tests, and Docker Postgres. It’s RealWorld-inspired, but cut to what I can defend in an interview."

## Why this project

| Question | Answer |
|----------|--------|
| Why JWT? | Stateless auth for REST; Bearer header; expiry in token claims |
| Why SQLAlchemy 2? | Typed mapped columns, relationships, portable SQLite/Postgres |
| How is ownership enforced? | Compare `author_id` to `current_user.id` → 403 |
| Why slug? | Stable public URL key; unique constraint; collision suffix |
| SQLite vs Postgres? | SQLite for tests/local; Compose Postgres for deploy realism |

## Entity model

```
User 1──* Article 1──* Comment
  │                     │
  └─────────────────────┘ (Comment.author)
```

## Live demo script

```bash
pytest -q
python run_api.py
# then hit /docs — register → create article → comment → delete as wrong user (403)
```
