"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ChartLine, Check } from "lucide-react";
import { toast } from "sonner";
import type { ScoreResult, Segment } from "@shadowenglab/contracts";
import { IntonationChart } from "@/components/IntonationChart";
import { ScoreHero } from "@/components/ScoreHero";
import { SpokenIpa } from "@/components/SpokenIpa";
import { TipList } from "@/components/TipList";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { saveEvalClip } from "@/lib/api";
import { resultNote, wordsMatchSegment } from "@/lib/resultView";
import { scorePercent } from "@/lib/scoreLevel";
import {
  EMPTY_HIGHLIGHT,
  tipHighlight,
  type TipHighlight,
} from "@/lib/tipHighlight";

interface ResultPanelProps {
  lessonId: string;
  segmentIndex: number;
  /** Câu đang tập: nguồn của đoạn văn dự phòng (E4) và của dòng IPA. */
  segment: Segment;
  result: ScoreResult;
  /** Số "Lượt k" hiển thị cho kết quả này. */
  attemptLabel: number;
  /** IPA đang bật (nút `IPA` / phím I). */
  ipaOn: boolean;
  /** Bản ghi trong phiên của lượt này; null khi không còn trong bộ nhớ. */
  blob: Blob | null;
  /** Clip của lượt này đã được lưu cho eval ở đây (phiên hiện tại). */
  saved: boolean;
  onSaved: () => void;
  /** `So sánh ngữ điệu` đang mở; state nằm ở PracticeRoom nên giữ nguyên khi chuyển câu. */
  chartOpen: boolean;
  onChartOpenChange: (open: boolean) => void;
}

/** Lớp tô từ khi gợi ý đang hover / focus (UI-SPEC); padding và margin âm triệt tiêu nên bố cục không dịch. */
const HIGHLIGHT_BASE = "-mx-1.5 -my-1 rounded-lg border-b-[3px] px-1.5 py-1";

function wordHighlightClass(index: number, highlight: TipHighlight): string {
  if (highlight.ref.includes(index)) {
    return `${HIGHLIGHT_BASE} border-original bg-original-soft`;
  }
  if (highlight.you.includes(index)) {
    return `${HIGHLIGHT_BASE} border-you bg-you-soft`;
  }
  if (highlight.neutral.includes(index)) {
    return `${HIGHLIGHT_BASE} border-[color:var(--slate-9)] bg-[color:var(--slate-4)]`;
  }
  return "";
}

const SENTENCE_CLASS =
  "m-0 text-[38px] font-semibold leading-[1.2] tracking-[-0.015em]";

/**
 * Vùng kết quả S3 ở `reviewing` (UI-SPEC "S3 — reviewing", cột phải mục 2–6): câu theo `words` +
 * IPA, `ScoreHero`, khối gợi ý (dòng khen / trung tính khi không có gợi ý) và `Lưu clip cho eval`.
 * Thay khối reviewing của P1. Người gọi đặt `key` theo (câu, lượt) để trạng thái mutation
 * không rò sang lượt khác. Khoảng cách 32 giữa các khối khớp `main` của cột phải.
 */
export function ResultPanel({
  lessonId,
  segmentIndex,
  segment,
  result,
  attemptLabel,
  ipaOn,
  blob,
  saved,
  onSaved,
  chartOpen,
  onChartOpenChange,
}: ResultPanelProps) {
  // Gợi ý đang hover / focus: state cục bộ của panel, không nằm trong machine (key theo lượt sẽ reset).
  const [hoveredTip, setHoveredTip] = useState<number | null>(null);

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

  // Mọi quyết định hiển thị đi qua hàm thuần đã có test, không có điều kiện inline (D-15, E4).
  const note = resultNote(result);
  const wordsOk = wordsMatchSegment(result.words, segment.text);
  // Gợi ý đang hover -> các từ của chính issue nó trỏ tới (FBK-03); issueRef lạc phạm vi thì không tô.
  const hoveredIssue =
    hoveredTip === null
      ? undefined
      : result.issues[result.tips[hoveredTip]?.issueRef ?? -1];
  const highlight = hoveredIssue
    ? tipHighlight(hoveredIssue, result.words)
    : EMPTY_HIGHLIGHT;

  return (
    <section
      aria-label={`Kết quả lượt ${attemptLabel}`}
      className="flex flex-col gap-8"
    >
      {/* Thông báo một lần khi kết quả xuất hiện; không dời focus (P3-G14). */}
      <span role="status" className="sr-only">
        {`Lượt ${attemptLabel}: ${scorePercent(result.scores.overall)} phần trăm giống bản gốc.`}
      </span>

      <div className="flex flex-col gap-[14px]">
        {wordsOk ? (
          // Từ chỉ là chữ: không gạch chân, số, màu hay click (D-06); cột dọc để Phase 5 thêm hàng điểm.
          <p
            className={`${SENTENCE_CLASS} flex flex-wrap gap-x-[14px] gap-y-[6px]`}
          >
            {result.words.map((word, index) => (
              <span
                key={index}
                className={`inline-flex flex-col ${wordHighlightClass(index, highlight)}`}
              >
                {word.text}
              </span>
            ))}
          </p>
        ) : (
          <p className={SENTENCE_CLASS}>{segment.text}</p>
        )}
        {ipaOn ? <SpokenIpa words={segment.words} /> : null}
      </div>

      <ScoreHero
        scores={result.scores}
        prosody={result.prosody}
        attemptLabel={attemptLabel}
      />

      <Collapsible
        open={chartOpen}
        onOpenChange={onChartOpenChange}
        className="flex flex-col gap-[10px] border-t border-border pt-6"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CollapsibleTrigger asChild>
            <Button variant="outline">
              <ChartLine aria-hidden="true" />
              So sánh ngữ điệu
            </Button>
          </CollapsibleTrigger>
          {chartOpen ? (
            <ul className="m-0 flex list-none gap-[14px] p-0 text-xs text-muted-foreground">
              <li className="flex items-center gap-[6px]">
                <span
                  aria-hidden="true"
                  className="h-[3px] w-4 rounded-[2px] bg-original"
                />
                Bản gốc
              </li>
              <li className="flex items-center gap-[6px]">
                <span
                  aria-hidden="true"
                  className="h-[3px] w-4 rounded-[2px] bg-you"
                />
                Bạn
              </li>
            </ul>
          ) : null}
        </div>
        <CollapsibleContent className="flex flex-col gap-[10px]">
          <h3 className="m-0 text-[13px] font-semibold leading-[1.2] text-muted-foreground">
            Ngữ điệu
          </h3>
          <IntonationChart
            prosody={result.prosody}
            words={result.words}
            issues={result.issues}
            highlight={highlight}
            tipsText={result.tips.map((tip) => tip.text).join(" ")}
          />
        </CollapsibleContent>
      </Collapsible>

      <div className="flex flex-col gap-[14px]">
        {result.tips.length >= 1 ? (
          <div className="border-t border-border pt-6">
            <TipList
              tips={result.tips}
              issues={result.issues}
              onHoverTip={setHoveredTip}
            />
          </div>
        ) : null}
        {note ? (
          <div className="border-t border-border pt-6">
            {note.kind === "praise" ? (
              <p
                role="status"
                className="m-0 flex items-center gap-2 rounded-lg bg-score-good-soft px-4 py-[14px] text-[15px] font-semibold leading-[1.5] text-foreground"
              >
                <Check
                  aria-hidden="true"
                  className="size-[18px] shrink-0 text-score-good-text"
                />
                {note.text}
              </p>
            ) : (
              <p
                role="status"
                className="m-0 rounded-lg bg-muted px-4 py-[14px] text-sm leading-[1.5] text-muted-foreground"
              >
                {note.text}
              </p>
            )}
          </div>
        ) : null}
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
      </div>
    </section>
  );
}
