// ESLint 9 flat config. Không dùng @next/eslint-plugin-next (crash với ESLint 9, Pitfall 2).
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import prettier from "eslint-config-prettier";

export default tseslint.config(
  {
    ignores: [
      "**/.next/**",
      "**/node_modules/**",
      "**/dist/**",
      "packages/contracts/schema/**",
      "services/**",
      "docs/**",
      ".planning/**",
      ".claude/**",
      "**/next-env.d.ts",
    ],
  },
  ...tseslint.configs.strict,
  {
    files: ["apps/**/*.{ts,tsx}"],
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
  // CLAUDE.md: TypeScript strict, không `any`.
  { rules: { "@typescript-eslint/no-explicit-any": "error" } },
  prettier,
);
