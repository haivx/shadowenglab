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

// Khung rỗng cho pha RED của Task 2: chữ ký đúng, chưa có hành vi.
export function wordCells(
  _wordBounds: readonly number[],
  _pointCount: number,
): number[] {
  return [];
}

export interface StressBarHeights {
  ref: number;
  user: number;
}

export function stressBarHeights(
  _stress: readonly { ref: number; user: number }[],
): StressBarHeights[] {
  return [];
}

export function topStressWord(
  _stress: readonly { ref: number }[],
): number | null {
  return -1;
}

export function pauseMarkerXs(
  _issues: readonly Issue[],
  _wordBounds: readonly number[],
): number[] {
  return [-1];
}

export function chartAriaLabel(_tipTexts: readonly string[]): string {
  return "";
}
