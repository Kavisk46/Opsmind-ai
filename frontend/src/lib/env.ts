export const isBrowser = typeof window !== "undefined";
export const isServer = !isBrowser;

export const isDev = process.env.NODE_ENV === "development";
export const isProd = process.env.NODE_ENV === "production";

// Next.js inlines NEXT_PUBLIC_* vars into the CLIENT bundle by doing a
// purely textual, static replacement of literal `process.env.NEXT_PUBLIC_X`
// expressions at build time — it does not evaluate JS to find them.
// Verified directly against this project's installed Next version's own
// docs (node_modules/next/dist/docs/01-app/02-guides/environment-variables.md):
// "dynamic lookups will NOT be inlined, such as: `process.env[varName]`".
//
// This is exactly the shape a `getEnvVar(key: string)` helper that does
// `process.env[key]` internally has — invisible to that static pass, so
// in the browser it ALWAYS evaluates to undefined regardless of what's
// set in Vercel/Render/anywhere else, silently falling through to
// `fallback` on every load. (Server-side code isn't affected — Node's
// real `process.env` supports dynamic keys just fine — which is exactly
// why this bug is invisible unless you inspect the actual client bundle.)
//
// The fix: every caller passes the value it already accessed via a
// LITERAL `process.env.NEXT_PUBLIC_X` expression — statically analyzable,
// so Next's compiler can find and inline it — plus the var's name only
// for the error message. This function never touches `process.env` itself.
export function getEnvVar(
  value: string | undefined,
  fallback: string | undefined,
  name: string
): string {
  const resolved = value ?? fallback;

  if (resolved === undefined) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return resolved;
}
