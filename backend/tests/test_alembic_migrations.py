"""Static, database-free checks of the migration chain itself.

Deliberately does NOT run `alembic upgrade head` against a real database
— verified by hand during this phase that it can't run against SQLite at
all: migration b7e2f4a9c6d1 uses `op.create_foreign_key()`, which Alembic
cannot apply to SQLite outside of its "batch mode" (SQLite has no ALTER
TABLE ADD CONSTRAINT; Alembic's batch mode works around this by
recreating the whole table, but these migrations were never written to
use it, since they only ever needed to run against this project's real
target, Postgres). Rewriting already-applied migrations to add batch
mode retroactively just to satisfy a test would be worse than not
testing this at all — migrations are a historical record once real
environments have run them, not something to edit after the fact.

Real end-to-end migration testing (spin up a throwaway Postgres — e.g.
via testcontainers or a CI service container — run `alembic upgrade
head` against it, diff the resulting schema against Base.metadata) is
the theoretically correct version of this test, and this project doesn't
have it: Docker/Postgres are not available in this development
environment (the same constraint noted throughout this project's
earlier phases). What follows is what CAN be verified with zero database
involvement at all — genuinely useful, not a consolation prize: a
migration history with two heads or a broken down_revision chain is a
real, common mistake (usually from two branches each adding a migration
off the same parent) that this catches with no infrastructure required.
"""

import os
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_VERSIONS_DIR = _BACKEND_DIR / "alembic" / "versions"


def _script_directory() -> ScriptDirectory:
    config = Config(str(_BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(config)


def test_migration_history_has_exactly_one_head():
    # More than one head means `alembic upgrade head` is ambiguous —
    # two migrations were each written as the "next" step after the same
    # parent, instead of one being rebased onto the other.
    script_dir = _script_directory()
    heads = script_dir.get_heads()
    assert len(heads) == 1


def test_every_migration_file_is_part_of_the_linear_chain():
    # walk_revisions() itself raises if any migration's down_revision
    # points at a revision ID that doesn't exist, or if there's a cycle —
    # simply completing this walk without error is already most of the
    # test. Comparing the count against the real files on disk catches
    # the remaining case: a migration file that exists but is orphaned
    # (nothing's down_revision points to it, so it'd never actually run).
    script_dir = _script_directory()
    revisions_in_chain = {rev.revision for rev in script_dir.walk_revisions()}

    version_files = [
        f for f in os.listdir(_VERSIONS_DIR)
        if f.endswith(".py") and not f.startswith("__")
    ]

    assert len(revisions_in_chain) == len(version_files)


def test_base_revision_has_no_down_revision():
    # Exactly one migration should have down_revision=None — the true
    # start of history. Two would mean two disconnected chains that
    # happen to both look valid in isolation.
    script_dir = _script_directory()
    bases = script_dir.get_bases()
    assert len(bases) == 1
