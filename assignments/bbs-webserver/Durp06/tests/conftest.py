import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from db import init_db
from main import app, get_engine_dep


def make_test_engine():
    """Create an in-memory SQLite engine that shares a single connection."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def client():
    test_engine = make_test_engine()
    init_db(test_engine)
    app.dependency_overrides[get_engine_dep] = lambda: test_engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
