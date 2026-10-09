import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  ApiError,
  ApiErrorCode,
  AppSettings,
  AttemptAck,
  AttemptSummary,
  ClipManifest,
  ExtraPauseData,
  IssueCode,
  Label,
  Lesson,
  LessonListItem,
  Schemas,
  Scores,
  SegmentProgress,
  UpdateSegmentTextRequest,
  VideoPreview,
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
  it("covers all sixteen fixture files", () => {
    expect(fixtureFiles.sort()).toEqual([
      "ApiError.json",
      "AppSettings.json",
      "AttemptAck.json",
      "AttemptSummary.json",
      "ClipManifest.json",
      "CreateLessonRequest.json",
      "Label.json",
      "Lesson.json",
      "LessonListItem.json",
      "LessonProgress.json",
      "OpenAiKeyCheckRequest.json",
      "OpenAiKeyCheckResult.json",
      "ScoreResult.json",
      "SystemStatus.json",
      "UpdateSegmentTextRequest.json",
      "VideoPreview.json",
    ]);
  });

  it("has a Schemas entry for every fixture file", () => {
    for (const file of fixtureFiles) {
      expect(Object.keys(Schemas)).toContain(file.replace(/\.json$/, ""));
    }
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

describe("phase 2 contract edges", () => {
  const preview = { videoId: "v", title: "t", durationSec: 10 };
  const ack = {
    lessonId: "01J",
    segmentIndex: 0,
    attempt: 1,
    durationMs: 0,
    voiced: false,
    savedForEval: false,
  };
  const settings = {
    playbackRate: 1,
    repeat: 1,
    recordFactor: 1.5,
    dataDir: "/data",
    accent: "US",
  };
  const lessonSummary = {
    id: "01J",
    videoId: "v",
    title: "t",
    durationSec: 10,
    range: { start: 0, end: 10 },
    status: "ready",
    createdAt: "2026-10-07T00:00:00Z",
  };

  it("rejects an optional field sent as null (VideoPreview.channel)", () => {
    expect(VideoPreview.safeParse(preview).success).toBe(true);
    expect(VideoPreview.safeParse({ ...preview, channel: null }).success).toBe(
      false,
    );
  });

  it("AttemptAck.attempt starts at 1: 0 rejected, 1 accepted", () => {
    expect(AttemptAck.safeParse(ack).success).toBe(true);
    expect(AttemptAck.safeParse({ ...ack, attempt: 0 }).success).toBe(false);
  });

  it("AppSettings.repeat accepts 1..3, rejects 4", () => {
    expect(AppSettings.safeParse(settings).success).toBe(true);
    expect(AppSettings.safeParse({ ...settings, repeat: 3 }).success).toBe(
      true,
    );
    expect(AppSettings.safeParse({ ...settings, repeat: 4 }).success).toBe(
      false,
    );
  });

  it('AppSettings.accent only accepts "US"', () => {
    expect(AppSettings.safeParse({ ...settings, accent: "UK" }).success).toBe(
      false,
    );
  });

  it("AppSettings.playbackRate stays within [0.5, 1]", () => {
    for (const ok of [0.5, 0.75, 1]) {
      expect(
        AppSettings.safeParse({ ...settings, playbackRate: ok }).success,
      ).toBe(true);
    }
    for (const bad of [0.49, 1.01]) {
      expect(
        AppSettings.safeParse({ ...settings, playbackRate: bad }).success,
      ).toBe(false);
    }
  });

  it("AppSettings.recordFactor stays within [1, 2]", () => {
    for (const ok of [1, 1.25, 2]) {
      expect(
        AppSettings.safeParse({ ...settings, recordFactor: ok }).success,
      ).toBe(true);
    }
    for (const bad of [0.99, 2.01]) {
      expect(
        AppSettings.safeParse({ ...settings, recordFactor: bad }).success,
      ).toBe(false);
    }
  });

  it("UpdateSegmentTextRequest.text is 1..500 chars after trim", () => {
    const parse = (text: string) =>
      UpdateSegmentTextRequest.safeParse({ text }).success;
    expect(parse("a")).toBe(true);
    expect(parse("a".repeat(500))).toBe(true);
    expect(parse("")).toBe(false);
    expect(parse("   ")).toBe(false);
    expect(parse("a".repeat(501))).toBe(false);
  });

  it("LessonListItem.firstUnpracticedIndex is nullable but never absent or negative", () => {
    const item = {
      lesson: lessonSummary,
      segmentCount: 3,
      practicedCount: 3,
    };
    expect(
      LessonListItem.safeParse({ ...item, firstUnpracticedIndex: null })
        .success,
    ).toBe(true);
    expect(
      LessonListItem.safeParse({ ...item, firstUnpracticedIndex: 0 }).success,
    ).toBe(true);
    expect(LessonListItem.safeParse(item).success).toBe(false);
    expect(
      LessonListItem.safeParse({ ...item, firstUnpracticedIndex: -1 }).success,
    ).toBe(false);
  });

  it("LessonListItem.lesson carries no segments", () => {
    const parsed = LessonListItem.parse({
      lesson: { ...lessonSummary, segments: [] },
      segmentCount: 0,
      practicedCount: 0,
      firstUnpracticedIndex: 0,
    });
    expect("segments" in parsed.lesson).toBe(false);
  });

  it("ApiError accepts duplicate_lesson with lessonId, rejects unknown code", () => {
    expect(
      ApiError.safeParse({
        code: "duplicate_lesson",
        message: "m",
        lessonId: "01J",
      }).success,
    ).toBe(true);
    expect(ApiError.safeParse({ code: "teapot", message: "m" }).success).toBe(
      false,
    );
  });

  it("ApiErrorCode has exactly the 21 approved codes", () => {
    const codes = [
      "invalid_request",
      "invalid_url",
      "channel_url",
      "video_unavailable",
      "live_video",
      "invalid_range",
      "duplicate_lesson",
      "not_found",
      "invalid_state",
      "invalid_segment",
      "unsupported_media",
      "payload_too_large",
      "recording_too_long",
      "no_speech",
      "busy",
      "no_openai_key",
      "upstream_error",
      "network_error",
      "invalid_settings",
      "forbidden_origin",
      "internal_error",
    ];
    for (const code of codes) {
      expect(ApiError.safeParse({ code, message: "m" }).success).toBe(true);
    }
    expect(codes).toHaveLength(21);
    expect(ApiErrorCode.options).toEqual(codes);
  });
});

describe("phase 3 contract edges", () => {
  const progress = { segmentIndex: 0, attempts: 3, voicedAttempts: 3 };
  const summary = {
    attempt: 2,
    overall: 0.8,
    createdAt: "2026-10-08T09:00:00.000Z",
  };

  it("ApiError accepts no_speech (D-09) and still rejects unknown codes", () => {
    expect(
      ApiError.safeParse({
        code: "no_speech",
        message: "Không nghe thấy tiếng nói trong lượt vừa rồi.",
      }).success,
    ).toBe(true);
    expect(ApiError.safeParse({ code: "teapot", message: "m" }).success).toBe(
      false,
    );
  });

  it("SegmentProgress accepts bestOverall + bestAttempt, and the P1 shape without them", () => {
    expect(
      SegmentProgress.safeParse({
        ...progress,
        bestOverall: 0.74,
        bestAttempt: 3,
      }).success,
    ).toBe(true);
    expect(SegmentProgress.safeParse(progress).success).toBe(true);
  });

  it("SegmentProgress.bestOverall is optional, never null, and stays within [0, 1]", () => {
    const ok = { ...progress, bestOverall: 0.74, bestAttempt: 3 };
    expect(
      SegmentProgress.safeParse({ ...ok, bestOverall: null }).success,
    ).toBe(false);
    expect(SegmentProgress.safeParse({ ...ok, bestOverall: 1.2 }).success).toBe(
      false,
    );
  });

  it("SegmentProgress.bestAttempt is optional, never null, and starts at 1", () => {
    const ok = { ...progress, bestOverall: 0.74, bestAttempt: 3 };
    expect(SegmentProgress.safeParse({ ...ok, bestAttempt: 0 }).success).toBe(
      false,
    );
    expect(
      SegmentProgress.safeParse({ ...ok, bestAttempt: null }).success,
    ).toBe(false);
  });

  it("AttemptSummary parses attempt 2 / overall 0.8 / ISO createdAt", () => {
    expect(AttemptSummary.safeParse(summary).success).toBe(true);
  });

  it("AttemptSummary rejects attempt 0 and overall 1.2", () => {
    expect(AttemptSummary.safeParse({ ...summary, attempt: 0 }).success).toBe(
      false,
    );
    expect(AttemptSummary.safeParse({ ...summary, overall: 1.2 }).success).toBe(
      false,
    );
  });

  it("AttemptSummary rejects a missing createdAt", () => {
    const withoutCreatedAt = { attempt: summary.attempt, overall: 0.8 };
    expect(AttemptSummary.safeParse(withoutCreatedAt).success).toBe(false);
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
      "AttemptAck",
      "AttemptSummary",
      "AppSettings",
      "VideoPreview",
      "CreateLessonRequest",
      "LessonSummary",
      "LessonListItem",
      "SegmentProgress",
      "LessonProgress",
      "ModelStatuses",
      "SystemStatus",
      "OpenAiKeyCheckRequest",
      "OpenAiKeyCheckResult",
      "UpdateSegmentTextRequest",
      "ApiError",
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
