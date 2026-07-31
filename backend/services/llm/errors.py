class ProviderError(Exception):
    """Base class for every typed LLM-provider failure below — lets a
    caller (api/routes/chat.py) catch `ProviderError` alone when it only
    cares "something about the provider went wrong," or one of the
    specific subclasses when it needs to react differently (e.g. a 429
    for rate limits vs. a 503 for provider-unavailable).
    """


class ProviderUnavailableError(ProviderError):
    """The provider itself refused/couldn't service the request — a bad
    API key, the provider's own account/billing issue, or any other
    provider-side rejection that isn't specifically a timeout, a rate
    limit, or a network failure. Maps to 503 Service Unavailable.
    """


class ProviderTimeoutError(ProviderError):
    """The request to the provider took too long. Maps to 504 Gateway
    Timeout — this app is the "gateway" from the caller's point of view,
    and it was ONE upstream dependency (the LLM provider) that timed out,
    not this app's own request handling.
    """


class ProviderRateLimitError(ProviderError):
    """The provider rejected the request for exceeding its own rate/usage
    limits. Maps to 429 Too Many Requests — the same status this app's
    own RateLimiter already uses for login/signup, reused here for
    consistency even though the limit being hit is the PROVIDER's, not
    this app's.
    """


class ProviderNetworkError(ProviderError):
    """A genuine network failure reaching the provider (DNS, connection
    refused, connection reset) — distinct from a timeout (the connection
    never completed at all, vs. completed but too slowly) and distinct
    from ProviderUnavailableError (the provider was never reached to
    reject anything). Maps to 502 Bad Gateway.
    """
