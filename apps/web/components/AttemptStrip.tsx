"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ApiRequestError, extendSegmentEnd } from "@/lib/api";
import type { AttemptChip } from "@/lib/attemptChips";
import { releaseFocusOnPointerUp } from "@/lib/player/useShortcuts";
import { queryKeys } from "@/lib/queries";
import { patchLessonSegment } from "@/lib/segmentCache";

const EXTENDED_TEXT = "Đã nới câu thêm 0.3 giây";
const EXTEND_FAILED_TEXT = "Không nới được câu này. Thử lại.";

interface AttemptStripProps {
  lessonId: string;
  /** `Segment.index` của câu đang tập (dùng cho POST …/extend-end). */
  segmentIndex: number;
  /** Số thứ tự câu hiển thị (từ 1). */
  sentenceNumber: number;
  /** Một chip cho mỗi lượt đã chấm (tối đa 6, xem `attemptChips`). */
  chips: AttemptChip[];
  /** Số `attempt` của lượt đang hiển thị (null = chưa xem lượt nào). */
  viewedAttempt: number | null;
  onSelectAttempt: (attempt: number) => void;
  /** IPA đang bật (nút `IPA` / phím I). */
  ipaOn: boolean;
  onToggleIpa: () => void;
}

/**
 * Dải `Câu n · Lượt k` phía trên câu đang tập, kèm nút `IPA` và `Mất chữ cuối?` (UI-SPEC S3 mục 1).
 * `Mất chữ cuối?` nới thêm 0.3 giây ở cuối câu; PracticeRoom thấy bài đổi thì gửi SEGMENTS_UPDATED cho machine.
 */
export function AttemptStrip({
  lessonId,
  segmentIndex,
  sentenceNumber,
  chips,
  viewedAttempt,
  onSelectAttempt,
  ipaOn,
  onToggleIpa,
}: AttemptStripProps) {
  const queryClient = useQueryClient();
  // Câu vừa được nới; thông báo chỉ hiện ở đúng câu đó.
  const [extendedIndex, setExtendedIndex] = useState<number | null>(null);

  const extend = useMutation({
    mutationFn: () => extendSegmentEnd(lessonId, segmentIndex),
    onSuccess: (updated) => {
      patchLessonSegment(queryClient, lessonId, updated);
      setExtendedIndex(updated.index);
    },
    onError: (error) => {
      if (error instanceof ApiRequestError) {
        toast.error(error.error.message);
        // Server bận (503) vẫn đã lưu phần nới: tải lại bài để lấy endExtraMs mới.
        if (error.status === 503 || error.status === 409) {
          void queryClient.invalidateQueries({
            queryKey: queryKeys.lesson(lessonId),
          });
        }
        return;
      }
      toast.error(EXTEND_FAILED_TEXT);
    },
  });

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-muted-foreground">
      <span className="font-bold text-foreground">Câu {sentenceNumber}</span>
      {chips.map((chip) => {
        const viewed = chip.attempt === viewedAttempt;
        return (
          <Button
            key={chip.attempt}
            variant="ghost"
            aria-current={viewed ? "true" : undefined}
            onPointerUp={releaseFocusOnPointerUp}
            onClick={() => onSelectAttempt(chip.attempt)}
            className={`rounded-lg px-3 text-[13px] ${
              viewed
                ? "font-semibold text-foreground"
                : "font-normal text-muted-foreground"
            }`}
          >
            {chip.label}
            {chip.isBest ? (
              <>
                {" · "}
                <span className="font-semibold">tốt nhất</span>
              </>
            ) : null}
          </Button>
        );
      })}
      <div className="ml-auto flex flex-wrap items-center gap-2">
        <span role="status">
          {extendedIndex === segmentIndex ? EXTENDED_TEXT : ""}
        </span>
        <Button
          variant="ghost"
          title="Nới thêm 0.3 giây ở cuối câu"
          disabled={extend.isPending}
          aria-busy={extend.isPending}
          onPointerUp={releaseFocusOnPointerUp}
          onClick={() => extend.mutate()}
          className="px-3.5 text-[13px] text-muted-foreground"
        >
          {extend.isPending ? (
            <LoaderCircle aria-hidden="true" className="animate-spin" />
          ) : null}
          Mất chữ cuối?
        </Button>
        <Button
          variant="ghost"
          kbd="I"
          title="Bật tắt IPA (I)"
          aria-pressed={ipaOn}
          onPointerUp={releaseFocusOnPointerUp}
          onClick={onToggleIpa}
          className="px-3.5 text-[13px] aria-pressed:bg-[color:var(--slate-4)]"
        >
          IPA
        </Button>
      </div>
    </div>
  );
}
