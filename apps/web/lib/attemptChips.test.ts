import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { AttemptSummary, ScoreResult } from "@shadowenglab/contracts";
import { describe, expect, it } from "vitest";
import { attemptChips } from "./attemptChips";

const FIXTURE = join(
  import.meta.dirname,
  "..",
  "..",
  "..",
  "packages",
  "contracts",
  "fixtures",
  "ScoreResult.json",
);

const BASE_RESULT = (
  JSON.parse(readFileSync(FIXTURE, "utf8")) as {
    name: string;
    data: ScoreResult;
  }[]
).find((c) => c.name === "full")!.data;

function summary(attempt: number, overall: number): AttemptSummary {
  return { attempt, overall, createdAt: "2026-10-08T09:00:00.000Z" };
}

function sessionResult(attempt: number, overall: number): ScoreResult {
  return {
    ...BASE_RESULT,
    attempt,
    scores: { ...BASE_RESULT.scores, overall },
  };
}

describe("attemptChips", () => {
  it("returns no chips when nothing is scored", () => {
    expect(attemptChips([], [])).toEqual([]);
    expect(attemptChips(undefined, [])).toEqual([]);
  });

  it("labels a single attempt by ordinal and never marks it best", () => {
    const chips = attemptChips([summary(2, 0.74)], []);

    expect(chips).toEqual([
      {
        attempt: 2,
        ordinal: 1,
        overall: 0.74,
        label: "Lượt 1 · 74",
        isBest: false,
      },
    ]);
  });

  it("numbers by ordinal among scored attempts and marks the later of tied bests", () => {
    const chips = attemptChips(
      [summary(1, 0.7), summary(3, 0.78), summary(4, 0.78)],
      [],
    );

    expect(chips.map((chip) => chip.label)).toEqual([
      "Lượt 1 · 70",
      "Lượt 2 · 78",
      "Lượt 3 · 78",
    ]);
    expect(
      chips.filter((chip) => chip.isBest).map((chip) => chip.attempt),
    ).toEqual([4]);
  });

  it("keeps the best chip when a newer attempt scores lower", () => {
    const chips = attemptChips([summary(1, 0.9), summary(2, 0.5)], []);

    expect(chips.find((chip) => chip.isBest)?.attempt).toBe(1);
    expect(chips).toHaveLength(2);
  });

  it("caps at 6 chips with an older best shown first, then the 5 most recent", () => {
    const list = [summary(1, 0.95)];
    for (let attempt = 2; attempt <= 8; attempt += 1) {
      list.push(summary(attempt, 0.5));
    }

    const chips = attemptChips(list, []);

    expect(chips.map((chip) => chip.attempt)).toEqual([1, 4, 5, 6, 7, 8]);
    expect(chips[0]?.isBest).toBe(true);
    // ordinals are over every scored attempt, not the visible ones
    expect(chips.map((chip) => chip.ordinal)).toEqual([1, 4, 5, 6, 7, 8]);
  });

  it("shows only the most recent chips when the best is among them", () => {
    const list: AttemptSummary[] = [];
    for (let attempt = 1; attempt <= 8; attempt += 1) {
      list.push(summary(attempt, attempt === 7 ? 0.9 : 0.5));
    }

    const chips = attemptChips(list, []);

    expect(chips).toHaveLength(6);
    expect(chips.map((chip) => chip.attempt)).toEqual([3, 4, 5, 6, 7, 8]);
    expect(chips.find((chip) => chip.isBest)?.attempt).toBe(7);
  });

  it("builds chips from this session when the list is not available", () => {
    const chips = attemptChips(undefined, [sessionResult(5, 0.81)]);

    expect(chips).toEqual([
      {
        attempt: 5,
        ordinal: 1,
        overall: 0.81,
        label: "Lượt 1 · 81",
        isBest: false,
      },
    ]);
  });

  it("merges a session result missing from the list and recomputes ordinals", () => {
    const chips = attemptChips(
      [summary(1, 0.6), summary(3, 0.7)],
      [sessionResult(4, 0.8)],
    );

    expect(chips.map((chip) => [chip.attempt, chip.ordinal])).toEqual([
      [1, 1],
      [3, 2],
      [4, 3],
    ]);
    expect(chips.find((chip) => chip.isBest)?.attempt).toBe(4);
  });

  it("lets the session copy win when an attempt appears in both", () => {
    const chips = attemptChips([summary(2, 0.5)], [sessionResult(2, 0.9)]);

    expect(chips).toHaveLength(1);
    expect(chips[0]?.overall).toBe(0.9);
  });
});
