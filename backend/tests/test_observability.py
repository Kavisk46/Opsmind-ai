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


# --- Security Hardening phase ---


def test_response_includes_security_headers(client):
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_cors_allows_the_configured_frontend_origin(client):
    # Settings.cors_allowed_origins_raw defaults to exactly this origin
    # (matching docker-compose.yml's frontend port) — a real browser
    # sends this Origin header on every cross-origin fetch(), and only
    # gets to read the response if the server echoes it back allowed.
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_does_not_allow_an_unrecognized_origin(client):
    response = client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


def test_unhandled_exception_returns_standard_envelope(client):
    # Simulates a genuine, unexpected bug — an exception raised from
    # INSIDE a route's body (login()'s call to rate_limiter.check()),
    # not a deliberately-raised HTTPException. Deliberately NOT an
    # exception raised during DEPENDENCY RESOLUTION itself (i.e. the
    # override callable raising directly) — verified directly while
    # building this test that a real, separate Starlette/FastAPI
    # limitation exists there: a custom @app.middleware("http") (this
    # app has one — add_process_time_and_log) built on
    # starlette.middleware.base.BaseHTTPMiddleware does not reliably see
    # the response a registered exception handler produces for an
    # exception raised THAT early, and the raw exception propagates
    # instead (a known upstream quirk, not something this phase's scope
    # includes rewriting the middleware stack to fix — see the security
    # review). An exception raised once a route body is already
    # executing — verified directly to work correctly — is also the far
    # more representative case: a real bug is almost always in business
    # logic, not in dependency construction itself.
    from api.dependencies import get_login_rate_limiter
    from main import app

    class _BrokenRateLimiter:
        def check(self, key: str) -> None:
            raise RuntimeError("simulated unexpected failure")

    async def _broken_dependency():
        return _BrokenRateLimiter()

    previous_override = app.dependency_overrides.get(get_login_rate_limiter)
    app.dependency_overrides[get_login_rate_limiter] = _broken_dependency
    try:
        response = client.post(
            "/auth/login", json={"email": "x@example.com", "password": "whatever123"}
        )
    finally:
        if previous_override is not None:
            app.dependency_overrides[get_login_rate_limiter] = previous_override

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_error"
    # The real exception message must NEVER reach the client — only the
    # server-side log line gets that detail (see main.py's handler).
    assert "simulated unexpected failure" not in body["message"]
    assert body["request_id"] == response.headers["X-Request-ID"]
