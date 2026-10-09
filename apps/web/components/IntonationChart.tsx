"use client";

import { useMemo, useState } from "react";
import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import type { Issue, Prosody, WordScore } from "@shadowenglab/contracts";
import { Alert } from "@/components/ui/alert";
import {
  buildChartRows,
  chartAriaLabel,
  chartDrawable,
  pauseMarkerXs,
  stressBarHeights,
  topStressWord,
  wordCells,
  yDomain,
} from "@/lib/chartData";

export interface IntonationChartProps {
  prosody: Prosody;
  words: WordScore[];
  issues: Issue[];
  /** Văn bản các gợi ý, đã nối bằng khoảng trắng (dùng cho nhãn truy cập). */
  tipsText: string;
}

const PLOT_HEIGHT = 112;
/** Lề ngang của plot; hàng từ dùng cùng giá trị (px-2) để các x thẳng hàng. */
const PLOT_MARGIN_X = 8;
const PLOT_MARGIN = {
  top: 8,
  right: PLOT_MARGIN_X,
  bottom: 8,
  left: PLOT_MARGIN_X,
} as const;
/** Hai nét ‖ cách nhau khoảng 3 px (UI-SPEC "Pause marker"). */
const PAUSE_STROKE_GAP_PX = 3;
const PAUSE_LABEL = "ngắt thừa";
/** Chỗ tối thiểu bên phải dấu ‖ để nhãn nằm bên phải; ít hơn thì nhãn lật sang trái. */
const PAUSE_LABEL_ROOM_PX = 64;

interface PauseLabelProps {
  viewBox?: { x?: number; y?: number };
  flip: boolean;
}

/** Nhãn `ngắt thừa` 11/600 `--issue-text`, lệch 6 px so với nét ‖, ở đỉnh plot. */
function PauseLabel({ viewBox, flip }: PauseLabelProps) {
  if (viewBox?.x === undefined || viewBox.y === undefined) return null;
  return (
    <text
      x={flip ? viewBox.x - 6 : viewBox.x + 6}
      y={viewBox.y + 11}
      textAnchor={flip ? "end" : "start"}
      fontSize={11}
      fontWeight={600}
      style={{ fill: "var(--issue-text)" }}
    >
      {PAUSE_LABEL}
    </text>
  );
}

/**
 * Biểu đồ ngữ điệu (UI-SPEC "IntonationChart"): hai contour semitone, bản gốc `--original`,
 * của bạn `--you`, trên baseline 0 st; dưới plot là hàng từ HTML có thanh trọng âm. Hình học
 * và dữ liệu do `lib/chartData.ts` tính; màu chỉ qua biến CSS. Không đủ cao độ thì hiện ghi chú
 * trung tính thay cho cả plot và hàng từ (E2 empty).
 */
export function IntonationChart({
  prosody,
  words,
  issues,
  tipsText,
}: IntonationChartProps) {
  const [plotWidth, setPlotWidth] = useState(0);
  const { contour, stress } = prosody;
  const rows = useMemo(() => buildChartRows(contour), [contour]);
  const domain = useMemo(() => yDomain(rows), [rows]);
  const cells = useMemo(
    () => wordCells(contour.wordBounds, rows.length),
    [contour.wordBounds, rows.length],
  );
  const bars = useMemo(() => stressBarHeights(stress), [stress]);
  const topWord = useMemo(() => topStressWord(stress), [stress]);
  const pauseXs = useMemo(
    () => pauseMarkerXs(issues, contour.wordBounds),
    [issues, contour.wordBounds],
  );

  if (!chartDrawable(contour)) {
    return (
      <Alert variant="neutral">
        Không đo được đủ cao độ ở lượt này để vẽ biểu đồ.
      </Alert>
    );
  }

  const lastX = Math.max(rows.length - 1, 1);
  const innerWidth = plotWidth - 2 * PLOT_MARGIN_X;
  // Đổi px sang đơn vị trục x để đặt hai nét ‖ cách nhau 3 px; chưa đo được thì gộp thành một nét.
  const halfGapX =
    innerWidth > 0 ? ((PAUSE_STROKE_GAP_PX / 2) * lastX) / innerWidth : 0;

  return (
    <div
      role="img"
      aria-label={chartAriaLabel([tipsText])}
      className="w-full min-w-[480px]"
    >
      <ResponsiveContainer
        width="100%"
        height={PLOT_HEIGHT}
        onResize={(width) => setPlotWidth(width)}
      >
        <LineChart data={rows} margin={PLOT_MARGIN} accessibilityLayer={false}>
          <XAxis type="number" dataKey="x" domain={[0, lastX]} hide />
          <YAxis hide domain={domain} />
          <ReferenceLine
            y={0}
            stroke="var(--slate-5)"
            strokeWidth={1}
            strokeDasharray="3 4"
          />
          {pauseXs.map((x) => (
            <ReferenceLine
              key={`pause-${x}`}
              x={x - halfGapX}
              stroke="var(--issue)"
              strokeWidth={2}
              ifOverflow="visible"
            />
          ))}
          {pauseXs.map((x) => {
            const flip =
              innerWidth > 0 &&
              ((lastX - x) / lastX) * innerWidth < PAUSE_LABEL_ROOM_PX;
            return (
              <ReferenceLine
                key={`pause-r-${x}`}
                x={x + halfGapX}
                stroke="var(--issue)"
                strokeWidth={2}
                ifOverflow="visible"
                label={(props: PauseLabelProps) => (
                  <PauseLabel viewBox={props.viewBox} flip={flip} />
                )}
              />
            );
          })}
          <Line
            dataKey="ref"
            dot={false}
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
            connectNulls={false}
            isAnimationActive={false}
            style={{ stroke: "var(--original)" }}
          />
          <Line
            dataKey="user"
            dot={false}
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
            connectNulls={false}
            isAnimationActive={false}
            style={{ stroke: "var(--you)" }}
          />
        </LineChart>
      </ResponsiveContainer>
      {cells.length > 0 ? (
        <div className="flex h-20 px-2">
          {cells.map((share, i) => {
            const label = words[i]?.text ?? stress[i]?.word ?? "";
            const height = bars[i] ?? { ref: 3, user: 3 };
            return (
              <div
                key={i}
                style={{ width: `${share * 100}%` }}
                className="flex min-w-0 shrink-0 flex-col items-center px-px pb-4 pt-3"
              >
                <div
                  aria-hidden="true"
                  className="flex h-8 items-end gap-[3px]"
                >
                  <span
                    className="w-[6px] rounded-[2px] bg-original"
                    style={{ height: height.ref }}
                  />
                  <span
                    className="w-[6px] rounded-[2px] bg-you"
                    style={{ height: height.user }}
                  />
                </div>
                <span
                  title={label}
                  className={`mt-0 h-5 w-full truncate text-center text-xs leading-5 ${
                    i === topWord
                      ? "font-bold text-foreground"
                      : "text-muted-foreground"
                  }`}
                >
                  {label}
                </span>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
