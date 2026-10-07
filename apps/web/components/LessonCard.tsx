"use client";

import type { LessonListItem } from "@shadowenglab/contracts";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";
import { JobSteps } from "@/components/JobSteps";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { retryLesson } from "@/lib/api";
import {
  cardCta,
  failureText,
  formatClock,
  isProcessing,
  safeThumbnailUrl,
} from "@/lib/lessonView";
import { queryKeys } from "@/lib/queries";
import { cn } from "@/lib/utils";

const MUSIC_WARNING =
  "Nhạc nền khá nhiều, một số câu có thể khó chấm. Cân nhắc chọn video khác.";

/**
 * Thẻ bài trong lưới S1, bốn trạng thái: ready · processing · warning (ready
 * có nhạc nền) · failed. Chỉ thẻ ready có liên kết sang phòng tập; thẻ lỗi chỉ
 * có `Thử lại`, không có xoá (D-03).
 */
export function LessonCard({ item }: { item: LessonListItem }) {
  const { lesson } = item;
  const failed = lesson.status === "failed";
  const processing = isProcessing(lesson.status);
  const ready = lesson.status === "ready";
  const thumbnail = safeThumbnailUrl(lesson.thumbnailUrl);
  const rangeSeconds = lesson.range.end - lesson.range.start;

  const queryClient = useQueryClient();
  const retry = useMutation({
    mutationFn: () => retryLesson(lesson.id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.lessons }),
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const allDone = item.segmentCount > 0 && item.firstUnpracticedIndex === null;
  const cta = cardCta(item);
  const progressPercent =
    item.segmentCount > 0
      ? Math.min(100, (item.practicedCount / item.segmentCount) * 100)
      : 0;

  return (
    <Card
      data-status={lesson.status}
      className={cn("gap-0 p-0", failed && "border-destructive-border")}
    >
      <div className="relative flex aspect-video items-center justify-center bg-video">
        {thumbnail ? (
          // Thẻ <img> thường (UI-SPEC): ảnh YouTube từ xa, tránh cấu hình next/image.
          <img
            src={thumbnail}
            alt=""
            loading="lazy"
            className="size-full object-cover"
          />
        ) : failed ? (
          <span className="text-sm text-[color:var(--slate-8)]">
            Không có ảnh
          </span>
        ) : processing ? (
          <span className="text-sm text-[color:var(--slate-8)]">
            Đang xử lý
          </span>
        ) : null}
        <span className="absolute bottom-2 left-2 rounded-sm bg-[rgba(0,0,0,0.6)] px-2 py-0.5 text-xs font-semibold text-white [font-variant-numeric:tabular-nums]">
          {formatClock(rangeSeconds)}
        </span>
      </div>

      <div className="flex flex-col gap-2.5 p-4">
        <h2
          title={lesson.title}
          className="line-clamp-2 break-words text-base font-bold leading-[1.3] text-foreground"
        >
          {lesson.title}
        </h2>

        {ready ? (
          <>
            <div className="flex flex-wrap items-center gap-1.5">
              {lesson.audioQuality?.label === "clean" ? (
                <Badge variant="success">Audio sạch</Badge>
              ) : null}
              {lesson.audioQuality?.label === "music" ? (
                <Badge variant="warning">Có nhạc nền</Badge>
              ) : null}
              <Badge variant="neutral">{item.segmentCount} câu</Badge>
            </div>
            {lesson.audioQuality?.label === "music" ? (
              <p className="text-[13px] leading-[1.45] text-warning-text">
                {MUSIC_WARNING}
              </p>
            ) : null}
            {item.segmentCount > 0 ? (
              <div className="flex flex-col gap-1.5">
                <Progress
                  value={progressPercent}
                  aria-label={`Đã tập ${item.practicedCount} trên ${item.segmentCount} câu`}
                />
                <span className="text-[13px] text-muted-foreground">
                  {allDone
                    ? `Đã xong ${item.segmentCount}/${item.segmentCount}`
                    : `Đã tập ${item.practicedCount}/${item.segmentCount}`}
                </span>
              </div>
            ) : null}
            <Button asChild variant={cta.variant} className="w-full">
              <Link href={`/lessons/${encodeURIComponent(lesson.id)}`}>
                {cta.label}
              </Link>
            </Button>
          </>
        ) : null}

        {processing ? <JobSteps status={lesson.status} /> : null}

        {failed ? (
          <>
            <p className="break-words text-sm leading-[1.5] text-destructive-text">
              {failureText(lesson.error)}
            </p>
            <Button
              variant="outline"
              className="w-full"
              disabled={retry.isPending}
              onClick={() => retry.mutate()}
            >
              {retry.isPending ? "Đang thử lại…" : "Thử lại"}
            </Button>
          </>
        ) : null}
      </div>
    </Card>
  );
}
