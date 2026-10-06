import { readFileSync } from "node:fs";
import { ZodError } from "zod";
import { Schemas, type SchemaName } from "./index";

// Dùng bởi test round-trip phía Python (D-21): stdin JSON -> Schemas[name].parse -> stdout JSON.
// Thoát 2 nếu tên kiểu không có trong Schemas, 1 nếu Zod từ chối dữ liệu.

const name = process.argv[2];
if (name === undefined || !Object.hasOwn(Schemas, name)) {
  process.stderr.write(
    `Unknown contract type: ${String(name)} (expected one of ${Object.keys(Schemas).join(", ")})\n`,
  );
  process.exit(2);
}

const text = readFileSync(0, "utf-8");
try {
  const result = Schemas[name as SchemaName].parse(JSON.parse(text));
  process.stdout.write(JSON.stringify(result));
} catch (error) {
  if (error instanceof ZodError) {
    process.stderr.write(`${JSON.stringify(error.issues, null, 2)}\n`);
    process.exit(1);
  }
  throw error;
}
