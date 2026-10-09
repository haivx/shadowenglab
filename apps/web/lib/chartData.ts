import type { Contour, Issue } from "@shadowenglab/contracts";

/** Một mẫu của biểu đồ: x là chỉ số frame (~20 ms), null = frame không hữu thanh. */
export interface ChartRow {
  x: number;
  ref: number | null;
  user: number | null;
}

/** Số điểm có giá trị tối thiểu mỗi bên để vẽ được biểu đồ (UI-SPEC "No data"). */
const MIN_VOICED_POINTS = 10;
/** Nửa khoảng y tối thiểu, đơn vị semitone (P3-G11). */
const MIN_HALF_RANGE = 6;

/** Ghép hai contour theo chỉ số; độ dài = số nhỏ hơn của hai bên. */
export function buildChartRows(contour: Contour): ChartRow[] {
  const length = Math.min(contour.ref.length, contour.user.length);
  const rows: ChartRow[] = [];
  for (let x = 0; x < length; x += 1) {
    rows.push({
      x,
      ref: contour.ref[x] ?? null,
      user: contour.user[x] ?? null,
    });
  }
  return rows;
}

function voicedCount(values: readonly (number | null)[]): number {
  return values.filter((value) => value !== null).length;
}

/** Đủ cao độ ở cả hai bên để vẽ; ngược lại hiện ghi chú trung tính (E2 empty). */
export function chartDrawable(contour: Contour): boolean {
  return (
    voicedCount(contour.ref) >= MIN_VOICED_POINTS &&
    voicedCount(contour.user) >= MIN_VOICED_POINTS
  );
}

/** Miền y đối xứng [-m, m], m = max(6, ceil(max|v|)) làm tròn lên số chẵn (P3-G11). */
export function yDomain(rows: readonly ChartRow[]): [number, number] {
  let peak = 0;
  for (const row of rows) {
    if (row.ref !== null) peak = Math.max(peak, Math.abs(row.ref));
    if (row.user !== null) peak = Math.max(peak, Math.abs(row.user));
  }
  const ceiled = Math.max(MIN_HALF_RANGE, Math.ceil(peak));
  const half = ceiled % 2 === 0 ? ceiled : ceiled + 1;
  return [-half, half];
}

/** Chiều cao thanh trọng âm: mẩu tối thiểu 3 px, tối đa 24 px (UI-SPEC "Word row"). */
const STRESS_STUB_PX = 3;
const STRESS_RANGE_PX = 21;

/**
 * Chiều rộng tương đối (tổng 1) của từng ô từ, theo phần `wordBounds` chiếm trên `pointCount`
 * điểm của contour. Ranh giới trùng nhau không được cho ô rộng 0 nên mỗi ô có sàn nhỏ rồi
 * chuẩn hoá lại; trường hợp bình thường không bị chạm.
 */
export function wordCells(
  wordBounds: readonly number[],
  pointCount: number,
): number[] {
  const first = wordBounds[0];
  if (first === undefined) return [];
  const total = pointCount - first;
  if (total <= 0) return [];
  const floor = 1 / (2 * total);
  let clamped = false;
  const widths = wordBounds.map((bound, i) => {
    const next = wordBounds[i + 1] ?? pointCount;
    const share = (next - bound) / total;
    if (share >= floor) return share;
    clamped = true;
    return floor;
  });
  if (!clamped) return widths;
  const sum = widths.reduce((a, b) => a + b, 0);
  return widths.map((width) => width / sum);
}

export interface StressBarHeights {
  ref: number;
  user: number;
}

/** Chiều cao (px) hai thanh mỗi từ: 3 + 21 × max(0, z) / z dương lớn nhất; không có z dương thì toàn mẩu 3 px. */
export function stressBarHeights(
  stress: readonly { ref: number; user: number }[],
): StressBarHeights[] {
  let maxPositive = 0;
  for (const entry of stress) {
    maxPositive = Math.max(maxPositive, entry.ref, entry.user);
  }
  const height = (z: number): number =>
    maxPositive > 0
      ? STRESS_STUB_PX + (Math.max(0, z) / maxPositive) * STRESS_RANGE_PX
      : STRESS_STUB_PX;
  return stress.map((entry) => ({
    ref: height(entry.ref),
    user: height(entry.user),
  }));
}

/** Chỉ số từ nổi nhất của bản gốc (max `ref`, hoà thì từ đứng trước); rỗng thì null. */
export function topStressWord(
  stress: readonly { ref: number; user: number }[],
): number | null {
  let best: number | null = null;
  stress.forEach((entry, i) => {
    const current = best === null ? undefined : stress[best];
    if (current === undefined || entry.ref > current.ref) best = i;
  });
  return best;
}

/**
 * Vị trí x của dấu ‖: `wordBounds[wordIndex + 1]` cho mỗi issue EXTRA_PAUSE. Từ cuối không có
 * ranh giới kế tiếp thì bỏ qua; ngắt nghỉ không phải issue không được vẽ (P3-G4).
 */
export function pauseMarkerXs(
  issues: readonly Issue[],
  wordBounds: readonly number[],
): number[] {
  const xs: number[] = [];
  for (const issue of issues) {
    if (issue.code !== "EXTRA_PAUSE") continue;
    const x = wordBounds[issue.wordIndex + 1];
    if (x !== undefined) xs.push(x);
  }
  return xs;
}

const ARIA_PREFIX =
  "Ngữ điệu: đường xanh ngọc là bản gốc, đường cam là của bạn.";

/** Nhãn `role="img"` của biểu đồ: giải thích màu rồi các gợi ý, đã bỏ dấu `*` đánh dấu từ. */
export function chartAriaLabel(tipTexts: readonly string[]): string {
  const tips = tipTexts
    .map((text) => text.replaceAll("*", "").trim())
    .filter((text) => text.length > 0);
  return [ARIA_PREFIX, ...tips].join(" ");
}
