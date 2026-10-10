import type { Issue } from "@shadowenglab/contracts";

/** Một đoạn của `Tip.text`: chữ thường hoặc từ được đánh dấu bằng `*từ*` (UI-SPEC marker rule). */
export type TipSegment =
  | { kind: "text"; value: string }
  | { kind: "word"; value: string; ordinal: number };

/** Một cặp `*` bao quanh một đoạn không chứa `*`; mọi thứ khác (kể cả `**`) là chữ thường. */
const MARKED_WORD = /\*([^*]+)\*/g;

/**
 * Tách `Tip.text` thành đoạn chữ và từ được đánh dấu. Chỉ trả dữ liệu thuần để UI dựng phần tử
 * React; không bao giờ sinh HTML (từ đến từ Whisper hoặc ô "Sửa câu", không tin cậy).
 */
export function splitTipMarkup(text: string): TipSegment[] {
  const segments: TipSegment[] = [];
  let cursor = 0;
  let ordinal = 0;
  for (const match of text.matchAll(MARKED_WORD)) {
    const start = match.index;
    if (start > cursor) {
      segments.push({ kind: "text", value: text.slice(cursor, start) });
    }
    segments.push({ kind: "word", value: match[1] ?? "", ordinal });
    ordinal += 1;
    cursor = start + match[0].length;
  }
  if (cursor < text.length) {
    segments.push({ kind: "text", value: text.slice(cursor) });
  }
  return segments;
}

/** Màu gạch chân của một từ được đánh dấu: bản gốc (`--original`), bạn (`--you`) hoặc trung tính. */
export type MarkedWordTone = "original" | "you" | "neutral";

/**
 * Màu gạch chân của từ đánh dấu thứ `ordinal` trong tip của mã `code` (UI-SPEC "Color").
 * Chỉ STRESS_MISMATCH có hai danh tính: backend luôn đặt từ của người học ở dấu đánh dấu thứ hai
 * (ordinal 1), mọi dấu khác là từ của bản gốc, kể cả cách nói nhắc từ gốc lần thứ hai (ordinal 2).
 * Bất biến này được test_scoring_tips.py kiểm cho mọi cách nói. Mã khác dùng màu trung tính.
 */
export function markedWordTone(
  code: Issue["code"] | undefined,
  ordinal: number,
): MarkedWordTone {
  if (code !== "STRESS_MISMATCH") return "neutral";
  return ordinal === 1 ? "you" : "original";
}
