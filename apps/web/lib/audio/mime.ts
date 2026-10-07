// Chọn định dạng cho MediaRecorder (RESEARCH Pattern 5a). Thứ tự ưu tiên: Chrome ghi webm/opus,
// Safari chỉ có mp4, webm không kèm codec là phương án cuối. Backend chuẩn hoá mọi định dạng
// sang WAV mono 16 kHz nên định dạng ở đây chỉ cần trình duyệt ghi được.

export const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/mp4",
  "audio/webm",
] as const;

/**
 * Trả về MIME đầu tiên trong danh sách ưu tiên mà trình duyệt hỗ trợ, hoặc undefined khi không có.
 * `isSupported` thường là `MediaRecorder.isTypeSupported`; truyền vào để test không cần DOM.
 */
export function pickMimeType(
  isSupported: (type: string) => boolean,
): string | undefined {
  return MIME_CANDIDATES.find((type) => isSupported(type));
}
