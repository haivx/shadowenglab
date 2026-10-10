// Lựa chọn hiện/ẩn IPA nhớ trên máy (Liam 2026-10-10): mặc định bật, storage lỗi thì vẫn chạy.
import { describe, expect, it } from "vitest";
import {
  IPA_PREFERENCE_KEY,
  readIpaPreference,
  writeIpaPreference,
} from "./ipaPreference";

function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
    data,
  };
}

describe("ipaPreference", () => {
  it("mặc định bật khi chưa lưu gì hoặc không có storage", () => {
    expect(readIpaPreference(memoryStorage())).toBe(true);
    expect(readIpaPreference(null)).toBe(true);
  });

  it("đọc lại đúng lựa chọn đã lưu", () => {
    const storage = memoryStorage();
    writeIpaPreference(storage, false);
    expect(storage.data.get(IPA_PREFERENCE_KEY)).toBe("0");
    expect(readIpaPreference(storage)).toBe(false);
    writeIpaPreference(storage, true);
    expect(readIpaPreference(storage)).toBe(true);
  });

  it("storage ném lỗi (chế độ riêng tư) thì đọc ra mặc định và ghi không ném", () => {
    const broken = {
      getItem: () => {
        throw new Error("denied");
      },
      setItem: () => {
        throw new Error("denied");
      },
    };
    expect(readIpaPreference(broken)).toBe(true);
    expect(() => writeIpaPreference(broken, false)).not.toThrow();
  });
});
