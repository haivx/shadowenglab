// Hàm thuần cho vùng kết quả S3: không React, không DOM (cùng kiểu với lessonView.ts).
import { scoreLevel } from "./scoreLevel";

export type ResultNote = { kind: "praise" | "neutral"; text: string };

// Hai câu của D-15; component chỉ hiển thị `note.text`, không giữ bản sao thứ hai.
const PRAISE_TEXT =
  "Rất sát bản gốc. Qua câu tiếp, hoặc thử lại để sát hơn nữa.";
const NEUTRAL_TEXT =
  "Chưa thấy lỗi cụ thể nào chắc chắn; nghe lại bản gốc rồi thử lại.";

/**
 * Dòng khen / trung tính khi KHÔNG có gợi ý nào (D-15, P3-G7).
 * Khen chỉ khi số hiển thị >= 80 (cùng quy tắc làm tròn với `scoreLevel`); dưới 80 không bao giờ khen.
 * Có gợi ý thì trả null: TipList sở hữu khối đó, hai thứ không cùng xuất hiện.
 */
export function resultNote(
  overall: number,
  tipCount: number,
): ResultNote | null {
  if (tipCount > 0) return null;
  return scoreLevel(overall) === "good"
    ? { kind: "praise", text: PRAISE_TEXT }
    : { kind: "neutral", text: NEUTRAL_TEXT };
}

function collapseWhitespace(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

/**
 * Các từ của kết quả còn khớp `segment.text` không (E4). Rỗng, thiếu từ hoặc khác từ (câu bị sửa
 * sau khi chấm) -> false và UI rơi về đoạn văn thường. Chuẩn hoá khoảng trắng ở cả hai phía.
 */
export function wordsMatchSegment(
  words: ReadonlyArray<{ text: string }>,
  text: string,
): boolean {
  if (words.length === 0) return false;
  const joined = words.map((word) => word.text).join(" ");
  return collapseWhitespace(joined) === collapseWhitespace(text);
}
