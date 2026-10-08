"use client";

import { Button } from "@/components/ui/button";
import { releaseFocusOnPointerUp } from "@/lib/player/useShortcuts";

interface AttemptStripProps {
  /** Số thứ tự câu hiển thị (từ 1). */
  sentenceNumber: number;
  /** Số lượt có tiếng của câu này (voicedAttempts); `Lượt k` chỉ hiện khi k ≥ 1. */
  voicedAttempts: number;
  /** IPA đang bật (nút `IPA` / phím I). */
  ipaOn: boolean;
  onToggleIpa: () => void;
}

/** Dải `Câu n · Lượt k` phía trên câu đang tập, kèm nút `IPA` (UI-SPEC S3 mục 1). */
export function AttemptStrip({
  sentenceNumber,
  voicedAttempts,
  ipaOn,
  onToggleIpa,
}: AttemptStripProps) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-muted-foreground">
      <span className="font-bold text-foreground">Câu {sentenceNumber}</span>
      {voicedAttempts >= 1 ? <span>Lượt {voicedAttempts}</span> : null}
      <div className="ml-auto flex flex-wrap items-center gap-2">
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
