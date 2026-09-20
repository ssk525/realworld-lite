"""Auth routes: register, login, profile."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.schemas import TokenOut, UserCreate, UserLogin, UserOut, UserUpdate
from app.services import users as user_service

router = APIRouter(tags=["auth"])


@router.post("/users", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> TokenOut:
    if user_service.email_or_username_taken(db, payload.email, payload.username):
        raise HTTPException(status_code=400, detail="Email or username already registered")
    user = user_service.create_user(
        db,
        email=payload.email,
        username=payload.username,
        password=payload.password,
        bio=payload.bio,
    )
    token = create_access_token(user.email)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/users/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    user = user_service.authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.email)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/user", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.put("/user", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    if payload.bio is not None:
        current_user.bio = payload.bio
    if payload.password is not None:
        current_user.hashed_password = hash_password(payload.password)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/profiles/{username}", response_model=UserOut)
def get_profile(username: str, db: Session = Depends(get_db)) -> User:
    user = user_service.get_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
