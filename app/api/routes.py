"""Auth and article API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.article import Article
from app.models.comment import Comment
from app.models.user import User
from app.schemas import (
    ArticleCreate,
    ArticleOut,
    ArticleUpdate,
    CommentCreate,
    CommentOut,
    TokenOut,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.services.slug import slugify

router = APIRouter()


@router.post("/users", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> TokenOut:
    if db.query(User).filter((User.email == payload.email) | (User.username == payload.username)).first():
        raise HTTPException(status_code=400, detail="Email or username already registered")
    user = User(
        email=payload.email.lower(),
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.email)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/users/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.email)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/user", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/articles", response_model=list[ArticleOut])
def list_articles(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)) -> list[Article]:
    limit = min(max(limit, 1), 100)
    return (
        db.query(Article)
        .options(joinedload(Article.author))
        .order_by(Article.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/articles", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: ArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Article:
    base = slugify(payload.title)
    slug = base
    idx = 1
    while db.query(Article).filter(Article.slug == slug).first():
        idx += 1
        slug = f"{base}-{idx}"
    article = Article(
        slug=slug,
        title=payload.title,
        description=payload.description,
        body=payload.body,
        author_id=current_user.id,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    db.refresh(article, attribute_names=["author"])
    return article


@router.get("/articles/{slug}", response_model=ArticleOut)
def get_article(slug: str, db: Session = Depends(get_db)) -> Article:
    article = (
        db.query(Article).options(joinedload(Article.author)).filter(Article.slug == slug).first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.put("/articles/{slug}", response_model=ArticleOut)
def update_article(
    slug: str,
    payload: ArticleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Article:
    article = (
        db.query(Article).options(joinedload(Article.author)).filter(Article.slug == slug).first()
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the article author")
    if payload.title is not None:
        article.title = payload.title
    if payload.description is not None:
        article.description = payload.description
    if payload.body is not None:
        article.body = payload.body
    db.commit()
    db.refresh(article)
    return article


@router.delete("/articles/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the article author")
    db.delete(article)
    db.commit()


@router.get("/articles/{slug}/comments", response_model=list[CommentOut])
def list_comments(slug: str, db: Session = Depends(get_db)) -> list[Comment]:
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return (
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.article_id == article.id)
        .order_by(Comment.created_at.asc())
        .all()
    )


@router.post(
    "/articles/{slug}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    slug: str,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Comment:
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    comment = Comment(body=payload.body, article_id=article.id, author_id=current_user.id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    db.refresh(comment, attribute_names=["author"])
    return comment


@router.delete("/articles/{slug}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    slug: str,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    comment = (
        db.query(Comment)
        .filter(Comment.id == comment_id, Comment.article_id == article.id)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the comment author")
    db.delete(comment)
    db.commit()
