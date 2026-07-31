import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// resolve.tsconfigPaths reads tsconfig.json's own "@/*": ["./src/*"]
// mapping directly, rather than duplicating that alias a second time
// here where it could drift out of sync with the real one Next.js/
// TypeScript use.
export default defineConfig({
  plugins: [react()],
  resolve: {
    tsconfigPaths: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    css: true,
  },
});
