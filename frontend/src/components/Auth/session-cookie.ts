// Two jobs: (1) a client-visible marker so proxy.ts (route protection)
// has something to check for — it only checks PRESENCE
// (request.cookies.has(...)), never the value, so nothing there needed
// to change — and (2), since this integration, the ACTUAL carrier for
// the real JWT across a page refresh. lib/api/token.ts's in-memory
// `authToken` is wiped on every reload by design (documented there as
// an XSS mitigation: never put a token somewhere `window.localStorage`
// or an injected script can trivially read); this cookie is what
// AuthProvider.tsx reads on mount to rehydrate that in-memory value via
// getSessionCookie() below.
//
// Honest security note, not glossed over: a plain (non-httpOnly) cookie
// set from client-side JS, as this is, has the SAME XSS-readability
// exposure as localStorage would — document.cookie is just as reachable
// by an injected script. The properly-hardened version of this would
// have the BACKEND set an httpOnly cookie directly on POST /auth/login,
// which this integration doesn't do because the backend currently
// returns the token in a JSON body only, and changing that is a backend
// change outside this integration's scope. This is a deliberate,
// documented trade-off, not an oversight.
export const SESSION_COOKIE_NAME = "opsmind_session";

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
