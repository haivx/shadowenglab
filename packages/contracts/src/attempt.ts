import * as z from "zod";
import { Milliseconds } from "./common";

/**
 * Phản hồi sau khi tải một lượt ghi âm lên (D-06; Phase 2, chưa chấm điểm).
 * `attempt` đếm mọi lượt tải lên theo (bài, câu), bắt đầu từ 1.
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
