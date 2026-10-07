"use client";

import { useEffect, useState } from "react";
import { Kbd } from "@/components/ui/kbd";

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

/**
 * Các biến thể khác (recording, noVoice, processing, error) do 02-14 thêm vào đây.
 * Thẻ trắng viền 1px, bo 12, padding 24, khoảng cách 18, câu 26/500 căn giữa (S3s).
 */
export type SentenceStatePanelProps = PlayingPanelProps;

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

export function SentenceStatePanel(props: SentenceStatePanelProps) {
  return <PlayingPanel {...props} />;
}
