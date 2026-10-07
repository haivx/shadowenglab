import { describe, expect, it } from "vitest";
import {
  clampThumb,
  defaultRange,
  estimateMinutes,
  estimateSentences,
  formatClockMs,
  parseClock,
  validateRange,
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

describe("validateRange", () => {
  const duration = 1200;
  const formatError = "Nhập thời gian dạng mm:ss, trong khoảng 00:00–20:00.";

  it("returns the parsed range for valid input", () => {
    expect(validateRange("03:00", "08:00", duration)).toEqual({
      ok: true,
      range: { start: 180, end: 480 },
    });
  });

  it("accepts the full video span", () => {
    expect(validateRange("00:00", "20:00", duration)).toEqual({
      ok: true,
      range: { start: 0, end: 1200 },
    });
  });

  it("flags only the start field when it cannot be parsed", () => {
    expect(validateRange("abc", "08:00", duration)).toEqual({
      ok: false,
      startError: formatError,
    });
  });

  it("flags only the end field when it cannot be parsed", () => {
    expect(validateRange("03:00", "99:99", duration)).toEqual({
      ok: false,
      endError: formatError,
    });
  });

  it("flags a time beyond the video duration on that field", () => {
    expect(validateRange("00:00", "21:00", duration)).toEqual({
      ok: false,
      endError: formatError,
    });
    expect(validateRange("25:00", "08:00", duration)).toEqual({
      ok: false,
      startError: formatError,
    });
  });

  it("flags both fields when both are invalid", () => {
    expect(validateRange("", "x", duration)).toEqual({
      ok: false,
      startError: formatError,
      endError: formatError,
    });
  });

  it("puts the order error on the end field when end is not after start", () => {
    expect(validateRange("08:00", "03:00", duration)).toEqual({
      ok: false,
      endError: "Kết thúc phải sau Bắt đầu.",
    });
    expect(validateRange("05:00", "05:00", duration)).toEqual({
      ok: false,
      endError: "Kết thúc phải sau Bắt đầu.",
    });
  });

  it("does not report an order error while a field is unparsable", () => {
    expect(validateRange("zz", "00:00", duration)).toEqual({
      ok: false,
      startError: formatError,
    });
  });
});

describe("clampThumb", () => {
  it("moves by one second", () => {
    expect(clampThumb(100, 1, false, 600)).toBe(101);
    expect(clampThumb(100, -1, false, 600)).toBe(99);
  });

  it("moves by ten seconds with Shift", () => {
    expect(clampThumb(100, 1, true, 600)).toBe(110);
    expect(clampThumb(100, -1, true, 600)).toBe(90);
  });

  it("stays within 0 and the duration", () => {
    expect(clampThumb(0, -1, false, 600)).toBe(0);
    expect(clampThumb(5, -1, true, 600)).toBe(0);
    expect(clampThumb(600, 1, false, 600)).toBe(600);
    expect(clampThumb(595, 1, true, 600)).toBe(600);
  });
});
