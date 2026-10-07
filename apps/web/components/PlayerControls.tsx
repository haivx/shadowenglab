"use client";

import { Play, RotateCcw, SkipBack, SkipForward, Square } from "lucide-react";
import { useRef, type PointerEvent } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PlayerEvent, RepeatCount } from "@/lib/player/playerMachine";
import {
  shortcutToAction,
  type ShortcutAction,
  type ShortcutStateValue,
} from "@/lib/player/shortcuts";

/** Nút bấm bằng chuột nhả focus để Space quay về hành động toàn cục (UI-SPEC Interaction Contract). */
function releaseFocus(event: PointerEvent<HTMLElement>) {
  event.currentTarget.blur();
}

const RATE_OPTIONS = [
  { value: "0.75", label: "0.75x" },
  { value: "1", label: "1x" },
] as const;

const REPEAT_OPTIONS = [
  { value: "1", label: "×1" },
  { value: "2", label: "×2" },
  { value: "3", label: "×3" },
] as const;

const RECORD_FACTOR_OPTIONS = [
  { value: "1.25", label: "+25%" },
  { value: "1.5", label: "+50%" },
  { value: "2", label: "+100%" },
] as const;

function toRepeat(value: string): RepeatCount | null {
  if (value === "1") return 1;
  if (value === "2") return 2;
  if (value === "3") return 3;
  return null;
}

function topLevelState(value: ShortcutStateValue): string {
  return typeof value === "string" ? value : (Object.keys(value)[0] ?? "");
}

/** Chỉ các sự kiện của machine; phím I/T là bật tắt UI, không đi qua nút điều khiển. */
function asPlayerEvent(action: ShortcutAction | null): PlayerEvent | null {
  if (!action) return null;
  if (action.type === "TOGGLE_IPA" || action.type === "TOGGLE_TRANSLATION") {
    return null;
  }
  return action;
}

interface SessionSelectProps {
  id: string;
  label: string;
  value: string;
  options: readonly { value: string; label: string }[];
  disabled: boolean;
  onChange: (value: string) => void;
}

/** Select có nhãn ở trên (cao 44). Chọn bằng chuột xong thì nhả focus, để Space không mở lại select. */
function SessionSelect({
  id,
  label,
  value,
  options,
  disabled,
  onChange,
}: SessionSelectProps) {
  const pickedWithPointer = useRef(false);
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <Label htmlFor={id} className="text-xs text-muted-foreground">
        {label}
      </Label>
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger id={id} className="h-11 font-medium">
          <SelectValue />
        </SelectTrigger>
        <SelectContent
          onPointerUp={() => {
            pickedWithPointer.current = true;
          }}
          onCloseAutoFocus={(event) => {
            if (!pickedWithPointer.current) return;
            pickedWithPointer.current = false;
            event.preventDefault();
            if (document.activeElement instanceof HTMLElement) {
              document.activeElement.blur();
            }
          }}
        >
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

interface PlayerControlsProps {
  /** `state.value` của playerMachine. */
  stateValue: ShortcutStateValue;
  segmentIndex: number;
  segmentCount: number;
  rate: number;
  repeat: RepeatCount;
  recordFactor: number;
  /** false cho tới khi video bắn `canplay` (UI-SPEC E7). */
  videoReady: boolean;
  send: (event: PlayerEvent) => void;
}

/** Thanh điều khiển phát của S3: Trước · Nghe câu mẫu · phát lại · Tiếp và ba select của phiên (G13). */
export function PlayerControls({
  stateValue,
  segmentIndex,
  segmentCount,
  rate,
  repeat,
  recordFactor,
  videoReady,
  send,
}: PlayerControlsProps) {
  const top = topLevelState(stateValue);
  const listening = top === "playing" || top === "previewing";
  const busy = top === "recording" || top === "scoring";

  // Nút và phím dùng chung một bảng quy tắc: nút bị khoá đúng ở trạng thái mà phím bị bỏ qua.
  const sampleEvent = asPlayerEvent(shortcutToAction(" ", stateValue));
  const replayEvent = asPlayerEvent(shortcutToAction("o", stateValue));
  const prevEvent = asPlayerEvent(shortcutToAction("ArrowLeft", stateValue));
  const nextEvent = asPlayerEvent(shortcutToAction("ArrowRight", stateValue));

  const sampleDisabled = !videoReady || busy || sampleEvent === null;
  const replayDisabled = !videoReady || replayEvent === null;
  const prevDisabled = !videoReady || segmentIndex <= 0 || prevEvent === null;
  const nextDisabled =
    !videoReady || segmentIndex >= segmentCount - 1 || nextEvent === null;
  const selectsDisabled = !videoReady || busy;

  return (
    <div
      aria-label="Điều khiển phát"
      className="flex flex-col gap-3 border-b border-border bg-card px-4 py-3.5"
    >
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="md"
          title="Câu trước (←)"
          disabled={prevDisabled}
          onPointerUp={releaseFocus}
          onClick={() => prevEvent && send(prevEvent)}
          className="px-3"
        >
          <SkipBack aria-hidden="true" />
          Trước
        </Button>
        <Button
          variant="solid"
          size="md"
          title="Nghe câu mẫu (Space)"
          kbd="Space"
          aria-pressed={listening}
          disabled={sampleDisabled}
          onPointerUp={releaseFocus}
          onClick={() => sampleEvent && send(sampleEvent)}
          className="flex-1 px-4 text-[15px]"
        >
          {listening ? (
            <Square aria-hidden="true" fill="currentColor" />
          ) : (
            <Play aria-hidden="true" fill="currentColor" />
          )}
          Nghe câu mẫu
        </Button>
        <Button
          variant="outline"
          size="icon"
          aria-label="Phát lại câu mẫu"
          title="Phát lại câu mẫu (O)"
          disabled={replayDisabled}
          onPointerUp={releaseFocus}
          onClick={() => replayEvent && send(replayEvent)}
        >
          <RotateCcw aria-hidden="true" />
        </Button>
        <Button
          variant="outline"
          size="md"
          title="Câu tiếp (→)"
          disabled={nextDisabled}
          onPointerUp={releaseFocus}
          onClick={() => nextEvent && send(nextEvent)}
          className="px-3"
        >
          Tiếp
          <SkipForward aria-hidden="true" />
        </Button>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <SessionSelect
          id="session-rate"
          label="Tốc độ"
          value={String(rate)}
          options={RATE_OPTIONS}
          disabled={selectsDisabled}
          onChange={(value) => send({ type: "SET_RATE", rate: Number(value) })}
        />
        <SessionSelect
          id="session-repeat"
          label="Lặp"
          value={String(repeat)}
          options={REPEAT_OPTIONS}
          disabled={selectsDisabled}
          onChange={(value) => {
            const next = toRepeat(value);
            if (next !== null) send({ type: "SET_REPEAT", repeat: next });
          }}
        />
        <SessionSelect
          id="session-record-factor"
          label="Thời gian ghi"
          value={String(recordFactor)}
          options={RECORD_FACTOR_OPTIONS}
          disabled={selectsDisabled}
          onChange={(value) =>
            send({ type: "SET_RECORD_FACTOR", recordFactor: Number(value) })
          }
        />
      </div>
    </div>
  );
}
