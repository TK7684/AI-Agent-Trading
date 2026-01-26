import { defineConfig } from "vitest/config";
import tsConfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  test: {
    environment: "node",
    include: ["server/**/*.test.ts", "server/**/*.spec.ts", "server/__tests__/**/*.test.ts"],
  },
  resolve: {
    plugins: [tsConfigPaths()],
  },
});
