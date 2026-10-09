import type { AttemptSummary, ScoreResult } from "@shadowenglab/contracts";
import { scorePercent } from "./scoreLevel";

/** Một chip của AttemptStrip: một lượt đã chấm (UI-SPEC "AttemptStrip", D-11). */
export interface AttemptChip {
  /** Số `attempt` thật của server (khoá để lấy kết quả đã lưu). */
  attempt: number;
  /** Thứ tự k trong các lượt đã chấm (1, 2, 3…), không phải số `attempt` thô. */
  ordinal: number;
  overall: number;
  /** `Lượt {k} · {điểm}`; điểm không tô màu. */
  label: string;
  /** Điểm cao nhất (hoà thì lượt sau); chỉ đặt khi có từ 2 lượt đã chấm. */
  isBest: boolean;
}

/** Tối đa 6 chip (UI-SPEC overflow): 5 lượt gần nhất cộng lượt tốt nhất nếu nó cũ hơn. */
export const MAX_ATTEMPT_CHIPS = 6;

/**
 * Chip của một câu từ danh sách server hợp với kết quả nhận trong phiên (theo số `attempt`;
 * bản trong phiên thắng). Danh sách chưa tải / lỗi thì chỉ còn kết quả phiên (E5 loading/error).
 * Số thứ tự tính trên mọi lượt đã chấm rồi mới cắt, nên nhãn không đổi khi chip bị ẩn.
 */
export function attemptChips(
  list: AttemptSummary[] | undefined,
  session: ScoreResult[],
  max: number = MAX_ATTEMPT_CHIPS,
): AttemptChip[] {
  const overallByAttempt = new Map<number, number>();
  for (const item of list ?? [])
    overallByAttempt.set(item.attempt, item.overall);
  for (const result of session) {
    overallByAttempt.set(result.attempt, result.scores.overall);
  }

  const ascending = [...overallByAttempt.entries()].sort((a, b) => a[0] - b[0]);
  if (ascending.length === 0) return [];

  // `>=` để hoà điểm thì lượt sau thắng (D-11).
  let bestAttempt = -1;
  let bestOverall = -Infinity;
  for (const [attempt, overall] of ascending) {
    if (overall >= bestOverall) {
      bestAttempt = attempt;
      bestOverall = overall;
    }
  }
  const markBest = ascending.length >= 2;

  const all: AttemptChip[] = ascending.map(([attempt, overall], position) => ({
    attempt,
    ordinal: position + 1,
    overall,
    label: `Lượt ${position + 1} · ${scorePercent(overall)}`,
    isBest: markBest && attempt === bestAttempt,
  }));

  if (all.length <= max) return all;
  const recent = all.slice(-max);
  if (recent.some((chip) => chip.attempt === bestAttempt)) return recent;
  const best = all.find((chip) => chip.attempt === bestAttempt);
  return best ? [best, ...all.slice(-(max - 1))] : recent;
}
