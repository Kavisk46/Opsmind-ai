import asyncio
import uuid

import pytest

from models.workspace import Workspace
from services.document_service import DuplicateFilenameError, UnsupportedFileTypeError


def _make_user(user_repository, email: str = "svc-owner@example.com"):
    return asyncio.run(
        user_repository.create(email=email, name="Service Owner", password_hash="h")
    )


def _make_workspace(db_session, created_by: uuid.UUID) -> Workspace:
    async def _create():
        workspace = Workspace(name="Test Workspace", created_by=created_by)
        db_session.add(workspace)
        await db_session.flush()
        return workspace

    return asyncio.run(_create())


# --- storage key namespacing -----------------------------------------------


def test_storage_key_is_namespaced_under_the_owner_id(document_service, user_repository):
    owner = _make_user(user_repository)
    workspace = _make_workspace(document_service.db, owner.id)

    document = asyncio.run(
        document_service.upload_document(
            owner_id=owner.id,
            workspace_id=workspace.id,
            filename="notes.txt",
            content_type="text/plain",
            data=b"hello",
        )
    )

    assert document.storage_key.startswith(f"{owner.id}/")


# --- filename sanitization ---------------------------------------------

def test_upload_sanitizes_a_path_traversal_filename(document_service, user_repository):
    owner = _make_user(user_repository, email="svc-traversal@example.com")
    workspace = _make_workspace(document_service.db, owner.id)

    document = asyncio.run(
        document_service.upload_document(
            owner_id=owner.id,
            workspace_id=workspace.id,
            filename="../../etc/passwd.txt",
            content_type="text/plain",
            data=b"hello",
        )
    )

    assert document.filename == "passwd.txt"


# --- duplicate filenames ---------------------------------------------------


def test_second_upload_with_same_filename_in_same_workspace_is_rejected(
    document_service, user_repository
):
    owner = _make_user(user_repository, email="svc-dup@example.com")
    workspace = _make_workspace(document_service.db, owner.id)
    asyncio.run(
        document_service.upload_document(
            owner_id=owner.id,
            workspace_id=workspace.id,
            filename="notes.txt",
            content_type="text/plain",
            data=b"first",
        )
    )

    with pytest.raises(DuplicateFilenameError):
        asyncio.run(
            document_service.upload_document(
                owner_id=owner.id,
                workspace_id=workspace.id,
                filename="notes.txt",
                content_type="text/plain",
                data=b"second",
            )
        )


def test_same_filename_is_allowed_in_different_workspaces(document_service, user_repository):
    owner_a = _make_user(user_repository, email="svc-owner-a@example.com")
    owner_b = _make_user(user_repository, email="svc-owner-b@example.com")
    workspace_a = _make_workspace(document_service.db, owner_a.id)
    workspace_b = _make_workspace(document_service.db, owner_b.id)
    asyncio.run(
        document_service.upload_document(
            owner_id=owner_a.id,
            workspace_id=workspace_a.id,
            filename="notes.txt",
            content_type="text/plain",
            data=b"from a",
        )
    )

    # Must not raise — the uq_documents_workspace_id_filename constraint is
    # scoped to (workspace_id, filename), never filename alone.
    document = asyncio.run(
        document_service.upload_document(
            owner_id=owner_b.id,
            workspace_id=workspace_b.id,
            filename="notes.txt",
            content_type="text/plain",
            data=b"from b",
        )
    )
    assert document.filename == "notes.txt"


def test_duplicate_upload_does_not_leave_an_orphaned_file_on_disk(
    document_service, user_repository
):
    owner = _make_user(user_repository, email="svc-dup-orphan@example.com")
    workspace = _make_workspace(document_service.db, owner.id)
    asyncio.run(
        document_service.upload_document(
            owner_id=owner.id,
            workspace_id=workspace.id,
            filename="notes.txt",
            content_type="text/plain",
            data=b"first",
        )
    )
    files_before = list(document_service.storage.base_dir.rglob("*"))
    file_count_before = len([p for p in files_before if p.is_file()])

    with pytest.raises(DuplicateFilenameError):
        asyncio.run(
            document_service.upload_document(
                owner_id=owner.id,
                workspace_id=workspace.id,
                filename="notes.txt",
                content_type="text/plain",
                data=b"second",
            )
        )

    files_after = list(document_service.storage.base_dir.rglob("*"))
    file_count_after = len([p for p in files_after if p.is_file()])
    assert file_count_after == file_count_before


# --- expanded accepted upload types -----------------------------------

@pytest.mark.parametrize(
    "content_type",
    [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/csv",
        "image/png",
        "image/jpeg",
    ],
)
def test_upload_accepts_the_newly_supported_types(
    document_service, user_repository, content_type
):
    owner = _make_user(user_repository, email=f"svc-{content_type.split('/')[-1]}@example.com")
    workspace = _make_workspace(document_service.db, owner.id)

    document = asyncio.run(
        document_service.upload_document(
            owner_id=owner.id,
            workspace_id=workspace.id,
            filename="asset.bin",
            content_type=content_type,
            data=b"binary-ish content",
        )
    )

    assert document.content_type == content_type


def test_upload_still_rejects_a_genuinely_unsupported_type(document_service, user_repository):
    owner = _make_user(user_repository, email="svc-zip@example.com")
    workspace = _make_workspace(document_service.db, owner.id)

    with pytest.raises(UnsupportedFileTypeError):
        asyncio.run(
            document_service.upload_document(
                owner_id=owner.id,
                workspace_id=workspace.id,
                filename="archive.zip",
                content_type="application/zip",
                data=b"PK\x03\x04",
            )
        )
