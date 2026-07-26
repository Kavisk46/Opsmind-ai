// Canonical shapes shared between AuthProvider.tsx (the public useAuth() API)
// and auth-api.ts (the real backend layer) — kept here so neither file has
// to redeclare the other's types.
export interface AuthUser {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
}

export interface AuthCredentials {
  email: string;
  password: string;
}
