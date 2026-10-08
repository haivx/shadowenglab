import { QueryClient } from "@tanstack/react-query";
import type { Lesson, Segment } from "@shadowenglab/contracts";
import { describe, expect, it } from "vitest";
import { queryKeys } from "./queries";
import { patchLessonSegment, replaceSegment } from "./segmentCache";

function segment(index: number, text: string, extra = 0): Segment {
  return {
    index,
    text,
    start: index,
    end: index + 1,
    endExtraMs: extra,
    words: [],
  };
}

function lesson(): Lesson {
  return {
    id: "01HX",
    videoId: "abc",
    title: "Bài",
    durationSec: 60,
    range: { start: 0, end: 60 },
    padMs: 150,
    status: "ready",
    segments: [segment(0, "one"), segment(1, "two"), segment(2, "three")],
    createdAt: "2026-10-08T00:00:00Z",
  };
}

describe("replaceSegment", () => {
  it("thay đúng câu theo index và giữ nguyên các câu còn lại", () => {
    const before = lesson();
    const after = replaceSegment(before, segment(1, "two!", 300));
    expect(after.segments[1]).toEqual(segment(1, "two!", 300));
    expect(after.segments[0]).toBe(before.segments[0]);
    expect(after.segments[2]).toBe(before.segments[2]);
    expect(before.segments[1]?.text).toBe("two");
  });
});

describe("patchLessonSegment", () => {
  it("cập nhật cache của bài khi đã có", () => {
    const client = new QueryClient();
    client.setQueryData(queryKeys.lesson("01HX"), lesson());
    patchLessonSegment(client, "01HX", segment(2, "three?"));
    const cached = client.getQueryData<Lesson>(queryKeys.lesson("01HX"));
    expect(cached?.segments[2]?.text).toBe("three?");
  });

  it("bỏ qua khi cache chưa có bài", () => {
    const client = new QueryClient();
    patchLessonSegment(client, "01HX", segment(0, "x"));
    expect(client.getQueryData(queryKeys.lesson("01HX"))).toBeUndefined();
  });
});
