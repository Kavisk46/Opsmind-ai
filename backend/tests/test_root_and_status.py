from fastapi.testclient import TestClient

from core.config import Settings, get_settings
from main import app

client = TestClient(app)


def test_root_returns_200():
    response = client.get("/")
    assert response.status_code == 200


def test_root_reports_docs_urls():
    body = client.get("/").json()
    assert body["docs_url"] == "/docs"
    assert body["redoc_url"] == "/redoc"


def test_status_returns_200():
    response = client.get("/status")
    assert response.status_code == 200


def test_status_reports_backend_ok():
    body = client.get("/status").json()
    assert body["backend"] == "ok"


def test_response_includes_process_time_header():
    response = client.get("/health")
    assert "X-Process-Time" in response.headers
    assert float(response.headers["X-Process-Time"]) >= 0


def test_health_reflects_overridden_settings():
    # Proves the actual payoff of Depends(get_settings) over importing the
    # settings singleton directly: no monkeypatching, no route changes —
    # just tell FastAPI to call this function instead, for this test only.
    app.dependency_overrides[get_settings] = lambda: Settings(environment="staging")
    try:
        response = client.get("/health")
        assert response.json()["environment"] == "staging"
    finally:
        app.dependency_overrides.pop(get_settings, None)
