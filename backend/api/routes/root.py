from fastapi import APIRouter, Depends

from core.config import Settings, get_settings
from schemas.root import APIInfoResponse

router = APIRouter(tags=["root"])


@router.get("/", response_model=APIInfoResponse)
def get_api_info(settings: Settings = Depends(get_settings)) -> APIInfoResponse:
    """The API's front door. Exists for a human (or a script) hitting the
    bare root URL with no other context — points them at the interactive
    docs instead of a bare 404.

    settings is injected via Depends(get_settings) rather than imported
    directly — see the docstring on get_settings() for why. See
    test_root_and_status.py's override test for what this buys us.
    """
    return APIInfoResponse(
        name=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        docs_url="/docs",
        redoc_url="/redoc",
    )
