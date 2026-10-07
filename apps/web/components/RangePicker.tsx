"use client";

import { Slider as SliderPrimitive } from "radix-ui";
import { useEffect, useId, useState } from "react";
import { Input } from "@/components/ui/input";
import {
  DEFAULT_RANGE_END_SEC,
  defaultRange,
  estimateMinutes,
  estimateSentences,
  formatClockMs,
  validateRange,
  type TimeRange,
} from "@/lib/time";

export interface RangePickerProps {
  durationSec: number;
  /** Đoạn hợp lệ, hoặc null khi một ô giờ đang sai (khoá `Tạo bài`). */
  onChange: (range: TimeRange | null) => void;
}

const THUMB_CLASS =
  "block size-6 shrink-0 rounded-full border-2 border-foreground bg-white";

/**
 * Chọn đoạn 2–5 phút trên video dài hơn 6 phút (LES-02): thanh trượt hai thumb
 * + hai ô mm:ss đồng bộ. Phím mũi tên dịch 1 giây, Shift+mũi tên 10 giây
 * (Radix Slider, step = 1 s). Ô sai chỉ báo lỗi ở chính ô đó; thumb giữ đoạn
 * hợp lệ cuối cùng.
 */
export function RangePicker({ durationSec, onChange }: RangePickerProps) {
  const max = Math.floor(durationSec);
  const initial = defaultRange(durationSec) ?? { start: 0, end: max };
  const [thumbs, setThumbs] = useState<[number, number]>([
    initial.start,
    Math.min(initial.end, max),
  ]);
  const [startText, setStartText] = useState(formatClockMs(initial.start));
  const [endText, setEndText] = useState(
    formatClockMs(Math.min(initial.end, max)),
  );
  const [touched, setTouched] = useState({ start: false, end: false });
  const startId = useId();
  const endId = useId();

  const validation = validateRange(startText, endText, durationSec);
  const startError =
    touched.start && !validation.ok ? validation.startError : undefined;
  const endError =
    touched.end && !validation.ok ? validation.endError : undefined;

  const validStart = validation.ok ? validation.range.start : undefined;
  const validEnd = validation.ok ? validation.range.end : undefined;
  useEffect(() => {
    onChange(
      validStart !== undefined && validEnd !== undefined
        ? { start: validStart, end: validEnd }
        : null,
    );
  }, [validStart, validEnd, onChange]);

  function handleSlider([start, end]: number[]) {
    if (start === undefined || end === undefined) return;
    setThumbs([start, end]);
    setStartText(formatClockMs(start));
    setEndText(formatClockMs(end));
  }

  function handleText(field: "start" | "end", value: string) {
    const nextStart = field === "start" ? value : startText;
    const nextEnd = field === "end" ? value : endText;
    if (field === "start") setStartText(value);
    else setEndText(value);
    const result = validateRange(nextStart, nextEnd, durationSec);
    if (result.ok) setThumbs([result.range.start, result.range.end]);
  }

  const seconds = thumbs[1] - thumbs[0];
  const [low, high] = estimateSentences(seconds);

  return (
    <div className="flex flex-col gap-3.5">
      <div className="flex flex-col gap-1">
        <span className="text-sm font-semibold">Chọn đoạn để tập</span>
        <span className="text-[13px] text-muted-foreground">
          Video dài hơn 6 phút. Một buổi tập nên dùng 2–5 phút.
        </span>
      </div>

      <SliderPrimitive.Root
        data-slot="range-picker-slider"
        value={thumbs}
        onValueChange={handleSlider}
        min={0}
        max={max}
        step={1}
        minStepsBetweenThumbs={1}
        className="relative flex h-10 w-full touch-none select-none items-center"
      >
        <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-[3px] bg-muted">
          <SliderPrimitive.Range className="absolute h-full bg-foreground" />
        </SliderPrimitive.Track>
        <SliderPrimitive.Thumb
          aria-label={`Điểm bắt đầu ${formatClockMs(thumbs[0])}`}
          className={THUMB_CLASS}
        />
        <SliderPrimitive.Thumb
          aria-label={`Điểm kết thúc ${formatClockMs(thumbs[1])}`}
          className={THUMB_CLASS}
        />
      </SliderPrimitive.Root>

      <div className="flex flex-wrap items-end gap-4">
        <label
          htmlFor={startId}
          className="flex flex-col gap-1.5 text-[13px] text-muted-foreground"
        >
          Bắt đầu
          <Input
            id={startId}
            inputMode="numeric"
            autoComplete="off"
            value={startText}
            onChange={(event) => handleText("start", event.target.value)}
            onBlur={() => setTouched((state) => ({ ...state, start: true }))}
            aria-invalid={startError !== undefined}
            aria-describedby={startError ? `${startId}-error` : undefined}
            className="w-[120px] px-3 font-mono text-[15px]"
          />
        </label>
        <label
          htmlFor={endId}
          className="flex flex-col gap-1.5 text-[13px] text-muted-foreground"
        >
          Kết thúc
          <Input
            id={endId}
            inputMode="numeric"
            autoComplete="off"
            value={endText}
            onChange={(event) => handleText("end", event.target.value)}
            onBlur={() => setTouched((state) => ({ ...state, end: true }))}
            aria-invalid={endError !== undefined}
            aria-describedby={endError ? `${endId}-error` : undefined}
            className="w-[120px] px-3 font-mono text-[15px]"
          />
        </label>
        <div className="flex flex-col justify-end gap-0.5 pb-1 text-[13px] text-muted-foreground">
          <span>
            ≈ {low}–{high} câu
          </span>
          <span>Xử lý ≈ {estimateMinutes(seconds)} phút, chạy nền</span>
        </div>
      </div>

      {startError ? (
        <p
          id={`${startId}-error`}
          role="alert"
          className="text-[13px] text-destructive-text"
        >
          {startError}
        </p>
      ) : null}
      {endError ? (
        <p
          id={`${endId}-error`}
          role="alert"
          className="text-[13px] text-destructive-text"
        >
          {endError}
        </p>
      ) : null}
      {seconds > DEFAULT_RANGE_END_SEC ? (
        <p role="status" className="text-[13px] text-warning-text">
          Đoạn dài hơn 5 phút: xử lý sẽ lâu hơn.
        </p>
      ) : null}
    </div>
  );
}
