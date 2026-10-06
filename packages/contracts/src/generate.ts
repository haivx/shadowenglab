import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import * as z from "zod";
import { Schemas } from "./index";

const outDir = process.argv[2] ?? "schema";

// io: "input" giữ field có default là optional (Pitfall 8).
// Không bật `reused: "ref"` (sinh def ẩn danh __schemaN, tên class pydantic không ổn định).
const wrapper = z.toJSONSchema(z.object(Schemas), { io: "input" }) as {
  $schema: string;
  $defs?: Record<string, unknown>;
};

const defs = wrapper.$defs ?? {};
const anonymous = Object.keys(defs).filter((key) => key.startsWith("__schema"));
if (anonymous.length > 0) {
  throw new Error(`Anonymous $defs generated: ${anonymous.join(", ")}`);
}
const missing = Object.keys(Schemas).filter((key) => !(key in defs));
if (missing.length > 0) {
  throw new Error(
    `Missing $defs for: ${missing.join(", ")} (thiếu .meta({ id }))`,
  );
}

mkdirSync(outDir, { recursive: true });
writeFileSync(
  join(outDir, "contracts.schema.json"),
  JSON.stringify({ $schema: wrapper.$schema, $defs: defs }, null, 2) + "\n",
);
