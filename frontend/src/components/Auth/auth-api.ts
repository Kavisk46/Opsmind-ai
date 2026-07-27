import { apiClient } from "@/lib/api";

import type { AuthCredentials, AuthUser } from "./types";

// Wire shapes the backend actually returns — verified directly against
// backend/schemas/auth.py and backend/schemas/user.py before writing
// this file, never guessed. Kept as separate, minimal interfaces here
// (not shared with the backend repo) since this is the ONE place in the
// frontend that needs to know the raw wire format; everything else in
// this app works with the app-level `AuthUser` shape below.
interface TokenResponse {
  access_token: string;
  token_type: string;
}

interface UserResponse {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

function toAuthUser(user: UserResponse): AuthUser {
  // Backend's UserResponse has no avatarUrl field at all — omitted
  // (AuthUser.avatarUrl is optional), not defaulted to null/undefined
  // explicitly, so this stays a straightforward, honest mapping rather
  // than inventing a value the backend never sent.
  return { id: user.id, name: user.name, email: user.email };
}

// --- Real endpoints (verified present: api/routes/auth.py, api/routes/users.py) ---

export interface LoginApiResult {
  // A union of one, deliberately — not a bare object. LoginForm.tsx's
  // existing `result.outcome === "otpRequired"` / `"emailVerificationRequired"`
  // branches (written against the mock, which had all three outcomes)
  // keep compiling and behaving correctly UNCHANGED: the real backend
  // has no OTP or email-verification concept at all (verified — see
  // auth.py/users.py), so those branches simply never match anymore.
  // This is what lets LoginForm.tsx require zero changes.
  outcome: "authenticated";
  user: AuthUser;
}

export async function login({
  email,
  password,
}: AuthCredentials): Promise<LoginApiResult> {
  // POST /auth/login sets the access/refresh tokens as httpOnly cookies
  // directly on this response (see backend/core/cookies.py) — the
  // browser stores them automatically because apiClient's fetch calls
  // use credentials: "include" (src/lib/api/client.ts); there is
  // nothing for this app's JS to read or store itself, which is the
  // whole point of httpOnly (a script — including an XSS payload —
  // cannot read these cookies, unlike the old in-memory-token/session-
  // cookie approach this replaced). The response body's access_token
  // field is deliberately ignored here.
  await apiClient.post<TokenResponse>("/auth/login", { email, password });
  const user = await getCurrentUser();

  return { outcome: "authenticated", user };
}

// POST /auth/logout — revokes the refresh token server-side (a REAL
// logout, not just "the client forgot its token") and clears both
// cookies via this response's Set-Cookie headers.
export async function logout(): Promise<void> {
  await apiClient.post<void>("/auth/logout");
}

// Full-page-navigation URLs for "Continue with ..." — deliberately NOT
// apiClient calls: these routes (backend/api/routes/oauth.py) redirect
// the BROWSER itself to each provider's consent screen, which only makes
// sense as a real navigation (`window.location.href = ...`), never a
// fetch()/XHR request.
export function getGoogleLoginUrl(): string {
  return apiClient.getBaseUrl() + "/auth/google/login";
}

export function getGithubLoginUrl(): string {
  return apiClient.getBaseUrl() + "/auth/github/login";
}

export function getMicrosoftLoginUrl(): string {
  return apiClient.getBaseUrl() + "/auth/microsoft/login";
}

export interface SignupInput {
  name: string;
  email: string;
  password: string;
}

export async function signup({
  name,
  email,
  password,
}: SignupInput): Promise<AuthUser> {
  // POST /users creates an ALREADY-ACTIVE account — there is no email-
  // verification step on the backend (verified: models/user.py has no
  // such flag, api/routes/users.py's create_user has no such branch).
  // Deliberately does NOT log the new user in (no setAuthToken() here)
  // — the mock didn't either, and SignupForm.tsx's existing redirect to
  // /verify-email is left completely alone per this integration's scope
  // ("do not change routes"). The practical effect: a real signup lands
  // on a verification page the backend doesn't need — the account is
  // already usable via /login immediately. See AuthProvider.tsx's
  // verifyEmail()/resendVerificationEmail() for how that page's actions
  // are handled honestly (a clear TODO, not a silent fake success).
  const user = await apiClient.post<UserResponse>("/users", {
    name,
    email,
    password,
  });
  return toAuthUser(user);
}

// GET /users/me — used both by login() above (to fetch the profile the
// login endpoint itself doesn't return) and by AuthProvider's session-
// restoration-on-refresh check (a 401 here means an expired/invalid
// stored token; the caller is responsible for clearing session state).
export async function getCurrentUser(): Promise<AuthUser> {
  const user = await apiClient.get<UserResponse>("/users/me");
  return toAuthUser(user);
}

// --- Everything below: NO corresponding backend endpoint exists. -----
// Verified directly by reading every route file in api/routes/ — only
// POST /auth/login, POST /users, and GET /users/me exist. There is no
// OTP endpoint, no email-verification endpoint, and no password-reset
// endpoint anywhere in this backend. Per this integration's explicit
// instructions, each is left as a clearly-marked TODO rather than
// guessed at or silently faked: every function below throws a real,
// user-facing Error instead of pretending to succeed. That error
// surfaces automatically through the SAME getAuthErrorMessage() /
// AuthErrorMessage pipeline every auth form already uses (see
// get-auth-error-message.ts) — no component changes needed for the
// message to display correctly.
//
// TODO(backend): implement real endpoints for these, then delete
// `notImplemented()` and the functions that call it. Plausible names,
// matching this project's existing REST conventions (POST /auth/login
// style) — NOT implemented anywhere today, named here only as a
// starting suggestion for whoever builds them:
//   POST /auth/forgot-password, POST /auth/reset-password,
//   POST /auth/verify-otp, POST /auth/resend-otp,
//   POST /users/verify-email, POST /users/resend-verification.

function notImplemented(action: string): never {
  throw new Error(
    `${action} isn't available yet — the backend has no matching endpoint. ` +
      "Your account is already fully active; try signing in directly."
  );
}

export interface ResetPasswordInput {
  email: string;
  token: string;
  password: string;
}

export async function forgotPassword(
  _email: string
): Promise<{ resetToken: string }> {
  return notImplemented("Password reset");
}

export async function resetPassword(
  _input: ResetPasswordInput
): Promise<void> {
  return notImplemented("Password reset");
}

export async function verifyOtp(_input: {
  email: string;
  code: string;
}): Promise<AuthUser> {
  return notImplemented("OTP verification");
}

export async function resendOtp(_email: string): Promise<void> {
  return notImplemented("OTP verification");
}

export async function verifyEmail(_email: string): Promise<void> {
  return notImplemented("Email verification");
}

export async function resendVerificationEmail(
  _email: string
): Promise<void> {
  return notImplemented("Email verification");
}
