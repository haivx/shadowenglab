import type { Word } from "@shadowenglab/contracts";
import { describe, expect, it } from "vitest";
import { ipaLine } from "./ipaLine";

function word(i: number, text: string, ipa?: string): Word {
  return { i, text, start: i, end: i + 1, asrProb: 0.9, ipa };
}

describe("ipaLine", () => {
  it("nối IPA của các từ trong một cặp dấu gạch chéo, từ thiếu IPA thành —", () => {
    const result = ipaLine([
      word(0, "an", "ən"),
      word(1, "honestly", "ɑnɪstli"),
      word(2, "uh"),
      word(3, "expect", "ɪkspɛkt"),
    ]);
    expect(result).toEqual({
      text: "/ən ɑnɪstli — ɪkspɛkt/",
      allMissing: false,
    });
  });

  it("không từ nào có IPA: allMissing", () => {
    const result = ipaLine([word(0, "an"), word(1, "honestly", "")]);
    expect(result.allMissing).toBe(true);
    expect(result.text).toBe("/— —/");
  });

  it("một từ có IPA", () => {
    expect(ipaLine([word(0, "hello", "həloʊ")])).toEqual({
      text: "/həloʊ/",
      allMissing: false,
    });
  });

  it("mảng rỗng: allMissing", () => {
    expect(ipaLine([]).allMissing).toBe(true);
  });

  it("không sinh IPA từ chữ: từ không có ipa luôn là —", () => {
    expect(ipaLine([word(0, "cat")]).text).toBe("/—/");
  });
});
