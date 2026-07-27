"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  forgotPassword as apiForgotPassword,
  getCurrentUser,
  getGithubLoginUrl,
  getGoogleLoginUrl,
  getMicrosoftLoginUrl,
  login as apiLogin,
  logout as apiLogout,
  resendOtp as apiResendOtp,
  resendVerificationEmail as apiResendVerificationEmail,
  resetPassword as apiResetPassword,
  signup as apiSignup,
  verifyEmail as apiVerifyEmail,
  verifyOtp as apiVerifyOtp,
  type ResetPasswordInput,
  type SignupInput,
} from "@/components/Auth/auth-api";
import { GUEST_AUTH_TOKEN, GUEST_USER } from "@/components/Auth/guest-mode";
import {
  AUTHENTICATED_SESSION_MARKER,
  clearSessionCookie,
  getSessionCookie,
  setSessionCookie,
} from "@/components/Auth/session-cookie";
import type { AuthCredentials, AuthUser } from "@/components/Auth/types";
import { apiClient, normalizeError } from "@/lib/api";
import { clearAuthToken, setAuthToken } from "@/lib/api/token";
import { isDev } from "@/lib/env";
import { logger } from "@/lib/logger";

// Dev-only convenience so the dashboard is reachable without manually
// signing in on every fresh browser session — reuses the same demo account
// documented on the login page. Never runs in production; proxy.ts's route
// protection is untouched and behaves identically either way.
const DEV_AUTO_LOGIN_CREDENTIALS: AuthCredentials = {
  email: "ava@opsmind.ai",
  password: "Password123!",
};

export type { AuthCredentials, AuthUser } from "@/components/Auth/types";
export type {
  ResetPasswordInput,
  SignupInput,
} from "@/components/Auth/auth-api";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface LoginResult {
  outcome: "authenticated" | "otpRequired" | "emailVerificationRequired";
  email: string;
}

export interface AuthContextValue {
  user: AuthUser | null;
  status: AuthStatus;
  // True only for the frontend-only Portfolio Demo Mode session (see
  // guest-mode.ts) — never set for a real, backend-authenticated user.
  isGuest: boolean;
  login: (credentials: AuthCredentials) => Promise<LoginResult>;
  // Navigates the browser to each provider's own consent screen — see
  // auth-api.ts's getGoogleLoginUrl()/getGithubLoginUrl()/
  // getMicrosoftLoginUrl(). Not async/no return value: this is a
  // full-page navigation away from this app, not a fetch() this
  // component could await a result from; the OAuth callback route
  // (backend) redirects back here once it's done, and the session-
  // restore effect below picks the resulting cookies up on that fresh
  // page load.
  loginWithGoogle: () => void;
  loginWithGithub: () => void;
  loginWithMicrosoft: () => void;
  // Grants the same "authenticated" state as a real login, via the same
  // session cookie and token slots, without calling the backend at all —
  // there's no account to look up, so this bypasses POST /auth/login
  // entirely rather than requiring a fake account server-side.
  loginAsGuest: () => Promise<void>;
  logout: () => Promise<void>;
  signup: (input: SignupInput) => Promise<void>;
  forgotPassword: (email: string) => Promise<{ resetToken: string }>;
  resetPassword: (input: ResetPasswordInput) => Promise<void>;
  verifyOtp: (input: { email: string; code: string }) => Promise<void>;
  resendOtp: (email: string) => Promise<void>;
  verifyEmail: (email: string) => Promise<void>;
  resendVerificationEmail: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

// Real backend integration point — connects to the FastAPI backend via
// apiClient (src/lib/api), never a hardcoded URL (see
// NEXT_PUBLIC_API_URL in src/lib/api/index.ts). The shape of this
// context is what every consumer (LoginForm, SignupForm, RequireAuth,
// ...) depends on; it hasn't changed, only what happens inside each
// callback has.
//
// Session restoration: the real session lives entirely in httpOnly
// cookies the BACKEND sets (see backend/core/cookies.py) — this app has
// no token of its own to read across a reload anymore, only a
// GET /users/me ("whoami") call below to ask the backend whether the
// browser's cookies still represent a valid session. Separately, every
// path that establishes a session (login() and this file's restore
// effect) also sets session-cookie.ts's marker on THIS app's own
// domain — required for proxy.ts's route protection to recognize the
// session at all, since the real cookies above live on the backend's
// different origin and are invisible to this app's own server. See
// session-cookie.ts's doc comment for the full explanation.
export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<AuthUser | null>(null);
  // Starts "loading", not "unauthenticated" — RequireAuth.tsx already
  // renders a full-screen loading fallback for any status other than
  // "authenticated" without redirecting, so this was already the
  // correct initial value for a status that has to be checked
  // asynchronously; it just wasn't wired up to anything until now.
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [isGuest, setIsGuest] = useState(false);

  const login = useCallback(
    async (credentials: AuthCredentials): Promise<LoginResult> => {
      // POST /auth/login sets the REAL httpOnly session cookies directly
      // on its own response (see auth-api.ts's login() doc comment) —
      // this app's JS never sees or manages that token itself. But those
      // cookies live on the BACKEND's own origin (Render), a different
      // domain than this frontend (Vercel) — proxy.ts, which protects
      // routes on THIS domain, can never see them directly (see
      // session-cookie.ts's doc comment for the full explanation).
      // setSessionCookie() here sets the marker proxy.ts actually checks,
      // on the frontend's own domain, so the very next navigation (e.g.
      // this function's caller pushing to "/") correctly recognizes the
      // session that was JUST established instead of bouncing it back to
      // /login.
      const result = await apiLogin(credentials);

      setSessionCookie(AUTHENTICATED_SESSION_MARKER);
      setUser(result.user);
      setStatus("authenticated");
      setIsGuest(false);
      return { outcome: "authenticated", email: result.user.email };
    },
    []
  );

  const loginWithGoogle = useCallback(() => {
    window.location.href = getGoogleLoginUrl();
  }, []);

  const loginWithGithub = useCallback(() => {
    window.location.href = getGithubLoginUrl();
  }, []);

  const loginWithMicrosoft = useCallback(() => {
    window.location.href = getMicrosoftLoginUrl();
  }, []);

  // Deliberately not async work beyond satisfying the `Promise<void>`
  // shape the rest of AuthContextValue uses — kept a Promise so a future
  // real backend (e.g. a scoped, rate-limited guest token endpoint) can
  // slot in behind this same signature without changing any caller.
  const loginAsGuest = useCallback(async () => {
    setAuthToken(GUEST_AUTH_TOKEN);
    setSessionCookie(GUEST_AUTH_TOKEN);
    setUser(GUEST_USER);
    setStatus("authenticated");
    setIsGuest(true);
  }, []);

  // Session restoration on refresh — runs once, on mount, before the
  // dev-auto-login effect below. Guest mode is checked first via
  // session-cookie.ts's marker (its only remaining job — see that file's
  // updated doc comment) since it's a purely frontend identity with no
  // backend session to restore. Otherwise, this calls GET /users/me
  // directly with no token of its own to read or check first: the real
  // access-token cookie is httpOnly, genuinely invisible to this code,
  // and that's the point. If it's expired, apiClient's own silent-
  // refresh-and-retry (src/lib/api/client.ts) transparently exchanges it
  // for a new one via the refresh-token cookie before this call would
  // even see a failure — this effect only ever observes the FINAL
  // outcome, success or a real, unrecoverable 401.
  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      if (getSessionCookie() === GUEST_AUTH_TOKEN) {
        if (cancelled) return;
        setAuthToken(GUEST_AUTH_TOKEN);
        setUser(GUEST_USER);
        setStatus("authenticated");
        setIsGuest(true);
        return;
      }

      try {
        const restoredUser = await getCurrentUser();
        if (cancelled) return;
        // Sets (or re-affirms) proxy.ts's marker now that a real session
        // is confirmed. This matters most right after an OAuth login:
        // the backend's callback redirects the browser to this app's
        // ROOT ("/"), a request proxy.ts sees BEFORE any of this app's
        // JS has run — with no marker cookie yet, that very first
        // request gets bounced to /login purely because nothing had a
        // chance to set one yet. Setting it here, the moment this effect
        // confirms the session is real, is what the pathname check right
        // below uses to escape that one-time bounce.
        setSessionCookie(AUTHENTICATED_SESSION_MARKER);
        setUser(restoredUser);
        setStatus("authenticated");
        setIsGuest(false);
        // Setting the cookie above doesn't retroactively re-run
        // proxy.ts's redirect for the CURRENT page — without this, an
        // OAuth login (or any case where proxy.ts bounced a request that
        // arrived before the marker existed) would leave a genuinely
        // authenticated user stuck looking at the login page. Same
        // pattern the dev-auto-login effect below already uses.
        if (pathname === "/login") {
          router.replace("/");
        }
      } catch {
        // No session, an expired refresh token, or the backend was
        // unreachable — either way, fail closed: land on
        // "unauthenticated" rather than a half-authenticated state.
        if (cancelled) return;
        setStatus("unauthenticated");
      }
    }

    void restoreSession();
    return () => {
      cancelled = true;
    };
    // Mount-once, deliberately: this must run exactly once per page load,
    // not re-run on every client-side navigation. pathname/router are
    // read for the one-time /login escape hatch above, not to react to
    // navigation — same reasoning as the dev-auto-login effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!isDev) {
      return;
    }
    // login()'s setState calls happen inside its async body, after
    // `await mockLogin(...)` resolves — not synchronously within this
    // effect — but the lint rule can't see through the Promise chain to
    // confirm that statically. Pre-existing dev-only convenience effect;
    // not restructured here since that's out of scope for Demo Mode.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    login(DEV_AUTO_LOGIN_CREDENTIALS)
      .then(() => {
        logger.info(
          "Dev auto-login: signed in as the demo account (ava@opsmind.ai) — disabled in production builds."
        );
        // Setting the session cookie client-side doesn't retroactively
        // re-run proxy.ts's redirect — without this, a developer who was
        // bounced to /login would get signed in in the background but stay
        // stuck looking at the login form.
        if (pathname === "/login") {
          router.replace("/");
        }
      })
      .catch(() => {
        // Best-effort convenience only — if it fails for any reason, the
        // developer just sees the normal login page and can sign in by hand.
      });
    // Mount-once: this must not re-fire if a developer logs out to test that
    // flow within the same page session (only a hard refresh should retry).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const logout = useCallback(async () => {
    // POST /auth/logout revokes the refresh token server-side and clears
    // both cookies via its own response — a REAL logout, not just this
    // tab forgetting a token. Best-effort: called for guest sessions too
    // (harmless — the route is idempotent with no cookie present at
    // all), and a network failure here shouldn't trap the user in a
    // "logged in" state they have no way to escape from locally.
    try {
      await apiLogout();
    } catch (error) {
      logger.error("Logout request failed", normalizeError(error));
    }
    clearAuthToken();
    clearSessionCookie();
    setUser(null);
    setStatus("unauthenticated");
    setIsGuest(false);
  }, []);

  // Wires apiClient's existing (previously unused) onUnauthorized hook —
  // fires whenever ANY request gets a 401 after retries/interceptors,
  // e.g. a token that expires mid-session — so the app correctly falls
  // back to "unauthenticated" everywhere, not just after an explicit
  // logout() call. `logout` is a stable useCallback (empty deps), so
  // this effect registers the handler exactly once.
  useEffect(() => {
    apiClient.onUnauthorized(() => {
      void logout();
    });
  }, [logout]);

  const signup = useCallback(async (input: SignupInput) => {
    await apiSignup(input);
  }, []);

  const forgotPassword = useCallback(async (email: string) => {
    return apiForgotPassword(email);
  }, []);

  const resetPassword = useCallback(async (input: ResetPasswordInput) => {
    await apiResetPassword(input);
  }, []);

  // No backend OTP endpoint exists (see auth-api.ts) — apiVerifyOtp()
  // always throws, so nothing after that call ever runs. Left as a
  // plain await (not restructured away) so VerifyOtpForm.tsx's existing
  // try/catch keeps receiving a real Error with a clear message, exactly
  // like every other TODO-stubbed function here.
  const verifyOtp = useCallback(
    async (input: { email: string; code: string }) => {
      await apiVerifyOtp(input);
    },
    []
  );

  const resendOtp = useCallback(async (email: string) => {
    await apiResendOtp(email);
  }, []);

  const verifyEmail = useCallback(async (email: string) => {
    await apiVerifyEmail(email);
  }, []);

  const resendVerificationEmail = useCallback(async (email: string) => {
    await apiResendVerificationEmail(email);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      isGuest,
      login,
      loginWithGoogle,
      loginWithGithub,
      loginWithMicrosoft,
      loginAsGuest,
      logout,
      signup,
      forgotPassword,
      resetPassword,
      verifyOtp,
      resendOtp,
      verifyEmail,
      resendVerificationEmail,
    }),
    [
      user,
      status,
      isGuest,
      login,
      loginWithGoogle,
      loginWithGithub,
      loginWithMicrosoft,
      loginAsGuest,
      logout,
      signup,
      forgotPassword,
      resetPassword,
      verifyOtp,
      resendOtp,
      verifyEmail,
      resendVerificationEmail,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
