"""TentService - FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
from fastapi.middleware.cors import CORSMiddleware

from api.endpoints import api_router
from db.setup import init_db
from utils.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    await init_db()
    yield
    # Shutdown: close connections, cleanup


app = FastAPI(
    title=get_settings().app_name,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    """Root health check."""
    return {"status": "ok", "service": "TentService"}
