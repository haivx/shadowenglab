// Mức màu của điểm (docs/design/tokens.md, UI-SPEC "Color"). Mọi màu điểm đi qua đây.
// Màu theo SỐ NGUYÊN ĐANG HIỂN THỊ: 0.796 hiện `80` nên xanh; 0.594 hiện `59` nên đỏ.

export type ScoreLevel = "good" | "ok" | "bad" | "unrated";

/** Số nguyên 0..100 hiển thị cho một điểm 0..1 (không có dấu %). */
export function scorePercent(score01: number): number {
  return Math.round(score01 * 100);
}

/** đỏ < 60, vàng 60–79, xanh ≥ 80; null (chưa chấm) = unrated. */
export function scoreLevel(score01: number | null): ScoreLevel {
  if (score01 === null) return "unrated";
  const percent = scorePercent(score01);
  if (percent >= 80) return "good";
  if (percent >= 60) return "ok";
  return "bad";
}

// Tra cứu literal để JIT của Tailwind thấy đủ class; không bao giờ ghép tên class động.
export const SCORE_TEXT_CLASS: Record<ScoreLevel, string> = {
  good: "text-score-good-text",
  ok: "text-score-ok-text",
  bad: "text-score-bad-text",
  unrated: "text-score-unrated-text",
};

export const SCORE_FILL_CLASS: Record<ScoreLevel, string> = {
  good: "bg-score-good",
  ok: "bg-score-ok",
  bad: "bg-score-bad",
  unrated: "bg-score-unrated",
};
