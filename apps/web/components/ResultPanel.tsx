"use client";

import { useMutation } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { toast } from "sonner";
import type { ScoreResult } from "@shadowenglab/contracts";
import { ScoreHero } from "@/components/ScoreHero";
import { Button } from "@/components/ui/button";
import { saveEvalClip } from "@/lib/api";

interface ResultPanelProps {
  lessonId: string;
  segmentIndex: number;
  result: ScoreResult;
  /** Số "Lượt k" hiển thị cho kết quả này. */
  attemptLabel: number;
  /** Bản ghi trong phiên của lượt này; null khi không còn trong bộ nhớ. */
  blob: Blob | null;
  /** Clip của lượt này đã được lưu cho eval ở đây (phiên hiện tại). */
  saved: boolean;
  onSaved: () => void;
}

/**
 * Vùng kết quả S3 ở `reviewing` (UI-SPEC "S3 — reviewing"): `ScoreHero` và `Lưu clip cho eval`.
 * Thay khối reviewing của P1. Người gọi đặt `key` theo (câu, lượt) để trạng thái mutation
 * không rò sang lượt khác.
 */
export function ResultPanel({
  lessonId,
  segmentIndex,
  result,
  attemptLabel,
  blob,
  saved,
  onSaved,
}: ResultPanelProps) {
  const save = useMutation({
    mutationFn: () => {
      if (!blob) throw new Error("Không có bản ghi để lưu");
      return saveEvalClip(lessonId, segmentIndex, result.attempt, blob);
    },
    onSuccess: onSaved,
    onError: () => {
      toast.error("Không lưu được clip. Thử lại.");
    },
  });

  return (
    <section
      aria-label={`Kết quả lượt ${attemptLabel}`}
      className="flex flex-col gap-8"
    >
      <ScoreHero
        scores={result.scores}
        prosody={result.prosody}
        attemptLabel={attemptLabel}
      />
      <div>
        <Button
          variant="ghost"
          disabled={saved || save.isPending || blob === null}
          onClick={() => save.mutate()}
        >
          {saved ? <Check aria-hidden="true" /> : null}
          {saved ? "Đã lưu clip" : "Lưu clip cho eval"}
        </Button>
      </div>
    </section>
  );
}
