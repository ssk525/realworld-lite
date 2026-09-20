"""Article domain helpers: slug uniqueness, tags, serialization."""

from __future__ import annotations

import math

from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased, joinedload

from app.models.article import Article
from app.models.tag import Tag
from app.models.user import User
from app.schemas import ArticleOut, PageMeta, UserOut
from app.services.slug import slugify


def normalize_tags(raw: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        name = item.strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name[:50])
        if len(out) >= 10:
            break
    return out


def get_or_create_tags(db: Session, names: list[str]) -> list[Tag]:
    tags: list[Tag] = []
    for name in normalize_tags(names):
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def unique_slug(db: Session, title: str, exclude_id: int | None = None) -> str:
    base = slugify(title)
    slug = base
    idx = 1
    while True:
        query = db.query(Article).filter(Article.slug == slug)
        if exclude_id is not None:
            query = query.filter(Article.id != exclude_id)
        if not query.first():
            return slug
        idx += 1
        slug = f"{base}-{idx}"


def serialize_article(article: Article, current_user: User | None = None) -> ArticleOut:
    favorited = False
    if current_user is not None:
        favorited = any(u.id == current_user.id for u in article.favorited_by)
    return ArticleOut(
        id=article.id,
        slug=article.slug,
        title=article.title,
        description=article.description,
        body=article.body,
        tag_list=sorted(t.name for t in article.tags),
        favorites_count=len(article.favorited_by),
        favorited=favorited,
        author=UserOut.model_validate(article.author),
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def article_query(db: Session):
    return db.query(Article).options(
        joinedload(Article.author),
        joinedload(Article.tags),
        joinedload(Article.favorited_by),
    )


def list_articles(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    author: str | None = None,
    tag: str | None = None,
    favorited_by: str | None = None,
    q: str | None = None,
) -> tuple[list[Article], PageMeta]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    author_user = aliased(User)
    fav_user = aliased(User)
    query = db.query(Article.id).select_from(Article)

    if author:
        query = query.join(author_user, Article.author).filter(author_user.username == author)
    if tag:
        query = query.join(Article.tags).filter(Tag.name == tag.lower())
    if favorited_by:
        query = query.join(fav_user, Article.favorited_by).filter(fav_user.username == favorited_by)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Article.title.ilike(like),
                Article.description.ilike(like),
                Article.body.ilike(like),
            )
        )

    query = query.distinct()
    total = query.count()
    pages = max(1, math.ceil(total / page_size)) if total else 0
    offset = (page - 1) * page_size

    id_rows = (
        query.order_by(Article.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    ids = [row[0] for row in id_rows]
    if not ids:
        return [], PageMeta(total=total, page=page, page_size=page_size, pages=pages)

    articles = article_query(db).filter(Article.id.in_(ids)).all()
    by_id = {a.id: a for a in articles}
    ordered = [by_id[i] for i in ids if i in by_id]
    return ordered, PageMeta(total=total, page=page, page_size=page_size, pages=pages)


def get_article_by_slug(db: Session, slug: str) -> Article | None:
    return article_query(db).filter(Article.slug == slug).first()
