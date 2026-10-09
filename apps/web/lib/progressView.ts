import type { LessonProgress } from "@shadowenglab/contracts";

// RED stub: chữ ký đã có, hành vi chưa hiện thực.
export type ScoreCell =
  | { kind: "score"; text: string; className: string }
  | { kind: "dot" }
  | { kind: "empty" };

export function bestBySegment(
  _progress: LessonProgress | undefined,
): ReadonlyMap<number, number> {
  return new Map();
}

export function transcriptScoreCell(
  _best: number | undefined,
  _practiced: boolean,
): ScoreCell {
  return { kind: "empty" };
}
