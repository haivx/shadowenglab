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

export type ShortcutToggle = { type: "TOGGLE_IPA" } | { type: "TOGGLE_TRANSLATION" };

export type ShortcutAction = PlayerEvent | ShortcutToggle;

export type ShortcutStateValue = string | Record<string, unknown>;

// Khung rỗng để test chạy đỏ trên assertion; hiện thực ở bước GREEN.
export function shouldHandleShortcut(event: ShortcutKeyEvent): boolean {
  return event.key.length > 0;
}

export function shortcutToAction(key: string, stateValue: ShortcutStateValue): ShortcutAction | null {
  return key.length > 0 && stateValue === "" ? { type: "TOGGLE_IPA" } : null;
}
