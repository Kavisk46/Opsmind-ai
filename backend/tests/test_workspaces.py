def _register(client, email: str) -> dict:
    response = client.post(
        "/users", json={"email": email, "name": "Test User", "password": "secret123"}
    )
    return response.json()


def _auth_headers(client, email: str) -> dict:
    _register(client, email)
    response = client.post("/auth/login", json={"email": email, "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- create / list / get ---


def test_create_workspace_returns_201_with_the_creator_as_owner(client):
    headers = _auth_headers(client, "create-ws@example.com")

    response = client.post(
        "/workspaces", headers=headers, json={"name": "Team Alpha", "description": "desc"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Team Alpha"
    assert body["description"] == "desc"


def test_create_workspace_with_blank_name_returns_400(client):
    headers = _auth_headers(client, "create-ws-blank@example.com")

    response = client.post("/workspaces", headers=headers, json={"name": "   "})

    assert response.status_code == 400


def test_list_workspaces_includes_the_auto_provisioned_personal_workspace(client):
    headers = _auth_headers(client, "list-ws@example.com")

    response = client.get("/workspaces", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_workspaces_includes_newly_created_ones(client):
    headers = _auth_headers(client, "list-ws-2@example.com")
    client.post("/workspaces", headers=headers, json={"name": "Team Beta"})

    response = client.get("/workspaces", headers=headers)

    assert len(response.json()) == 2


def test_get_workspace_returns_it_for_a_member(client):
    headers = _auth_headers(client, "get-ws@example.com")
    created = client.post("/workspaces", headers=headers, json={"name": "Ops"}).json()

    response = client.get(f"/workspaces/{created['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_workspace_returns_404_for_a_non_member(client):
    owner_headers = _auth_headers(client, "get-ws-owner@example.com")
    outsider_headers = _auth_headers(client, "get-ws-outsider@example.com")
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Secret"}).json()

    response = client.get(f"/workspaces/{created['id']}", headers=outsider_headers)

    assert response.status_code == 404


def test_get_unauthenticated_returns_401(client):
    response = client.get("/workspaces")

    assert response.status_code == 401


# --- rename / delete ---


def test_rename_workspace_succeeds_for_the_owner(client):
    headers = _auth_headers(client, "rename-ws@example.com")
    created = client.post("/workspaces", headers=headers, json={"name": "Old"}).json()

    response = client.patch(
        f"/workspaces/{created['id']}", headers=headers, json={"name": "New"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New"


def test_rename_workspace_denied_for_a_viewer(client):
    owner_headers = _auth_headers(client, "rename-ws-owner@example.com")
    viewer = _register(client, "rename-ws-viewer@example.com")
    viewer_headers = _auth_headers(client, "rename-ws-viewer@example.com")
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Ops"}).json()
    client.post(
        f"/workspaces/{created['id']}/members",
        headers=owner_headers,
        json={"user_id": viewer["id"], "role": "viewer"},
    )

    response = client.patch(
        f"/workspaces/{created['id']}", headers=viewer_headers, json={"name": "Hijacked"}
    )

    assert response.status_code == 403


def test_delete_workspace_succeeds_for_the_owner(client):
    headers = _auth_headers(client, "delete-ws@example.com")
    created = client.post("/workspaces", headers=headers, json={"name": "Doomed"}).json()

    response = client.delete(f"/workspaces/{created['id']}", headers=headers)

    assert response.status_code == 204
    assert client.get(f"/workspaces/{created['id']}", headers=headers).status_code == 404


def test_delete_workspace_denied_for_an_admin(client):
    owner_headers = _auth_headers(client, "delete-ws-owner@example.com")
    admin = _register(client, "delete-ws-admin@example.com")
    admin_headers = _auth_headers(client, "delete-ws-admin@example.com")
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Ops"}).json()
    client.post(
        f"/workspaces/{created['id']}/members",
        headers=owner_headers,
        json={"user_id": admin["id"], "role": "admin"},
    )

    response = client.delete(f"/workspaces/{created['id']}", headers=admin_headers)

    assert response.status_code == 403


# --- membership routes ---


def test_add_workspace_member_succeeds_for_the_owner(client):
    owner_headers = _auth_headers(client, "add-member-owner@example.com")
    new_member = _register(client, "add-member-new@example.com")
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Ops"}).json()

    response = client.post(
        f"/workspaces/{created['id']}/members",
        headers=owner_headers,
        json={"user_id": new_member["id"], "role": "editor"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "editor"


def test_add_workspace_member_denied_for_a_viewer(client):
    owner_headers = _auth_headers(client, "add-member-denied-owner@example.com")
    viewer = _register(client, "add-member-denied-viewer@example.com")
    viewer_headers = _auth_headers(client, "add-member-denied-viewer@example.com")
    third_party = _register(client, "add-member-denied-third@example.com")
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Ops"}).json()
    client.post(
        f"/workspaces/{created['id']}/members",
        headers=owner_headers,
        json={"user_id": viewer["id"], "role": "viewer"},
    )

    response = client.post(
        f"/workspaces/{created['id']}/members",
        headers=viewer_headers,
        json={"user_id": third_party["id"], "role": "viewer"},
    )

    assert response.status_code == 403


def test_list_workspace_members_includes_every_member(client):
    owner_headers = _auth_headers(client, "list-members-owner@example.com")
    member = _register(client, "list-members-member@example.com")
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Ops"}).json()
    client.post(
        f"/workspaces/{created['id']}/members",
        headers=owner_headers,
        json={"user_id": member["id"], "role": "viewer"},
    )

    response = client.get(f"/workspaces/{created['id']}/members", headers=owner_headers)

    assert response.status_code == 200
    assert {m["user_id"] for m in response.json()} == {
        member["id"],
        _extract_owner_id(client, owner_headers),
    }


def test_change_workspace_member_role_updates_it(client):
    owner_headers = _auth_headers(client, "change-role-owner@example.com")
    member = _register(client, "change-role-member@example.com")
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Ops"}).json()
    client.post(
        f"/workspaces/{created['id']}/members",
        headers=owner_headers,
        json={"user_id": member["id"], "role": "viewer"},
    )

    response = client.patch(
        f"/workspaces/{created['id']}/members/{member['id']}",
        headers=owner_headers,
        json={"role": "admin"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_change_workspace_member_role_returns_404_for_a_non_member(client):
    owner_headers = _auth_headers(client, "change-role-404-owner@example.com")
    stranger = _register(client, "change-role-404-stranger@example.com")
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Ops"}).json()

    response = client.patch(
        f"/workspaces/{created['id']}/members/{stranger['id']}",
        headers=owner_headers,
        json={"role": "admin"},
    )

    assert response.status_code == 404


def test_change_workspace_member_role_returns_409_when_demoting_the_last_owner(client):
    owner_headers = _auth_headers(client, "last-owner-409@example.com")
    owner_id = _extract_owner_id(client, owner_headers)
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Ops"}).json()

    response = client.patch(
        f"/workspaces/{created['id']}/members/{owner_id}",
        headers=owner_headers,
        json={"role": "admin"},
    )

    assert response.status_code == 409


def test_remove_workspace_member_succeeds_for_the_owner(client):
    owner_headers = _auth_headers(client, "remove-member-owner@example.com")
    member = _register(client, "remove-member-member@example.com")
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Ops"}).json()
    client.post(
        f"/workspaces/{created['id']}/members",
        headers=owner_headers,
        json={"user_id": member["id"], "role": "viewer"},
    )

    response = client.delete(
        f"/workspaces/{created['id']}/members/{member['id']}", headers=owner_headers
    )

    assert response.status_code == 204
    remaining = client.get(f"/workspaces/{created['id']}/members", headers=owner_headers).json()
    assert member["id"] not in {m["user_id"] for m in remaining}


def test_remove_workspace_member_returns_409_when_removing_the_last_owner(client):
    owner_headers = _auth_headers(client, "last-owner-remove-409@example.com")
    owner_id = _extract_owner_id(client, owner_headers)
    created = client.post("/workspaces", headers=owner_headers, json={"name": "Ops"}).json()

    response = client.delete(
        f"/workspaces/{created['id']}/members/{owner_id}", headers=owner_headers
    )

    assert response.status_code == 409


def _extract_owner_id(client, owner_headers: dict) -> str:
    # The auto-provisioned personal workspace's only member is the owner
    # themself — this is the simplest way to learn "my own user id" from
    # pure HTTP responses, without adding a dedicated /users/me route
    # just for this test file's sake.
    workspaces = client.get("/workspaces", headers=owner_headers).json()
    personal_workspace_id = workspaces[0]["id"]
    members = client.get(
        f"/workspaces/{personal_workspace_id}/members", headers=owner_headers
    ).json()
    return members[0]["user_id"]
