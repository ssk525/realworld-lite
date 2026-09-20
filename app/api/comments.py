"""Comment routes nested under articles."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.article import Article
from app.models.comment import Comment
from app.models.user import User
from app.schemas import CommentCreate, CommentOut

router = APIRouter(prefix="/articles", tags=["comments"])


def _get_article_or_404(db: Session, slug: str) -> Article:
    article = db.query(Article).filter(Article.slug == slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("/{slug}/comments", response_model=list[CommentOut])
def list_comments(slug: str, db: Session = Depends(get_db)) -> list[Comment]:
    article = _get_article_or_404(db, slug)
    return (
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.article_id == article.id)
        .order_by(Comment.created_at.asc())
        .all()
    )


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
    comment = Comment(body=payload.body, article_id=article.id, author_id=current_user.id)
    db.add(comment)
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
