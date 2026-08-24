"""API tests for auth, articles, and comments."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force sqlite before app imports settings cache
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret"

from app.core.database import Base, get_db  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _auth_header(client: TestClient, email: str = "a@example.com", username: str = "alice") -> dict:
    resp = client.post(
        "/api/users",
        json={"email": email, "username": username, "password": "secret12"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "realworld-lite"


def test_register_login_me(client: TestClient) -> None:
    headers = _auth_header(client)
    me = client.get("/api/user", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "alice"

    login = client.post("/api/users/login", json={"email": "a@example.com", "password": "secret12"})
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_duplicate_register(client: TestClient) -> None:
    _auth_header(client)
    again = client.post(
        "/api/users",
        json={"email": "a@example.com", "username": "alice", "password": "secret12"},
    )
    assert again.status_code == 400


def test_article_crud_and_ownership(client: TestClient) -> None:
    alice = _auth_header(client, "a@example.com", "alice")
    bob = _auth_header(client, "b@example.com", "bob")

    created = client.post(
        "/api/articles",
        headers=alice,
        json={"title": "Hello World", "description": "desc", "body": "body text"},
    )
    assert created.status_code == 201
    slug = created.json()["slug"]
    assert slug.startswith("hello-world")

    listed = client.get("/api/articles")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    forbidden = client.put(
        f"/api/articles/{slug}",
        headers=bob,
        json={"title": "Hack"},
    )
    assert forbidden.status_code == 403

    updated = client.put(
        f"/api/articles/{slug}",
        headers=alice,
        json={"title": "Hello Again", "body": "updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Hello Again"

    deleted = client.delete(f"/api/articles/{slug}", headers=alice)
    assert deleted.status_code == 204
    assert client.get(f"/api/articles/{slug}").status_code == 404


def test_comments(client: TestClient) -> None:
    alice = _auth_header(client, "a@example.com", "alice")
    bob = _auth_header(client, "b@example.com", "bob")
    article = client.post(
        "/api/articles",
        headers=alice,
        json={"title": "Post", "description": "", "body": "x"},
    ).json()
    slug = article["slug"]

    comment = client.post(
        f"/api/articles/{slug}/comments",
        headers=bob,
        json={"body": "Nice post"},
    )
    assert comment.status_code == 201
    cid = comment.json()["id"]

    comments = client.get(f"/api/articles/{slug}/comments")
    assert comments.status_code == 200
    assert len(comments.json()) == 1

    deny = client.delete(f"/api/articles/{slug}/comments/{cid}", headers=alice)
    assert deny.status_code == 403

    ok = client.delete(f"/api/articles/{slug}/comments/{cid}", headers=bob)
    assert ok.status_code == 204


def test_unauthenticated_create(client: TestClient) -> None:
    resp = client.post("/api/articles", json={"title": "No Auth", "body": "x"})
    assert resp.status_code == 401
