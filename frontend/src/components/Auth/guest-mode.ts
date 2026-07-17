import type { AuthUser } from "./types";

// Defines what "being a guest" means across the app — AuthProvider sets
// this user/token when entering Portfolio Demo Mode, UserProfileDropdown
// reads the role label to display in place of an email, and DemoModeBanner
// keys off AuthProvider's `isGuest` flag (not this file directly). Kept
// separate from auth-mock-api.ts since a guest is never looked up from the
// mock user list — it's a fixed, frontend-only identity, not an account.
export const GUEST_USER: AuthUser = {
  id: "guest",
  name: "Guest User",
  email: "guest@opsmind.ai",
};

export const GUEST_ROLE_LABEL = "Portfolio Viewer";

// Not a real credential — occupies the same in-memory-only slot as a
// genuine mock token (see lib/api/token.ts), just a distinguishable value
// for debugging/log output.
export const GUEST_AUTH_TOKEN = "guest-demo-session";
