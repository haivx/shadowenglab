import type { ScoreResult } from "@shadowenglab/contracts";
import type { AttemptChip } from "./attemptChips";

export type ViewedEvent =
  | { type: "sentenceChanged"; chips: AttemptChip[] }
  | { type: "chipsLoaded"; chips: AttemptChip[] }
  | { type: "scored"; attempt: number }
  | { type: "selected"; attempt: number };

export type ViewedResult =
  | { kind: "none" }
  | { kind: "session"; result: ScoreResult; ordinal: number }
  | { kind: "stored"; attempt: number; ordinal: number };

export function nextViewedAttempt(
  current: number | null,
  _event: ViewedEvent,
): number | null {
  return current;
}

export function resolveViewedResult(
  _viewedAttempt: number | null,
  _session: ScoreResult[],
  _chips: AttemptChip[],
): ViewedResult {
  return { kind: "none" };
}
