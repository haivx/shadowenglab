"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LevelMeter } from "@/components/LevelMeter";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Skeleton } from "@/components/ui/skeleton";
import { releaseFocusOnPointerUp } from "@/lib/player/useShortcuts";

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
  /** Dòng phiên âm `/…/` dưới câu; null khi tắt IPA hoặc không từ nào có IPA. */
  ipa: string | null;
}

interface RecordingPanelProps {
  variant: "recording";
  sentence: string;
  /** 0..10 vạch sáng của LevelMeter. */
  bars: number;
  /** Dòng phiên âm `/…/` dưới câu; null khi tắt IPA hoặc không từ nào có IPA. */
  ipa: string | null;
}

interface ScoringPanelProps {
  variant: "scoring";
  sentence: string;
}

interface NoVoicePanelProps {
  variant: "noVoice";
  sentence: string;
  onRecord: () => void;
}

interface MicErrorPanelProps {
  variant: "micError";
  sentence: string;
  onRecord: () => void;
}

interface UploadErrorPanelProps {
  variant: "uploadError";
  sentence: string;
  /** RETRY_UPLOAD: gửi lại đúng bản ghi đã giữ trong bộ nhớ. */
  onRetry: () => void;
  onRecord: () => void;
}

/**
 * Thẻ trắng viền 1px, bo 12, padding 24, khoảng cách 18, câu 26/500 căn giữa (S3s).
 * Biến thể: playing, recording, scoring, noVoice, micError, uploadError.
 */
export type SentenceStatePanelProps =
  | PlayingPanelProps
  | RecordingPanelProps
  | ScoringPanelProps
  | NoVoicePanelProps
  | MicErrorPanelProps
  | UploadErrorPanelProps;

/** Phiên âm gọn dưới câu trong panel (font IPA, teal-12 như SpokenIpa); cách câu 14px như S3. */
function PanelIpa({ ipa }: { ipa: string | null }) {
  if (ipa === null) return null;
  return (
    <p
      lang="en-fonipa"
      aria-label="IPA từ audio mẫu"
      className="m-0 -mt-1 break-words text-center font-ipa text-base leading-[1.4] text-[color:var(--teal-12)]"
    >
      {ipa}
    </p>
  );
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function PlayingPanel({
  sentence,
  repeat,
  rep,
  autoRecord,
  getPassProgress,
  ipa,
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
      <PanelIpa ipa={ipa} />
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

/** Tần suất cập nhật số giây đã ghi: 0.1 s khớp độ phân giải `s.s` của chip. */
const ELAPSED_TICK_MS = 100;

function RecordingPanel({ sentence, bars, ipa }: RecordingPanelProps) {
  const [elapsedMs, setElapsedMs] = useState(0);

  // Ghi đến khi người dùng dừng (Liam 2026-10-10), nên chip đếm lên từ lúc panel mount.
  useEffect(() => {
    const startedAt = performance.now();
    const timer = window.setInterval(() => {
      setElapsedMs(performance.now() - startedAt);
    }, ELAPSED_TICK_MS);
    return () => window.clearInterval(timer);
  }, []);

  const seconds = (elapsedMs / 1000).toFixed(1);

  return (
    <section className="flex flex-col gap-[18px] rounded-lg border-2 border-recording bg-card p-[23px]">
      {/* Chỉ báo `Đang ghi` một lần cho trình đọc màn hình; số giây đổi mỗi 0.1 s nên không đặt live. */}
      <span role="status" className="sr-only">
        Đang ghi
      </span>
      <span
        aria-hidden="true"
        className="inline-flex h-[30px] items-center gap-2 self-start rounded-[15px] bg-recording px-3 text-[13px] font-semibold text-white [font-variant-numeric:tabular-nums]"
      >
        <span className="size-2 rounded-full bg-white" />
        Đang ghi · {seconds}s
      </span>
      <p className="m-0 text-center text-[26px] font-medium leading-[1.3]">
        {sentence}
      </p>
      <PanelIpa ipa={ipa} />
      <LevelMeter bars={bars} />
      <span className="text-center text-[13px] text-muted-foreground">
        <Kbd>Space</Kbd> hoặc Dừng ghi để kết thúc
      </span>
    </section>
  );
}

/** Sau ngần này mà chưa có kết quả thì đổi chú thích (P3-G9, D-03: lần đầu của câu tính đặc trưng bản gốc). */
const SLOW_CAPTION_MS = 5000;

/**
 * Ba khối xương tương ứng ba chỉ số của ScoreHero (S3s 4, UI-SPEC "State 4"): 72px, bo 12, nền muted.
 * Dùng lại cho khung chờ kết quả của lượt cũ (03-10).
 */
export function MetricSkeleton() {
  return (
    <div aria-hidden="true" className="grid grid-cols-3 gap-3">
      {[0, 1, 2].map((key) => (
        <Skeleton key={key} className="h-[72px] rounded-lg" />
      ))}
    </div>
  );
}

function ScoringPanel({ sentence }: ScoringPanelProps) {
  const [slow, setSlow] = useState(false);

  // Panel chỉ mount khi machine vào `scoring`, nên mốc 5 s tính từ lúc bắt đầu chấm.
  useEffect(() => {
    const timer = window.setTimeout(() => setSlow(true), SLOW_CAPTION_MS);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <section
      aria-busy="true"
      className="flex flex-col gap-4 rounded-lg border border-border bg-card p-6"
    >
      <p className="m-0 text-center text-[26px] font-medium leading-[1.3]">
        {sentence}
      </p>
      <MetricSkeleton />
      <span className="text-center text-[13px] text-muted-foreground">
        {slow ? (
          "Đang so với bản gốc… Lần đầu của câu này có thể lâu hơn một chút."
        ) : (
          <>
            Đang so với bản gốc… Bạn có thể nghe lại bản ghi của mình{" "}
            <Kbd>M</Kbd>
          </>
        )}
      </span>
    </section>
  );
}

/** Câu 26/500 màu muted ở các panel lỗi/không có tiếng (S3s state 3). */
function MutedSentence({ sentence }: { sentence: string }) {
  return (
    <p className="m-0 text-center text-[26px] font-medium leading-[1.3] text-muted-foreground">
      {sentence}
    </p>
  );
}

/** Hàng nút giữa panel: `Ghi lại` (R) và liên kết `Chọn micro` tới S8. */
function RecordAndMicButtons({ onRecord }: { onRecord: () => void }) {
  return (
    <div className="flex flex-wrap justify-center gap-2.5">
      <Button
        variant="solid"
        kbd="R"
        onPointerUp={releaseFocusOnPointerUp}
        onClick={onRecord}
        className="px-[18px] text-[15px]"
      >
        Ghi lại
      </Button>
      <Button
        asChild
        variant="outline"
        className="px-[18px] text-[15px]"
        onPointerUp={releaseFocusOnPointerUp}
      >
        <Link href="/settings">Chọn micro</Link>
      </Button>
    </div>
  );
}

const PANEL_ALERT = "flex-col items-stretch justify-start gap-1.5";

function NoVoicePanel({ sentence, onRecord }: NoVoicePanelProps) {
  return (
    <section className="flex flex-col gap-[18px] rounded-lg border border-border bg-card p-6">
      <MutedSentence sentence={sentence} />
      <Alert variant="warning" role="alert" className={PANEL_ALERT}>
        <AlertTitle className="text-[15px] font-bold">
          Không nghe thấy gì trong lượt vừa rồi
        </AlertTitle>
        <AlertDescription>
          Kiểm tra micro đang chọn hoặc nói gần hơn. Lượt này không được tính.
        </AlertDescription>
      </Alert>
      <RecordAndMicButtons onRecord={onRecord} />
    </section>
  );
}

function MicErrorPanel({ sentence, onRecord }: MicErrorPanelProps) {
  return (
    <section className="flex flex-col gap-[18px] rounded-lg border border-border bg-card p-6">
      <MutedSentence sentence={sentence} />
      <Alert variant="warning" role="alert" className={PANEL_ALERT}>
        <AlertDescription className="font-semibold">
          Không mở được micro. Cho phép micro cho localhost:3000 hoặc chọn micro
          khác.
        </AlertDescription>
      </Alert>
      <RecordAndMicButtons onRecord={onRecord} />
    </section>
  );
}

function UploadErrorPanel({
  sentence,
  onRetry,
  onRecord,
}: UploadErrorPanelProps) {
  return (
    <section className="flex flex-col gap-[18px] rounded-lg border border-border bg-card p-6">
      <MutedSentence sentence={sentence} />
      <Alert variant="error" className={PANEL_ALERT}>
        <AlertDescription className="font-semibold">
          Không xử lý được bản ghi. Bản ghi của bạn vẫn còn, bấm Thử lại để gửi
          lại.
        </AlertDescription>
      </Alert>
      <div className="flex flex-wrap justify-center gap-2.5">
        <Button
          variant="solid"
          onPointerUp={releaseFocusOnPointerUp}
          onClick={onRetry}
          className="px-[18px] text-[15px]"
        >
          Thử lại
        </Button>
        <Button
          variant="outline"
          kbd="R"
          onPointerUp={releaseFocusOnPointerUp}
          onClick={onRecord}
          className="px-[18px] text-[15px]"
        >
          Ghi lại
        </Button>
      </div>
    </section>
  );
}

export function SentenceStatePanel(props: SentenceStatePanelProps) {
  switch (props.variant) {
    case "playing":
      return <PlayingPanel {...props} />;
    case "recording":
      return <RecordingPanel {...props} />;
    case "scoring":
      return <ScoringPanel {...props} />;
    case "noVoice":
      return <NoVoicePanel {...props} />;
    case "micError":
      return <MicErrorPanel {...props} />;
    case "uploadError":
      return <UploadErrorPanel {...props} />;
  }
}
