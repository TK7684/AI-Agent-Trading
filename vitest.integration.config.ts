import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  root: path.resolve(import.meta.dirname),
  test: {
    environment: "node",
    include: ["server/**/*.integration.test.ts", "server/**/*.integration.spec.ts"],
    globals: true,
    setupFiles: ["./test-utils/setup.ts"],
    testTimeout: 30000,
  },
});