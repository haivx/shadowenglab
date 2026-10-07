import type { LessonStatus } from "@shadowenglab/contracts";
import { Progress } from "@/components/ui/progress";
import { stepRows, type StepState } from "@/lib/lessonView";
import { cn } from "@/lib/utils";

const QUEUED_LINE = "Đang xếp hàng · chờ bài khác xử lý xong.";

const STATE_TEXT: Record<StepState, string> = {
  done: "Xong",
  running: "Đang chạy",
  pending: "Chờ",
};

/**
 * Tiến độ xử lý của một bài (S1). Contract không có phần trăm từng bước nên
 * bước đang chạy dùng thanh không xác định (G17).
 */
export function JobSteps({ status }: { status: LessonStatus }) {
  const rows = stepRows(status);
  return (
    <div className="flex flex-col gap-2.5">
      {status === "queued" ? (
        <p className="text-sm font-semibold text-foreground">{QUEUED_LINE}</p>
      ) : null}
      <ol aria-label="Tiến độ xử lý" className="flex flex-col gap-2">
        {rows.map((row) => (
          <li
            key={row.step}
            aria-current={row.state === "running" ? "step" : undefined}
            className="flex flex-col gap-1.5"
          >
            <div className="flex items-center justify-between gap-2 text-sm">
              <span
                className={cn(
                  row.state === "running"
                    ? "font-semibold text-foreground"
                    : "text-muted-foreground",
                )}
              >
                {row.label}
              </span>
              <span
                className={cn(
                  "text-[13px]",
                  row.state === "done" && "font-semibold text-success-text",
                  row.state === "running" && "font-semibold text-foreground",
                  row.state === "pending" && "text-muted-foreground",
                )}
              >
                {STATE_TEXT[row.state]}
              </span>
            </div>
            {row.state === "running" ? (
              <Progress indeterminate aria-label={`${row.label}: đang chạy`} />
            ) : null}
          </li>
        ))}
      </ol>
      <p className="text-[13px] text-muted-foreground">
        Bạn có thể tập bài khác trong lúc chờ.
      </p>
    </div>
  );
}
