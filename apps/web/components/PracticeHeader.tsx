import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface SegmentedProgressProps {
  total: number;
  /** Chỉ số (từ 0) của câu đang tập. */
  currentIndex: number;
  /** Câu đã tập = có ít nhất một lượt có tiếng (D-08). Chỉ màu xám trung tính, không màu điểm. */
  practiced: ReadonlySet<number>;
}

/** Lưới N đoạn: hiện tại `--foreground`, đã tập `--muted-foreground`, còn lại slate-4 (D-08). */
export function SegmentedProgress({
  total,
  currentIndex,
  practiced,
}: SegmentedProgressProps) {
  return (
    <div
      role="img"
      aria-label={`Tiến độ ${currentIndex + 1} trên ${total} câu`}
      className="grid flex-1 gap-0.5"
      style={{ gridTemplateColumns: `repeat(${total}, minmax(0, 1fr))` }}
    >
      {Array.from({ length: total }, (_, index) => (
        <span
          key={index}
          className={cn(
            "h-1 rounded-[2px]",
            index === currentIndex
              ? "bg-foreground"
              : practiced.has(index)
                ? "bg-muted-foreground"
                : "bg-[color:var(--slate-4)]",
          )}
        />
      ))}
    </div>
  );
}

/** Liên kết về S1, cao 44 (PLY-07). Dùng cả ở trạng thái tải và lỗi của S3. */
export function BackToLibraryLink() {
  return (
    <Link
      href="/"
      className="inline-flex h-11 items-center gap-1.5 rounded px-2.5 text-sm font-semibold text-muted-foreground transition-colors [transition-duration:120ms] hover:bg-muted hover:text-foreground"
    >
      <ChevronLeft aria-hidden="true" className="size-4" strokeWidth={2} />
      Thư viện
    </Link>
  );
}

interface PracticeHeaderProps extends SegmentedProgressProps {
  title: string;
}

/** Header S3: về Thư viện, tên bài, tiến độ. Không có `Kết thúc buổi` (S5 ngoài phạm vi, G5). */
export function PracticeHeader({
  title,
  total,
  currentIndex,
  practiced,
}: PracticeHeaderProps) {
  return (
    <header className="flex flex-wrap items-center gap-4 border-b border-border px-6 py-2.5">
      <BackToLibraryLink />
      <h1 className="m-0 min-w-0 truncate text-[15px] font-bold" title={title}>
        {title}
      </h1>
      <div className="flex min-w-[200px] flex-[1_1_240px] items-center gap-2.5">
        <SegmentedProgress
          total={total}
          currentIndex={currentIndex}
          practiced={practiced}
        />
        <span className="font-mono text-[13px] text-muted-foreground">
          {currentIndex + 1}/{total}
        </span>
      </div>
    </header>
  );
}
