import { describe, expect, it } from "vitest";
import { resultNote, wordsMatchSegment } from "./resultView";

const PRAISE = "Rất sát bản gốc. Qua câu tiếp, hoặc thử lại để sát hơn nữa.";
const NEUTRAL =
  "Chưa thấy lỗi cụ thể nào chắc chắn; nghe lại bản gốc rồi thử lại.";

describe("resultNote (D-15)", () => {
  it("khen khi số hiển thị >= 80 và không có gợi ý", () => {
    expect(resultNote(0.8, 0)).toEqual({ kind: "praise", text: PRAISE });
    expect(resultNote(1, 0)?.kind).toBe("praise");
  });

  it("0.795 làm tròn thành 80 nên vẫn khen, cùng quy tắc với scoreLevel", () => {
    expect(resultNote(0.795, 0)?.kind).toBe("praise");
  });

  it("0.794 hiện 79 nên dùng dòng trung tính, không khen", () => {
    expect(resultNote(0.794, 0)).toEqual({ kind: "neutral", text: NEUTRAL });
  });

  it("không bao giờ khen khi dưới 80", () => {
    expect(resultNote(0.3, 0)?.kind).toBe("neutral");
    expect(resultNote(0, 0)?.kind).toBe("neutral");
    expect(resultNote(0.6, 0)?.text).toBe(NEUTRAL);
  });

  it("có gợi ý thì không có dòng nào: TipList sở hữu khối này", () => {
    expect(resultNote(0.95, 1)).toBeNull();
    expect(resultNote(0.2, 3)).toBeNull();
  });
});

describe("wordsMatchSegment (E4)", () => {
  const w = (...texts: string[]) => texts.map((text) => ({ text }));

  it("danh sách từ rỗng -> false", () => {
    expect(wordsMatchSegment([], "Hello world")).toBe(false);
  });

  it("khớp khi ghép các từ bằng một dấu cách bằng câu", () => {
    expect(wordsMatchSegment(w("Hello", "world"), "Hello world")).toBe(true);
  });

  it("chuẩn hoá khoảng trắng ở cả hai phía", () => {
    expect(wordsMatchSegment(w("Hello", "world"), "  Hello   world ")).toBe(
      true,
    );
    expect(wordsMatchSegment(w(" Hello ", "world"), "Hello world")).toBe(true);
  });

  it("thiếu từ hoặc khác từ -> false (rơi về đoạn văn thường)", () => {
    expect(wordsMatchSegment(w("Hello"), "Hello world")).toBe(false);
    expect(wordsMatchSegment(w("Hello", "word"), "Hello world")).toBe(false);
  });
});
