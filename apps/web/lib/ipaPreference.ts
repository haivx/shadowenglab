/** Khoá localStorage nhớ lựa chọn hiện/ẩn IPA (nút `IPA`, phím `I`). */
export const IPA_PREFERENCE_KEY = "shadowenglab.ipaOn";

type ReadableStorage = Pick<Storage, "getItem">;
type WritableStorage = Pick<Storage, "setItem">;

/**
 * IPA mặc định bật (Liam 2026-10-10): phiên âm hiện dưới câu khi chờ, phát mẫu và ghi âm.
 * Chỉ "0" mới là tắt; storage thiếu hoặc ném lỗi (chế độ riêng tư) thì dùng mặc định.
 */
export function readIpaPreference(storage: ReadableStorage | null): boolean {
  try {
    return storage?.getItem(IPA_PREFERENCE_KEY) !== "0";
  } catch {
    return true;
  }
}

/** Ghi lựa chọn; lỗi storage bị bỏ qua vì đây chỉ là tiện ích theo máy. */
export function writeIpaPreference(
  storage: WritableStorage | null,
  on: boolean,
): void {
  try {
    storage?.setItem(IPA_PREFERENCE_KEY, on ? "1" : "0");
  } catch {
    // Không lưu được thì lần sau quay về mặc định.
  }
}
