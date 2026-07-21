from pydantic import BaseModel


class APIInfoResponse(BaseModel):
    """Response body for GET / — a landing point for anyone (human or
    tooling) hitting the API root with no idea what it is yet.
    """

    name: str
    version: str
    description: str
    docs_url: str
    redoc_url: str
