"use client";

import { ArrowRight, Mic, Play, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PlayerEvent } from "@/lib/player/playerMachine";
import {
  shortcutToAction,
  type ShortcutAction,
  type ShortcutStateValue,
} from "@/lib/player/shortcuts";
import { releaseFocusOnPointerUp } from "@/lib/player/useShortcuts";

/** Nút nghe lại đang phát (để `aria-pressed` và đổi icon play → stop). */
export type ActiveListen = "original" | "yours" | "both" | null;

function topLevelState(value: ShortcutStateValue): string {
  return typeof value === "string" ? value : (Object.keys(value)[0] ?? "");
}

/**
 * Nút nào đang phát theo `state.value`: previewing là `Bản gốc` (O ở idle);
 * ở reviewing / noVoice / error / scoring thì trạng thái con `original | yours | both`.
 */
export function activeListen(value: ShortcutStateValue): ActiveListen {
  if (typeof value === "string") {
    return value === "previewing" ? "original" : null;
  }
  const child = Object.values(value)[0];
  return child === "original" || child === "yours" || child === "both"
    ? child
    : null;
}

/** Chỉ sự kiện của machine; I/T là bật tắt UI và không đi qua footer. */
function asPlayerEvent(action: ShortcutAction | null): PlayerEvent | null {
  if (!action) return null;
  if (action.type === "TOGGLE_IPA" || action.type === "TOGGLE_TRANSLATION") {
    return null;
  }
  return action;
}

const PRESSED_ORIGINAL =
  "aria-pressed:shadow-[inset_0_0_0_2px_var(--original-text)]";
const PRESSED_YOU = "aria-pressed:shadow-[inset_0_0_0_2px_var(--you-text)]";
const PRESSED_NEUTRAL =
  "aria-pressed:shadow-[inset_0_0_0_2px_var(--foreground)]";

interface ResultActionBarProps {
  /** `state.value` của playerMachine. */
  stateValue: ShortcutStateValue;
  segmentIndex: number;
  segmentCount: number;
  /** Câu hiện tại đã có bản ghi trong phiên này (D-07). */
  hasRecording: boolean;
  /** false cho tới khi video `canplay`: khoá các nút cần phát video. */
  videoReady: boolean;
  send: (event: PlayerEvent) => void;
}

/**
 * Footer dính đáy của S3 (UI-SPEC "Footer", G10), hiện ở mọi trạng thái.
 * Nút và phím dùng chung bảng `shortcutToAction`: nút bị khoá đúng chỗ phím bị bỏ qua.
 * `Của bạn` / `Lần lượt cả hai` dùng `aria-disabled` (không `disabled`) cho tới khi có bản ghi.
 */
export function ResultActionBar({
  stateValue,
  segmentIndex,
  segmentCount,
  hasRecording,
  videoReady,
  send,
}: ResultActionBarProps) {
  const top = topLevelState(stateValue);
  const recording = top === "recording";
  const active = activeListen(stateValue);

  const originalEvent = asPlayerEvent(shortcutToAction("o", stateValue));
  const yoursEvent = asPlayerEvent(shortcutToAction("m", stateValue));
  const bothEvent = asPlayerEvent(shortcutToAction("b", stateValue));
  const recordEvent = asPlayerEvent(shortcutToAction("r", stateValue));
  const stopEvent = asPlayerEvent(shortcutToAction(" ", stateValue));
  const nextEvent = asPlayerEvent(shortcutToAction("ArrowRight", stateValue));

  const originalDisabled = !videoReady || originalEvent === null;
  const yoursDisabled = !hasRecording || yoursEvent === null;
  const bothDisabled = !videoReady || !hasRecording || bothEvent === null;
  const isLast = segmentIndex >= segmentCount - 1;
  const nextDisabled = isLast || nextEvent === null;

  // `aria-disabled` giữ nút trong thứ tự Tab; bấm vào khi đang khoá thì bỏ qua.
  const fire = (event: PlayerEvent | null, disabled: boolean) => () => {
    if (!disabled && event) send(event);
  };

  return (
    <footer
      aria-label="Hành động với kết quả"
      className="sticky bottom-0 flex flex-wrap items-center gap-2.5 border-t border-[color:var(--slate-5)] bg-card px-6 py-3"
    >
      <span className="mr-1 text-[13px] font-semibold text-muted-foreground">
        Nghe lại
      </span>
      <Button
        variant="soft-original"
        kbd="O"
        title="Nghe lại bản gốc (O)"
        aria-pressed={active === "original"}
        disabled={originalDisabled}
        onPointerUp={releaseFocusOnPointerUp}
        onClick={fire(originalEvent, originalDisabled)}
        className={`px-3.5 ${PRESSED_ORIGINAL}`}
      >
        {active === "original" ? (
          <Square aria-hidden="true" fill="currentColor" />
        ) : (
          <Play aria-hidden="true" fill="currentColor" />
        )}
        Bản gốc
      </Button>
      <Button
        variant="soft-you"
        kbd="M"
        title="Nghe lại bản của bạn (M)"
        aria-pressed={active === "yours"}
        aria-disabled={yoursDisabled}
        onPointerUp={releaseFocusOnPointerUp}
        onClick={fire(yoursEvent, yoursDisabled)}
        className={`px-3.5 aria-disabled:opacity-50 ${PRESSED_YOU}`}
      >
        {active === "yours" ? (
          <Square aria-hidden="true" fill="currentColor" />
        ) : (
          <Play aria-hidden="true" fill="currentColor" />
        )}
        Của bạn
      </Button>
      <Button
        variant="outline"
        kbd="B"
        title="Nghe lần lượt bản gốc rồi bản của bạn (B)"
        aria-pressed={active === "both"}
        aria-disabled={bothDisabled}
        onPointerUp={releaseFocusOnPointerUp}
        onClick={fire(bothEvent, bothDisabled)}
        className={`px-3.5 aria-disabled:opacity-50 ${PRESSED_NEUTRAL}`}
      >
        Lần lượt cả hai
      </Button>
      <span className="flex-1" />
      {recording ? (
        <Button
          variant="outline"
          size="lg"
          kbd="Space"
          title="Dừng ghi (Space)"
          onPointerUp={releaseFocusOnPointerUp}
          onClick={fire(stopEvent, stopEvent === null)}
        >
          <Square aria-hidden="true" fill="currentColor" />
          Dừng ghi
        </Button>
      ) : (
        <Button
          variant="outline"
          size="lg"
          kbd="R"
          title="Ghi lại (R)"
          disabled={recordEvent === null}
          onPointerUp={releaseFocusOnPointerUp}
          onClick={fire(recordEvent, recordEvent === null)}
        >
          <Mic aria-hidden="true" />
          Ghi lại
        </Button>
      )}
      <Button
        variant="solid"
        size="lg"
        title={isLast ? "Đây là câu cuối" : "Câu tiếp (→)"}
        disabled={nextDisabled}
        onPointerUp={releaseFocusOnPointerUp}
        onClick={fire(nextEvent, nextDisabled)}
        className="px-5"
      >
        Câu tiếp
        <ArrowRight aria-hidden="true" />
      </Button>
    </footer>
  );
}
