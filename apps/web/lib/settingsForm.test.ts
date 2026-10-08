import { describe, expect, it } from "vitest";
import {
  PLAYBACK_RATE_OPTIONS,
  RECORD_FACTOR_OPTIONS,
  REPEAT_OPTIONS,
  dataDirNote,
  initialField,
  optionLabel,
  settingsReducer,
  snapToOption,
} from "./settingsForm";

describe("settingsReducer", () => {
  it("change hiện giá trị mới ngay, giữ giá trị đã lưu cũ và chuyển sang saving", () => {
    const state = settingsReducer(initialField("1x"), {
      type: "change",
      value: "0.75x",
    });
    expect(state).toEqual({
      display: "0.75x",
      saved: "1x",
      status: "saving",
      pending: "0.75x",
    });
  });

  it("lưu thành công: giá trị mới thành giá trị đã lưu, status saved", () => {
    const saving = settingsReducer(initialField(1), {
      type: "change",
      value: 2,
    });
    const state = settingsReducer(saving, { type: "success", value: 2 });
    expect(state.display).toBe(2);
    expect(state.saved).toBe(2);
    expect(state.status).toBe("saved");
    expect(state.pending).toBeUndefined();
  });

  it("lưu thất bại: hoàn tác về giá trị đã lưu, status error, nhớ giá trị chờ để thử lại", () => {
    const saving = settingsReducer(initialField(1.5), {
      type: "change",
      value: 2,
    });
    const state = settingsReducer(saving, { type: "failure", value: 2 });
    expect(state.display).toBe(1.5);
    expect(state.saved).toBe(1.5);
    expect(state.status).toBe("error");
    expect(state.pending).toBe(2);
  });

  it("không bao giờ hiện giá trị chưa lưu như đã lưu sau khi thất bại", () => {
    const failed = settingsReducer(
      settingsReducer(initialField(1), { type: "change", value: 3 }),
      { type: "failure", value: 3 },
    );
    expect(failed.display).toBe(failed.saved);
    expect(failed.status).not.toBe("saved");
  });

  it("retry gửi lại giá trị chờ: hiện lại giá trị đó và quay về saving", () => {
    const failed = settingsReducer(
      settingsReducer(initialField(1), { type: "change", value: 3 }),
      { type: "failure", value: 3 },
    );
    const state = settingsReducer(failed, { type: "retry" });
    expect(state).toEqual({
      display: 3,
      saved: 1,
      status: "saving",
      pending: 3,
    });
  });

  it("retry khi không có giá trị chờ thì không đổi gì", () => {
    const state = initialField(1);
    expect(settingsReducer(state, { type: "retry" })).toBe(state);
  });

  it("phản hồi thành công của lần đổi cũ không che lần đổi mới hơn đang lưu", () => {
    let state = settingsReducer(initialField(1), { type: "change", value: 2 });
    state = settingsReducer(state, { type: "change", value: 3 });
    state = settingsReducer(state, { type: "success", value: 2 });
    expect(state.saved).toBe(2);
    expect(state.display).toBe(3);
    expect(state.status).toBe("saving");
    state = settingsReducer(state, { type: "success", value: 3 });
    expect(state.status).toBe("saved");
    expect(state.saved).toBe(3);
  });

  it("phản hồi lỗi của lần đổi cũ bị bỏ qua khi đã có lần đổi mới hơn", () => {
    let state = settingsReducer(initialField(1), { type: "change", value: 2 });
    state = settingsReducer(state, { type: "change", value: 3 });
    const after = settingsReducer(state, { type: "failure", value: 2 });
    expect(after).toBe(state);
  });
});

describe("tuỳ chọn và nhãn", () => {
  it("thời gian ghi: +25% ↔ 1.25, +50% ↔ 1.5, +100% ↔ 2.0", () => {
    expect(RECORD_FACTOR_OPTIONS.map((o) => [o.label, o.value])).toEqual([
      ["+25%", 1.25],
      ["+50%", 1.5],
      ["+100%", 2],
    ]);
    expect(optionLabel(RECORD_FACTOR_OPTIONS, 1.5)).toBe("+50%");
  });

  it("tốc độ: 0.75 ↔ 0.75x, 1 ↔ 1x", () => {
    expect(PLAYBACK_RATE_OPTIONS.map((o) => [o.label, o.value])).toEqual([
      ["0.75x", 0.75],
      ["1x", 1],
    ]);
    expect(optionLabel(PLAYBACK_RATE_OPTIONS, 0.75)).toBe("0.75x");
  });

  it("số lần lặp: ×1, ×2, ×3", () => {
    expect(REPEAT_OPTIONS.map((o) => o.label)).toEqual(["×1", "×2", "×3"]);
    expect(optionLabel(REPEAT_OPTIONS, 3)).toBe("×3");
  });

  it("giá trị lạ không có nhãn; snapToOption chọn tuỳ chọn gần nhất", () => {
    expect(optionLabel(PLAYBACK_RATE_OPTIONS, 0.9)).toBeUndefined();
    expect(snapToOption(PLAYBACK_RATE_OPTIONS, 0.9).value).toBe(1);
    expect(snapToOption(PLAYBACK_RATE_OPTIONS, 0.6).value).toBe(0.75);
    expect(snapToOption(RECORD_FACTOR_OPTIONS, 1.5).value).toBe(1.5);
  });
});

describe("dataDirNote", () => {
  it("thư mục mới khác thư mục đang dùng: nhắc khởi động lại và nêu thư mục cũ", () => {
    expect(dataDirNote("/new", "/old")).toBe(
      "Khởi động lại make dev để áp dụng; dữ liệu cũ vẫn ở /old.",
    );
  });

  it("đặt lại đúng thư mục đang dùng thì không cần khởi động lại", () => {
    expect(dataDirNote("/old", "/old")).toBe("Đã lưu");
  });
});
