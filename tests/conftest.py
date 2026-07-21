"""Test configuration"""

import pytest
from backend.db.models import init_db, create_tables


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    from backend.db import models
    init_db("sqlite:///:memory:")
    create_tables()
    yield
    if models.engine is not None:
        models.engine.dispose()


@pytest.fixture
def db_session():
    from backend.db.models import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
