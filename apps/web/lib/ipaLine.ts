import type { Word } from "@shadowenglab/contracts";

/** Dấu thay cho từ chưa nhận dạng chắc (G9). */
export const MISSING_IPA = "—";

export interface IpaLine {
  /** `/a b — c/`: IPA của các từ nối bằng dấu cách trong một cặp dấu gạch chéo. */
  text: string;
  /** true khi không từ nào có IPA: hiện "Chưa nhận dạng chắc câu này." thay cho dòng IPA. */
  allMissing: boolean;
}

/**
 * Dòng IPA của một câu (D-14, D-15).
 * Chỉ đọc `word.ipa` nhận dạng từ chính giọng người nói; không bao giờ tự sinh IPA từ chữ.
 */
export function ipaLine(words: readonly Word[]): IpaLine {
  const parts = words.map((word) =>
    word.ipa !== undefined && word.ipa !== "" ? word.ipa : MISSING_IPA,
  );
  const allMissing = parts.every((part) => part === MISSING_IPA);
  return { text: `/${parts.join(" ")}/`, allMissing };
}
