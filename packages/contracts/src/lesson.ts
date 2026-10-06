import * as z from "zod";
import { IsoTimestamp, Milliseconds, Probability, Seconds } from "./common";

/**
 * Từ trong một câu (D-04).
 * `i` là chỉ số của từ TRONG segment chứa nó, bắt đầu từ 0 (quyết định 01-01 mục 4).
 */
export const Word = z
  .object({
    i: z.number().int().min(0),
    text: z.string(),
    start: Seconds,
    end: Seconds,
    asrProb: Probability,
    ipa: z.string().optional(),
    refConfidence: Probability.optional(),
    prominence: z.number().optional(),
  })
  .meta({ id: "Word" });

/** Segment giữ mốc gốc chưa đệm (D-05). */
export const Segment = z
  .object({
    index: z.number().int().min(0),
    text: z.string(),
    start: Seconds,
    end: Seconds,
    endExtraMs: Milliseconds.default(0),
    words: z.array(Word),
    translation: z.string().optional(),
  })
  .meta({ id: "Segment" });

export const TimeRange = z
  .object({ start: Seconds, end: Seconds })
  .meta({ id: "TimeRange" });

export const AudioQuality = z
  .object({
    label: z.enum(["clean", "music"]),
    nonVocalRatio: z.number().min(0),
  })
  .meta({ id: "AudioQuality" });

export const LessonError = z
  .object({ step: z.string(), message: z.string() })
  .meta({ id: "LessonError" });

/** Trạng thái job nằm trong Lesson (D-06). Không có meta id: inline thành Literal. */
export const LessonStatus = z.enum([
  "queued",
  "downloading",
  "separating",
  "transcribing",
  "segmenting",
  "analyzing",
  "ready",
  "failed",
]);

export const Lesson = z
  .object({
    id: z.string(), // ulid
    videoId: z.string(),
    title: z.string(),
    durationSec: Seconds,
    thumbnailUrl: z.string().optional(),
    range: TimeRange,
    padMs: Milliseconds.default(150),
    status: LessonStatus,
    error: LessonError.optional(),
    audioQuality: AudioQuality.optional(),
    segments: z.array(Segment),
    createdAt: IsoTimestamp,
  })
  .meta({ id: "Lesson" });

export type Word = z.infer<typeof Word>;
export type Segment = z.infer<typeof Segment>;
export type TimeRange = z.infer<typeof TimeRange>;
export type AudioQuality = z.infer<typeof AudioQuality>;
export type LessonError = z.infer<typeof LessonError>;
export type LessonStatus = z.infer<typeof LessonStatus>;
export type Lesson = z.infer<typeof Lesson>;
