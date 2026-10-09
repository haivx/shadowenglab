"use client";

import { useEffect, type PointerEvent } from "react";
import type { ActorRefFrom } from "xstate";
import type { playerMachine } from "./playerMachine";
import {
  allowShortcutAction,
  shortcutToAction,
  shouldHandleShortcut,
  type ShortcutToggle,
} from "./shortcuts";

/** Phần của actor mà hook cần: gửi sự kiện và đọc `state.value` tại thời điểm bấm phím. */
type PlayerActor = Pick<
  ActorRefFrom<typeof playerMachine>,
  "send" | "getSnapshot"
>;

/**
 * Nút bấm bằng chuột nhả focus ngay khi thả chuột, để Space quay về hành động toàn cục.
 * Nút focus bằng Tab thì không bị ảnh hưởng và giữ Space/Enter gốc (UI-SPEC Interaction Contract).
 */
export function releaseFocusOnPointerUp(
  event: PointerEvent<HTMLElement>,
): void {
  event.currentTarget.blur();
}

/** Space/Enter kích hoạt phần tử tương tác đang focus bằng Tab thì để trình duyệt xử lý. */
const NATIVE_ACTIVATION = 'button, a[href], summary, [role="button"]';

export interface UseShortcutsOptions {
  /** I / T: bật tắt IPA và bản dịch (02-18 xử lý). Không truyền thì hai phím này bị bỏ qua. */
  onToggle?: (toggle: ShortcutToggle) => void;
  /** false khi video chưa `canplay` hoặc lỗi: bỏ qua phím làm video phát. */
  videoReady?: boolean;
  /**
   * false khi lượt đang xem không còn bản ghi trong phiên: M/B không làm gì (D-11, FBK-04).
   * Mặc định true.
   */
  yoursEnabled?: boolean;
}

/**
 * Một listener `keydown` trên window cho phòng tập (PLY-07).
 * `shouldHandleShortcut` → `shortcutToAction(key, state.value)` → `preventDefault()` chỉ khi có hành động.
 * Gỡ listener khi unmount nên an toàn với StrictMode.
 */
export function useShortcuts(
  actor: PlayerActor,
  {
    onToggle,
    videoReady = true,
    yoursEnabled = true,
  }: UseShortcutsOptions = {},
): void {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (
        !shouldHandleShortcut({
          key: event.key,
          target,
          ctrlKey: event.ctrlKey,
          metaKey: event.metaKey,
          altKey: event.altKey,
          repeat: event.repeat,
        })
      ) {
        return;
      }
      if (event.key === " " && target?.closest(NATIVE_ACTIVATION)) return;

      const action = shortcutToAction(event.key, actor.getSnapshot().value);
      if (action === null) return;

      if (
        action.type === "TOGGLE_IPA" ||
        action.type === "TOGGLE_TRANSLATION"
      ) {
        if (!onToggle) return;
        event.preventDefault();
        onToggle(action);
        return;
      }
      if (!allowShortcutAction(action, { videoReady, yoursEnabled })) return;

      event.preventDefault();
      actor.send(action);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [actor, onToggle, videoReady, yoursEnabled]);
}
