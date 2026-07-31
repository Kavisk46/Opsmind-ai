from authlib.integrations.base_client import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.cookies import set_auth_cookies
from core.database import get_db
from core.logging import logger
from core.oauth import oauth
from services.auth_service import AuthService
from services.workspace_service import WorkspaceService

router = APIRouter(prefix="/auth", tags=["oauth"])

# Checked explicitly here (a clean 404) rather than letting an unknown
# provider fall through to Authlib and fail with a less obvious error.
_SUPPORTED_PROVIDERS = {"google", "github", "microsoft"}


class _NoVerifiedEmailError(Exception):
    """Raised only for GitHub (see _resolve_identity) — a GitHub account
    can have zero verified email addresses at all, which every other
    provider here guarantees won't happen (Google/Microsoft only ever
    return an already-verified address via OIDC)."""


def _require_supported_and_configured(provider: str) -> None:
    if provider not in _SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown sign-in provider: {provider!r}.",
        )

    client = oauth.create_client(provider)
    if client is None or not client.client_id:
        # A clear, honest 503 — not a cryptic failure deep inside Authlib
        # (e.g. an empty client_id producing a malformed authorize URL).
        # Real deployments must set {provider}_client_id/_secret (see
        # docs/oauth-setup.md); local development without them still
        # boots fine, this route just isn't usable until configured.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider.capitalize()} sign-in is not configured on this server.",
        )


@router.get("/{provider}/login")
async def oauth_login(provider: str, request: Request):
    """Redirects the browser to the provider's own consent screen.
    Authlib generates and stores a CSRF `state` (and, for OIDC providers
    like Google, a `nonce`) in the signed session cookie main.py's
    SessionMiddleware provides — verified automatically when the
    provider redirects back to the callback route below.
    """
    _require_supported_and_configured(provider)

    client = oauth.create_client(provider)
    redirect_uri = f"{settings.backend_base_url}/auth/{provider}/callback"
    return await client.authorize_redirect(request, redirect_uri)


async def _resolve_identity(provider: str, client, token: dict) -> tuple[str, str, str]:
    """Resolves (email, name, provider_account_id) for whichever provider
    just completed a login — the one place that knowledge lives, so
    AuthService.get_or_create_oauth_user() stays provider-agnostic.
    """
    if provider in ("google", "microsoft"):
        # Both are full OIDC providers registered via server_metadata_url
        # (core/oauth.py) — Authlib parses the id_token into
        # token["userinfo"] automatically for either, using the same
        # standard claims (`sub`, `email`, `name`); the explicit
        # client.userinfo() call is only a fallback in case that parsing
        # ever doesn't happen (it always has in testing against Google).
        userinfo = token.get("userinfo") or await client.userinfo(token=token)
        return userinfo["email"], userinfo.get("name") or userinfo["email"], userinfo["sub"]

    if provider == "github":
        # GitHub has no OIDC id_token at all — /user is a plain
        # authenticated REST call (core/oauth.py's api_base_url makes
        # "user" resolve to https://api.github.com/user).
        profile_response = await client.get("user", token=token)
        profile = profile_response.json()

        email = profile.get("email")
        if not email:
            # /user OMITS email entirely when the account's address is
            # private (a common GitHub default) — /user/emails (granted
            # by the "user:email" scope registered in core/oauth.py) is
            # the only way to get one at all in that case. Prefer the
            # primary verified address; fall back to any verified one.
            emails_response = await client.get("user/emails", token=token)
            emails = emails_response.json()
            chosen = next(
                (e for e in emails if e.get("primary") and e.get("verified")),
                next((e for e in emails if e.get("verified")), None),
            )
            if chosen is None:
                raise _NoVerifiedEmailError()
            email = chosen["email"]

        name = profile.get("name") or profile["login"]
        # GitHub's numeric user id, stringified — schemas/oauth_account's
        # provider_account_id column is a String for exactly this reason
        # (Google/Microsoft's `sub` is already a string; GitHub's isn't).
        return email, name, str(profile["id"])

    # Unreachable while _SUPPORTED_PROVIDERS is exactly these three —
    # present so adding a fourth provider without a matching branch here
    # fails loudly (a clear 500 in testing) instead of silently
    # mis-mapping fields.
    raise NotImplementedError(f"No identity resolution for provider: {provider!r}")


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Completes the flow: exchanges the provider's authorization code
    for a token, resolves the signed-in person's identity, finds-or-
    creates the matching local User (see AuthService.get_or_create_oauth_user),
    and issues this app's OWN session — the same access/refresh cookies
    a password login would set. The provider's token is never itself
    stored or reused past this request; once we have our own cookies,
    its job is done.

    Ends in a redirect to the FRONTEND, not a JSON response — this route
    is only ever reached via a full-page browser navigation (the
    provider's own redirect), never an XHR/fetch call a frontend script
    is waiting on.
    """
    _require_supported_and_configured(provider)
    client = oauth.create_client(provider)

    try:
        token = await client.authorize_access_token(request)
        email, name, provider_account_id = await _resolve_identity(provider, client, token)
    except OAuthError as error:
        # Verified against Authlib's documented base_client error type,
        # but not exercised against a real Google/Microsoft/GitHub app in
        # this environment (no live credentials here) — if the exact
        # exception type ever proves wrong during first real testing,
        # this is the one line to correct; nothing else in this route
        # depends on which exception class it is.
        logger.error("OAuth callback failed for provider %s: %s", provider, error)
        return RedirectResponse(f"{settings.frontend_url}/login?error=oauth_failed")
    except _NoVerifiedEmailError:
        logger.error("OAuth callback for %s found no verified email", provider)
        return RedirectResponse(f"{settings.frontend_url}/login?error=oauth_no_email")

    service = AuthService(db)
    user = await service.get_or_create_oauth_user(
        provider=provider,
        provider_account_id=provider_account_id,
        email=email,
        name=name,
    )
    # Same reasoning as the password-signup route (api/routes/users.py) —
    # a brand-new OAuth user needs a workspace to operate in too. Safe to
    # call for a RETURNING oauth user as well (ensure_personal_workspace
    # is a no-op once a default workspace already exists).
    await WorkspaceService(db).ensure_personal_workspace(user.id, user.name)
    tokens = await service.issue_token_pair(user.id)

    redirect = RedirectResponse(settings.frontend_url)
    set_auth_cookies(
        redirect, access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )
    return redirect
