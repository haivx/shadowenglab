// Khung rỗng cho pha RED: hàm tồn tại nhưng chưa có hành vi.
export type ResultNote = { kind: "praise" | "neutral"; text: string };

export function resultNote(
  overall: number,
  tipCount: number,
): ResultNote | null {
  void overall;
  void tipCount;
  return null;
}

export function wordsMatchSegment(
  words: ReadonlyArray<{ text: string }>,
  text: string,
): boolean {
  void words;
  void text;
  return false;
}
