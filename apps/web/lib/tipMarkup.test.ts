import { describe, expect, it } from "vitest";
import { splitTipMarkup } from "./tipMarkup";

describe("splitTipMarkup", () => {
  it("tách hai từ được đánh dấu và đánh số theo thứ tự", () => {
    expect(splitTipMarkup("Nhấn vào *expect*, không phải *honestly*.")).toEqual(
      [
        { kind: "text", value: "Nhấn vào " },
        { kind: "word", value: "expect", ordinal: 0 },
        { kind: "text", value: ", không phải " },
        { kind: "word", value: "honestly", ordinal: 1 },
        { kind: "text", value: "." },
      ],
    );
  });

  it("câu không có dấu * là một đoạn chữ", () => {
    const text = "Giọng hơi phẳng; lên xuống rõ hơn theo bản gốc.";
    expect(splitTipMarkup(text)).toEqual([{ kind: "text", value: text }]);
  });

  it("dấu * lẻ hiển thị nguyên văn", () => {
    expect(splitTipMarkup("a *b")).toEqual([{ kind: "text", value: "a *b" }]);
  });

  it("cặp ** rỗng không phải từ, giữ nguyên văn", () => {
    expect(splitTipMarkup("**")).toEqual([{ kind: "text", value: "**" }]);
  });

  it("HTML chỉ là chữ, không bị diễn giải", () => {
    expect(splitTipMarkup("<b>x</b> *y*")).toEqual([
      { kind: "text", value: "<b>x</b> " },
      { kind: "word", value: "y", ordinal: 0 },
    ]);
  });

  it("từ ở đầu và cuối câu không sinh đoạn chữ rỗng", () => {
    expect(splitTipMarkup("*a* b *c*")).toEqual([
      { kind: "word", value: "a", ordinal: 0 },
      { kind: "text", value: " b " },
      { kind: "word", value: "c", ordinal: 1 },
    ]);
  });

  it("chuỗi rỗng không có đoạn nào", () => {
    expect(splitTipMarkup("")).toEqual([]);
  });
});
