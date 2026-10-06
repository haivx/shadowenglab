import { Lesson, Segment } from "./lesson";
import { IssueCode, ScoreResult } from "./score";

export * from "./common";
export * from "./lesson";
export * from "./score";

/** Các kiểu được xuất ra JSON Schema bundle (task 2 mở rộng thành đủ sáu kiểu FND-02). */
export const Schemas = { Segment, Lesson, ScoreResult, IssueCode } as const;
export type SchemaName = keyof typeof Schemas;
