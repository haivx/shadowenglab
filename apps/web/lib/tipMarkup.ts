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
