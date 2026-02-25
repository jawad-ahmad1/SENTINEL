"""
Global exception handlers — prevents stack-trace leakage to clients.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)


async def _http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "success": False},
    )


async def _integrity_error_handler(_request: Request, exc: IntegrityError) -> JSONResponse:
    logger.error("Database integrity error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=409,
        content={"detail": "Database constraint violation", "success": False},
    )


async def _sqlalchemy_error_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Database error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal database error", "success": False},
    )


async def _generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "success": False},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI app."""
    app.add_exception_handler(HTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, _integrity_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SQLAlchemyError, _sqlalchemy_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _generic_exception_handler)
