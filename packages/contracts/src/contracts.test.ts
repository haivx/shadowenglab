import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  ClipManifest,
  ExtraPauseData,
  IssueCode,
  Label,
  Lesson,
  Schemas,
  Scores,
  Word,
  type SchemaName,
} from "./index";

const FIXTURE_DIR = join(import.meta.dirname, "..", "fixtures");
const SCHEMA_PATH = join(
  import.meta.dirname,
  "..",
  "schema",
  "contracts.schema.json",
);

interface FixtureCase {
  name: string;
  data: unknown;
}

const fixtureFiles = readdirSync(FIXTURE_DIR).filter((f) =>
  f.endsWith(".json"),
);

describe("fixtures", () => {
  it("covers all four fixture files", () => {
    expect(fixtureFiles.sort()).toEqual([
      "ClipManifest.json",
      "Label.json",
      "Lesson.json",
      "ScoreResult.json",
    ]);
  });

  for (const file of fixtureFiles) {
    const typeName = file.replace(/\.json$/, "") as SchemaName;
    const cases = JSON.parse(
      readFileSync(join(FIXTURE_DIR, file), "utf-8"),
    ) as FixtureCase[];
    for (const c of cases) {
      it(`${typeName}:${c.name} parses`, () => {
        expect(Schemas[typeName].safeParse(c.data).success).toBe(true);
      });
    }
  }
});

describe("negative and boundary edges", () => {
  const word = { i: 0, text: "a", start: 0, end: 1, asrProb: 0.5 };

  it("rejects an optional field sent as null (Word.ipa)", () => {
    expect(Word.safeParse(word).success).toBe(true);
    expect(Word.safeParse({ ...word, ipa: null }).success).toBe(false);
  });

  it("accepts scores 0 and 1, rejects -0.0001 and 1.0001", () => {
    const base = { overall: 0, sound: null, intonation: 0, rhythm: 0 };
    expect(Scores.safeParse(base).success).toBe(true);
    expect(Scores.safeParse({ ...base, overall: 1 }).success).toBe(true);
    expect(Scores.safeParse({ ...base, overall: 1.0001 }).success).toBe(false);
    expect(Scores.safeParse({ ...base, overall: -0.0001 }).success).toBe(false);
  });

  it("Label.overall accepts 1 and 5, rejects 0 and 6", () => {
    const base = {
      clipId: "c",
      raterId: "r",
      overall: 3,
      wordFlags: [],
      finalContourMatch: true,
      unsure: false,
      durationMs: 1000,
      createdAt: "2026-10-06T00:00:00Z",
    };
    for (const ok of [1, 5]) {
      expect(Label.safeParse({ ...base, overall: ok }).success).toBe(true);
    }
    for (const bad of [0, 6]) {
      expect(Label.safeParse({ ...base, overall: bad }).success).toBe(false);
    }
  });

  it("ms must be a non-negative integer", () => {
    expect(ExtraPauseData.safeParse({ refMs: 0, userMs: 5 }).success).toBe(
      true,
    );
    expect(ExtraPauseData.safeParse({ refMs: -1, userMs: 5 }).success).toBe(
      false,
    );
    expect(ExtraPauseData.safeParse({ refMs: 1.5, userMs: 5 }).success).toBe(
      false,
    );
  });

  it("accepts an empty Lesson (queued, no segments) and Label with no wordFlags", () => {
    const lesson = {
      id: "01J",
      videoId: "v",
      title: "t",
      durationSec: 0,
      range: { start: 0, end: 0 },
      status: "queued",
      segments: [],
      createdAt: "2026-10-06T00:00:00Z",
    };
    expect(Lesson.safeParse(lesson).success).toBe(true);
  });

  it("ClipManifest without gold parses to gold none", () => {
    const parsed = ClipManifest.parse({
      clipId: "c",
      videoId: "v",
      sentenceText: "hello",
      words: [{ i: 0, text: "hello" }],
      refAudio: "ref.wav",
      userAudio: "user.wav",
    });
    expect(parsed.gold).toBe("none");
  });

  it("IssueCode has exactly the 7 codes", () => {
    expect([...IssueCode.options].sort()).toEqual(
      [
        "EXTRA_PAUSE",
        "FINAL_CONTOUR",
        "FLAT_PITCH",
        "PHONE",
        "PITCH_DEVIATION",
        "STRESS_MISMATCH",
        "WORD_MISSING",
      ].sort(),
    );
  });
});

describe("committed schema naming", () => {
  const schema = JSON.parse(readFileSync(SCHEMA_PATH, "utf-8")) as {
    $defs: Record<string, unknown>;
  };
  const keys = Object.keys(schema.$defs);

  it("has stable $defs for every named type", () => {
    for (const name of [
      "Segment",
      "Lesson",
      "ScoreResult",
      "IssueCode",
      "ClipManifest",
      "Label",
      "Word",
      "Issue",
      "WordFlags",
      "ClipWord",
    ]) {
      expect(keys).toContain(name);
    }
  });

  it("has no anonymous or positional def names", () => {
    expect(keys.filter((k) => /^(__schema\d+|Data\d*)$/.test(k))).toEqual([]);
  });

  it("keeps every integer bound inside the JS safe range", () => {
    const text = readFileSync(SCHEMA_PATH, "utf-8");
    for (const m of text.matchAll(/"(?:minimum|maximum)":\s*(-?\d+)\b/g)) {
      expect(Math.abs(Number(m[1]))).toBeLessThanOrEqual(9007199254740991);
    }
  });
});
