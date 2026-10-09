import type { Contour } from "@shadowenglab/contracts";

export interface ChartRow {
  x: number;
  ref: number | null;
  user: number | null;
}

// Khung rỗng cho pha RED: chữ ký đúng, chưa có hành vi.
export function buildChartRows(_contour: Contour): ChartRow[] {
  return [];
}

export function chartDrawable(_contour: Contour): boolean {
  return false;
}

export function yDomain(_rows: ChartRow[]): [number, number] {
  return [0, 0];
}
