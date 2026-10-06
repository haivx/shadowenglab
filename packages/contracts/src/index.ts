import { Lesson, Segment } from "./lesson";

export * from "./common";
export * from "./lesson";

/** Các kiểu được xuất ra JSON Schema bundle (01-05 mở rộng thành đủ sáu kiểu FND-02). */
export const Schemas = { Segment, Lesson } as const;
export type SchemaName = keyof typeof Schemas;
