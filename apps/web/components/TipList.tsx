"use client";

import type { Issue, Tip } from "@shadowenglab/contracts";
import { markedWordTone, splitTipMarkup } from "@/lib/tipMarkup";

interface TipListProps {
  /** Đúng thứ tự và số lượng backend trả về (D-14); UI không sắp xếp, không bỏ, không tự thêm. */
  tips: Tip[];
  /** `ScoreResult.issues`; `tip.issueRef` trỏ vào danh sách này. */
  issues: Issue[];
  /** Hover / focus hàng nào thì báo chỉ số hàng đó; rời / blur thì báo `null`. */
  onHoverTip: (index: number | null) => void;
}

/** Lớp Tailwind viết nguyên văn để JIT nhìn thấy (không ghép chuỗi). */
const DECORATION = {
  original: "decoration-original",
  you: "decoration-you",
  neutral: "decoration-[color:var(--slate-9)]",
} as const;

/**
 * Màu gạch chân của từ được đánh dấu (UI-SPEC "TipList"): `--slate-9` cho mọi mã, riêng
 * STRESS_MISMATCH thì từ của bản gốc gạch `--original` (mọi lần nhắc), từ của bạn gạch `--you`.
 */
function wordDecoration(code: Issue["code"] | undefined, ordinal: number) {
  return DECORATION[markedWordTone(code, ordinal)];
}

/**
 * Danh sách gợi ý đánh số `01`–`03` (UI-SPEC "TipList"). Văn bản gợi ý chỉ được dựng thành phần tử
 * React từ `splitTipMarkup`, không bao giờ là chuỗi HTML (từ đến từ Whisper và ô "Sửa câu").
 * Mỗi hàng `tabIndex={0}` để bàn phím có cùng highlight như hover (P3-G14).
 */
export function TipList({ tips, issues, onHoverTip }: TipListProps) {
  return (
    <ol className="m-0 flex list-none flex-col gap-[14px] p-0 text-base leading-[1.5]">
      {tips.map((tip, index) => {
        const code = issues[tip.issueRef]?.code;
        return (
          <li
            key={index}
            tabIndex={0}
            onMouseEnter={() => onHoverTip(index)}
            onMouseLeave={() => onHoverTip(null)}
            onFocus={() => onHoverTip(index)}
            onBlur={() => onHoverTip(null)}
            className="grid grid-cols-[28px_minmax(0,1fr)] gap-2 rounded-lg hover:bg-muted focus-visible:bg-muted"
          >
            <span
              aria-hidden="true"
              className="pt-[3px] font-mono text-[13px] font-medium text-muted-foreground"
            >
              {String(index + 1).padStart(2, "0")}
            </span>
            <span className="min-w-0 [overflow-wrap:anywhere]">
              {splitTipMarkup(tip.text).map((segment, i) =>
                segment.kind === "word" ? (
                  <span
                    key={i}
                    className={`font-bold underline decoration-2 underline-offset-4 ${wordDecoration(
                      code,
                      segment.ordinal,
                    )}`}
                  >
                    {segment.value}
                  </span>
                ) : (
                  <span key={i}>{segment.value}</span>
                ),
              )}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
