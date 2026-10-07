"use client";

import { useEffect, useRef, type ReactNode } from "react";
import type { Segment } from "@shadowenglab/contracts";
import { Skeleton } from "@/components/ui/skeleton";
import { releaseFocusOnPointerUp } from "@/lib/player/useShortcuts";
import { cn } from "@/lib/utils";

/** `mm:ss` của thời điểm bắt đầu câu. */
function formatMmSs(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(whole / 60);
  return `${String(minutes).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
}

const GROUP_LABEL_CLASS =
  "text-xs font-bold uppercase tracking-[0.06em] text-[color:var(--slate-9)]";

interface TranscriptListProps {
  segments: readonly Segment[];
  /** Chỉ số (từ 0) của câu đang tập. */
  currentIndex: number;
  /** Câu đã tập (voicedAttempts >= 1, D-08): chấm xám trung tính. */
  practiced: ReadonlySet<number>;
  /** Chọn câu: dừng phát và đưa câu đó thành câu hiện tại. */
  onSelect: (index: number) => void;
  /** Chỗ cho nút `Dịch` / `Sửa câu` (02-18 điền vào). */
  toolbar?: ReactNode;
}

/** Danh sách câu của S3, cuộn bên trong aside; hàng hiện tại tự cuộn vào khung nhìn. */
export function TranscriptList({
  segments,
  currentIndex,
  practiced,
  onSelect,
  toolbar,
}: TranscriptListProps) {
  const currentRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    currentRef.current?.scrollIntoView({ block: "nearest", behavior: "auto" });
  }, [currentIndex]);

  return (
    <section
      aria-label="Transcript"
      className="flex max-h-[360px] min-h-0 flex-1 flex-col min-[1160px]:max-h-none"
    >
      <div className="flex min-h-11 items-center justify-between px-4 pt-2.5">
        <span className={GROUP_LABEL_CLASS}>
          Transcript · {segments.length} câu
        </span>
        {toolbar ? <span className="flex gap-1">{toolbar}</span> : null}
      </div>
      <ol className="m-0 flex min-h-0 flex-1 list-none flex-col overflow-y-auto p-0 py-2">
        {segments.map((segment, index) => {
          const isCurrent = index === currentIndex;
          const isPracticed = practiced.has(index);
          return (
            <li key={segment.index}>
              <button
                type="button"
                ref={isCurrent ? currentRef : undefined}
                aria-current={isCurrent ? "true" : undefined}
                onPointerUp={releaseFocusOnPointerUp}
                onClick={() => onSelect(index)}
                className={cn(
                  "grid min-h-11 w-full grid-cols-[44px_minmax(0,1fr)_28px] gap-2 text-left text-sm leading-[1.45] transition-colors [transition-duration:120ms]",
                  isCurrent
                    ? "border-l-[3px] border-foreground bg-card py-2.5 pl-[13px] pr-4 font-semibold text-foreground shadow-[inset_0_1px_0_var(--border),inset_0_-1px_0_var(--border)]"
                    : cn(
                        "px-4 py-2 hover:bg-muted",
                        isPracticed
                          ? "text-muted-foreground"
                          : "text-foreground",
                      ),
                )}
              >
                <span
                  className={cn(
                    "pt-[3px] font-mono text-[11px] font-normal",
                    isCurrent
                      ? "text-foreground"
                      : !isPracticed && "text-[color:var(--slate-9)]",
                  )}
                >
                  {formatMmSs(segment.start)}
                </span>
                <span>{segment.text}</span>
                <span className="flex justify-end pt-1.5">
                  {isPracticed ? (
                    <>
                      <span
                        aria-hidden="true"
                        className="size-2 rounded-full bg-muted-foreground"
                      />
                      <span className="sr-only">Đã tập</span>
                    </>
                  ) : null}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/** Hàng khung xương trong lúc bài đang tải (UI-SPEC E8 loading). */
export function TranscriptListSkeleton() {
  return (
    <section
      aria-label="Transcript"
      aria-busy="true"
      className="flex min-h-0 flex-1 flex-col"
    >
      <div className="flex min-h-11 items-center px-4 pt-2.5">
        <Skeleton className="h-3 w-32" />
      </div>
      <div className="flex flex-col gap-3 px-4 py-3">
        {Array.from({ length: 8 }, (_, index) => (
          <div key={index} className="flex items-center gap-2">
            <Skeleton className="h-3 w-11" />
            <Skeleton className="h-4 flex-1" />
          </div>
        ))}
      </div>
    </section>
  );
}
