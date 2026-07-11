"use client";

import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
}

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface AuthContextValue {
  user: AuthUser | null;
  status: AuthStatus;
  login: (credentials: AuthCredentials) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

// Placeholder boundary: swap login/logout + initial status for real auth (NextAuth/Clerk/JWT) without touching useAuth() consumers.
export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("unauthenticated");

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      login: async () => {
        throw new Error("AuthProvider.login is not implemented yet.");
      },
      logout: async () => {
        setUser(null);
        setStatus("unauthenticated");
      },
    }),
    [user, status]
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
