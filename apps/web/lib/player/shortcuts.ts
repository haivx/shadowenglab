// Quy tắc phím tắt thuần (PLY-07, RESEARCH Pitfall 12). Không đụng DOM: nhận đối tượng cấu trúc,
// UI truyền KeyboardEvent thật. Người gọi chỉ `preventDefault()` khi `shortcutToAction` trả khác null.
import type { PlayerEvent } from "./playerMachine";

export type ShortcutTarget = {
  tagName: string;
  isContentEditable?: boolean;
  getAttribute(name: string): string | null;
  closest(selector: string): unknown;
};

export type ShortcutKeyEvent = {
  key: string;
  target: ShortcutTarget | null;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  repeat: boolean;
};

/** Bật tắt thuộc về state UI, không đi vào machine. */
export type ShortcutToggle =
  { type: "TOGGLE_IPA" } | { type: "TOGGLE_TRANSLATION" };

export type ShortcutAction = PlayerEvent | ShortcutToggle;

/** `state.value` của machine: chuỗi, hoặc object khi đang ở trạng thái con (reviewing.yours). */
export type ShortcutStateValue = string | Record<string, unknown>;

const TEXT_FIELD_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);
const POPUP_ROLES = new Set(["combobox", "listbox"]);
const POPUP_SELECTOR = '[role="listbox"], [role="combobox"]';
const DIALOG_SELECTOR = '[role="dialog"]';

export function shouldHandleShortcut(event: ShortcutKeyEvent): boolean {
  if (event.repeat || event.ctrlKey || event.metaKey || event.altKey)
    return false;

  const target = event.target;
  if (!target) return true;

  if (TEXT_FIELD_TAGS.has(target.tagName.toUpperCase())) return false;
  if (target.isContentEditable) return false;

  const role = target.getAttribute("role");
  if (role !== null && POPUP_ROLES.has(role)) return false;
  if (target.closest(POPUP_SELECTOR)) return false;
  if (target.closest(DIALOG_SELECTOR)) return false;

  return true;
}

type Key = "space" | "r" | "left" | "right" | "o" | "m" | "b";
type StateGroup =
  "idle" | "listening" | "recording" | "processing" | "afterAttempt";

const KEY_BY_INPUT: Record<string, Key> = {
  " ": "space",
  r: "r",
  ArrowLeft: "left",
  ArrowRight: "right",
  o: "o",
  m: "m",
  b: "b",
};

const GROUP_BY_STATE: Record<string, StateGroup> = {
  idle: "idle",
  playing: "listening",
  previewing: "listening",
  recording: "recording",
  scoring: "processing",
  reviewing: "afterAttempt",
  noVoice: "afterAttempt",
  error: "afterAttempt",
};

const PREV: PlayerEvent = { type: "PREV" };
const NEXT: PlayerEvent = { type: "NEXT" };

// Bảng phím theo cột trạng thái của UI-SPEC "Interaction Contract". Ô trống = bỏ qua.
const TABLE: Record<StateGroup, Partial<Record<Key, PlayerEvent>>> = {
  idle: {
    space: { type: "PLAY" },
    r: { type: "RECORD" },
    left: PREV,
    right: NEXT,
    o: { type: "PREVIEW" },
    // M/B ở idle chỉ chạy khi câu đã có bản ghi: machine tự bỏ qua nếu chưa có.
    m: { type: "LISTEN_YOURS" },
    b: { type: "LISTEN_BOTH" },
  },
  listening: { space: { type: "STOP" }, left: PREV, right: NEXT },
  recording: { space: { type: "STOP" } },
  processing: { m: { type: "LISTEN_YOURS" } },
  afterAttempt: {
    space: { type: "PLAY" },
    r: { type: "RECORD" },
    left: PREV,
    right: NEXT,
    o: { type: "LISTEN_ORIGINAL" },
    m: { type: "LISTEN_YOURS" },
    b: { type: "LISTEN_BOTH" },
  },
};

function topLevelState(stateValue: ShortcutStateValue): string {
  if (typeof stateValue === "string") return stateValue;
  return Object.keys(stateValue)[0] ?? "";
}

export function shortcutToAction(
  key: string,
  stateValue: ShortcutStateValue,
): ShortcutAction | null {
  const normalized = key.length === 1 ? key.toLowerCase() : key;

  // I và T luôn hoạt động, ở mọi trạng thái.
  if (normalized === "i") return { type: "TOGGLE_IPA" };
  if (normalized === "t") return { type: "TOGGLE_TRANSLATION" };

  const mapped = KEY_BY_INPUT[normalized];
  const group = GROUP_BY_STATE[topLevelState(stateValue)];
  if (mapped === undefined || group === undefined) return null;
  return TABLE[group][mapped] ?? null;
}
