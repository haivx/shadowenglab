import { ClipManifest, Label } from "./eval";
import { Lesson, Segment } from "./lesson";
import { IssueCode, ScoreResult } from "./score";

export * from "./common";
export * from "./eval";
export * from "./lesson";
export * from "./score";

/** Sáu kiểu FND-02 được xuất ra JSON Schema bundle và dùng bởi cli-parse. */
export const Schemas = {
  Segment,
  Lesson,
  ScoreResult,
  IssueCode,
  ClipManifest,
  Label,
} as const;
export type SchemaName = keyof typeof Schemas;
