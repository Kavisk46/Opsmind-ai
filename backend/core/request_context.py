import contextvars

# ContextVars, not a plain module-level variable: a normal global would
# be shared/overwritten across concurrently-in-flight requests (this app
# is async — many requests are genuinely interleaved on one event loop).
# A ContextVar gives each async task its own isolated value, automatically
# propagated into whatever that request's code awaits, without threading
# a "request_id" parameter through every function call in the codebase.
_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
_user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)


def get_request_id() -> str | None:
    return _request_id_var.get()


def set_user_id(user_id: str) -> None:
    _user_id_var.set(user_id)


def get_user_id() -> str | None:
    return _user_id_var.get()
