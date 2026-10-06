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

export type WordFlags = z.infer<typeof WordFlags>;
export type Label = z.infer<typeof Label>;
export type ClipWord = z.infer<typeof ClipWord>;
export type ClipManifest = z.infer<typeof ClipManifest>;
