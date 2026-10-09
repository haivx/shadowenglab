---
phase: 03-p2-ch-m-ng-i-u
plan: 08
subsystem: ui
tags: [react, tailwind, recharts, vitest, tip-list, highlight]

requires:
  - phase: 03-p2-ch-m-ng-i-u
    plan: 04
    provides: "ResultPanel with the praise/neutral line and sentence word spans"
  - phase: 03-p2-ch-m-ng-i-u
    plan: 06
    provides: "Backend tips with *word* markup and issueRef (rules/tips.py)"
  - phase: 03-p2-ch-m-ng-i-u
    plan: 07
    provides: "IntonationChart (Recharts) and chartData helpers"
provides:
  - "lib/tipMarkup.ts: splitTipMarkup (*word* -> text/word segments with ordinals)"
  - "lib/tipHighlight.ts: tipHighlight(issue, words) -> {ref, you, neutral}, EMPTY_HIGHLIGHT"
  - "components/TipList.tsx: numbered 01-03 tip rows, hover/focus callback"
  - "ResultPanel: hovered-tip state, TipList branch, sentence word highlight"
  - "IntonationChart: highlight prop, ReferenceArea per highlighted word"
affects: [03-10, 03-11]

actuals:
  tokens: 9000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Untrusted tip/word text only reaches the DOM as React text children built from pure segment data"
    - "Highlight resolution in a pure node-tested helper; components only map indexes to literal Tailwind classes"

key-files:
  created:
    - apps/web/lib/tipMarkup.ts
    - apps/web/lib/tipMarkup.test.ts
    - apps/web/lib/tipHighlight.ts
    - apps/web/lib/tipHighlight.test.ts
    - apps/web/components/TipList.tsx
  modified:
    - apps/web/components/ResultPanel.tsx
    - apps/web/components/IntonationChart.tsx

key-decisions:
  - "Hovered-tip state lives in ResultPanel (useState), not in the machine and not in PracticeRoom; the existing key on (sentence, attempt) resets it for every new result"
  - "STRESS_MISMATCH ref resolution prefers issue.wordIndex when that word already matches refWord, so a repeated word highlights the right occurrence"
  - "PHONE and WORD_MISSING (Phase 5 codes) resolve to an empty highlight until their UI exists"

patterns-established:
  - "TipList row = grid 28px / minmax(0,1fr), tabIndex 0, onMouseEnter+onFocus -> onHoverTip(i), onMouseLeave+onBlur -> onHoverTip(null)"

requirements-completed: [FBK-03, RUL-02]

coverage:
  - id: D1
    description: "*word* markup splitting: pairs become word segments with ordinals, unmatched or empty markers and HTML stay literal text"
    requirement: FBK-03
    verification:
      - kind: unit
        ref: "apps/web/lib/tipMarkup.test.ts#splitTipMarkup"
        status: pass
    human_judgment: false
  - id: D2
    description: "Tip to word highlight resolution for all five Layer C codes (normalised matching, fallbacks, out-of-range guards)"
    requirement: FBK-03
    verification:
      - kind: unit
        ref: "apps/web/lib/tipHighlight.test.ts#tipHighlight"
        status: pass
    human_judgment: false
  - id: D3
    description: "TipList, ResultPanel highlight wiring and IntonationChart ReferenceArea compile in the Next 14 build, lint clean, no raw HTML injection"
    requirement: RUL-02
    verification:
      - kind: other
        ref: "pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web && tsc --noEmit && ! grep -rn dangerouslySetInnerHTML apps/web"
        status: pass
    human_judgment: false
  - id: D4
    description: "Visual behaviour: hover and Tab through tips highlight the right words in the sentence and as a grey band in the open chart; 120-character tip and 18-word sentence wrap at 1280 px without horizontal scroll or overlap"
    requirement: FBK-03
    verification: []
    human_judgment: true
    rationale: "Pixel layout, Recharts ReferenceArea rendering with a CSS variable fill, and E3/E4 long-text backstops are only observable in a browser; collected in the 03-11 UAT"

duration: 12min
completed: 2026-10-09
status: complete
plan_head_before: 9fdf2210e79179d781003cebdaf3e892cedab364
plan_head_after: 2b5fe7319c5c0bc126354b3ba6da73dd3c9016e1
commits: 4
---

# Phase 3 Plan 08: TipList and hover highlight Summary

**Backend Vietnamese tips now render as a numbered `TipList` with `*word*` marks shown as bold underlined React text (never HTML), and hovering or Tab-focusing a tip tints its words in the sentence (teal/orange for STRESS_MISMATCH, slate otherwise) and draws a `--slate-4` band behind the chart lines.**

## Performance

- **Duration:** about 12 min
- **Completed:** 2026-10-09
- **Tasks:** 2 (Task 1 tracer, Task 2 auto, both TDD)
- **Files:** 5 created, 2 modified (all under `apps/web`)

`commits: 4` is measured with `git rev-list --count 9fdf2210..HEAD`: RED + GREEN for each task. The SUMMARY docs commit follows `plan_head_after`.

## Accomplishments

- `splitTipMarkup` scans for `*run-without-star*` pairs; `a *b`, `**` and `<b>x</b>` stay literal text. Pure data out, no HTML.
- `TipList` (`"use client"`): props `{ tips: Tip[]; issues: Issue[]; onHoverTip: (index: number | null) => void }`. `ol` list-none, flex column gap 14, 16/1.5; each `li` grid `28px minmax(0,1fr)` gap 8, `tabIndex={0}`, `hover:bg-muted focus-visible:bg-muted`, index `01`-`03` mono 13/500 muted pt 3, text column `overflow-wrap: anywhere`. Marked words bold 700 + 2 px underline in `--slate-9`; for a STRESS_MISMATCH tip the first word is underlined `--original`, the second `--you` (P3-G5). Order and count are exactly the backend's.
- `ResultPanel`: `useState<number | null>` for the hovered tip; renders `TipList` when `tips.length >= 1`, else the existing praise/neutral line (never both, `resultNote` returns null with tips). Sentence word spans get `ref` / `you` / `neutral` classes (3 px bottom border, `rounded-lg px-1.5 py-1 -mx-1.5 -my-1` so layout does not shift). Highlighting only applies on the `words` rendering path; the plain `segment.text` fallback (E4 error) has no spans. An out-of-range `issueRef` yields an empty highlight.
- `IntonationChart`: new optional `highlight?: TipHighlight`; a `ReferenceArea` per unique highlighted index (`x1 = wordBounds[i]`, `x2 = wordBounds[i+1] ?? rows.length - 1`, fill `var(--slate-4)`) placed before the baseline and lines; the hovered word's label in the word row becomes bold `--foreground`.

## Task Commits

1. **Task 1: Tracer, Tip.text with `*word*` -> numbered TipList in the result panel** (TDD, tracer)
   - RED: `82558bb` (test) - splitTipMarkup tests against a pass-through stub
   - GREEN: `b62bebc` (feat) - splitTipMarkup, TipList, ResultPanel branch
2. **Task 2: Hover/focus tip -> highlight words in sentence and chart** (TDD)
   - RED: `e128927` (test) - tipHighlight tests against an empty-result stub
   - GREEN: `2b5fe73` (feat) - tipHighlight, sentence highlight, chart ReferenceArea

**Tracer gate:** `human_verify_mode` is `end-of-phase` and the tracer `<verify>` is automated-only, so it was re-run after the tracer commit (vitest 7/7, web build, no `dangerouslySetInnerHTML`) and passed. Logged: "Tracer verified end-to-end - expanding".

## TDD Gate Compliance

- **RED 1** (`82558bb`): with a stub returning the whole text as one segment, 4 of 7 `tipMarkup` tests failed on assertions (two-word split, HTML + word, leading/trailing words, empty string -> `[]`); the 3 that passed (no marker, lone `*`, `**`) hold trivially against the stub and are recorded as characterization. Semantic assessment: failures are the missing behaviour, not import or fixture faults. `gsd_run check tdd-red-evidence` was not run (default vitest reporter, same as 03-01/03-04/03-07).
- **GREEN 1** (`b62bebc`): tipMarkup 7/7, build, eslint exit 0.
- **RED 2** (`e128927`): with a stub returning an empty highlight, 7 of 10 `tipHighlight` tests failed on `toEqual` assertions (STRESS_MISMATCH x4, EXTRA_PAUSE, PITCH_DEVIATION, FINAL_CONTOUR); the 3 passing are the empty-expected cases (FLAT_PITCH, empty words, out-of-range).
- **GREEN 2** (`2b5fe73`): tipHighlight 10/10, tipMarkup 7/7, chartData 22/22 (39 total); whole web suite 231/231; build, eslint, `tsc --noEmit`, prettier check exit 0.
- **REFACTOR:** none.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `match[1]` is `string | undefined` under `noUncheckedIndexedAccess`**
- **Found during:** Task 1 (`next build` type check after the first GREEN draft; vitest had passed)
- **Fix:** `match[1] ?? ""` in `splitTipMarkup`
- **Files modified:** `apps/web/lib/tipMarkup.ts`
- **Committed in:** `b62bebc`

**2. [Rule 2 - Missing critical] Out-of-range guards in `tipHighlight` and `ResultPanel`**
- **Found during:** Task 2
- **Issue:** `wordIndex` / `issueRef` come from the backend; an out-of-range value must not produce a highlight of a non-existent word or throw on `result.tips[...]`.
- **Fix:** `inRange` checks on every `wordIndex`, empty `FINAL_CONTOUR` for zero words, `issues[tips[h]?.issueRef ?? -1]` lookup returning undefined -> `EMPTY_HIGHLIGHT`.
- **Files modified:** `apps/web/lib/tipHighlight.ts`, `apps/web/components/ResultPanel.tsx`
- **Committed in:** `2b5fe73`

---

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 2). **Impact on plan:** none on scope, contract or UI-SPEC.

## Decisions Made

- Hover state stays inside `ResultPanel`, as the plan and the parallel-execution note require; `PracticeRoom.tsx` was not touched (its existing `key={index:attempt}` on `ResultPanel` resets hover per result).
- A repeated word ("the ... the") highlights the occurrence at `issue.wordIndex` when it matches `refWord`, before falling back to the first match.
- `Task 1` left `hoveredTip` unread (destructured as `[, setHoveredTip]`) to keep lint clean until Task 2 consumed it.

## Issues Encountered

- The worktree had no `node_modules`; ran `pnpm install --frozen-lockfile` (no package added, lockfile unchanged).
- The harness shell guard rejected compound git/heredoc commands; commands were split and files written with the Write tool.
- The per-plan commit ledger was not written; `plan_head_before` is the base HEAD verified at start (`9fdf2210`), and `commits: 4` was measured with `git rev-list --count`.

## Known Stubs

None. The RED-phase stubs in `tipMarkup.ts` and `tipHighlight.ts` were replaced in the GREEN commits.

## Threat Flags

None. T-03-18 mitigated as planned: `splitTipMarkup` -> React text children only, grep for `dangerouslySetInnerHTML` over `apps/web/components`, `lib` and `app` returns nothing, and the backend already strips `*` from inserted words (03-06). T-03-SC accepted: no package added.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Pending human check (03-11 UAT, collected from Task 2 `<human-check>` and the E3/E4 backstops): hover and Tab through the tips of a scored sentence with a STRESS_MISMATCH and an EXTRA_PAUSE tip; confirm the right words tint in the sentence and as a grey band in the open chart; check a 120-character tip with a 20-character marked word and an 18-word sentence at 1280 px for wrapping and no overlap.
- Open from 03-07: that Recharts honours CSS-variable colours (`var(--slate-4)` fill of `ReferenceArea` shares that risk with the line strokes); if the band is invisible, switch to a className-based fill.
- Open item J (pending Liam, 03-01): the chart band is neutral `--slate-4` for every code while the sentence uses teal/orange only for STRESS_MISMATCH (P3-G5).

## Self-Check: PASSED

- FOUND: apps/web/lib/tipMarkup.ts, tipMarkup.test.ts, tipHighlight.ts, tipHighlight.test.ts, apps/web/components/TipList.tsx
- FOUND commits 82558bb, b62bebc, e128927, 2b5fe73 on this branch (4 commits since 9fdf2210)
- Acceptance: `splitTipMarkup` import and `tabIndex={0}` in TipList.tsx; `<TipList` only under `result.tips.length >= 1` in ResultPanel.tsx; `tipHighlight` exported; `ReferenceArea` in IntonationChart.tsx; `highlight=` passed in ResultPanel.tsx
- Verification: vitest (tipHighlight, tipMarkup, chartData) 39/39 and full web suite 231/231; `pnpm --filter @shadowenglab/web build`, `pnpm exec eslint apps/web`, `tsc --noEmit`, prettier check exit 0; no `dangerouslySetInnerHTML` in apps/web; no hex literal in the new files

---
*Phase: 03-p2-ch-m-ng-i-u*
*Completed: 2026-10-09*
