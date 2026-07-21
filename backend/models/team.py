from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.user import User


class Team(BaseModel):
    """The `teams` table — the multi-tenancy boundary. A User optionally
    belongs to one Team (see models/user.py's nullable team_id); documents
    and conversations are scoped to a User today, not directly to a Team.
    Team exists now so that team-level scoping can be added later without
    retrofitting a column onto tables that predate the concept.
    """

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="team")
