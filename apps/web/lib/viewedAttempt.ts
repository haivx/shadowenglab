// Lượt đang xem của một câu (UI-SPEC "AttemptStrip", "Past-attempt result", D-11, FBK-06).
// Hàm thuần: không React, DOM hay mạng. PracticeRoom giữ state bằng `useReducer(nextViewedAttempt)`.
import type { ScoreResult } from "@shadowenglab/contracts";
import type { AttemptChip } from "./attemptChips";

export type ViewedEvent =
  | { type: "sentenceChanged"; chips: AttemptChip[] }
  | { type: "chipsLoaded"; chips: AttemptChip[] }
  | { type: "scored"; attempt: number }
  | { type: "selected"; attempt: number };

/** Nguồn của kết quả đang xem: trong phiên, đã lưu trên server (phải tải), hoặc chưa có. */
export type ViewedResult =
  | { kind: "none" }
  | { kind: "session"; result: ScoreResult; ordinal: number }
  | { kind: "stored"; attempt: number; ordinal: number };

/** Lượt mới nhất = `attempt` lớn nhất; không phải chip đầu (có thể là lượt tốt nhất cũ hơn). */
function latestAttempt(chips: AttemptChip[]): number | null {
  let latest: number | null = null;
  for (const chip of chips) {
    if (latest === null || chip.attempt > latest) latest = chip.attempt;
  }
  return latest;
}

/**
 * Chuyển câu về lượt chấm mới nhất của câu đó (hoặc không có); danh sách tải xong chỉ điền khi chưa
 * chọn gì nên không đè lượt người dùng đã bấm; lượt vừa chấm (R) và chip được bấm trở thành lượt đang xem.
 */
export function nextViewedAttempt(
  current: number | null,
  event: ViewedEvent,
): number | null {
  switch (event.type) {
    case "sentenceChanged":
      return latestAttempt(event.chips);
    case "chipsLoaded":
      return current ?? latestAttempt(event.chips);
    case "scored":
    case "selected":
      return event.attempt;
  }
}

/**
 * Chỉ lượt có chip mới xem được nên nhãn `Lượt k` luôn là thứ tự của chip. Có kết quả trong phiên
 * thì dùng chính nó; ngược lại phải lấy bản đã lưu (D-11).
 */
export function resolveViewedResult(
  viewedAttempt: number | null,
  session: ScoreResult[],
  chips: AttemptChip[],
): ViewedResult {
  if (viewedAttempt === null) return { kind: "none" };
  const chip = chips.find((item) => item.attempt === viewedAttempt);
  if (!chip) return { kind: "none" };
  const result = session.find((item) => item.attempt === viewedAttempt);
  if (result) return { kind: "session", result, ordinal: chip.ordinal };
  return { kind: "stored", attempt: viewedAttempt, ordinal: chip.ordinal };
}

/**
 * `Của bạn (M)` và `Lần lượt cả hai (B)` chỉ dùng được khi bản ghi trong bộ nhớ chính là lượt đang xem;
 * chưa xem lượt nào thì giữ quy tắc P1 (`hasRecording`). Trình duyệt chỉ giữ bản ghi mới nhất của mỗi
 * câu (D-07) nên lượt cũ hơn không bao giờ phát bản ghi khác (D-11, FBK-04).
 */
export function yoursAvailable(
  viewedAttempt: number | null,
  recordingAttempt: number | undefined,
): boolean {
  return viewedAttempt === null || recordingAttempt === viewedAttempt;
}
