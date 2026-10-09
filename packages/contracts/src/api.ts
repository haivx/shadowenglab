import * as z from "zod";
import { Score01, Seconds } from "./common";
import { Lesson } from "./lesson";

/** Mã lỗi API (D-22). Không có meta id: inline thành Literal. */
export const ApiErrorCode = z.enum([
  "invalid_request",
  "invalid_url",
  "channel_url",
  "video_unavailable",
  "live_video",
  "invalid_range",
  "duplicate_lesson",
  "not_found",
  "invalid_state",
  "invalid_segment",
  "unsupported_media",
  "payload_too_large",
  "recording_too_long",
  "no_speech",
  "busy",
  "no_openai_key",
  "upstream_error",
  "network_error",
  "invalid_settings",
  "forbidden_origin",
  "internal_error",
]);

/**
 * Phong bì lỗi. `message` là câu tiếng Việt cho người dùng, không bao giờ chứa
 * đường dẫn hay stack trace. `lessonId` chỉ đi kèm `duplicate_lesson`.
 */
export const ApiError = z
  .object({
    code: ApiErrorCode,
    message: z.string(),
    lessonId: z.string().optional(),
  })
  .meta({ id: "ApiError" });

export const VideoPreview = z
  .object({
    videoId: z.string(),
    title: z.string(),
    durationSec: Seconds,
    channel: z.string().optional(),
    thumbnailUrl: z.string().optional(),
    existingLessonId: z.string().optional(),
  })
  .meta({ id: "VideoPreview" });

export const CreateLessonRequest = z
  .object({
    url: z.string(),
    start: Seconds.optional(),
    end: Seconds.optional(),
  })
  .meta({ id: "CreateLessonRequest" });

/** Lesson không có `segments` (id riêng để tên pydantic ổn định). */
export const LessonSummary = Lesson.omit({ segments: true }).meta({
  id: "LessonSummary",
});

/** Phần tử của GET /lessons: payload nhẹ, không kèm segments. */
export const LessonListItem = z
  .object({
    lesson: LessonSummary,
    segmentCount: z.number().int().min(0),
    practicedCount: z.number().int().min(0),
    /** null = mọi câu đã tập. */
    firstUnpracticedIndex: z.number().int().min(0).nullable(),
  })
  .meta({ id: "LessonListItem" });

export const SegmentProgress = z
  .object({
    segmentIndex: z.number().int().min(0),
    /** Mọi lượt tải lên. */
    attempts: z.number().int().min(0),
    /** "Đã tập" = voicedAttempts >= 1 (D-08). */
    voicedAttempts: z.number().int().min(0),
    /**
     * Điểm tốt nhất của câu. Có mặt cùng `bestAttempt` khi câu có ≥ 1 lượt đã
     * chấm; tốt nhất = overall cao nhất, hoà lấy lượt sau (D-11). Optional,
     * không bao giờ null.
     */
    bestOverall: Score01.optional(),
    /** Số thứ tự lượt đạt `bestOverall` (cùng điều kiện có mặt). */
    bestAttempt: z.number().int().min(1).optional(),
  })
  .meta({ id: "SegmentProgress" });

export const LessonProgress = z
  .object({
    lessonId: z.string(),
    /** Chỉ những câu có ít nhất một lượt. */
    segments: z.array(SegmentProgress),
    firstUnpracticedIndex: z.number().int().min(0).nullable(),
  })
  .meta({ id: "LessonProgress" });

export const UpdateSegmentTextRequest = z
  .object({ text: z.string().trim().min(1).max(500) })
  .meta({ id: "UpdateSegmentTextRequest" });

export type ApiErrorCode = z.infer<typeof ApiErrorCode>;
export type ApiError = z.infer<typeof ApiError>;
export type VideoPreview = z.infer<typeof VideoPreview>;
export type CreateLessonRequest = z.infer<typeof CreateLessonRequest>;
export type LessonSummary = z.infer<typeof LessonSummary>;
export type LessonListItem = z.infer<typeof LessonListItem>;
export type SegmentProgress = z.infer<typeof SegmentProgress>;
export type LessonProgress = z.infer<typeof LessonProgress>;
export type UpdateSegmentTextRequest = z.infer<typeof UpdateSegmentTextRequest>;
