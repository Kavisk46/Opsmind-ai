# Importing every model here — not just Base — is what registers each
# mapped class in SQLAlchemy's registry before any relationship() string
# forward-reference (e.g. User.team: Mapped["Team | None"]) is resolved.
# Mapper configuration runs lazily, on first real ORM use — a model whose
# module nothing in the app's actual runtime import graph ever imports
# (Team has no route/service/repository yet, unlike Document/Conversation,
# which get pulled in via api/dependencies.py) raises "failed to locate a
# name" at that point, even though the class itself is defined correctly.
# Same reasoning as alembic/env.py's identical import list, applied here
# so the app itself doesn't depend on that migration-only entry point.
from models.base import Base  # noqa: F401
from models.conversation import Conversation  # noqa: F401
from models.document import Document  # noqa: F401
from models.message import Message  # noqa: F401
from models.oauth_account import OAuthAccount  # noqa: F401
from models.refresh_token import RefreshToken  # noqa: F401
from models.team import Team  # noqa: F401
from models.user import User  # noqa: F401
