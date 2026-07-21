import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base every ORM model inherits from.

    This is what lets Alembic discover every table in one place: it reads
    `Base.metadata` (populated automatically as each model file is
    imported) to know the full set of tables that should exist.
    """


class BaseModel(Base):
    """Adds the three columns every domain model needs — a UUID primary
    key, created_at, updated_at — in exactly one place. A model inherits
    from this instead of Base directly to get all three for free, instead
    of redeclaring the same five lines in every model file.

    __abstract__ = True tells SQLAlchemy this class itself is not a table
    — no `basemodels` table gets created. Only concrete subclasses
    (Team, User, Document, ...) that set their own __tablename__ become
    real tables; they inherit these three columns as if declared directly
    on them.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # onupdate runs on every UPDATE statement SQLAlchemy issues for this
    # row — set once at insert (same as created_at), then refreshed
    # automatically every time the row changes afterward, with no calling
    # code responsible for remembering to bump it by hand.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
