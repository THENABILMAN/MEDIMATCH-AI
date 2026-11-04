import logging
import re
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Optional

# Ensure backend root is on sys.path so 'app.*' imports work from any working directory
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import (
    admin,
    appointments,
    auth,
    chat,
    doctors,
    health,
    recommendations,
    users,
)
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import configure_logging, request_id_var
from app.schemas.profile import SpecialtyRead
from app.schemas.responses import ErrorResponse
from app.search.sync import wait_for_background_syncs
from app.services.admin_service import list_specialties

logger = logging.getLogger("medimatch.request")

REQUEST_ID_FORMAT = re.compile(r"^[A-Za-z0-9-]{1,64}$")
ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "bad_gateway",
    503: "service_unavailable",
}
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
}


ERROR_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409, 429, 503)
}


def _error_body(status_code: int, detail: Any) -> Dict[str, Any]:
    """Every error keeps `detail`, which the web app reads, and adds a code and request id."""
    return {
        "detail": detail,
        "code": ERROR_CODES.get(status_code, "error"),
        "request_id": request_id_var.get(),
    }


async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.status_code, exc.detail),
        headers=exc.headers,
    )


async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # `input` and `ctx` can repeat what was sent, which may be a password
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content=_error_body(422, jsonable_encoder(errors)))


async def _unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled {type(exc).__name__}")
    return JSONResponse(
        status_code=500,
        content=_error_body(500, "Something went wrong on our side. Please try again."),
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield
    wait_for_background_syncs()


def _content_length(request: Request) -> Optional[int]:
    value = request.headers.get("content-length")
    return int(value) if value and value.isdigit() else None


async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Gives each request an id, refuses oversized bodies, and logs one line without any content."""
    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if REQUEST_ID_FORMAT.match(supplied) else str(uuid.uuid4())
    token = request_id_var.set(request_id)
    started = time.perf_counter()

    try:
        length = _content_length(request)
        if length is not None and length > settings.MAX_REQUEST_BYTES:
            response: Response = JSONResponse(
                status_code=413, content=_error_body(413, "This request is too large.")
            )
        else:
            try:
                response = await call_next(request)
            except Exception as exc:
                # Handled here so the id and headers below reach this response too
                response = await _unexpected_error(request, exc)

        response.headers["X-Request-ID"] = request_id
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)

        elapsed_ms = round((time.perf_counter() - started) * 1000)
        logger.info(f"{request.method} {request.url.path} {response.status_code} {elapsed_ms}ms")
        return response
    finally:
        request_id_var.reset(token)


def create_app() -> FastAPI:
    production = settings.ENVIRONMENT == "production"
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="AI-powered doctor recommendation & appointment booking platform API",
        version="0.1.0",
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
        lifespan=lifespan,
    )

    application.add_exception_handler(StarletteHTTPException, _http_error)
    application.add_exception_handler(RequestValidationError, _validation_error)
    application.add_exception_handler(Exception, _unexpected_error)

    # Sign-in uses bearer tokens, not cookies, so browsers need no credentialed access
    if settings.BACKEND_CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID", "Retry-After"],
        )
    application.middleware("http")(request_context)

    # Include v1 API router (/api/v1/...)
    application.include_router(api_router, prefix=settings.API_V1_STR, include_in_schema=False)

    # The web app calls these root paths
    application.include_router(health.router)
    for router in (
        users.router,
        auth.router,
        doctors.router,
        appointments.router,
        admin.router,
        chat.router,
        recommendations.router,
    ):
        application.include_router(router, responses=ERROR_RESPONSES)

    @application.get("/specialties", response_model=list[SpecialtyRead], summary="Public specialties listing")
    def root_specialties() -> list[SpecialtyRead]:
        return list_specialties()

    @application.get("/", response_model=Dict[str, str], summary="Root index")
    def root_index() -> Dict[str, str]:
        return {"message": f"Welcome to {settings.PROJECT_NAME} API", "health_check": "/health"}

    return application


app = create_app()
