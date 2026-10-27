import os
from collections.abc import Generator

os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["REDIS_URL"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app

get_settings.cache_clear()


@pytest.fixture()
def db_connection() -> Generator[Connection, None, None]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.fail("DATABASE_URL must point to the dedicated test database")

    engine = create_engine(database_url, pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()

    try:
        yield connection
    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()


@pytest.fixture()
def db_session(db_connection: Connection) -> Generator[Session, None, None]:
    with Session(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
    ) as session:
        yield session


@pytest.fixture()
def auth_client(db_connection: Connection) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with Session(
            bind=db_connection,
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(
    auth_client: TestClient,
) -> Generator[dict[str, str], None, None]:
    response = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "Test.User@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    yield response.json()
