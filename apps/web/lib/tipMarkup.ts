/** Một đoạn của `Tip.text`: chữ thường hoặc từ được đánh dấu bằng `*từ*` (UI-SPEC marker rule). */
export type TipSegment =
  | { kind: "text"; value: string }
  | { kind: "word"; value: string; ordinal: number };

export function splitTipMarkup(text: string): TipSegment[] {
  return [{ kind: "text", value: text }];
}
