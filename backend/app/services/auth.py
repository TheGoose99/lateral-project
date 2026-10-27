from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def register_customer(db: Session, data: RegisterRequest) -> User:
    user = User(
        email=str(data.email).lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role="customer",
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Do not assume every integrity failure means a duplicate email.
        existing_user = db.scalar(select(User.id).where(User.email == str(data.email).lower()))
        if existing_user is not None:
            raise EmailAlreadyRegisteredError from exc
        raise

    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))

    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError

    if not user.is_active:
        raise InvalidCredentialsError

    return user
