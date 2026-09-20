"""Aggregate API router."""

from fastapi import APIRouter

from app.api import articles, auth, comments, tags

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(articles.router)
api_router.include_router(comments.router)
api_router.include_router(tags.router)
