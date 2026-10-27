from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User


class InvalidRefreshTokenError(Exception):
    pass


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str


def issue_token_pair(db: Session, user: User) -> IssuedTokens:
    settings = get_settings()
    plaintext = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(plaintext),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.flush()
    return IssuedTokens(
        access_token=create_access_token(str(user.id)),
        refresh_token=plaintext,
    )


def rotate_refresh_token(db: Session, refresh_token: str) -> IssuedTokens:
    token_hash = hash_refresh_token(refresh_token)
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    )
    now = datetime.now(UTC)

    if stored is None:
        raise InvalidRefreshTokenError

    if stored.revoked_at is not None:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == stored.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.flush()
        raise InvalidRefreshTokenError

    if stored.expires_at <= now:
        stored.revoked_at = now
        db.flush()
        raise InvalidRefreshTokenError

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        stored.revoked_at = now
        db.flush()
        raise InvalidRefreshTokenError

    stored.revoked_at = now
    return issue_token_pair(db, user)


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    stored = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(refresh_token)
        )
    )
    if stored is None:
        raise AppError(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        db.flush()
