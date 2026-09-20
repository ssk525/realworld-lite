"""Article CRUD, search, favorites."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models.article import Article
from app.models.user import User
from app.schemas import ArticleCreate, ArticleListOut, ArticleOut, ArticleUpdate
from app.services import articles as article_service

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=ArticleListOut)
def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    author: str | None = None,
    tag: str | None = None,
    favorited: str | None = Query(default=None, description="Username whose favorites to list"),
    q: str | None = Query(default=None, description="Search title/description/body"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> ArticleListOut:
    items, meta = article_service.list_articles(
        db,
        page=page,
        page_size=page_size,
        author=author,
        tag=tag,
        favorited_by=favorited,
        q=q,
    )
    return ArticleListOut(
        items=[article_service.serialize_article(a, current_user) for a in items],
        meta=meta,
    )


@router.post("", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: ArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArticleOut:
    article = Article(
        slug=article_service.unique_slug(db, payload.title),
        title=payload.title,
        description=payload.description,
        body=payload.body,
        author_id=current_user.id,
    )
    article.tags = article_service.get_or_create_tags(db, payload.tag_list)
    db.add(article)
    db.commit()
    article = article_service.get_article_by_slug(db, article.slug)
    assert article is not None
    return article_service.serialize_article(article, current_user)


@router.get("/{slug}", response_model=ArticleOut)
def get_article(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> ArticleOut:
    article = article_service.get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article_service.serialize_article(article, current_user)


@router.put("/{slug}", response_model=ArticleOut)
def update_article(
    slug: str,
    payload: ArticleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArticleOut:
    article = article_service.get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the article author")
    if payload.title is not None:
        article.title = payload.title
        article.slug = article_service.unique_slug(db, payload.title, exclude_id=article.id)
    if payload.description is not None:
        article.description = payload.description
    if payload.body is not None:
        article.body = payload.body
    if payload.tag_list is not None:
        article.tags = article_service.get_or_create_tags(db, payload.tag_list)
    db.commit()
    article = article_service.get_article_by_slug(db, article.slug)
    assert article is not None
    return article_service.serialize_article(article, current_user)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    article = article_service.get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the article author")
    db.delete(article)
    db.commit()


@router.post("/{slug}/favorite", response_model=ArticleOut)
def favorite_article(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArticleOut:
    article = article_service.get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if current_user not in article.favorited_by:
        article.favorited_by.append(current_user)
        db.commit()
        article = article_service.get_article_by_slug(db, slug)
        assert article is not None
    return article_service.serialize_article(article, current_user)


@router.delete("/{slug}/favorite", response_model=ArticleOut)
def unfavorite_article(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArticleOut:
    article = article_service.get_article_by_slug(db, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if current_user in article.favorited_by:
        article.favorited_by.remove(current_user)
        db.commit()
        article = article_service.get_article_by_slug(db, slug)
        assert article is not None
    return article_service.serialize_article(article, current_user)
