"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.routes import router
from app.core.config import get_settings
from app.core.database import init_db
from app.schemas import HealthOut

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="RealWorld Lite",
    description="Scoped RealWorld-style backend: JWT auth, articles CRUD, comments, SQL.",
    version=__version__,
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok", service=settings.service_name, version=__version__)
