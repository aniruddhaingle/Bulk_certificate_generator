from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_celery_dispatch(monkeypatch):
    """Tests under tests/api/ exercise only the HTTP + database contract.
    Background processing (Celery/worker behavior) is a separate concern,
    covered deliberately in tests/integration/ instead. Mocking the dispatch
    call here makes that boundary explicit, rather than relying on eager-mode
    Celery's cross-connection invisibility as an implicit (and fragile)
    no-op the way earlier phases did."""
    mock_task = MagicMock()
    monkeypatch.setattr("app.services.job_service.process_certificate_job", mock_task)
    return mock_task
