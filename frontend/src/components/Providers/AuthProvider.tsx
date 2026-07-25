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
  login as apiLogin,
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
  clearSessionCookie,
  getSessionCookie,
  setSessionCookie,
} from "@/components/Auth/session-cookie";
import type { AuthCredentials, AuthUser } from "@/components/Auth/types";
import { apiClient } from "@/lib/api";
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
// Session restoration: the in-memory token (lib/api/token.ts) is wiped
// on every reload by design — session-cookie.ts's cookie is what
// survives a reload and is used below to rehydrate it via a real
// GET /users/me ("whoami") call, exactly as this file used to note as
// the eventual real-backend behavior.
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
      const result = await apiLogin(credentials);

      setAuthToken(result.token);
      setSessionCookie(result.token);
      setUser(result.user);
      setStatus("authenticated");
      setIsGuest(false);
      return { outcome: "authenticated", email: result.user.email };
    },
    []
  );

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
  // dev-auto-login effect below. Reads whatever token session-cookie.ts
  // persisted across the reload (real user or guest) and rehydrates
  // this component's in-memory state from it.
  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      const token = getSessionCookie();

      if (!token) {
        if (!cancelled) setStatus("unauthenticated");
        return;
      }

      // Guest mode's token never was, and never will be, a real JWT —
      // checked first so restoring it doesn't waste a doomed API call
      // against GET /users/me. Guest mode's own definition (guest-mode.ts)
      // is untouched; this just correctly re-enters it after a refresh,
      // which the in-memory-only mock could never do at all.
      if (token === GUEST_AUTH_TOKEN) {
        if (cancelled) return;
        setAuthToken(GUEST_AUTH_TOKEN);
        setUser(GUEST_USER);
        setStatus("authenticated");
        setIsGuest(true);
        return;
      }

      try {
        setAuthToken(token);
        const restoredUser = await getCurrentUser();
        if (cancelled) return;
        setUser(restoredUser);
        setStatus("authenticated");
        setIsGuest(false);
      } catch {
        // Expired/invalid token, or the backend was unreachable —
        // either way, fail closed: clear everything and land on
        // "unauthenticated" rather than a half-authenticated state.
        if (cancelled) return;
        clearAuthToken();
        clearSessionCookie();
        setStatus("unauthenticated");
      }
    }

    void restoreSession();
    return () => {
      cancelled = true;
    };
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
