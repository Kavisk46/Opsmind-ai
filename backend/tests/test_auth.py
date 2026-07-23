def _register(client, email: str = "auth-user@example.com", password: str = "secret123") -> None:
    client.post("/users", json={"email": email, "name": "Auth User", "password": password})


def test_login_returns_bearer_access_token(client):
    _register(client)

    response = client.post(
        "/auth/login", json={"email": "auth-user@example.com", "password": "secret123"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_login_with_wrong_password_returns_401(client):
    _register(client, email="auth-wrong-pw@example.com")

    response = client.post(
        "/auth/login", json={"email": "auth-wrong-pw@example.com", "password": "not-the-password"}
    )

    assert response.status_code == 401


def test_login_with_nonexistent_email_returns_401(client):
    response = client.post(
        "/auth/login", json={"email": "nobody-here@example.com", "password": "whatever123"}
    )

    assert response.status_code == 401


def test_login_wrong_password_and_nonexistent_email_return_identical_error(client):
    # Anti-enumeration: a caller must not be able to tell "that email
    # doesn't exist" apart from "that email exists but the password is
    # wrong" by comparing response bodies — both are the SAME
    # InvalidCredentialsError -> 401 mapping (see AuthService.login()).
    # This test proves the two responses are byte-for-byte identical in
    # message, not just the same status code.
    _register(client, email="auth-enum-check@example.com")

    wrong_password = client.post(
        "/auth/login",
        json={"email": "auth-enum-check@example.com", "password": "wrong"},
    )
    nonexistent_email = client.post(
        "/auth/login",
        json={"email": "definitely-not-registered@example.com", "password": "wrong"},
    )

    assert wrong_password.status_code == nonexistent_email.status_code == 401
    assert wrong_password.json()["message"] == nonexistent_email.json()["message"]


def test_login_with_malformed_email_returns_422(client):
    response = client.post(
        "/auth/login", json={"email": "not-an-email", "password": "secret123"}
    )

    assert response.status_code == 422


def test_login_with_missing_password_returns_422(client):
    response = client.post("/auth/login", json={"email": "someone@example.com"})

    assert response.status_code == 422
