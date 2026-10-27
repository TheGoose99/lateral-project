from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from app.core.errors import AppError
from app.core.rate_limit import enforce_rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    register_customer,
)
from app.services.tokens import (
    InvalidRefreshTokenError,
    issue_token_pair,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
DbSession = Annotated[Session, Depends(get_db)]


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _unauthorized_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(request: Request, data: RegisterRequest, db: DbSession) -> User:
    enforce_rate_limit(request, "auth", get_settings().auth_rate_limit_per_minute)
    try:
        return register_customer(db, data)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    data: LoginRequest,
    db: DbSession,
    response: Response,
) -> TokenResponse:
    enforce_rate_limit(request, "auth", get_settings().auth_rate_limit_per_minute)
    try:
        user = authenticate_user(db, str(data.email), data.password)
        tokens = issue_token_pair(db, user)
        _commit(db)
        set_auth_cookies(response, request, tokens.access_token, tokens.refresh_token)
        return TokenResponse(access_token=tokens.access_token)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, db: DbSession, response: Response) -> TokenResponse:
    enforce_rate_limit(request, "auth", get_settings().auth_rate_limit_per_minute)
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise _unauthorized_refresh()
    try:
        tokens = rotate_refresh_token(db, refresh_token)
        _commit(db)
        set_auth_cookies(response, request, tokens.access_token, tokens.refresh_token)
        return TokenResponse(access_token=tokens.access_token)
    except InvalidRefreshTokenError:
        _commit(db)
        clear_auth_cookies(response, request)
        raise _unauthorized_refresh() from None


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: DbSession, response: Response) -> None:
    enforce_rate_limit(request, "auth", get_settings().auth_rate_limit_per_minute)
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if refresh_token:
        try:
            revoke_refresh_token(db, refresh_token)
            _commit(db)
        except AppError:
            db.rollback()
    clear_auth_cookies(response, request)


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
