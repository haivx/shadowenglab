import { describe, expect, it } from "vitest";
import {
  defaultRange,
  estimateMinutes,
  estimateSentences,
  formatClockMs,
  parseClock,
} from "./time";

describe("parseClock", () => {
  it("parses mm:ss into seconds", () => {
    expect(parseClock("00:00")).toBe(0);
    expect(parseClock("05:00")).toBe(300);
    expect(parseClock("12:34")).toBe(754);
  });

  it("accepts one to three digit minutes up to 999", () => {
    expect(parseClock("5:30")).toBe(330);
    expect(parseClock("999:59")).toBe(999 * 60 + 59);
  });

  it("ignores surrounding whitespace", () => {
    expect(parseClock("  03:00 ")).toBe(180);
  });

  it("rejects seconds above 59", () => {
    expect(parseClock("05:60")).toBeNull();
    expect(parseClock("99:99")).toBeNull();
  });

  it("rejects text that is not mm:ss", () => {
    expect(parseClock("abc")).toBeNull();
    expect(parseClock("")).toBeNull();
    expect(parseClock("5")).toBeNull();
    expect(parseClock("1:2")).toBeNull();
    expect(parseClock("-1:00")).toBeNull();
    expect(parseClock("1000:00")).toBeNull();
    expect(parseClock("01:00:00")).toBeNull();
  });
});

describe("formatClockMs", () => {
  it("pads minutes and seconds to two digits", () => {
    expect(formatClockMs(0)).toBe("00:00");
    expect(formatClockMs(65)).toBe("01:05");
    expect(formatClockMs(300)).toBe("05:00");
  });

  it("floors fractional seconds and clamps negatives to zero", () => {
    expect(formatClockMs(59.9)).toBe("00:59");
    expect(formatClockMs(-5)).toBe("00:00");
  });

  it("keeps three digit minutes", () => {
    expect(formatClockMs(754 * 60)).toBe("754:00");
  });

  it("round-trips with parseClock", () => {
    expect(parseClock(formatClockMs(754))).toBe(754);
  });
});

describe("defaultRange", () => {
  it("is null for videos up to 6 minutes", () => {
    expect(defaultRange(0)).toBeNull();
    expect(defaultRange(180)).toBeNull();
    expect(defaultRange(360)).toBeNull();
  });

  it("is 00:00 to 05:00 for longer videos", () => {
    expect(defaultRange(361)).toEqual({ start: 0, end: 300 });
    expect(defaultRange(1200)).toEqual({ start: 0, end: 300 });
  });
});

describe("estimateSentences", () => {
  it("returns d/8 to d/5 rounded", () => {
    expect(estimateSentences(300)).toEqual([38, 60]);
    expect(estimateSentences(120)).toEqual([15, 24]);
  });
});

describe("estimateMinutes", () => {
  it("is 0.8 x minutes rounded", () => {
    expect(estimateMinutes(300)).toBe(4);
    expect(estimateMinutes(600)).toBe(8);
  });

  it("is at least one minute", () => {
    expect(estimateMinutes(10)).toBe(1);
    expect(estimateMinutes(0)).toBe(1);
  });
});
