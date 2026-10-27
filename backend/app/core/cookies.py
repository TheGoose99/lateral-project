import secrets
from typing import Final

from fastapi import Request, Response

from app.core.config import get_settings

ACCESS_COOKIE: Final = "takeaway_access"
REFRESH_COOKIE: Final = "takeaway_refresh"
CSRF_COOKIE: Final = "takeaway_csrf"


def _secure(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "")
    return request.url.scheme == "https" or forwarded.split(",")[0].strip() == "https"


def _refresh_path() -> str:
    return f"{get_settings().api_prefix}/auth"


def set_auth_cookies(
    response: Response,
    request: Request,
    access_token: str,
    refresh_token: str,
) -> None:
    settings = get_settings()
    secure = _secure(request)
    csrf = secrets.token_urlsafe(32)
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        path=_refresh_path(),
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
        httponly=False,
        samesite="lax",
        secure=secure,
    )


def clear_auth_cookies(response: Response, request: Request) -> None:
    secure = _secure(request)
    response.delete_cookie(
        ACCESS_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    response.delete_cookie(
        REFRESH_COOKIE,
        path=_refresh_path(),
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    response.delete_cookie(
        CSRF_COOKIE,
        path="/",
        httponly=False,
        samesite="lax",
        secure=secure,
    )
