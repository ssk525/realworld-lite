"""API tests: auth, articles, comments, tags, favorites, pagination."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["RATE_LIMIT"] = "1000/minute"
os.environ["AUTH_RATE_LIMIT"] = "5/minute"
os.environ["AUTO_CREATE_TABLES"] = "true"

from datetime import datetime, timedelta, timezone  # noqa: E402

from jose import jwt  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402

get_settings.cache_clear()

from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402

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
    limiter.reset()

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


def _auth_header(
    client: TestClient,
    email: str = "a@example.com",
    username: str = "alice",
) -> dict:
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
    body = resp.json()
    assert body["service"] == "realworld-lite"
    assert body["version"] == "2.1.0"
    assert "X-Request-ID" in resp.headers


def test_register_login_me_update(client: TestClient) -> None:
    headers = _auth_header(client)
    me = client.get("/api/user", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "alice"

    login = client.post(
        "/api/users/login",
        json={"email": "a@example.com", "password": "secret12"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]

    updated = client.put("/api/user", headers=headers, json={"bio": "backend eng"})
    assert updated.status_code == 200
    assert updated.json()["bio"] == "backend eng"

    profile = client.get("/api/profiles/alice")
    assert profile.status_code == 200
    assert profile.json()["bio"] == "backend eng"


def test_duplicate_register(client: TestClient) -> None:
    _auth_header(client)
    again = client.post(
        "/api/users",
        json={"email": "a@example.com", "username": "alice", "password": "secret12"},
    )
    assert again.status_code == 400


def test_article_crud_ownership_and_tags(client: TestClient) -> None:
    alice = _auth_header(client, "a@example.com", "alice")
    bob = _auth_header(client, "b@example.com", "bob")

    created = client.post(
        "/api/articles",
        headers=alice,
        json={
            "title": "Hello World",
            "description": "desc",
            "body": "body text",
            "tag_list": ["Python", "fastapi", "python"],
        },
    )
    assert created.status_code == 201, created.text
    data = created.json()
    slug = data["slug"]
    assert slug.startswith("hello-world")
    assert data["tag_list"] == ["fastapi", "python"]

    listed = client.get("/api/articles")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["meta"]["total"] == 1
    assert len(payload["items"]) == 1

    by_tag = client.get("/api/articles", params={"tag": "python"})
    assert by_tag.json()["meta"]["total"] == 1

    by_author = client.get("/api/articles", params={"author": "alice"})
    assert by_author.json()["meta"]["total"] == 1

    search = client.get("/api/articles", params={"q": "body"})
    assert search.json()["meta"]["total"] == 1

    tags = client.get("/api/tags")
    assert tags.status_code == 200
    assert "python" in tags.json()["tags"]

    forbidden = client.put(
        f"/api/articles/{slug}",
        headers=bob,
        json={"title": "Hack"},
    )
    assert forbidden.status_code == 403

    updated = client.put(
        f"/api/articles/{slug}",
        headers=alice,
        json={"title": "Hello Again", "body": "updated", "tag_list": ["sql"]},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Hello Again"
    assert updated.json()["tag_list"] == ["sql"]
    new_slug = updated.json()["slug"]

    deleted = client.delete(f"/api/articles/{new_slug}", headers=alice)
    assert deleted.status_code == 204
    assert client.get(f"/api/articles/{new_slug}").status_code == 404


def test_favorites_and_pagination(client: TestClient) -> None:
    alice = _auth_header(client, "a@example.com", "alice")
    bob = _auth_header(client, "b@example.com", "bob")

    for i in range(3):
        resp = client.post(
            "/api/articles",
            headers=alice,
            json={"title": f"Post {i}", "description": "", "body": f"content {i}", "tag_list": []},
        )
        assert resp.status_code == 201

    page1 = client.get("/api/articles", params={"page": 1, "page_size": 2})
    assert page1.status_code == 200
    assert page1.json()["meta"]["total"] == 3
    assert page1.json()["meta"]["page_size"] == 2
    assert len(page1.json()["items"]) == 2

    slug = page1.json()["items"][0]["slug"]
    fav = client.post(f"/api/articles/{slug}/favorite", headers=bob)
    assert fav.status_code == 200
    assert fav.json()["favorites_count"] == 1
    assert fav.json()["favorited"] is True

    bob_favs = client.get("/api/articles", params={"favorited": "bob"})
    assert bob_favs.json()["meta"]["total"] == 1

    unfav = client.delete(f"/api/articles/{slug}/favorite", headers=bob)
    assert unfav.status_code == 200
    assert unfav.json()["favorites_count"] == 0


def test_comments(client: TestClient) -> None:
    alice = _auth_header(client, "a@example.com", "alice")
    bob = _auth_header(client, "b@example.com", "bob")
    article = client.post(
        "/api/articles",
        headers=alice,
        json={"title": "Post", "description": "", "body": "x", "tag_list": []},
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


def _article(client: TestClient, headers: dict, title: str = "Post") -> str:
    resp = client.post(
        "/api/articles",
        headers=headers,
        json={"title": title, "description": "", "body": "x", "tag_list": []},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["slug"]


def test_comment_update_is_author_only(client: TestClient) -> None:
    alice = _auth_header(client, "a@example.com", "alice")
    bob = _auth_header(client, "b@example.com", "bob")
    slug = _article(client, alice)
    cid = client.post(
        f"/api/articles/{slug}/comments", headers=bob, json={"body": "first"}
    ).json()["id"]

    deny = client.put(f"/api/articles/{slug}/comments/{cid}", headers=alice, json={"body": "hacked"})
    assert deny.status_code == 403

    ok = client.put(f"/api/articles/{slug}/comments/{cid}", headers=bob, json={"body": "edited"})
    assert ok.status_code == 200
    assert ok.json()["body"] == "edited"
    assert ok.json()["updated_at"] is not None

    missing = client.put(f"/api/articles/{slug}/comments/9999", headers=bob, json={"body": "x"})
    assert missing.status_code == 404


def test_nested_replies_thread_and_cascade(client: TestClient) -> None:
    alice = _auth_header(client, "a@example.com", "alice")
    bob = _auth_header(client, "b@example.com", "bob")
    slug = _article(client, alice)
    root = client.post(
        f"/api/articles/{slug}/comments", headers=bob, json={"body": "root"}
    ).json()["id"]
    reply = client.post(
        f"/api/articles/{slug}/comments",
        headers=alice,
        json={"body": "reply", "parent_id": root},
    )
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == root
    reply_id = reply.json()["id"]
    client.post(
        f"/api/articles/{slug}/comments",
        headers=bob,
        json={"body": "reply to reply", "parent_id": reply_id},
    )

    thread = client.get(f"/api/articles/{slug}/comments/thread").json()
    assert len(thread) == 1
    assert thread[0]["body"] == "root"
    assert thread[0]["replies"][0]["body"] == "reply"
    assert thread[0]["replies"][0]["replies"][0]["body"] == "reply to reply"

    other_slug = _article(client, alice, "Other")
    cross = client.post(
        f"/api/articles/{other_slug}/comments",
        headers=alice,
        json={"body": "wrong article", "parent_id": root},
    )
    assert cross.status_code == 400

    assert client.delete(f"/api/articles/{slug}/comments/{root}", headers=bob).status_code == 204
    assert client.get(f"/api/articles/{slug}/comments").json() == []


def test_login_rate_limit_returns_429(client: TestClient) -> None:
    _auth_header(client)
    body = {"email": "a@example.com", "password": "wrong-password"}
    codes = [client.post("/api/users/login", json=body).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429


def test_expired_token_is_rejected(client: TestClient) -> None:
    _auth_header(client)
    settings = get_settings()
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = jwt.encode(
        {"sub": "a@example.com", "exp": past, "iat": past - timedelta(minutes=60)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    resp = client.get("/api/user", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_expires_after_configured_minutes(client: TestClient) -> None:
    headers = _auth_header(client)
    token = headers["Authorization"].split()[1]
    claims = jwt.get_unverified_claims(token)
    assert claims["exp"] - claims["iat"] == get_settings().access_token_expire_minutes * 60


def test_unauthenticated_create(client: TestClient) -> None:
    resp = client.post("/api/articles", json={"title": "No Auth", "body": "x"})
    assert resp.status_code == 401


def test_invalid_login(client: TestClient) -> None:
    _auth_header(client)
    bad = client.post(
        "/api/users/login",
        json={"email": "a@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401
