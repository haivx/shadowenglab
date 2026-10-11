import * as z from "zod";
import { IsoTimestamp, Milliseconds, Score01 } from "./common";

/** Cờ lỗi của một từ do người chấm gắn; chỉ lưu từ có cờ (D-16). */
export const WordFlags = z
  .object({
    wordIndex: z.number().int().min(0),
    flags: z.array(z.enum(["sound", "stress", "pitch", "pause", "speed"])),
  })
  .meta({ id: "WordFlags" });

/** Nhãn của người chấm cho một clip (D-16). `wordIndex` khớp ClipManifest.words[].i. */
export const Label = z
  .object({
    clipId: z.string(),
    raterId: z.string(),
    overall: z.union([
      z.literal(1),
      z.literal(2),
      z.literal(3),
      z.literal(4),
      z.literal(5),
    ]),
    wordFlags: z.array(WordFlags),
    finalContourMatch: z.boolean(),
    unsure: z.boolean(),
    note: z.string().optional(),
    durationMs: Milliseconds,
    createdAt: IsoTimestamp,
  })
  .meta({ id: "Label" });

export const ClipWord = z
  .object({ i: z.number().int().min(0), text: z.string() })
  .meta({ id: "ClipWord" });

/** Manifest một clip cho app eval (D-17). */
export const ClipManifest = z
  .object({
    clipId: z.string(),
    videoId: z.string(),
    sentenceText: z.string(),
    words: z.array(ClipWord),
    refAudio: z.string(),
    userAudio: z.string(),
    gold: z.enum(["none", "identical", "wrong"]).default("none"),
    systemScore: Score01.optional(),
  })
  .meta({ id: "ClipManifest" });

/**
 * Cách Liam cố ý nói sai khi tạo bộ lỗi eval; tách khỏi IssueCode (D-03).
 * Thứ tự cố định theo D-03. `weak_form` và `final_drop` thuộc Lớp A (Phase 5, D-07):
 * mọi issue Lớp C trên các case này là dương tính giả.
 */
export const ErrorType = z
  .enum([
    "wrong_stress",
    "flat",
    "extra_pause",
    "final_rise",
    "pitch_off",
    "weak_form",
    "final_drop",
  ])
  .meta({ id: "ErrorType" });

/** Lỗi có thật Liam nghe thấy ngoài kịch bản; issue khớp nó là trung tính, không TP cũng không FP (D-09). */
export const EvalAlsoPresent = z
  .object({
    errorType: ErrorType,
    wordIndex: z.number().int().min(0).optional(),
  })
  .meta({ id: "EvalAlsoPresent" });

/**
 * Một dòng của `eval/cases.jsonl` — nhãn do Liam viết cho một câu của một bài (D-02).
 *
 * Dấu nhận diện câu (D-05): `segStartMs`, `segEndMs`, `segEndExtraMs`
 * (round(giây × 1000) của segment lúc viết case) và `segTextHash` (16 ký tự hex đầu
 * của sha256(text UTF-8)). Lệch bất kỳ trường nào → script eval báo lỗi, thoát 2 (A6).
 *
 * `split` vắng mặt = chưa chốt (A4); `analyze.py` và `sweep.py` thoát 2 khi còn case thiếu split.
 * `clip` là stem `{lessonId}_{NNNN}_{AA}` do `tag_clips.py tag` điền.
 *
 * Bất biến kiểm ở Python (`eval/evalkit/cases.py`), không dùng refine Zod vì refine không sinh sang JSON Schema (A5):
 * - kind `error` ⇔ có `errorType`; `correct` ⇒ không `errorType`, không `wordIndex`.
 * - errorType theo từ (`wrong_stress`, `extra_pause`, `pitch_off`, `weak_form`, `final_drop`) bắt buộc `wordIndex`;
 *   mức câu (`flat`, `final_rise`) không có `wordIndex`.
 * - `caseId` duy nhất; `clip` duy nhất; `wordIndex` < số từ của câu; câu có ≥ STRESS_MIN_WORDS (5) từ (D-11).
 * Trường optional là vắng mặt, không bao giờ null.
 */
export const EvalCase = z
  .object({
    caseId: z.string().min(1),
    lessonId: z.string(),
    segmentIndex: z.number().int().min(0),
    segStartMs: Milliseconds,
    segEndMs: Milliseconds,
    segEndExtraMs: Milliseconds,
    segTextHash: z.string().length(16),
    kind: z.enum(["error", "correct"]),
    errorType: ErrorType.optional(),
    wordIndex: z.number().int().min(0).optional(),
    alsoPresent: z.array(EvalAlsoPresent).optional(),
    split: z.enum(["tuning", "heldout"]).optional(),
    clip: z.string().optional(),
    note: z.string().optional(),
  })
  .meta({ id: "EvalCase" });

export type WordFlags = z.infer<typeof WordFlags>;
export type Label = z.infer<typeof Label>;
export type ClipWord = z.infer<typeof ClipWord>;
export type ClipManifest = z.infer<typeof ClipManifest>;
export type ErrorType = z.infer<typeof ErrorType>;
export type EvalAlsoPresent = z.infer<typeof EvalAlsoPresent>;
export type EvalCase = z.infer<typeof EvalCase>;
