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
  mockForgotPassword,
  mockLogin,
  mockResendOtp,
  mockResendVerificationEmail,
  mockResetPassword,
  mockSignup,
  mockVerifyEmail,
  mockVerifyOtp,
  type ResetPasswordInput,
  type SignupInput,
} from "@/components/Auth/auth-mock-api";
import {
  clearSessionCookie,
  setSessionCookie,
} from "@/components/Auth/session-cookie";
import type { AuthCredentials, AuthUser } from "@/components/Auth/types";
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
} from "@/components/Auth/auth-mock-api";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface LoginResult {
  outcome: "authenticated" | "otpRequired" | "emailVerificationRequired";
  email: string;
}

export interface AuthContextValue {
  user: AuthUser | null;
  status: AuthStatus;
  login: (credentials: AuthCredentials) => Promise<LoginResult>;
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

// Placeholder boundary: swap the mock calls below for real auth
// (NextAuth/Clerk/JWT) without touching useAuth() consumers — the shape of
// this context is the actual integration point, not an implementation detail.
// Known mock limitation: state is in-memory only, so a hard refresh resets
// `status` to "unauthenticated" even though middleware.ts's session cookie
// (and thus route access) persists — a real backend would rehydrate this
// via a "whoami" call on mount instead.
export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("unauthenticated");

  const login = useCallback(
    async (credentials: AuthCredentials): Promise<LoginResult> => {
      const result = await mockLogin(credentials);

      if (result.outcome !== "authenticated") {
        return { outcome: result.outcome, email: result.user.email };
      }

      setAuthToken(`mock-token-${result.user.id}`);
      setSessionCookie();
      setUser(result.user);
      setStatus("authenticated");
      return { outcome: "authenticated", email: result.user.email };
    },
    []
  );

  useEffect(() => {
    if (!isDev) {
      return;
    }
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
  }, []);

  const signup = useCallback(async (input: SignupInput) => {
    await mockSignup(input);
  }, []);

  const forgotPassword = useCallback(async (email: string) => {
    return mockForgotPassword(email);
  }, []);

  const resetPassword = useCallback(async (input: ResetPasswordInput) => {
    await mockResetPassword(input);
  }, []);

  const verifyOtp = useCallback(
    async (input: { email: string; code: string }) => {
      const authenticatedUser = await mockVerifyOtp(input);
      setAuthToken(`mock-token-${authenticatedUser.id}`);
      setSessionCookie();
      setUser(authenticatedUser);
      setStatus("authenticated");
    },
    []
  );

  const resendOtp = useCallback(async (email: string) => {
    await mockResendOtp(email);
  }, []);

  const verifyEmail = useCallback(async (email: string) => {
    await mockVerifyEmail(email);
  }, []);

  const resendVerificationEmail = useCallback(async (email: string) => {
    await mockResendVerificationEmail(email);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      login,
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
      login,
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
