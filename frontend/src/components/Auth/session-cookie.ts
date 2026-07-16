// Purely a client-visible marker so middleware.ts (the route-protection
// placeholder) has something to check for — NOT a real session token; the
// actual mock auth token stays in-memory via lib/api/token.ts. A real
// implementation would replace this with a signed, httpOnly cookie issued
// by the server.
export const SESSION_COOKIE_NAME = "opsmind_session";

export function setSessionCookie(): void {
  document.cookie = `${SESSION_COOKIE_NAME}=1; path=/; max-age=${60 * 60 * 24}`;
}

export function clearSessionCookie(): void {
  document.cookie = `${SESSION_COOKIE_NAME}=; path=/; max-age=0`;
}
