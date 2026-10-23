"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class HealthOut(BaseModel):
    status: str
    service: str
    version: str


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=72)
    bio: str = Field(default="", max_length=500)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserUpdate(BaseModel):
    bio: str | None = Field(default=None, max_length=500)
    password: str | None = Field(default=None, min_length=6, max_length=72)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    bio: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ArticleCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=500)
    body: str = Field(min_length=1)
    tag_list: list[str] = Field(default_factory=list, max_length=10)


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    body: str | None = None
    tag_list: list[str] | None = Field(default=None, max_length=10)


class ArticleOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    body: str
    tag_list: list[str] = Field(default_factory=list)
    favorites_count: int = 0
    favorited: bool = False
    author: UserOut
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ArticleListOut(BaseModel):
    items: list[ArticleOut]
    meta: PageMeta


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    parent_id: int | None = None


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentOut(BaseModel):
    id: int
    body: str
    author: UserOut
    parent_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CommentThreadOut(CommentOut):
    replies: list["CommentThreadOut"] = []


class TagListOut(BaseModel):
    tags: list[str]
