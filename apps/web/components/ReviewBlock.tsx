"use client";

import { useMutation } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { saveEvalClip } from "@/lib/api";

interface ReviewBlockProps {
  lessonId: string;
  segmentIndex: number;
  /** Số lượt đã ghi hiển thị ở tiêu đề (`Đã ghi lượt {k}`). */
  attemptLabel: number;
  /** Số thứ tự lượt do server cấp (AttemptAck.attempt), dùng cho PUT eval-clip. */
  attempt: number;
  /** Bản ghi của lượt này; chỉ nằm trong bộ nhớ trình duyệt (D-07). */
  blob: Blob;
  durationMs: number;
  /** Câu cuối của bài: thêm một dòng báo đã tới cuối. */
  isLast: boolean;
  /** Clip của lượt này đã được lưu cho eval ở đây (phiên hiện tại). */
  saved: boolean;
  onSaved: () => void;
}

/**
 * Khối reviewing của P1 (D-05, D-08): chỉ mời nghe lại và so sánh, tuyệt đối không có điểm, phần trăm
 * hay màu tốt/xấu. `Lưu clip cho eval` là nút phụ chủ dự án đã duyệt (D-09, UI-SPEC E11).
 * Người gọi đặt `key` theo (câu, lượt) để trạng thái mutation không rò sang lượt khác.
 */
export function ReviewBlock({
  lessonId,
  segmentIndex,
  attemptLabel,
  attempt,
  blob,
  durationMs,
  isLast,
  saved,
  onSaved,
}: ReviewBlockProps) {
  const save = useMutation({
    mutationFn: () => saveEvalClip(lessonId, segmentIndex, attempt, blob),
    onSuccess: onSaved,
    onError: () => {
      toast.error("Không lưu được clip. Thử lại.");
    },
  });

  const seconds = (durationMs / 1000).toFixed(1);

  return (
    <section
      aria-label="Kết quả lượt ghi"
      className="flex flex-col gap-3 border-t border-border pt-6"
    >
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="m-0 text-lg font-bold leading-[1.2]">
          Đã ghi lượt {attemptLabel}
        </h2>
        <span className="text-[13px] text-muted-foreground [font-variant-numeric:tabular-nums]">
          {seconds}s
        </span>
      </div>
      <p className="m-0 text-sm text-muted-foreground">
        Nghe lại bản gốc và bản của bạn để so sánh. Chưa chấm điểm ở bản này.
        {isLast ? " Bạn đã tới câu cuối của bài." : null}
      </p>
      <div>
        <Button
          variant="ghost"
          disabled={saved || save.isPending}
          onClick={() => save.mutate()}
        >
          {saved ? <Check aria-hidden="true" /> : null}
          {saved ? "Đã lưu clip" : "Lưu clip cho eval"}
        </Button>
      </div>
    </section>
  );
}
