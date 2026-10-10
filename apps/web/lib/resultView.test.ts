import type { Issue, Tip } from "@shadowenglab/contracts";
import { describe, expect, it } from "vitest";
import {
  resultNote,
  wordsMatchSegment,
  type ResultNoteInput,
} from "./resultView";

const PRAISE = "Rất sát bản gốc. Qua câu tiếp, hoặc thử lại để sát hơn nữa.";
const NEUTRAL =
  "Chưa thấy lỗi cụ thể nào chắc chắn; nghe lại bản gốc rồi thử lại.";

const FLAT_ISSUE: Issue = { code: "FLAT_PITCH", data: { pitchRange: 0.3 } };
const TIP: Tip = { text: "Gợi ý", issueRef: 0, source: "template" };

interface Overrides {
  overall?: number;
  speed?: number;
  pitchRange?: number;
  melodyMatch?: number;
  segmentIndex?: number;
  attempt?: number;
  issues?: Issue[];
  tips?: Tip[];
}

/** Kết quả không issue, không tip, cả ba chỉ số 0.9 trừ khi ghi đè. */
function input(o: Overrides = {}): ResultNoteInput {
  return {
    segmentIndex: o.segmentIndex ?? 0,
    attempt: o.attempt ?? 1,
    issues: o.issues ?? [],
    tips: o.tips ?? [],
    scores: { overall: o.overall ?? 0.9 },
    prosody: {
      speed: o.speed ?? 0.9,
      pitchRange: o.pitchRange ?? 0.9,
      melodyMatch: o.melodyMatch ?? 0.9,
    },
  };
}

// Lời văn đã duyệt (03-GAP-TIPS-PROPOSAL.md mục C'), chép lại độc lập với resultView.ts.
const MELODY = [
  (v: number) =>
    `Giai điệu mới khớp ${v}%: nghe lại bản gốc, chú ý chỗ giọng đi lên, đi xuống rồi bắt chước đúng hướng.`,
  (v: number) =>
    `Đường lên xuống của bạn còn khác bản gốc (khớp ${v}%). Mở So sánh ngữ điệu để xem đoạn lệch rồi đọc lại.`,
  (v: number) =>
    `Đọc lại từng cụm theo bản gốc, bám chỗ giọng lên và xuống; giai điệu hiện khớp ${v}%.`,
];
const RANGE = [
  (v: number) =>
    `Độ lên xuống mới khớp ${v}% với bản gốc; nghe lại xem bản gốc lên cao, xuống thấp tới đâu rồi bắt chước đúng mức đó.`,
  (v: number) =>
    `Biên độ giọng của bạn khác bản gốc (khớp ${v}%). Mở So sánh ngữ điệu để so độ cao thấp của hai đường.`,
  (v: number) =>
    `Bám theo độ cao thấp của bản gốc ở từng cụm; độ lên xuống hiện khớp ${v}%.`,
];
const SPEED = [
  (v: number) =>
    `Nhịp đọc của bạn còn lệch bản gốc (khớp ${v}%); đọc cùng lúc với bản gốc để bắt nhịp.`,
  (v: number) =>
    `Tốc độ khớp ${v}%: nghe lại bản gốc, để ý độ dài các khoảng nghỉ rồi đọc theo đúng nhịp đó.`,
  (v: number) =>
    `Nhại sát theo bản gốc, gần như cùng lúc, để tốc độ khớp hơn; hiện khớp ${v}%.`,
];

/** Cách nói thứ `i` của một bộ ghi chú, đã điền số `v`. */
function at(set: Array<(v: number) => string>, i: number, v: number): string {
  const make = set[i];
  if (!make) throw new Error(`không có cách nói ${i}`);
  return make(v);
}

describe("resultNote (D-15)", () => {
  it("khen khi không issue và cả overall lẫn ba chỉ số hiển thị >= 80", () => {
    expect(
      resultNote(
        input({ overall: 0.8, speed: 0.8, pitchRange: 0.8, melodyMatch: 0.8 }),
      ),
    ).toEqual({ kind: "praise", text: PRAISE });
    expect(resultNote(input({ overall: 1 }))?.kind).toBe("praise");
  });

  it("0.795 làm tròn thành 80 nên vẫn khen, cùng quy tắc với scoreLevel", () => {
    expect(
      resultNote(input({ overall: 0.795, melodyMatch: 0.795 }))?.kind,
    ).toBe("praise");
  });

  it("overall 0.794 hiện 79: không khen, dòng trung tính khi mọi chỉ số >= 80", () => {
    expect(resultNote(input({ overall: 0.794 }))).toEqual({
      kind: "neutral",
      text: NEUTRAL,
    });
  });

  it("có issue nhưng không dựng được tip: giữ D-15, không bao giờ ghi chú theo chỉ số", () => {
    expect(
      resultNote(
        input({ issues: [FLAT_ISSUE], overall: 0.95, melodyMatch: 0.5 }),
      )?.kind,
    ).toBe("praise");
    expect(
      resultNote(
        input({ issues: [FLAT_ISSUE], overall: 0.6, melodyMatch: 0.5 }),
      ),
    ).toEqual({ kind: "neutral", text: NEUTRAL });
  });

  it("có gợi ý thì không có dòng nào: TipList sở hữu khối này", () => {
    expect(resultNote(input({ tips: [TIP], issues: [FLAT_ISSUE] }))).toBeNull();
    expect(
      resultNote(
        input({ tips: [TIP, TIP, TIP], issues: [FLAT_ISSUE], overall: 0.2 }),
      ),
    ).toBeNull();
  });
});

describe("resultNote (D-15b: ghi chú theo chỉ số)", () => {
  const uat = {
    overall: 0.69,
    speed: 0.82,
    pitchRange: 0.64,
    melodyMatch: 0.6,
  };

  it("ca UAT 69 (tốc độ 82, lên xuống 64, giai điệu 60): hai ghi chú, thấp nhất trước", () => {
    const note = resultNote(input(uat));

    expect(note).toEqual({
      kind: "metrics",
      text: `${at(MELODY, 0, 60)} ${at(RANGE, 0, 64)}`,
    });
    expect(note?.text).not.toContain("82");
  });

  it("lượt 2 dùng cách nói thứ hai, câu 3 lượt 1 quay về cách nói đầu (3 mod 3)", () => {
    expect(resultNote(input({ ...uat, attempt: 2 }))?.text).toBe(
      `${at(MELODY, 1, 60)} ${at(RANGE, 1, 64)}`,
    );
    expect(resultNote(input({ ...uat, attempt: 3 }))?.text).toBe(
      `${at(MELODY, 2, 60)} ${at(RANGE, 2, 64)}`,
    );
    expect(
      resultNote(input({ ...uat, segmentIndex: 3, attempt: 1 }))?.text,
    ).toBe(`${at(MELODY, 0, 60)} ${at(RANGE, 0, 64)}`);
    expect(
      resultNote(input({ ...uat, segmentIndex: 1, attempt: 1 }))?.text,
    ).toBe(resultNote(input({ ...uat, segmentIndex: 0, attempt: 2 }))?.text);
  });

  it("cả ba dưới 80: tối đa hai ghi chú, thấp nhất trước", () => {
    const note = resultNote(
      input({ overall: 0.6, speed: 0.5, pitchRange: 0.7, melodyMatch: 0.6 }),
    );

    expect(note?.text).toBe(`${at(SPEED, 0, 50)} ${at(MELODY, 0, 60)}`);
  });

  it("hòa số hiển thị: giai điệu trước lên xuống trước tốc độ", () => {
    expect(
      resultNote(input({ pitchRange: 0.7, melodyMatch: 0.7, speed: 0.9 }))
        ?.text,
    ).toBe(`${at(MELODY, 0, 70)} ${at(RANGE, 0, 70)}`);
    expect(
      resultNote(input({ pitchRange: 0.7, speed: 0.7, melodyMatch: 0.9 }))
        ?.text,
    ).toBe(`${at(RANGE, 0, 70)} ${at(SPEED, 0, 70)}`);
  });

  it("làm tròn như ScoreHero: 0.795 hiện 80 không ghi chú, 0.794 hiện 79 thì ghi chú với 79", () => {
    expect(resultNote(input({ melodyMatch: 0.795 }))?.kind).toBe("praise");
    expect(resultNote(input({ melodyMatch: 0.794 }))).toEqual({
      kind: "metrics",
      text: at(MELODY, 0, 79),
    });
  });

  it("overall >= 80 nhưng một chỉ số < 80: ghi chú chỉ số, không khen", () => {
    const note = resultNote(
      input({ overall: 0.86, speed: 0.95, pitchRange: 0.92, melodyMatch: 0.7 }),
    );

    expect(note).toEqual({ kind: "metrics", text: at(MELODY, 0, 70) });
  });

  it("không ghi chú nào chứa dấu * và cùng đầu vào cho cùng kết quả", () => {
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      const given = {
        overall: 0.5,
        speed: 0.4,
        pitchRange: 0.5,
        melodyMatch: 0.6,
        attempt,
      };
      const a = resultNote(input(given));
      expect(a).toEqual(resultNote(input(given)));
      expect(a?.text).not.toContain("*");
    }
  });
});

describe("wordsMatchSegment (E4)", () => {
  const w = (...texts: string[]) => texts.map((text) => ({ text }));

  it("danh sách từ rỗng -> false", () => {
    expect(wordsMatchSegment([], "Hello world")).toBe(false);
  });

  it("khớp khi ghép các từ bằng một dấu cách bằng câu", () => {
    expect(wordsMatchSegment(w("Hello", "world"), "Hello world")).toBe(true);
  });

  it("chuẩn hoá khoảng trắng ở cả hai phía", () => {
    expect(wordsMatchSegment(w("Hello", "world"), "  Hello   world ")).toBe(
      true,
    );
    expect(wordsMatchSegment(w(" Hello ", "world"), "Hello world")).toBe(true);
  });

  it("thiếu từ hoặc khác từ -> false (rơi về đoạn văn thường)", () => {
    expect(wordsMatchSegment(w("Hello"), "Hello world")).toBe(false);
    expect(wordsMatchSegment(w("Hello", "word"), "Hello world")).toBe(false);
  });
});
