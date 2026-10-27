import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import router as auth_router
from app.api.orders import router as orders_router
from app.api.restaurants import router as restaurants_router
from app.api.staff import router as staff_router
from app.core.config import get_settings
from app.core.csrf import CsrfProtectMiddleware
from app.core.errors import AppError
from app.core.logging import RequestContextMiddleware, configure_logging
from app.core.rate_limit import redis_ready
from app.db.session import engine

configure_logging()
settings = get_settings()
logger = logging.getLogger("takeaway")
docs_enabled = settings.app_env != "production"

_default_secret = "local-only-change-this-secret-key-32-bytes"
if len(settings.secret_key) < 32 or settings.secret_key == _default_secret:
    if settings.app_env == "production":
        raise RuntimeError("SECRET_KEY must be a random value of at least 32 bytes")
    logger.warning(
        "SECRET_KEY is a development default. "
        "Set a random 32+ byte secret before sharing this environment."
    )

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Takeaway ordering API. Customers browse menus and place orders; "
        "staff and admins manage menus and advance order status. "
        "The SPA authenticates with httpOnly cookies and a CSRF header. "
        "For Swagger, `POST /api/v1/auth/login` still returns `access_token`; "
        "use **Authorize** with that Bearer token. "
        "Checkout accepts an optional `Idempotency-Key` header."
    ),
    docs_url="/api/docs" if docs_enabled else None,
    openapi_url="/api/openapi.json" if docs_enabled else None,
    redoc_url=None,
    swagger_ui_parameters={"persistAuthorization": True},
    openapi_tags=[
        {
            "name": "authentication",
            "description": "Register, login, cookie refresh, and current user.",
        },
        {"name": "restaurants", "description": "Public restaurant and menu browsing."},
        {"name": "orders", "description": "Customer ordering, tracking, and staff queue."},
        {"name": "staff", "description": "Staff/admin menu management."},
    ],
)

app.add_middleware(CsrfProtectMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "Idempotency-Key",
        "X-CSRF-Token",
    ],
)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(restaurants_router, prefix=settings.api_prefix)
app.include_router(orders_router, prefix=settings.api_prefix)
app.include_router(staff_router, prefix=settings.api_prefix)


@app.exception_handler(AppError)
def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    logger.info("application error %s: %s", exc.status_code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
def ready() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable"},
        )

    payload: dict[str, str] = {"status": "ready", "database": "ok"}
    if settings.redis_url:
        if not redis_ready():
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "database": "ok", "redis": "unavailable"},
            )
        payload["redis"] = "ok"
    return JSONResponse(status_code=200, content=payload)


@app.get(f"{settings.api_prefix}/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "ok"}
