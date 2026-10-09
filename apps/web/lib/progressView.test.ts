import type { LessonProgress } from "@shadowenglab/contracts";
import { describe, expect, it } from "vitest";
import {
  bestBySegment,
  segmentFillClass,
  transcriptScoreCell,
} from "./progressView";

function progress(segments: LessonProgress["segments"]): LessonProgress {
  return { lessonId: "lesson-1", segments, firstUnpracticedIndex: null };
}

describe("bestBySegment", () => {
  it("undefined (chưa có progress) -> Map rỗng", () => {
    expect(bestBySegment(undefined).size).toBe(0);
  });

  it("chỉ giữ các câu có bestOverall, bỏ câu chỉ có lượt chưa chấm", () => {
    const best = bestBySegment(
      progress([
        {
          segmentIndex: 0,
          attempts: 4,
          voicedAttempts: 4,
          bestOverall: 0.74,
          bestAttempt: 3,
        },
        { segmentIndex: 1, attempts: 1, voicedAttempts: 0 },
      ]),
    );
    expect(best.size).toBe(1);
    expect(best.get(0)).toBe(0.74);
    expect(best.has(1)).toBe(false);
  });

  it("giữ bestOverall = 0 (điểm 0 vẫn là đã chấm)", () => {
    const best = bestBySegment(
      progress([
        {
          segmentIndex: 2,
          attempts: 1,
          voicedAttempts: 1,
          bestOverall: 0,
          bestAttempt: 1,
        },
      ]),
    );
    expect(best.get(2)).toBe(0);
  });
});

describe("transcriptScoreCell", () => {
  it("có điểm tốt nhất -> số nguyên làm tròn, màu qua scoreLevel", () => {
    const cell = transcriptScoreCell(0.796, true);
    expect(cell.kind).toBe("score");
    if (cell.kind !== "score") return;
    expect(cell.text).toBe("80");
    expect(cell.className).toContain("text-score-good-text");
  });

  it("0.594 hiện 59 nên đỏ; 0.65 hiện 65 nên vàng", () => {
    const bad = transcriptScoreCell(0.594, true);
    const ok = transcriptScoreCell(0.65, true);
    if (bad.kind !== "score" || ok.kind !== "score") {
      throw new Error("expected score cells");
    }
    expect(bad.text).toBe("59");
    expect(bad.className).toContain("text-score-bad-text");
    expect(ok.text).toBe("65");
    expect(ok.className).toContain("text-score-ok-text");
  });

  it("100 vẫn là score cell", () => {
    const cell = transcriptScoreCell(1, true);
    if (cell.kind !== "score") throw new Error("expected score cell");
    expect(cell.text).toBe("100");
  });

  it("không có điểm nhưng đã tập (P1) -> chấm xám", () => {
    expect(transcriptScoreCell(undefined, true)).toEqual({ kind: "dot" });
  });

  it("không có điểm và chưa tập -> ô trống", () => {
    expect(transcriptScoreCell(undefined, false)).toEqual({ kind: "empty" });
  });
});

describe("segmentFillClass", () => {
  it("câu hiện tại luôn --foreground, bất kể điểm", () => {
    expect(
      segmentFillClass({ index: 2, current: 2, best: 0.5, practiced: true }),
    ).toBe("bg-foreground");
  });

  it("câu có điểm tô theo scoreLevel của lượt tốt nhất", () => {
    expect(
      segmentFillClass({ index: 1, current: 2, best: 0.5, practiced: true }),
    ).toBe("bg-score-bad");
    expect(
      segmentFillClass({ index: 1, current: 2, best: 0.65, practiced: true }),
    ).toBe("bg-score-ok");
    expect(
      segmentFillClass({ index: 1, current: 2, best: 0.9, practiced: true }),
    ).toBe("bg-score-good");
  });

  it("đã tập nhưng chưa có điểm -> --muted-foreground", () => {
    expect(
      segmentFillClass({
        index: 0,
        current: 2,
        best: undefined,
        practiced: true,
      }),
    ).toBe("bg-muted-foreground");
  });

  it("chưa đụng tới -> slate-4", () => {
    expect(
      segmentFillClass({
        index: 0,
        current: 2,
        best: undefined,
        practiced: false,
      }),
    ).toBe("bg-[color:var(--slate-4)]");
  });
});
