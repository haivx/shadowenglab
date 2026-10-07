"use client";

import { useEffect, useRef, useState } from "react";
import { LevelMeter } from "@/components/LevelMeter";
import { Kbd } from "@/components/ui/kbd";
import { Skeleton } from "@/components/ui/skeleton";

interface PlayingPanelProps {
  variant: "playing";
  sentence: string;
  /** Số lần lặp của lượt nghe hiện tại. */
  repeat: number;
  /** Lần lặp đang phát (1..repeat); 0 trước khi lần đầu bắt đầu. */
  rep: number;
  /** true: phát xong tự chuyển sang ghi (Space). false: chỉ nghe bản gốc một lần (O). */
  autoRecord: boolean;
  /** Tiến độ 0..1 của lần phát hiện tại, đọc từ video mỗi khung hình. */
  getPassProgress: () => number;
}

interface RecordingPanelProps {
  variant: "recording";
  sentence: string;
  /** Tổng thời gian ghi (ms) = recordDelay của machine; đếm ngược tính từ lúc panel mount. */
  durationMs: number;
  /** 0..10 vạch sáng của LevelMeter. */
  bars: number;
}

interface ProcessingPanelProps {
  variant: "processing";
  sentence: string;
}

/**
 * Các biến thể khác (noVoice, micError, uploadError) do tác vụ sau thêm vào đây.
 * Thẻ trắng viền 1px, bo 12, padding 24, khoảng cách 18, câu 26/500 căn giữa (S3s).
 */
export type SentenceStatePanelProps =
  PlayingPanelProps | RecordingPanelProps | ProcessingPanelProps;

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function PlayingPanel({
  sentence,
  repeat,
  rep,
  autoRecord,
  getPassProgress,
}: PlayingPanelProps) {
  const [pass, setPass] = useState(0);

  useEffect(() => {
    let frame = 0;
    const loop = () => {
      const next = clamp01(getPassProgress());
      setPass((prev) => (Math.abs(prev - next) < 0.002 ? prev : next));
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [getPassProgress]);

  const current = Math.min(Math.max(rep, 1), repeat);
  const fraction = clamp01((current - 1 + pass) / repeat);
  const chip =
    repeat > 1
      ? `Đang phát bản gốc · lần ${current}/${repeat}`
      : "Đang phát bản gốc";

  return (
    <section className="flex flex-col gap-[18px] rounded-lg border border-border bg-card p-6">
      <div aria-live="polite" className="self-start">
        <span className="inline-flex h-[30px] items-center gap-2 rounded-[15px] bg-original-soft px-3 text-[13px] font-semibold text-original-text">
          <span
            aria-hidden="true"
            className="size-2 rounded-full bg-original"
          />
          {chip}
        </span>
      </div>
      <p className="m-0 text-center text-[26px] font-medium leading-[1.3]">
        {sentence}
      </p>
      <div
        aria-hidden="true"
        className="h-1.5 overflow-hidden rounded-[3px] bg-muted"
      >
        <div
          className="h-full bg-original"
          style={{ width: `${Math.round(fraction * 100)}%` }}
        />
      </div>
      <span className="text-center text-[13px] text-muted-foreground">
        {autoRecord ? "Phát xong sẽ tự chuyển sang lượt của bạn · " : null}
        <Kbd>Space</Kbd> dừng
      </span>
    </section>
  );
}

/** Tần suất cập nhật số đếm ngược: 0.1 s khớp độ phân giải `s.s` của chip. */
const COUNTDOWN_TICK_MS = 100;

function RecordingPanel({ sentence, durationMs, bars }: RecordingPanelProps) {
  const [remainingMs, setRemainingMs] = useState(durationMs);
  const startedAtRef = useRef<number | null>(null);

  // Panel chỉ mount khi machine vào `recording`, cùng lúc hẹn giờ `recordDelay` bắt đầu,
  // nên mốc thời gian lấy lúc mount trùng với lúc tự dừng.
  useEffect(() => {
    startedAtRef.current = performance.now();
    const timer = window.setInterval(() => {
      const startedAt = startedAtRef.current ?? performance.now();
      setRemainingMs(Math.max(0, durationMs - (performance.now() - startedAt)));
    }, COUNTDOWN_TICK_MS);
    return () => window.clearInterval(timer);
  }, [durationMs]);

  const seconds = (remainingMs / 1000).toFixed(1);

  return (
    <section className="flex flex-col gap-[18px] rounded-lg border-2 border-recording bg-card p-[23px]">
      {/* Chỉ báo `Đang ghi` một lần cho trình đọc màn hình; số đếm ngược đổi mỗi 0.1 s nên không đặt live. */}
      <span role="status" className="sr-only">
        Đang ghi
      </span>
      <span
        aria-hidden="true"
        className="inline-flex h-[30px] items-center gap-2 self-start rounded-[15px] bg-recording px-3 text-[13px] font-semibold text-white [font-variant-numeric:tabular-nums]"
      >
        <span className="size-2 rounded-full bg-white" />
        Đang ghi · còn {seconds}s
      </span>
      <p className="m-0 text-center text-[26px] font-medium leading-[1.3]">
        {sentence}
      </p>
      <LevelMeter bars={bars} />
      <span className="text-center text-[13px] text-muted-foreground">
        <Kbd>Space</Kbd> hoặc im lặng 1 giây để dừng sớm
      </span>
    </section>
  );
}

/** Độ rộng 6 chip xương theo S3s (state 4). */
const SKELETON_CHIP_WIDTHS = [56, 96, 40, 76, 84, 44] as const;

function ProcessingPanel({ sentence }: ProcessingPanelProps) {
  return (
    <section
      aria-busy="true"
      className="flex flex-col gap-4 rounded-lg border border-border bg-card p-6"
    >
      <p className="m-0 text-center text-[26px] font-medium leading-[1.3]">
        {sentence}
      </p>
      <div aria-hidden="true" className="flex justify-center gap-2">
        {SKELETON_CHIP_WIDTHS.map((width, index) => (
          <Skeleton key={index} className="h-10 rounded-lg" style={{ width }} />
        ))}
      </div>
      <span className="text-center text-[13px] text-muted-foreground">
        Đang xử lý bản ghi… Bạn có thể nghe lại bản ghi của mình <Kbd>M</Kbd>
      </span>
    </section>
  );
}

export function SentenceStatePanel(props: SentenceStatePanelProps) {
  switch (props.variant) {
    case "playing":
      return <PlayingPanel {...props} />;
    case "recording":
      return <RecordingPanel {...props} />;
    case "processing":
      return <ProcessingPanel {...props} />;
  }
}
