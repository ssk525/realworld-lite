"""Tag listing."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tag import Tag
from app.schemas import TagListOut

router = APIRouter(tags=["tags"])


@router.get("/tags", response_model=TagListOut)
def list_tags(db: Session = Depends(get_db)) -> TagListOut:
    rows = db.query(Tag).order_by(Tag.name.asc()).all()
    return TagListOut(tags=[t.name for t in rows])
