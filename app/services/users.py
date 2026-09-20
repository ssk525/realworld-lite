"""User domain helpers."""

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).first()


def get_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def email_or_username_taken(db: Session, email: str, username: str) -> bool:
    return (
        db.query(User)
        .filter((User.email == email.lower()) | (User.username == username))
        .first()
        is not None
    )


def create_user(db: Session, *, email: str, username: str, password: str, bio: str = "") -> User:
    user = User(
        email=email.lower(),
        username=username,
        hashed_password=hash_password(password),
        bio=bio or "",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
