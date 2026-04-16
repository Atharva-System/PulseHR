"""FastAPI middleware — request logging and CORS."""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from utils.logger import get_logger

logger = get_logger(__name__)


def add_middleware(app: FastAPI) -> None:
    """Attach all middleware to the FastAPI application."""

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Request logging ---
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} "
            f"({duration_ms:.1f}ms)"
        )
        return response
