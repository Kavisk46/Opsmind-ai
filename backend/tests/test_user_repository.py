import asyncio
import uuid


# --- create / get_by_id ---


def test_create_persists_a_new_user(user_repository):
    user = asyncio.run(
        user_repository.create(email="new@example.com", name="New User", password_hash="hashed")
    )

    assert user.id is not None
    assert user.email == "new@example.com"
    # Model-declared defaults (models/user.py) — proving they're actually
    # applied on insert, not just documented.
    assert user.role == "member"
    assert user.is_active is True


def test_get_by_id_returns_the_created_user(user_repository):
    created = asyncio.run(
        user_repository.create(email="lookup@example.com", name="Lookup", password_hash="h")
    )

    fetched = asyncio.run(user_repository.get_by_id(created.id))

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.email == "lookup@example.com"


def test_get_by_id_returns_none_for_unknown_id(user_repository):
    result = asyncio.run(user_repository.get_by_id(uuid.uuid4()))
    assert result is None


# --- query filters (specific to UserRepository, not on BaseRepository) ---


def test_get_by_email_finds_the_matching_user(user_repository):
    asyncio.run(
        user_repository.create(email="findme@example.com", name="Find Me", password_hash="h")
    )

    result = asyncio.run(user_repository.get_by_email("findme@example.com"))

    assert result is not None
    assert result.name == "Find Me"


def test_get_by_email_returns_none_when_no_match(user_repository):
    result = asyncio.run(user_repository.get_by_email("nobody@example.com"))
    assert result is None


def test_list_active_users_excludes_deactivated_ones(user_repository):
    active = asyncio.run(
        user_repository.create(email="active@example.com", name="Active", password_hash="h")
    )
    inactive = asyncio.run(
        user_repository.create(email="inactive@example.com", name="Inactive", password_hash="h")
    )
    asyncio.run(user_repository.update(inactive, is_active=False))

    result = asyncio.run(user_repository.list_active_users())

    ids = {u.id for u in result}
    assert active.id in ids
    assert inactive.id not in ids


# --- update / delete ---


def test_update_changes_persisted_fields(user_repository):
    user = asyncio.run(
        user_repository.create(email="update@example.com", name="Old Name", password_hash="h")
    )

    updated = asyncio.run(user_repository.update(user, name="New Name"))
    assert updated.name == "New Name"

    # Re-fetched independently of the object update() returned — proves
    # the change is genuinely persisted in the session's view of the
    # database, not just mutated on the Python object in memory.
    refetched = asyncio.run(user_repository.get_by_id(user.id))
    assert refetched.name == "New Name"


def test_delete_removes_the_user(user_repository):
    user = asyncio.run(
        user_repository.create(email="delete@example.com", name="Delete Me", password_hash="h")
    )

    asyncio.run(user_repository.delete(user))

    assert asyncio.run(user_repository.get_by_id(user.id)) is None


def test_exists_reflects_creation_and_deletion(user_repository):
    user = asyncio.run(
        user_repository.create(email="exists@example.com", name="Exists", password_hash="h")
    )
    assert asyncio.run(user_repository.exists(user.id)) is True

    asyncio.run(user_repository.delete(user))
    assert asyncio.run(user_repository.exists(user.id)) is False
