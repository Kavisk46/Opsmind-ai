from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_reports_ok_status():
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "ok"


def test_health_reports_environment():
    response = client.get("/health")
    body = response.json()
    assert body["environment"] == "development"


def test_health_reports_version_and_uptime():
    response = client.get("/health")
    body = response.json()
    assert body["version"]
    assert body["uptime_seconds"] >= 0
