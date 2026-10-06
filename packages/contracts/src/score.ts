import * as z from "zod";
import { Milliseconds, Score01, Seconds } from "./common";

/** 7 mã lỗi Lớp C (D-12). Export riêng để UI/template/LLM dùng chung một danh sách. */
export const IssueCode = z
  .enum([
    "STRESS_MISMATCH",
    "EXTRA_PAUSE",
    "FINAL_CONTOUR",
    "FLAT_PITCH",
    "PITCH_DEVIATION",
    "PHONE",
    "WORD_MISSING",
  ])
  .meta({ id: "IssueCode" });

// Dữ liệu riêng của từng mã (D-12). Mỗi object có id để codegen không sinh tên Data1, Data2...

export const StressMismatchData = z
  .object({ refWord: z.string(), userWord: z.string() })
  .meta({ id: "StressMismatchData" });

export const ExtraPauseData = z
  .object({ refMs: Milliseconds, userMs: Milliseconds })
  .meta({ id: "ExtraPauseData" });

export const FinalContourData = z
  .object({ refSlope: z.number(), userSlope: z.number() })
  .meta({ id: "FinalContourData" });

export const FlatPitchData = z
  .object({ pitchRange: Score01 })
  .meta({ id: "FlatPitchData" });

export const PitchDeviationData = z
  .object({ meanDiffSt: z.number() })
  .meta({ id: "PitchDeviationData" });

export const PhoneData = z
  .object({
    refPhones: z.string(),
    userPhones: z.string(),
    similarity: Score01,
  })
  .meta({ id: "PhoneData" });

export const WordMissingData = z.object({}).meta({ id: "WordMissingData" });

// `wordIndex` là chỉ số trong `ScoreResult.words` (cùng phạm vi với Word.i, 01-01 mục 4).
const WordIndex = z.number().int().min(0);

export const StressMismatchIssue = z
  .object({
    code: z.literal("STRESS_MISMATCH"),
    wordIndex: WordIndex,
    data: StressMismatchData,
  })
  .meta({ id: "StressMismatchIssue" });

export const ExtraPauseIssue = z
  .object({
    code: z.literal("EXTRA_PAUSE"),
    wordIndex: WordIndex,
    data: ExtraPauseData,
  })
  .meta({ id: "ExtraPauseIssue" });

export const FinalContourIssue = z
  .object({ code: z.literal("FINAL_CONTOUR"), data: FinalContourData })
  .meta({ id: "FinalContourIssue" });

export const FlatPitchIssue = z
  .object({ code: z.literal("FLAT_PITCH"), data: FlatPitchData })
  .meta({ id: "FlatPitchIssue" });

export const PitchDeviationIssue = z
  .object({
    code: z.literal("PITCH_DEVIATION"),
    wordIndex: WordIndex,
    data: PitchDeviationData,
  })
  .meta({ id: "PitchDeviationIssue" });

export const PhoneIssue = z
  .object({
    code: z.literal("PHONE"),
    wordIndex: WordIndex,
    data: PhoneData,
  })
  .meta({ id: "PhoneIssue" });

export const WordMissingIssue = z
  .object({
    code: z.literal("WORD_MISSING"),
    wordIndex: WordIndex,
    data: WordMissingData,
  })
  .meta({ id: "WordMissingIssue" });

export const Issue = z
  .discriminatedUnion("code", [
    StressMismatchIssue,
    ExtraPauseIssue,
    FinalContourIssue,
    FlatPitchIssue,
    PitchDeviationIssue,
    PhoneIssue,
    WordMissingIssue,
  ])
  .meta({ id: "Issue" });

/** Điểm từng từ (D-11). start/end là giây trên audio người học. Màu chip suy từ similarity. */
export const WordScore = z
  .object({
    text: z.string(),
    status: z.enum(["scored", "missing", "ref_unclear"]),
    similarity: Score01,
    start: Seconds,
    end: Seconds,
    refPhones: z.string().optional(),
    userPhones: z.string().optional(),
  })
  .meta({ id: "WordScore" });

/** Đường cao độ cả câu trên trục chuẩn hoá chung; null = frame không hữu thanh (D-13). */
export const Contour = z
  .object({
    ref: z.array(z.number().nullable()),
    user: z.array(z.number().nullable()),
    wordBounds: z.array(z.number().int().min(0)),
  })
  .meta({ id: "Contour" });

export const StressEntry = z
  .object({ word: z.string(), ref: z.number(), user: z.number() })
  .meta({ id: "StressEntry" });

export const PauseEntry = z
  .object({
    afterWord: z.number().int().min(0),
    refMs: Milliseconds,
    userMs: Milliseconds,
  })
  .meta({ id: "PauseEntry" });

export const Prosody = z
  .object({
    speed: Score01,
    pitchRange: Score01,
    melodyMatch: Score01,
    contour: Contour,
    stress: z.array(StressEntry),
    pauses: z.array(PauseEntry),
  })
  .meta({ id: "Prosody" });

/** Khối điểm tổng (D-10). sound null ở P2–P3 hoặc khi cả câu ref_unclear. */
export const Scores = z
  .object({
    overall: Score01,
    sound: Score01.nullable(),
    intonation: Score01,
    rhythm: Score01,
  })
  .meta({ id: "Scores" });

/** Gợi ý (D-14). issueRef là chỉ số trong ScoreResult.issues. */
export const Tip = z
  .object({
    text: z.string(),
    issueRef: z.number().int().min(0),
    source: z.enum(["template", "llm"]),
  })
  .meta({ id: "Tip" });

export const Versions = z
  .object({ scorer: z.string(), thresholds: z.string() })
  .meta({ id: "Versions" });

/** Kết quả một lượt chấm (D-10..D-15). */
export const ScoreResult = z
  .object({
    lessonId: z.string(),
    segmentIndex: z.number().int().min(0),
    attempt: z.number().int().min(1),
    mode: z.enum(["full", "intonationOnly"]),
    versions: Versions,
    timingMs: z.record(z.string(), z.number().min(0)),
    scores: Scores,
    words: z.array(WordScore),
    prosody: Prosody,
    issues: z.array(Issue),
    tips: z.array(Tip),
  })
  .meta({ id: "ScoreResult" });

export type IssueCode = z.infer<typeof IssueCode>;
export type Issue = z.infer<typeof Issue>;
export type WordScore = z.infer<typeof WordScore>;
export type Contour = z.infer<typeof Contour>;
export type Prosody = z.infer<typeof Prosody>;
export type Scores = z.infer<typeof Scores>;
export type Tip = z.infer<typeof Tip>;
export type Versions = z.infer<typeof Versions>;
export type ScoreResult = z.infer<typeof ScoreResult>;
