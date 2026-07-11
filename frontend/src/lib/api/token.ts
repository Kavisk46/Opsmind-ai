// In-memory only — never localStorage/sessionStorage. A token readable by
// `window.localStorage` is readable by any injected script (XSS); keeping it
// in a module-scoped variable means it only ever lives in this JS realm and
// is naturally cleared on full page reload.
let authToken: string | null = null;

export function getAuthToken(): string | null {
  return authToken;
}

export function setAuthToken(token: string): void {
  authToken = token;
}

export function clearAuthToken(): void {
  authToken = null;
}
