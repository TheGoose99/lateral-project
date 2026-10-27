from datetime import timedelta

import jwt

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_verifies_correct_password():
    hashed = hash_password("correct-horse-battery-staple")

    assert hashed != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_contains_user_subject():
    token = create_access_token("user-123")

    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["typ"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_expired_access_token_is_rejected():
    token = create_access_token(
        "user-123",
        expires_delta=timedelta(seconds=-1),
    )

    try:
        decode_access_token(token)
        assert False, "Expected an expired token to be rejected"
    except jwt.ExpiredSignatureError:
        pass
