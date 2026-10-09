import type { Issue, WordScore } from "@shadowenglab/contracts";

/** Chỉ số từ (trong `ScoreResult.words`) cần tô khi một gợi ý được hover / focus. */
export interface TipHighlight {
  /** Từ của bản gốc (teal) — chỉ STRESS_MISMATCH. */
  ref: number[];
  /** Từ bạn đã nhấn thay vào (cam) — chỉ STRESS_MISMATCH. */
  you: number[];
  /** Từ trung tính (xám) cho mọi mã khác. */
  neutral: number[];
}

export const EMPTY_HIGHLIGHT: TipHighlight = { ref: [], you: [], neutral: [] };

export function tipHighlight(
  _issue: Issue,
  _words: Pick<WordScore, "text">[],
): TipHighlight {
  return EMPTY_HIGHLIGHT;
}
