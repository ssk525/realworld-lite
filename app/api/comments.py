"""Comment routes nested under articles, with threaded replies."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.article import Article
from app.models.comment import Comment
from app.models.user import User
from app.schemas import CommentCreate, CommentOut, CommentThreadOut, CommentUpdate, UserOut

router = APIRouter(prefix="/articles", tags=["comments"])


def _get_article_or_404(db: Session, slug: str) -> Article:
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _get_comment_or_404(db: Session, article: Article, comment_id: int) -> Comment:
    comment = (
        db.query(Comment)
        .filter(Comment.id == comment_id, Comment.article_id == article.id)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


def _article_comments(db: Session, article: Article) -> list[Comment]:
    return (
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.article_id == article.id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )


@router.get("/{slug}/comments", response_model=list[CommentOut])
def list_comments(slug: str, db: Session = Depends(get_db)) -> list[Comment]:
    article = _get_article_or_404(db, slug)
    return _article_comments(db, article)


@router.get("/{slug}/comments/thread", response_model=list[CommentThreadOut])
def list_comment_thread(slug: str, db: Session = Depends(get_db)) -> list[CommentThreadOut]:
    """Comments as a tree: top-level comments with their replies nested inside."""
    article = _get_article_or_404(db, slug)
    nodes: dict[int, CommentThreadOut] = {}
    roots: list[CommentThreadOut] = []
    for comment in _article_comments(db, article):
        nodes[comment.id] = CommentThreadOut(
            id=comment.id,
            body=comment.body,
            author=UserOut.model_validate(comment.author),
            parent_id=comment.parent_id,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            replies=[],
        )
    for node in nodes.values():
        parent = nodes.get(node.parent_id) if node.parent_id else None
        if parent is not None:
            parent.replies.append(node)
        else:
            roots.append(node)
    return roots


@router.post(
    "/{slug}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    slug: str,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Comment:
    article = _get_article_or_404(db, slug)
    if payload.parent_id is not None:
        parent = (
            db.query(Comment)
            .filter(Comment.id == payload.parent_id, Comment.article_id == article.id)
            .first()
        )
        if not parent:
            raise HTTPException(status_code=400, detail="Parent comment not found on this article")
    comment = Comment(
        body=payload.body,
        article_id=article.id,
        author_id=current_user.id,
        parent_id=payload.parent_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    db.refresh(comment, attribute_names=["author"])
    return comment


@router.put("/{slug}/comments/{comment_id}", response_model=CommentOut)
def update_comment(
    slug: str,
    comment_id: int,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Comment:
    article = _get_article_or_404(db, slug)
    comment = _get_comment_or_404(db, article, comment_id)
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the comment author")
    comment.body = payload.body
    comment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)
    db.refresh(comment, attribute_names=["author"])
    return comment


@router.delete("/{slug}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    slug: str,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    article = _get_article_or_404(db, slug)
    comment = _get_comment_or_404(db, article, comment_id)
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the comment author")
    db.delete(comment)
    db.commit()
