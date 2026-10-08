// Logic thuần của màn S8 Settings (UI-SPEC "S8 Settings"). Component chỉ nối state vào đây.

/** Khung một mục của S8: trắng, viền 1px, bo 12, padding 24, gap 16. */
export const SETTINGS_SECTION_CLASS =
  "flex flex-col gap-4 rounded-xl border border-border bg-card p-6";

export interface Option<T> {
  value: T;
  label: string;
}

/** `Tốc độ mặc định` → `playbackRate`. */
export const RATE_OPTIONS: readonly Option<number>[] = [
  { value: 0.75, label: "0.75x" },
  { value: 1, label: "1x" },
];

/** `Số lần lặp` → `repeat`. */
export const REPEAT_OPTIONS: readonly Option<1 | 2 | 3>[] = [
  { value: 1, label: "×1" },
  { value: 2, label: "×2" },
  { value: 3, label: "×3" },
];

/** `Thời gian ghi` → `recordFactor` (mặc định +50%). */
export const RECORD_FACTOR_OPTIONS: readonly Option<number>[] = [
  { value: 1.25, label: "+25%" },
  { value: 1.5, label: "+50%" },
  { value: 2, label: "+100%" },
];

/** Giá trị mặc định khi chưa tải được cài đặt (khớp mặc định phía server, D-10). */
export const DEFAULT_PLAYBACK_RATE = 1;
export const DEFAULT_REPEAT = 1;
export const DEFAULT_RECORD_FACTOR = 1.5;

export function optionLabel<T>(
  options: readonly Option<T>[],
  value: T,
): string | undefined {
  return options.find((option) => option.value === value)?.label;
}

/**
 * File cài đặt do người dùng sửa tay có thể chứa số ngoài danh sách (ví dụ 0.9):
 * chọn tuỳ chọn gần nhất để hiển thị, không ném lỗi.
 */
export function snapToOption(
  options: readonly Option<number>[],
  value: number,
): Option<number> {
  let best: Option<number> | undefined;
  for (const option of options) {
    if (
      !best ||
      Math.abs(option.value - value) < Math.abs(best.value - value)
    ) {
      best = option;
    }
  }
  if (!best) throw new Error("snapToOption: danh sách tuỳ chọn rỗng");
  return best;
}

export type SaveStatus = "idle" | "saving" | "saved" | "error";

/**
 * Một ô tự lưu. `display` là thứ select đang hiện, `saved` là giá trị backend đã xác nhận,
 * `pending` là giá trị đang gửi (hoặc vừa thất bại, chờ `Thử lại`).
 * Bất biến: `status === "saved"` chỉ khi `display === saved` (E13: không bao giờ hiện giá trị
 * chưa lưu như đã lưu).
 */
export interface FieldState<T> {
  display: T;
  saved: T;
  status: SaveStatus;
  pending?: T;
}

export type FieldAction<T> =
  | { type: "change"; value: T }
  | { type: "success"; value: T }
  | { type: "failure"; value: T }
  | { type: "retry" };

export function initialField<T>(value: T): FieldState<T> {
  return { display: value, saved: value, status: "idle" };
}

export function settingsReducer<T>(
  state: FieldState<T>,
  action: FieldAction<T>,
): FieldState<T> {
  switch (action.type) {
    case "change":
      return {
        display: action.value,
        saved: state.saved,
        status: "saving",
        pending: action.value,
      };
    case "success":
      // Phản hồi của lần đổi cũ khi đã có lần đổi mới hơn: ghi nhận giá trị đã lưu
      // nhưng vẫn chờ lần mới.
      if (state.status === "saving" && state.display !== action.value) {
        return { ...state, saved: action.value };
      }
      return { display: action.value, saved: action.value, status: "saved" };
    case "failure":
      if (state.status === "saving" && state.display !== action.value) {
        return state;
      }
      return {
        display: state.saved,
        saved: state.saved,
        status: "error",
        pending: action.value,
      };
    case "retry":
      if (state.pending === undefined) return state;
      return {
        display: state.pending,
        saved: state.saved,
        status: "saving",
        pending: state.pending,
      };
  }
}

/**
 * Thư mục dữ liệu vừa lưu khác thư mục backend đang dùng thì chỉ có hiệu lực sau khi khởi động
 * lại, dữ liệu cũ không bị di chuyển (D-12). Đặt lại đúng thư mục đang dùng thì không cần.
 */
export function dataDirNeedsRestart(
  savedDir: string,
  activeDir: string,
): boolean {
  return savedDir !== activeDir;
}
