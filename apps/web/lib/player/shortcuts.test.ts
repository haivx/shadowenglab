import { describe, expect, it } from "vitest";
import {
  shortcutToAction,
  shouldHandleShortcut,
  type ShortcutKeyEvent,
  type ShortcutTarget,
} from "./shortcuts";

function target(
  overrides: Partial<ShortcutTarget> & { role?: string } = {},
): ShortcutTarget {
  const { role, ...rest } = overrides;
  return {
    tagName: "DIV",
    isContentEditable: false,
    getAttribute: (name) => (name === "role" && role ? role : null),
    closest: () => null,
    ...rest,
  };
}

function keyEvent(overrides: Partial<ShortcutKeyEvent> = {}): ShortcutKeyEvent {
  return {
    key: " ",
    target: target(),
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    repeat: false,
    ...overrides,
  };
}

describe("shouldHandleShortcut", () => {
  it("true cho target là BUTTON hoặc body, và khi không có target", () => {
    expect(
      shouldHandleShortcut(keyEvent({ target: target({ tagName: "BUTTON" }) })),
    ).toBe(true);
    expect(
      shouldHandleShortcut(keyEvent({ target: target({ tagName: "BODY" }) })),
    ).toBe(true);
    expect(shouldHandleShortcut(keyEvent({ target: null }))).toBe(true);
  });

  it.each(["INPUT", "TEXTAREA", "SELECT", "input"])(
    "false khi focus ở %s",
    (tagName) => {
      expect(
        shouldHandleShortcut(keyEvent({ target: target({ tagName }) })),
      ).toBe(false);
    },
  );

  it.each(["combobox", "listbox"])("false khi focus ở role=%s", (role) => {
    expect(shouldHandleShortcut(keyEvent({ target: target({ role }) }))).toBe(
      false,
    );
  });

  it("false khi target nằm trong một listbox/combobox (ví dụ option của Select)", () => {
    const inListbox = target({
      closest: (selector) =>
        selector === '[role="listbox"], [role="combobox"]' ? {} : null,
    });
    expect(shouldHandleShortcut(keyEvent({ target: inListbox }))).toBe(false);
  });

  it("false khi contenteditable", () => {
    expect(
      shouldHandleShortcut(
        keyEvent({ target: target({ isContentEditable: true }) }),
      ),
    ).toBe(false);
  });

  it("false khi target nằm trong dialog đang mở", () => {
    const inDialog = target({
      tagName: "BUTTON",
      closest: (selector) => (selector === '[role="dialog"]' ? {} : null),
    });
    expect(shouldHandleShortcut(keyEvent({ target: inDialog }))).toBe(false);
  });

  it.each(["ctrlKey", "metaKey", "altKey"] as const)(
    "false khi giữ %s",
    (modifier) => {
      expect(shouldHandleShortcut(keyEvent({ [modifier]: true }))).toBe(false);
    },
  );

  it("false khi phím lặp (giữ phím)", () => {
    expect(shouldHandleShortcut(keyEvent({ repeat: true }))).toBe(false);
  });
});

describe("shortcutToAction", () => {
  it("Space theo trạng thái", () => {
    expect(shortcutToAction(" ", "idle")).toEqual({ type: "PLAY" });
    expect(shortcutToAction(" ", "playing")).toEqual({ type: "STOP" });
    expect(shortcutToAction(" ", "previewing")).toEqual({ type: "STOP" });
    expect(shortcutToAction(" ", "recording")).toEqual({ type: "STOP" });
    expect(shortcutToAction(" ", "scoring")).toBeNull();
    for (const state of ["reviewing", "noVoice", "error"]) {
      expect(shortcutToAction(" ", state)).toEqual({ type: "PLAY" });
    }
  });

  it("R chỉ hoạt động ở idle, reviewing, noVoice, error", () => {
    expect(shortcutToAction("r", "idle")).toEqual({ type: "RECORD" });
    expect(shortcutToAction("r", "reviewing")).toEqual({ type: "RECORD" });
    expect(shortcutToAction("r", "noVoice")).toEqual({ type: "RECORD" });
    expect(shortcutToAction("r", "error")).toEqual({ type: "RECORD" });
    expect(shortcutToAction("r", "playing")).toBeNull();
    expect(shortcutToAction("r", "recording")).toBeNull();
    expect(shortcutToAction("r", "scoring")).toBeNull();
  });

  it("mũi tên chuyển câu, bị bỏ qua khi ghi hoặc xử lý", () => {
    expect(shortcutToAction("ArrowRight", "reviewing")).toEqual({
      type: "NEXT",
    });
    expect(shortcutToAction("ArrowLeft", "idle")).toEqual({ type: "PREV" });
    expect(shortcutToAction("ArrowRight", "playing")).toEqual({ type: "NEXT" });
    expect(shortcutToAction("ArrowLeft", "recording")).toBeNull();
    expect(shortcutToAction("ArrowRight", "scoring")).toBeNull();
  });

  it("O: nghe mẫu một lần ở idle, LISTEN_ORIGINAL ở reviewing/noVoice/error, bỏ qua khi phát/ghi", () => {
    expect(shortcutToAction("o", "idle")).toEqual({ type: "PREVIEW" });
    expect(shortcutToAction("o", "reviewing")).toEqual({
      type: "LISTEN_ORIGINAL",
    });
    expect(shortcutToAction("o", "noVoice")).toEqual({
      type: "LISTEN_ORIGINAL",
    });
    expect(shortcutToAction("o", "playing")).toBeNull();
    expect(shortcutToAction("o", "recording")).toBeNull();
  });

  it("M và B nghe lại bản ghi", () => {
    expect(shortcutToAction("m", "reviewing")).toEqual({
      type: "LISTEN_YOURS",
    });
    expect(shortcutToAction("m", "scoring")).toEqual({ type: "LISTEN_YOURS" });
    expect(shortcutToAction("m", "recording")).toBeNull();
    expect(shortcutToAction("b", "noVoice")).toEqual({ type: "LISTEN_BOTH" });
    expect(shortcutToAction("b", "scoring")).toBeNull();
  });

  it("I và T bật tắt IPA / dịch ở mọi trạng thái", () => {
    for (const state of [
      "idle",
      "playing",
      "recording",
      "scoring",
      "reviewing",
      "noVoice",
      "error",
    ]) {
      expect(shortcutToAction("i", state)).toEqual({ type: "TOGGLE_IPA" });
      expect(shortcutToAction("t", state)).toEqual({
        type: "TOGGLE_TRANSLATION",
      });
    }
  });

  it("phím hoa hoạt động như phím thường", () => {
    expect(shortcutToAction("R", "idle")).toEqual({ type: "RECORD" });
    expect(shortcutToAction("O", "idle")).toEqual({ type: "PREVIEW" });
    expect(shortcutToAction("I", "playing")).toEqual({ type: "TOGGLE_IPA" });
  });

  it("nhận state.value dạng object (trạng thái con): lấy khoá cấp trên cùng", () => {
    expect(shortcutToAction(" ", { reviewing: "yours" })).toEqual({
      type: "PLAY",
    });
    expect(shortcutToAction("m", { scoring: "idle" })).toEqual({
      type: "LISTEN_YOURS",
    });
  });

  it("phím không có trong bảng trả null", () => {
    expect(shortcutToAction("x", "idle")).toBeNull();
    expect(shortcutToAction("Enter", "reviewing")).toBeNull();
  });
});
