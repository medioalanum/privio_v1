"""Routers package initialization."""

from app.routers.commitments import router as commitments_router
from app.routers.deposits import router as deposits_router
from app.routers.web import router as web_router

__all__ = ["commitments_router", "deposits_router", "web_router"]
