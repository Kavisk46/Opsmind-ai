export const isBrowser = typeof window !== "undefined";
export const isServer = !isBrowser;

export const isDev = process.env.NODE_ENV === "development";
export const isProd = process.env.NODE_ENV === "production";

// Client-side code can only read `process.env` keys prefixed `NEXT_PUBLIC_`
// (Next.js inlines those at build time; anything else is undefined in the browser).
export function getEnvVar(key: string, fallback?: string): string {
  const value = process.env[key] ?? fallback;

  if (value === undefined) {
    throw new Error(`Missing required environment variable: ${key}`);
  }

  return value;
}
