/**
 * Hàm thuần cho S2 (khoảng thời gian, ước lượng). Không đọc DOM, không gọi API.
 */

/** Video dài hơn ngưỡng này thì phải chọn đoạn (LES-02). */
export const LONG_VIDEO_SEC = 360;
/** Đoạn mặc định 00:00–05:00 (LES-02, G15). */
export const DEFAULT_RANGE_END_SEC = 300;

export interface TimeRange {
  start: number;
  end: number;
}

const CLOCK_PATTERN = /^(\d{1,3}):(\d{2})$/;

/** "mm:ss" -> giây. Phút 0–999, giây 0–59; sai định dạng -> null. */
export function parseClock(text: string): number | null {
  const match = CLOCK_PATTERN.exec(text.trim());
  if (!match) return null;
  const minutes = Number(match[1]);
  const seconds = Number(match[2]);
  if (seconds > 59) return null;
  return minutes * 60 + seconds;
}

/** Giây -> "mm:ss" (phút tối thiểu 2 chữ số). */
export function formatClockMs(seconds: number): string {
  const total = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

/** null khi video <= 6 phút (dùng toàn bộ); ngược lại 0 .. min(300, duration). */
export function defaultRange(durationSec: number): TimeRange | null {
  if (durationSec <= LONG_VIDEO_SEC) return null;
  return { start: 0, end: Math.min(DEFAULT_RANGE_END_SEC, durationSec) };
}

/** Số câu ước lượng [thấp, cao] cho d giây (G16). */
export function estimateSentences(durationSec: number): [number, number] {
  return [Math.round(durationSec / 8), Math.round(durationSec / 5)];
}

/** Số phút xử lý ước lượng, tối thiểu 1 (G16). */
export function estimateMinutes(durationSec: number): number {
  return Math.max(1, Math.round((0.8 * durationSec) / 60));
}

export const END_BEFORE_START_ERROR = "Kết thúc phải sau Bắt đầu.";

export function rangeFormatError(durationSec: number): string {
  return `Nhập thời gian dạng mm:ss, trong khoảng 00:00–${formatClockMs(durationSec)}.`;
}

export type RangeValidation =
  | { ok: true; range: TimeRange }
  | { ok: false; startError?: string; endError?: string };

/** Giây hợp lệ trong [0, duration], hoặc null (sai định dạng / ngoài video). */
function parseWithin(text: string, durationSec: number): number | null {
  const seconds = parseClock(text);
  return seconds !== null && seconds <= durationSec ? seconds : null;
}

/**
 * Kiểm tra hai ô mm:ss. Mỗi ô lỗi riêng; chỉ khi cả hai đọc được mới so thứ tự
 * (Kết thúc phải sau Bắt đầu, báo ở ô Kết thúc).
 */
export function validateRange(
  startText: string,
  endText: string,
  durationSec: number,
): RangeValidation {
  const start = parseWithin(startText, durationSec);
  const end = parseWithin(endText, durationSec);
  const formatError = rangeFormatError(durationSec);

  if (start === null || end === null) {
    return {
      ok: false,
      ...(start === null ? { startError: formatError } : {}),
      ...(end === null ? { endError: formatError } : {}),
    };
  }
  if (end <= start) {
    return { ok: false, endError: END_BEFORE_START_ERROR };
  }
  return { ok: true, range: { start, end } };
}

/** Dịch một thumb 1 giây (10 giây khi giữ Shift), giữ trong [0, duration]. */
export function clampThumb(
  value: number,
  step: number,
  shift: boolean,
  durationSec: number,
): number {
  const next = value + step * (shift ? 10 : 1);
  return Math.min(Math.max(next, 0), durationSec);
}
