import type { Issue, WordScore } from "@shadowenglab/contracts";

/** Chỉ số từ (trong `ScoreResult.words`) cần tô khi một gợi ý được hover / focus. */
export interface TipHighlight {
  /** Từ của bản gốc (teal) — chỉ STRESS_MISMATCH. */
  ref: number[];
  /** Từ bạn đã nhấn thay vào (cam) — chỉ STRESS_MISMATCH. */
  you: number[];
  /** Từ trung tính (xám) cho mọi mã khác. */
  neutral: number[];
}

export const EMPTY_HIGHLIGHT: TipHighlight = { ref: [], you: [], neutral: [] };

type WordText = Pick<WordScore, "text">;

/** Chữ thường, bỏ dấu câu ở đầu và cuối (giữ dấu nháy bên trong như `don't`). */
function normalise(text: string): string {
  return text.toLowerCase().replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");
}

function inRange(index: number, words: readonly WordText[]): boolean {
  return Number.isInteger(index) && index >= 0 && index < words.length;
}

function findWord(
  target: string,
  words: readonly WordText[],
): number | undefined {
  const wanted = normalise(target);
  if (wanted === "") return undefined;
  const found = words.findIndex((word) => normalise(word.text) === wanted);
  return found === -1 ? undefined : found;
}

/**
 * Gợi ý -> các từ nó nói tới (UI-SPEC "Highlight resolution"). Hàm thuần, mọi chỉ số nằm trong
 * `words`; FLAT_PITCH là cấp câu nên không từ nào được tô.
 */
export function tipHighlight(
  issue: Issue,
  words: readonly WordText[],
): TipHighlight {
  switch (issue.code) {
    case "STRESS_MISMATCH": {
      // Từ lặp lại ("the ... the"): nếu từ ở wordIndex đã khớp thì giữ đúng vị trí đó.
      const atIndex =
        inRange(issue.wordIndex, words) &&
        normalise(words[issue.wordIndex]?.text ?? "") ===
          normalise(issue.data.refWord)
          ? issue.wordIndex
          : undefined;
      const ref =
        atIndex ??
        findWord(issue.data.refWord, words) ??
        (inRange(issue.wordIndex, words) ? issue.wordIndex : undefined);
      const you = findWord(issue.data.userWord, words);
      return {
        ref: ref === undefined ? [] : [ref],
        you: you === undefined ? [] : [you],
        neutral: [],
      };
    }
    case "EXTRA_PAUSE":
    case "PITCH_DEVIATION":
      return {
        ref: [],
        you: [],
        neutral: inRange(issue.wordIndex, words) ? [issue.wordIndex] : [],
      };
    case "FINAL_CONTOUR":
      return {
        ref: [],
        you: [],
        neutral: words.length > 0 ? [words.length - 1] : [],
      };
    default:
      return EMPTY_HIGHLIGHT;
  }
}
