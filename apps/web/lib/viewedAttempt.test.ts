import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { ScoreResult } from "@shadowenglab/contracts";
import { describe, expect, it } from "vitest";
import type { AttemptChip } from "./attemptChips";
import { nextViewedAttempt, resolveViewedResult } from "./viewedAttempt";

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

function loadBaseResult(): ScoreResult {
  const cases = JSON.parse(readFileSync(FIXTURE, "utf8")) as {
    name: string;
    data: ScoreResult;
  }[];
  const found = cases.find((c) => c.name === "full");
  if (!found) throw new Error("ScoreResult fixture 'full' not found");
  return found.data;
}

const BASE_RESULT = loadBaseResult();

function resultOf(attempt: number): ScoreResult {
  return { ...BASE_RESULT, attempt };
}

function chip(attempt: number, ordinal: number, isBest = false): AttemptChip {
  return {
    attempt,
    ordinal,
    overall: 0.7,
    label: `Lượt ${ordinal} · 70`,
    isBest,
  };
}

// Chip order as the strip shows it: an older best first, then the most recent ascending.
const CAPPED_CHIPS = [
  chip(1, 1, true),
  chip(4, 4),
  chip(5, 5),
  chip(6, 6),
  chip(7, 7),
  chip(8, 8),
];

describe("nextViewedAttempt", () => {
  it("views nothing when the new sentence has no scored attempt", () => {
    expect(nextViewedAttempt(4, { type: "sentenceChanged", chips: [] })).toBe(
      null,
    );
  });

  it("views the latest attempt of the new sentence, not the first or best chip", () => {
    expect(
      nextViewedAttempt(4, { type: "sentenceChanged", chips: CAPPED_CHIPS }),
    ).toBe(8);
  });

  it("picks the latest attempt once the list arrives after a sentence change", () => {
    const chips = [chip(1, 1), chip(2, 2), chip(3, 3)];

    expect(nextViewedAttempt(null, { type: "chipsLoaded", chips })).toBe(3);
  });

  it("keeps a chip the user picked when the list refreshes", () => {
    const chips = [chip(1, 1), chip(2, 2), chip(3, 3)];

    expect(nextViewedAttempt(2, { type: "chipsLoaded", chips })).toBe(2);
  });

  it("stays on nothing when the list arrives empty", () => {
    expect(nextViewedAttempt(null, { type: "chipsLoaded", chips: [] })).toBe(
      null,
    );
  });

  it("makes a freshly scored attempt the viewed one", () => {
    expect(nextViewedAttempt(2, { type: "scored", attempt: 5 })).toBe(5);
  });

  it("follows a chip click", () => {
    expect(nextViewedAttempt(5, { type: "selected", attempt: 2 })).toBe(2);
  });
});

describe("resolveViewedResult", () => {
  const chips = [chip(2, 1), chip(3, 2, true)];

  it("is none when no attempt is viewed", () => {
    expect(resolveViewedResult(null, [resultOf(3)], chips)).toEqual({
      kind: "none",
    });
  });

  it("uses the in-session result object and the chip ordinal", () => {
    const session = resultOf(3);

    const viewed = resolveViewedResult(3, [session], chips);

    expect(viewed).toEqual({ kind: "session", result: session, ordinal: 2 });
    if (viewed.kind !== "session") throw new Error("expected a session result");
    expect(viewed.result).toBe(session);
  });

  it("asks for the stored result when the attempt is not in the session", () => {
    expect(resolveViewedResult(2, [resultOf(3)], chips)).toEqual({
      kind: "stored",
      attempt: 2,
      ordinal: 1,
    });
  });

  it("is none for an attempt that has no chip", () => {
    expect(resolveViewedResult(9, [resultOf(9)], chips)).toEqual({
      kind: "none",
    });
  });
});
