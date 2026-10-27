import secrets

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.cookies import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_CSRF_EXEMPT_SUFFIXES = ("/auth/login", "/auth/register")


class CsrfProtectMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.method not in _UNSAFE_METHODS:
            return await call_next(request)

        path = request.url.path
        if path.endswith(_CSRF_EXEMPT_SUFFIXES):
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            return await call_next(request)

        has_session_cookie = any(
            request.cookies.get(name)
            for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE)
        )
        if not has_session_cookie:
            return await call_next(request)

        origin = request.headers.get("origin")
        if origin and origin != get_settings().frontend_origin:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid request origin"},
            )

        cookie = request.cookies.get(CSRF_COOKIE)
        header = request.headers.get("x-csrf-token")
        if (
            not cookie
            or not header
            or not secrets.compare_digest(cookie, header)
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid"},
            )

        return await call_next(request)
