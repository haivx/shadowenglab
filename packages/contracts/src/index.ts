import {
  ApiError,
  CreateLessonRequest,
  LessonListItem,
  LessonProgress,
  UpdateSegmentTextRequest,
  VideoPreview,
} from "./api";
import { AttemptAck, AttemptSummary } from "./attempt";
import { ClipManifest, ErrorType, EvalCase, Label } from "./eval";
import { Lesson, Segment } from "./lesson";
import { IssueCode, ScoreResult } from "./score";
import {
  AppSettings,
  OpenAiKeyCheckRequest,
  OpenAiKeyCheckResult,
  SystemStatus,
} from "./settings";

export * from "./api";
export * from "./attempt";
export * from "./common";
export * from "./eval";
export * from "./lesson";
export * from "./score";
export * from "./settings";

/**
 * Các kiểu I/O được xuất ra JSON Schema bundle và dùng bởi cli-parse.
 * Sáu kiểu đầu là FND-02 (Phase 1); mười một kiểu sau là contract Phase 2 (02-01);
 * AttemptSummary là phần thêm của Phase 3 (03-01).
 * ErrorType, EvalCase là phần thêm của Phase 4 (04-01).
 */
export const Schemas = {
  Segment,
  Lesson,
  ScoreResult,
  IssueCode,
  ClipManifest,
  Label,
  ErrorType,
  EvalCase,
  AttemptAck,
  AttemptSummary,
  AppSettings,
  VideoPreview,
  CreateLessonRequest,
  LessonListItem,
  LessonProgress,
  SystemStatus,
  OpenAiKeyCheckRequest,
  OpenAiKeyCheckResult,
  UpdateSegmentTextRequest,
  ApiError,
} as const;
export type SchemaName = keyof typeof Schemas;
