import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE_NAME } from "@/components/Auth/session-cookie";

// Route protection: checks for the session marker cookie AuthProvider.tsx
// sets on THIS app's own domain, for both real and guest sessions (see
// components/Auth/session-cookie.ts's doc comment for exactly why this
// indirection is required — the real session cookies live on the
// backend's own, different origin and are never visible here directly).
// Deliberately presence-only, not JWT verification: the real security
// boundary is the backend's get_current_user dependency, which verifies
// a signed token on every API call regardless of what this middleware
// decides — this layer only ever controls which PAGE gets served, never
// which data a request can read.
const AUTH_PATHS = [
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
  "/verify-otp",
  "/verify-email",
];

// Only these two make no sense to show once a session already exists.
// Forgot Password / Reset Password / OTP / Email Verification stay
// reachable regardless of session state (e.g. a reset-link click while an
// old session lingers shouldn't get silently bounced to the dashboard).
const GUEST_ONLY_PATHS = ["/login", "/signup"];

function matchesPath(paths: string[], pathname: string): boolean {
  return paths.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`)
  );
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has(SESSION_COOKIE_NAME);

  if (!hasSession && !matchesPath(AUTH_PATHS, pathname)) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (hasSession && matchesPath(GUEST_ONLY_PATHS, pathname)) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|opengraph-image|twitter-image).*)",
  ],
};
