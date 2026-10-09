import type { AttemptSummary, ScoreResult } from "@shadowenglab/contracts";

export interface AttemptChip {
  attempt: number;
  ordinal: number;
  overall: number;
  label: string;
  isBest: boolean;
}

export function attemptChips(
  _list: AttemptSummary[] | undefined,
  _session: ScoreResult[],
  _max = 6,
): AttemptChip[] {
  return [];
}
