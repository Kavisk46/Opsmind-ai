import uuid


def test_response_includes_request_id_header(client):
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
    # A real, valid UUID -- not just "some string was present"
    uuid.UUID(response.headers["X-Request-ID"])


def test_two_requests_get_different_request_ids(client):
    first = client.get("/health").headers["X-Request-ID"]
    second = client.get("/health").headers["X-Request-ID"]
    assert first != second


def test_response_includes_api_version_header(client):
    response = client.get("/health")
    assert response.headers["X-API-Version"]


def test_error_response_uses_standard_envelope(client, auth_headers):
    # A 404 from an existing, unrelated route -- proves the envelope is
    # applied GLOBALLY (main.py's exception handler), not opted into by
    # each route individually.
    response = client.get(f"/documents/{uuid.uuid4()}", headers=auth_headers())
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "not_found"
    assert body["message"]
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_validation_error_uses_standard_envelope(client, auth_headers):
    # Malformed body (question missing entirely) -- FastAPI's automatic
    # 422, not a route-raised HTTPException, still gets the same envelope.
    headers = auth_headers(email="obs-validation@example.com")
    response = client.post("/chat", headers=headers, json={})
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["request_id"]


def test_readiness_reports_all_dependencies(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "connected"
    assert body["chromadb"] == "connected"
    assert body["storage"] == "writable"
    assert body["llm"] in ("loaded", "not_loaded_yet")


def test_status_reports_all_dependencies(client):
    response = client.get("/status")
    assert response.status_code == 200
    body = response.json()
    assert body["backend"] == "ok"
    assert body["database"] == "connected"
    assert body["chromadb"] == "connected"
    assert body["storage"] == "writable"
    assert body["redis"] == "not_configured"


def test_metrics_endpoint_returns_prometheus_format(client):
    # Hit a real route first so there's at least one recorded sample.
    client.get("/health")

    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text
    assert "opsmind_http_requests_total" in text
    assert "opsmind_http_request_duration_seconds" in text


def test_login_rate_limit_blocks_after_max_attempts(client):
    # 5 is this fixture's configured max_requests — the 6th within the
    # same window must be rejected, proving the limiter actually
    # accumulates hits across requests within one test (not resetting
    # every call, which would be an easy, silent bug to introduce).
    payload = {"email": "nonexistent@example.com", "password": "wrong"}
    for _ in range(5):
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401  # wrong credentials, not rate-limited yet

    response = client.post("/auth/login", json=payload)
    assert response.status_code == 429
    body = response.json()
    assert body["error"] == "too_many_requests"
