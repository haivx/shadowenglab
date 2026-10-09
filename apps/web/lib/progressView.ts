import type { LessonProgress } from "@shadowenglab/contracts";
import {
  SCORE_FILL_CLASS,
  SCORE_TEXT_CLASS,
  scoreLevel,
  scorePercent,
} from "./scoreLevel";

/** Ô điểm bên phải một hàng của TranscriptList (UI-SPEC E6). */
export type ScoreCell =
  | { kind: "score"; text: string; className: string }
  | { kind: "dot" }
  | { kind: "empty" };

/**
 * Điểm tốt nhất theo câu (`bestOverall`, D-11). Chỉ câu có ≥ 1 lượt đã chấm mới có mặt;
 * câu chỉ có lượt chưa chấm (P1 hoặc no_speech) không vào map.
 */
export function bestBySegment(
  progress: LessonProgress | undefined,
): ReadonlyMap<number, number> {
  const best = new Map<number, number>();
  for (const item of progress?.segments ?? []) {
    if (item.bestOverall !== undefined) {
      best.set(item.segmentIndex, item.bestOverall);
    }
  }
  return best;
}

/** Có điểm -> số + màu theo scoreLevel; chỉ đã tập (chưa chấm) -> chấm xám P1; còn lại trống. */
export function transcriptScoreCell(
  best: number | undefined,
  practiced: boolean,
): ScoreCell {
  if (best !== undefined) {
    return {
      kind: "score",
      text: String(scorePercent(best)),
      className: SCORE_TEXT_CLASS[scoreLevel(best)],
    };
  }
  return practiced ? { kind: "dot" } : { kind: "empty" };
}

export interface SegmentFillInput {
  index: number;
  /** Chỉ số (từ 0) của câu đang tập. */
  current: number;
  /** bestOverall của câu, undefined nếu chưa có lượt đã chấm. */
  best: number | undefined;
  /** Câu đã tập (voicedAttempts >= 1). */
  practiced: boolean;
}

/**
 * Màu một đoạn của SegmentedProgress: hiện tại `--foreground` (bất kể điểm), có điểm thì
 * `--score-{level}` của lượt tốt nhất (D-11), đã tập chưa chấm `--muted-foreground`, còn lại slate-4.
 */
export function segmentFillClass({
  index,
  current,
  best,
  practiced,
}: SegmentFillInput): string {
  if (index === current) return "bg-foreground";
  if (best !== undefined) return SCORE_FILL_CLASS[scoreLevel(best)];
  return practiced ? "bg-muted-foreground" : "bg-[color:var(--slate-4)]";
}
