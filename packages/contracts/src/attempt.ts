import * as z from "zod";
import { Milliseconds, Score01 } from "./common";

/**
 * Phản hồi sau khi tải một lượt ghi âm lên (D-06; Phase 2, chưa chấm điểm).
 * `attempt` đếm mọi lượt tải lên theo (bài, câu), bắt đầu từ 1.
 * Chỉ còn dùng cho PUT …/attempts/{n}/eval-clip (D-09); POST trả ScoreResult.
 */
export const AttemptAck = z
  .object({
    lessonId: z.string(),
    segmentIndex: z.number().int().min(0),
    attempt: z.number().int().min(1),
    durationMs: Milliseconds,
    voiced: z.boolean(),
    savedForEval: z.boolean(),
  })
  .meta({ id: "AttemptAck" });

export type AttemptAck = z.infer<typeof AttemptAck>;

/**
 * Một dòng trong danh sách lượt đã chấm của một câu (D-11):
 * GET /lessons/{id}/segments/{index}/attempts. Chỉ lượt có điểm, `attempt`
 * tăng dần; `createdAt` là ISO-8601 UTC ("…Z").
 */
export const AttemptSummary = z
  .object({
    attempt: z.number().int().min(1),
    overall: Score01,
    createdAt: z.string(),
  })
  .meta({ id: "AttemptSummary" });

export type AttemptSummary = z.infer<typeof AttemptSummary>;
