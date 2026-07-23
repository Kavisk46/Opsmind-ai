import asyncio

from core.security import hash_password
from models.user import User


def _register_and_login(client, email: str = "member@example.com") -> str:
    client.post(
        "/users", json={"email": email, "name": "Member", "password": "secret123"}
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "secret123"}
    )
    return response.json()["access_token"]


def _create_admin_and_login(client, email: str = "admin@example.com") -> str:
    # No public endpoint can create an admin — self-service role
    # escalation would be a real vulnerability (see UserCreate's schema:
    # deliberately has no `role` field). Inserted directly against the
    # test database instead, exactly the way a real deployment would only
    # ever grant admin via a trusted, out-of-band path (a DB migration
    # seed, an internal admin tool) — never through the public signup API.
    async def _create() -> None:
        async with client.session_factory() as session:
            user = User(
                email=email,
                name="Admin",
                password_hash=hash_password("secret123"),
                role="admin",
            )
            session.add(user)
            await session.commit()

    asyncio.run(_create())
    response = client.post(
        "/auth/login", json={"email": email, "password": "secret123"}
    )
    return response.json()["access_token"]


def test_list_users_without_auth_returns_401(client):
    response = client.get("/users")
    assert response.status_code == 401


def test_list_users_as_member_returns_403(client):
    token = _register_and_login(client)
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_list_users_as_admin_returns_200(client):
    token = _create_admin_and_login(client)
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_create_user_with_duplicate_email_returns_409(client):
    payload = {"email": "dup@example.com", "name": "First", "password": "secret123"}
    first = client.post("/users", json=payload)
    assert first.status_code == 201

    second = client.post(
        "/users", json={"email": "dup@example.com", "name": "Second", "password": "secret456"}
    )
    assert second.status_code == 409


def test_create_user_with_malformed_email_returns_422(client):
    response = client.post(
        "/users", json={"email": "not-an-email", "name": "Someone", "password": "secret123"}
    )
    assert response.status_code == 422


def test_get_my_profile_returns_the_calling_user(client):
    client.post(
        "/users", json={"email": "me-user@example.com", "name": "Me User", "password": "secret123"}
    )
    login = client.post(
        "/auth/login", json={"email": "me-user@example.com", "password": "secret123"}
    )
    token = login.json()["access_token"]

    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me-user@example.com"
    assert body["name"] == "Me User"


def test_get_my_profile_without_auth_returns_401(client):
    response = client.get("/users/me")
    assert response.status_code == 401
