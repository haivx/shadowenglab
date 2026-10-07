import type { ReactNode } from "react";

interface AttemptStripProps {
  /** Số thứ tự câu hiển thị (từ 1). */
  sentenceNumber: number;
  /** Số lượt có tiếng của câu này (voicedAttempts); `Lượt k` chỉ hiện khi k ≥ 1. */
  voicedAttempts: number;
  /** Bên phải: nút bật IPA và `Mất chữ cuối?` do 02-18 thêm vào. */
  trailing?: ReactNode;
}

/** Dải `Câu n · Lượt k` phía trên câu đang tập (UI-SPEC S3 mục 1). */
export function AttemptStrip({
  sentenceNumber,
  voicedAttempts,
  trailing,
}: AttemptStripProps) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-muted-foreground">
      <span className="font-bold text-foreground">Câu {sentenceNumber}</span>
      {voicedAttempts >= 1 ? <span>Lượt {voicedAttempts}</span> : null}
      {trailing ? (
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {trailing}
        </div>
      ) : null}
    </div>
  );
}
