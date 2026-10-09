import { describe, expect, it } from "vitest";
import type { Issue } from "@shadowenglab/contracts";
import { EMPTY_HIGHLIGHT, tipHighlight } from "./tipHighlight";

const words = ["I", "honestly", "expect", "it"].map((text) => ({ text }));

function stress(
  wordIndex: number,
  refWord: string,
  userWord: string,
): Extract<Issue, { code: "STRESS_MISMATCH" }> {
  return {
    code: "STRESS_MISMATCH",
    wordIndex,
    data: { refWord, userWord },
  };
}

describe("tipHighlight", () => {
  it("STRESS_MISMATCH: từ bản gốc là ref, từ bạn nhấn là you (bỏ hoa thường và dấu câu)", () => {
    expect(tipHighlight(stress(2, "expect", "Honestly,"), words)).toEqual({
      ref: [2],
      you: [1],
      neutral: [],
    });
  });

  it("STRESS_MISMATCH: refWord không khớp từ nào thì ref rơi về wordIndex", () => {
    expect(tipHighlight(stress(3, "zzz", "honestly"), words)).toEqual({
      ref: [3],
      you: [1],
      neutral: [],
    });
  });

  it("STRESS_MISMATCH: userWord không tìm thấy thì you rỗng", () => {
    expect(tipHighlight(stress(2, "expect", "nothing"), words)).toEqual({
      ref: [2],
      you: [],
      neutral: [],
    });
  });

  it("STRESS_MISMATCH: từ lặp lại thì ưu tiên đúng vị trí wordIndex", () => {
    const repeated = ["the", "cat", "the", "dog"].map((text) => ({ text }));
    expect(tipHighlight(stress(2, "the", "dog"), repeated).ref).toEqual([2]);
  });

  it("STRESS_MISMATCH: wordIndex ngoài phạm vi và không khớp thì không tô gì", () => {
    expect(tipHighlight(stress(9, "zzz", "yyy"), words)).toEqual(
      EMPTY_HIGHLIGHT,
    );
  });

  it("EXTRA_PAUSE: tô trung tính đúng wordIndex", () => {
    const issue: Issue = {
      code: "EXTRA_PAUSE",
      wordIndex: 1,
      data: { refMs: 30, userMs: 530 },
    };
    expect(tipHighlight(issue, words)).toEqual({
      ref: [],
      you: [],
      neutral: [1],
    });
  });

  it("PITCH_DEVIATION: tô trung tính đúng wordIndex", () => {
    const issue: Issue = {
      code: "PITCH_DEVIATION",
      wordIndex: 1,
      data: { meanDiffSt: 3.2 },
    };
    expect(tipHighlight(issue, words).neutral).toEqual([1]);
  });

  it("FINAL_CONTOUR: tô từ cuối câu", () => {
    const issue: Issue = {
      code: "FINAL_CONTOUR",
      data: { refSlope: -16.5, userSlope: 13.8 },
    };
    expect(tipHighlight(issue, words)).toEqual({
      ref: [],
      you: [],
      neutral: [3],
    });
  });

  it("FINAL_CONTOUR: câu không có từ thì không tô gì", () => {
    const issue: Issue = {
      code: "FINAL_CONTOUR",
      data: { refSlope: -16.5, userSlope: 13.8 },
    };
    expect(tipHighlight(issue, [])).toEqual(EMPTY_HIGHLIGHT);
  });

  it("FLAT_PITCH: cấp câu, không từ nào được tô", () => {
    const issue: Issue = { code: "FLAT_PITCH", data: { pitchRange: 0.0015 } };
    expect(tipHighlight(issue, words)).toEqual(EMPTY_HIGHLIGHT);
  });
});
