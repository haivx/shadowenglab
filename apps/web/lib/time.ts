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
  void durationSec;
  throw new Error("not implemented");
}

export type RangeValidation =
  | { ok: true; range: TimeRange }
  | { ok: false; startError?: string; endError?: string };

export function validateRange(
  startText: string,
  endText: string,
  durationSec: number,
): RangeValidation {
  void [startText, endText, durationSec];
  throw new Error("not implemented");
}

export function clampThumb(
  value: number,
  step: number,
  shift: boolean,
  durationSec: number,
): number {
  void [value, step, shift, durationSec];
  throw new Error("not implemented");
}
