import { cn } from "@/lib/utils";

/** Số vạch của đồng hồ mức âm; khớp BAR_COUNT trong lib/audio/level.ts. */
const BAR_TOTAL = 10;
const MIN_HEIGHT_PX = 6;
const MAX_HEIGHT_PX = 36;

interface LevelMeterProps {
  /** 0..10 vạch sáng (từ PlayerLevel.bars hoặc bộ đo ở S8). */
  bars: number;
  className?: string;
}

/**
 * Mức âm micro (UI-SPEC S3 mục 2): 10 vạch rộng 5 px, cách 4, khung cao 40.
 * Vạch sáng dùng `--recording` và cao dần theo vị trí (6–36 px); vạch chưa sáng thấp 6 px màu `--red-7`.
 * Khung có `aria-label`, từng vạch `aria-hidden` để trình đọc màn hình không đọc từng khung hình.
 * Tái dùng ở S8 `Thử micro`.
 */
export function LevelMeter({ bars, className }: LevelMeterProps) {
  const lit = Math.min(BAR_TOTAL, Math.max(0, Math.round(bars)));
  return (
    <div
      role="img"
      aria-label="Mức âm micro"
      className={cn("flex h-10 items-center justify-center gap-1", className)}
    >
      {Array.from({ length: BAR_TOTAL }, (_, index) => {
        const active = index < lit;
        const height = active
          ? MIN_HEIGHT_PX +
            Math.round(
              ((MAX_HEIGHT_PX - MIN_HEIGHT_PX) * (index + 1)) / BAR_TOTAL,
            )
          : MIN_HEIGHT_PX;
        return (
          <span
            key={index}
            aria-hidden="true"
            className={cn(
              "w-[5px] rounded-[3px]",
              active ? "bg-recording" : "bg-[color:var(--red-7)]",
            )}
            style={{ height }}
          />
        );
      })}
    </div>
  );
}
