import pytest
from fastapi.testclient import TestClient

from thermal_guard.config import Settings
from thermal_guard.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app(
        Settings(
            database_path=":memory:",
            mqtt_enabled=False,
            absolute_warning_c=70,
            absolute_critical_c=85,
        )
    )
    with TestClient(app) as test_client:
        yield test_client
