"use client";

import { useMemo } from "react";
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
import { buildChartRows, chartDrawable, yDomain } from "@/lib/chartData";

export interface IntonationChartProps {
  prosody: Prosody;
  words: WordScore[];
  issues: Issue[];
  /** Văn bản các gợi ý, đã nối bằng khoảng trắng (dùng cho nhãn truy cập). */
  tipsText: string;
}

const PLOT_HEIGHT = 112;
const PLOT_MARGIN = { top: 8, right: 8, bottom: 8, left: 8 } as const;

/**
 * Biểu đồ ngữ điệu (UI-SPEC "IntonationChart"): hai contour semitone, bản gốc `--original`,
 * của bạn `--you`, trên baseline 0 st. Hình học và dữ liệu do `lib/chartData.ts` tính; màu chỉ
 * qua biến CSS. Không đủ cao độ thì hiện ghi chú trung tính thay cho biểu đồ (E2 empty).
 */
export function IntonationChart({ prosody }: IntonationChartProps) {
  const drawable = chartDrawable(prosody.contour);
  const rows = useMemo(
    () => buildChartRows(prosody.contour),
    [prosody.contour],
  );
  const domain = useMemo(() => yDomain(rows), [rows]);

  if (!drawable) {
    return (
      <Alert variant="neutral">
        Không đo được đủ cao độ ở lượt này để vẽ biểu đồ.
      </Alert>
    );
  }

  return (
    <div className="w-full min-w-[480px]">
      <ResponsiveContainer width="100%" height={PLOT_HEIGHT}>
        <LineChart data={rows} margin={PLOT_MARGIN} accessibilityLayer={false}>
          <XAxis
            type="number"
            dataKey="x"
            domain={[0, Math.max(rows.length - 1, 1)]}
            hide
          />
          <YAxis hide domain={domain} />
          <ReferenceLine
            y={0}
            stroke="var(--slate-5)"
            strokeWidth={1}
            strokeDasharray="3 4"
          />
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
    </div>
  );
}
