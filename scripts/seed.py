#!/usr/bin/env python3
"""Seed demo users + articles for local demos and interview walkthroughs."""

from __future__ import annotations

from app.core.database import SessionLocal, init_db
from app.models.article import Article
from app.models.user import User
from app.services import articles as article_service
from app.services import users as user_service


SEED_USERS = [
    {"email": "alice@example.com", "username": "alice", "password": "secret12", "bio": "Backend engineer"},
    {"email": "bob@example.com", "username": "bob", "password": "secret12", "bio": "Product reader"},
]

SEED_ARTICLES = [
    {
        "author": "alice",
        "title": "Why ownership checks belong in the API",
        "description": "403 beats hope",
        "body": "Never trust the client for authorization. Verify author_id on mutate paths.",
        "tag_list": ["security", "fastapi"],
    },
    {
        "author": "alice",
        "title": "Pagination without surprise costs",
        "description": "meta + items",
        "body": "Return total/page/page_size so clients can build UX without N+1 round trips.",
        "tag_list": ["sqlalchemy", "api-design"],
    },
    {
        "author": "bob",
        "title": "Notes from reading RealWorld specs",
        "description": "scoped clone",
        "body": "Ship the subset that proves auth, CRUD, and relational modeling.",
        "tag_list": ["learning"],
    },
]


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        users: dict[str, User] = {}
        for row in SEED_USERS:
            existing = user_service.get_by_username(db, row["username"])
            if existing:
                users[row["username"]] = existing
                continue
            users[row["username"]] = user_service.create_user(
                db,
                email=row["email"],
                username=row["username"],
                password=row["password"],
                bio=row["bio"],
            )

        for row in SEED_ARTICLES:
            author = users[row["author"]]
            exists = (
                db.query(Article)
                .filter(Article.title == row["title"], Article.author_id == author.id)
                .first()
            )
            if exists:
                continue
            article = Article(
                slug=article_service.unique_slug(db, row["title"]),
                title=row["title"],
                description=row["description"],
                body=row["body"],
                author_id=author.id,
            )
            article.tags = article_service.get_or_create_tags(db, row["tag_list"])
            db.add(article)
        db.commit()
        print("Seed complete: alice/bob (password: secret12) + sample articles.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
