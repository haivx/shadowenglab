import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const WEB_ROOT = join(import.meta.dirname, "..");
const REPO_ROOT = join(WEB_ROOT, "..", "..");

/** Bản đồ `--name: value` trong một file CSS, bỏ comment và khoảng trắng thừa. */
function parseCustomProperties(css: string): Map<string, string> {
  const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const map = new Map<string, string>();
  for (const match of withoutComments.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    const [, name, value] = match;
    if (name && value) map.set(name, value.replace(/\s+/g, " ").trim());
  }
  return map;
}

function read(...segments: string[]): string {
  return readFileSync(join(...segments), "utf8");
}

describe("design tokens", () => {
  it("apps/web/app/tokens.css declares the same variables and values as docs/design/tokens.css", () => {
    const source = parseCustomProperties(
      read(REPO_ROOT, "docs", "design", "tokens.css"),
    );
    const synced = parseCustomProperties(read(WEB_ROOT, "app", "tokens.css"));

    expect(source.size).toBeGreaterThan(50);
    expect(Object.fromEntries(synced)).toEqual(Object.fromEntries(source));
  });

  it("tailwind.config.ts maps colours to var() without an hsl() wrapper", () => {
    const config = read(WEB_ROOT, "tailwind.config.ts");

    expect(config).toContain("var(--original)");
    expect(config).toContain("var(--you)");
    expect(config).toContain("var(--recording)");
    expect(config).not.toContain("hsl(var(");
  });
});
