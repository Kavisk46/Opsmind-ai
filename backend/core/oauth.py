from authlib.integrations.starlette_client import OAuth

from core.config import settings

# One shared registry, not one client object per provider built ad hoc in
# each route — this is what lets api/routes/oauth.py's login/callback
# routes be written ONCE, parameterized by provider name, rather than
# duplicated per provider (see that file's `oauth.create_client(provider)`
# call). Registering a client here only requires it have real credentials
# configured; Google is registered unconditionally below because Authlib
# resolves its endpoints from the well-known OIDC discovery document
# rather than hardcoded URLs, and registering with an empty client_id is
# harmless until someone actually starts the login flow (see
# api/routes/oauth.py's explicit "not configured" check, which is what
# produces a clear error instead of a confusing failure deep inside
# Authlib).
oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Microsoft is also full OIDC — same shape as Google, just a
# tenant-scoped discovery URL ("common" accepts both personal and
# work/school accounts; see core/config.py's microsoft_tenant_id).
oauth.register(
    name="microsoft",
    client_id=settings.microsoft_client_id,
    client_secret=settings.microsoft_client_secret,
    server_metadata_url=(
        f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}"
        "/v2.0/.well-known/openid-configuration"
    ),
    client_kwargs={"scope": "openid email profile"},
)

# GitHub predates OIDC and has no discovery document at all — its
# endpoints are hardcoded here instead of a server_metadata_url, and
# api/routes/oauth.py fetches its userinfo with a plain authenticated
# GET (client.get("user", token=token)) rather than the OIDC-standard
# `token["userinfo"]`/`client.userinfo()` Google and Microsoft both
# populate automatically. "user:email" is requested specifically because
# GitHub's /user response omits email entirely when a user has made
# theirs private — see api/routes/oauth.py's fallback to /user/emails.
oauth.register(
    name="github",
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user user:email"},
)
