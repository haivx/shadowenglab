import { describe, expect, it } from "vitest";
import { pickMimeType } from "./mime";

describe("pickMimeType", () => {
  it("kiểu Chrome: ưu tiên audio/webm;codecs=opus", () => {
    const supported = new Set([
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
    ]);
    expect(pickMimeType((type) => supported.has(type))).toBe(
      "audio/webm;codecs=opus",
    );
  });

  it("kiểu Safari: chỉ có audio/mp4", () => {
    expect(pickMimeType((type) => type === "audio/mp4")).toBe("audio/mp4");
  });

  it("webm không kèm codec là phương án cuối", () => {
    expect(pickMimeType((type) => type === "audio/webm")).toBe("audio/webm");
  });

  it("không hỗ trợ gì thì trả undefined để trình duyệt tự chọn", () => {
    expect(pickMimeType(() => false)).toBeUndefined();
  });
});
