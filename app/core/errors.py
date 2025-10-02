from __future__ import annotations
from typing import Any, Dict, Optional
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError

from app.schemas.common import ErrorResponse

log = logging.getLogger("errors")


def _json_error(
    status_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": ErrorResponse(code=code, message=message, details=details).model_dump()},
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        code_map = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            422: "unprocessable_entity",
        }
        code = code_map.get(exc.status_code, "http_error")
        msg = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return _json_error(exc.status_code, code, msg)

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(request: Request, exc: RequestValidationError):
        return _json_error(
            422, "validation_error", "The request is invalid.", {"errors": exc.errors()}
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_exc(request: Request, exc: IntegrityError):
        sqlstate = getattr(exc.orig, "sqlstate", None) if hasattr(exc, "orig") else None
        code = (
            "duplicate"
            if (sqlstate == "23505" or "unique" in str(exc.orig).lower())
            else "conflict"
        )
        msg = (
            "Duplicate key violates unique constraint."
            if code == "duplicate"
            else "Integrity constraint violated."
        )
        log.info("IntegrityError: %s", exc)
        return _json_error(409, code, msg, {"sqlstate": sqlstate})

    @app.exception_handler(Exception)
    async def _unhandled_exc(request: Request, exc: Exception):
        log.error("Unhandled error: %s", exc, exc_info=True)
        return _json_error(500, "internal_error", "Internal Server Error.")
