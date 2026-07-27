// A client-visible marker so proxy.ts (route protection) has something
// to check for on the FRONTEND's own domain — it only checks PRESENCE
// (request.cookies.has(...)), never the value, so nothing there needs to
// change based on what this file stores.
//
// Why this has to exist AT ALL post-OAuth-migration: the real session
// lives entirely in httpOnly `access_token`/`refresh_token` cookies the
// BACKEND sets (see backend/core/cookies.py) — but those are scoped to
// the BACKEND's own origin (Render), a genuinely different domain than
// this frontend (Vercel). A cookie set by one origin is never sent to,
// or visible from, a different origin's server — that's the browser's
// own same-origin cookie jar, not something any code here controls. So
// proxy.ts, which only ever sees cookies sent to THIS app's domain, can
// never directly check the real session cookies no matter what name it
// looks for. This marker is the bridge: AuthProvider.tsx sets it, on
// THIS domain, once it has confirmed (via a real `GET /users/me` call)
// that a real session exists — real or guest, this is the ONLY thing
// proxy.ts ever checks.
//
// This was previously narrowed to guest-mode-only during the OAuth
// migration (a real regression — see AuthProvider.tsx's login()/session-
// restore effect for the fix): once nothing called setSessionCookie()
// for a real login anymore, proxy.ts could never recognize a real,
// successfully-authenticated user, and bounced them straight back to
// /login. Restoring it as a marker BOTH paths set fixes that without
// changing proxy.ts's own logic at all — presence-only checking was
// never a real security boundary (that's `get_current_user` on the
// backend, verifying a signed JWT) and still isn't; this file has never
// stored anything an XSS payload could use for anything real.
export const SESSION_COOKIE_NAME = "opsmind_session";

// The value real (non-guest) sessions store — distinguishable from
// GUEST_AUTH_TOKEN (guest-mode.ts) so AuthProvider's session-restore
// effect knows which branch to take, but otherwise not a secret: proxy.ts
// never inspects it, only whether the cookie is present at all.
export const AUTHENTICATED_SESSION_MARKER = "authenticated";

export function setSessionCookie(token: string): void {
  document.cookie = `${SESSION_COOKIE_NAME}=${encodeURIComponent(token)}; path=/; max-age=${60 * 60 * 24}`;
}

export function getSessionCookie(): string | null {
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${SESSION_COOKIE_NAME}=([^;]*)`)
  );
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

export function clearSessionCookie(): void {
  document.cookie = `${SESSION_COOKIE_NAME}=; path=/; max-age=0`;
}
