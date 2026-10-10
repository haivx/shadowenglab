// Hàm thuần cho vùng kết quả S3: không React, không DOM (cùng kiểu với lessonView.ts).
import type { Prosody, ScoreResult, Scores } from "@shadowenglab/contracts";
import { scoreLevel, scorePercent } from "./scoreLevel";

export type ResultNote = {
  kind: "praise" | "metrics" | "neutral";
  text: string;
};

/** Phần của `ScoreResult` mà `resultNote` đọc; dữ liệu lưu sẵn nên lượt cũ mở lại ra đúng chữ cũ. */
export type ResultNoteInput = Pick<
  ScoreResult,
  "segmentIndex" | "attempt" | "issues" | "tips"
> & {
  scores: Pick<Scores, "overall">;
  prosody: Pick<Prosody, "speed" | "pitchRange" | "melodyMatch">;
};

// Hai câu của D-15; component chỉ hiển thị `note.text`, không giữ bản sao thứ hai.
const PRAISE_TEXT =
  "Rất sát bản gốc. Qua câu tiếp, hoặc thử lại để sát hơn nữa.";
const NEUTRAL_TEXT =
  "Chưa thấy lỗi cụ thể nào chắc chắn; nghe lại bản gốc rồi thử lại.";

type MetricKey = "melodyMatch" | "pitchRange" | "speed";

/**
 * Ghi chú theo chỉ số (D-15b), ba cách nói mỗi chỉ số, chép nguyên văn từ
 * 03-GAP-TIPS-PROPOSAL.md mục C'. `{v}` là số nguyên đang hiển thị ở ScoreHero.
 */
const METRIC_NOTES: Record<MetricKey, readonly [string, string, string]> = {
  melodyMatch: [
    "Giai điệu mới khớp {v}%: nghe lại bản gốc, chú ý chỗ giọng đi lên, đi xuống rồi bắt chước đúng hướng.",
    "Đường lên xuống của bạn còn khác bản gốc (khớp {v}%). Mở So sánh ngữ điệu để xem đoạn lệch rồi đọc lại.",
    "Đọc lại từng cụm theo bản gốc, bám chỗ giọng lên và xuống; giai điệu hiện khớp {v}%.",
  ],
  pitchRange: [
    "Độ lên xuống mới khớp {v}% với bản gốc; nghe lại xem bản gốc lên cao, xuống thấp tới đâu rồi bắt chước đúng mức đó.",
    "Biên độ giọng của bạn khác bản gốc (khớp {v}%). Mở So sánh ngữ điệu để so độ cao thấp của hai đường.",
    "Bám theo độ cao thấp của bản gốc ở từng cụm; độ lên xuống hiện khớp {v}%.",
  ],
  speed: [
    "Nhịp đọc của bạn còn lệch bản gốc (khớp {v}%); đọc cùng lúc với bản gốc để bắt nhịp.",
    "Tốc độ khớp {v}%: nghe lại bản gốc, để ý độ dài các khoảng nghỉ rồi đọc theo đúng nhịp đó.",
    "Nhại sát theo bản gốc, gần như cùng lúc, để tốc độ khớp hơn; hiện khớp {v}%.",
  ],
};

/** Thứ tự khi hai chỉ số hiển thị cùng một số: giai điệu, độ lên xuống, tốc độ. */
const METRIC_ORDER: readonly MetricKey[] = [
  "melodyMatch",
  "pitchRange",
  "speed",
];
const METRIC_NOTE_MAX = 2;
const METRIC_NOTE_BELOW = 80;

/**
 * Khối nhận xét khi KHÔNG có gợi ý nào (D-15, D-15b, P3-G7).
 * - Có gợi ý: null, TipList sở hữu khối đó và hai thứ không cùng xuất hiện.
 * - Không issue và có chỉ số hiển thị < 80: tối đa 2 ghi chú theo chỉ số, thấp nhất trước (D-15b).
 *   Cách nói theo `(segmentIndex + attempt - 1) mod 3`, cùng quy tắc với gợi ý ở backend (D-16),
 *   dựng từ `segmentIndex`/`attempt` đã lưu nên mở lại lượt cũ ra đúng chữ cũ.
 * - Còn lại (D-15): khen chỉ khi overall hiển thị >= 80 (cùng quy tắc làm tròn với `scoreLevel`),
 *   nếu không thì dòng trung tính. Có issue nhưng không dựng được gợi ý cũng đi nhánh này.
 */
export function resultNote(result: ResultNoteInput): ResultNote | null {
  if (result.tips.length > 0) return null;
  if (result.issues.length === 0) {
    const low = METRIC_ORDER.map((key, order) => ({
      key,
      order,
      shown: scorePercent(result.prosody[key]),
    }))
      .filter((metric) => metric.shown < METRIC_NOTE_BELOW)
      .sort((a, b) => a.shown - b.shown || a.order - b.order)
      .slice(0, METRIC_NOTE_MAX);
    if (low.length > 0) {
      const variant = (result.segmentIndex + result.attempt - 1) % 3;
      const text = low
        .map((metric) =>
          METRIC_NOTES[metric.key][variant]!.replace(
            "{v}",
            String(metric.shown),
          ),
        )
        .join(" ");
      return { kind: "metrics", text };
    }
  }
  return scoreLevel(result.scores.overall) === "good"
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
