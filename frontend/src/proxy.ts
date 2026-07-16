import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE_NAME } from "@/components/Auth/session-cookie";

// Placeholder route protection: checks for the mock session cookie set by
// AuthProvider (see components/Auth/session-cookie.ts). A real
// implementation would verify a signed session/JWT here instead of just
// checking for presence.
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
