import os

# Must run before any `app.*` import: Settings requires DATABASE_URL and reads it
# at import time. Point tests at a disposable database by default; override by
# exporting DATABASE_URL yourself (e.g. in CI) before running pytest.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://certuser:certpassword@localhost:5432/certificates_test",
)
# Run Celery tasks synchronously, in-process, with no broker — see
# app/workers/celery_app.py. Without this, `.delay()` calls made by tests
# that don't use the `eager_worker` fixture below would try to reach a
# worker process via session_scope()'s own fresh connection; since that
# connection can't see this test's still-uncommitted transaction, they
# safely no-op instead of raising.
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models  # noqa: F401  (registers tables on Base.metadata)
from app.db.base import Base
from app.db.session import get_db
from app.main import app


def _ensure_database_exists(database_url: str) -> None:
    url = make_url(database_url)
    db_name = url.database
    maintenance_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with maintenance_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
        ).first()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    maintenance_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_database_exists(settings.database_url)
    test_engine = create_engine(settings.database_url, future=True)
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def db_session(engine):
    """One DB transaction per test, rolled back at the end, even though the
    code under test calls session.commit() (standard SQLAlchemy savepoint
    pattern for isolating ORM tests)."""
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, future=True)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def eager_worker(db_session, monkeypatch, tmp_path):
    """Makes eager-mode Celery tasks operate on the SAME session/transaction
    as the test (and the API calls made through `client`), and redirects
    generated PDFs to a throwaway directory. Without this, tasks.py's own
    session_scope() would open an unrelated connection that can't see this
    test's uncommitted data (see the CELERY_TASK_ALWAYS_EAGER comment above)."""
    from contextlib import contextmanager

    from app.core.config import settings

    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    @contextmanager
    def _shared_scope():
        yield db_session

    monkeypatch.setattr("app.workers.tasks.session_scope", _shared_scope)
    return db_session
