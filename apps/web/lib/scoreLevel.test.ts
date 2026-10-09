import { describe, expect, it } from "vitest";
import {
  SCORE_FILL_CLASS,
  SCORE_TEXT_CLASS,
  scoreLevel,
  scorePercent,
  type ScoreLevel,
} from "./scoreLevel";

describe("scoreLevel", () => {
  it("null -> unrated", () => {
    expect(scoreLevel(null)).toBe("unrated");
  });

  it("làm tròn về số nguyên hiển thị trước khi so ngưỡng", () => {
    expect(scoreLevel(0.796)).toBe("good");
    expect(scoreLevel(0.795)).toBe("good");
    expect(scoreLevel(0.794)).toBe("ok");
    expect(scoreLevel(0.595)).toBe("ok");
    expect(scoreLevel(0.594)).toBe("bad");
  });

  it("biên 0, 0.8 và 1", () => {
    expect(scoreLevel(0)).toBe("bad");
    expect(scoreLevel(0.8)).toBe("good");
    expect(scoreLevel(1)).toBe("good");
  });
});

describe("scorePercent", () => {
  it("là Math.round(score * 100)", () => {
    expect(scorePercent(0.796)).toBe(80);
    expect(scorePercent(0.594)).toBe(59);
    expect(scorePercent(0)).toBe(0);
    expect(scorePercent(1)).toBe(100);
  });
});

describe("tra cứu class", () => {
  const levels: ScoreLevel[] = ["good", "ok", "bad", "unrated"];

  it("mọi mức có class chữ và class nền dạng literal", () => {
    for (const level of levels) {
      expect(SCORE_TEXT_CLASS[level]).toBe(`text-score-${level}-text`);
      expect(SCORE_FILL_CLASS[level]).toBe(`bg-score-${level}`);
    }
  });
});
