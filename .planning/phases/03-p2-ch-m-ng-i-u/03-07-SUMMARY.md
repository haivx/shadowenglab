---
phase: 03-p2-ch-m-ng-i-u
plan: 07
subsystem: ui
tags: [recharts, react, tailwind, vitest, intonation-chart]

requires:
  - phase: 03-p2-ch-m-ng-i-u
    plan: 02
    provides: "recharts 3.10.1 and the Collapsible primitive"
  - phase: 03-p2-ch-m-ng-i-u
    plan: 04
    provides: "ResultPanel / ScoreHero in the S3 reviewing region"
provides:
  - "lib/chartData.ts: buildChartRows, chartDrawable, yDomain, wordCells, stressBarHeights, topStressWord, pauseMarkerXs, chartAriaLabel (pure, node-tested)"
  - "components/IntonationChart.tsx: Recharts plot + HTML word/stress row + pause marker + no-data Alert"
  - "ResultPanel: So sánh ngữ điệu toggle (Collapsible, outline 44) and Bản gốc / Bạn legend; props chartOpen, onChartOpenChange"
  - "PracticeRoom: chartOpen state (session only, survives sentence changes)"
  - "globals.css: --issue / --issue-text alias tokens (P3-G4)"
affects: [03-08, 03-10, 03-11]

actuals:
  tokens: 6000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "All chart geometry and data shaping in pure helpers (lib/chartData.ts); the component only composes them"
    - "Chart colours only through CSS variables (var(--original), var(--you), var(--slate-5), var(--issue), var(--issue-text)); no hex literal in chart files"
    - "Pause marker = two 2 px ReferenceLine strokes whose x offset is converted from 3 px using the ResponsiveContainer width (onResize)"

key-files:
  created:
    - apps/web/lib/chartData.ts
    - apps/web/lib/chartData.test.ts
    - apps/web/components/IntonationChart.tsx
  modified:
    - apps/web/components/ResultPanel.tsx
    - apps/web/components/PracticeRoom.tsx
    - apps/web/app/globals.css

key-decisions:
  - "Pause marker label flips to the left of the marker when less than 64 px remain to its right, so ngắt thừa is never clipped at the plot edge"
  - "wordCells floors each cell at half an average point-share and renormalises only when a floor was applied, so duplicate wordBounds never produce a zero-width cell while normal input is returned exactly"
  - "IntonationChart reads word labels from words[i].text and falls back to stress[i].word, so a words/wordBounds length mismatch still draws labelled cells"

patterns-established:
  - "Tracer then expansion: tracer plot behind the toggle first, word row, markers, legend and aria label after"

requirements-completed: [FBK-02]

coverage:
  - id: D1
    description: "Chart data shaping: rows from both contours, drawable threshold (10 voiced points per side), symmetric even y domain"
    requirement: FBK-02
    verification:
      - kind: unit
        ref: "apps/web/lib/chartData.test.ts#buildChartRows / chartDrawable / yDomain"
        status: pass
    human_judgment: false
  - id: D2
    description: "Word row geometry and annotations: cell widths from wordBounds, stress bar heights, top stress word, EXTRA_PAUSE marker positions, accessible label without * markers"
    requirement: FBK-02
    verification:
      - kind: unit
        ref: "apps/web/lib/chartData.test.ts#wordCells / stressBarHeights / topStressWord / pauseMarkerXs / chartAriaLabel"
        status: pass
    human_judgment: false
  - id: D3
    description: "Chart renders in the Next 14 build and ResultPanel/PracticeRoom wiring type-checks (Recharts 3.10.1 + Collapsible toggle, chartOpen state)"
    requirement: FBK-02
    verification:
      - kind: other
        ref: "pnpm --filter @shadowenglab/web build && pnpm --filter @shadowenglab/web exec tsc --noEmit && pnpm exec eslint apps/web"
        status: pass
    human_judgment: false
  - id: D4
    description: "Visual match to S3-S4-phong-tap.png: teal original / orange learner lines drawn through CSS variables, dashed baseline, word labels, stress bars, double-stroke ngắt thừa marker, legend, 1-word and 25-word sentences"
    requirement: FBK-02
    verification: []
    human_judgment: true
    rationale: "Recharts stroke via style={{ stroke: var(--...) }} (RESEARCH A4) and pixel alignment of plot and word row are only observable in a browser; collected in the 03-11 UAT (human-check on Task 2)"

duration: 14min
completed: 2026-10-09
status: complete
plan_head_before: b3a35fb47508c0ada98d441f61d9136dbc0e0ceb
plan_head_after: 8915462413488fc9bb68e7c1286759022415f559
commits: 4
---

# Phase 3 Plan 07: IntonationChart Summary

**`So sánh ngữ điệu` now opens a Recharts chart of the original (teal) and learner (orange) semitone contours on a dashed 0 st baseline, with a per-word stress-bar row, a double-stroke `ngắt thừa` marker for EXTRA_PAUSE issues, a legend and a `role="img"` label, all shaped by pure node-tested helpers.**

## Performance

- **Duration:** about 14 min
- **Started:** 2026-10-09T14:21Z (approx.)
- **Completed:** 2026-10-09T14:31Z (approx.)
- **Tasks:** 2 (Task 1 tracer, Task 2 auto, both TDD)
- **Files modified:** 6 in `apps/web` (3 created, 3 modified)

`commits: 4` is measured from `plan_head_before` and counts RED + GREEN for each task; the SUMMARY docs commit follows `plan_head_after`.

## Accomplishments

- `lib/chartData.ts` holds every computation (no React): `buildChartRows`, `chartDrawable`, `yDomain` (Task 1) and `wordCells`, `stressBarHeights`, `topStressWord`, `pauseMarkerXs`, `chartAriaLabel` (Task 2). 22 vitest cases.
- `IntonationChart` ("use client"): `ResponsiveContainer` 112 px, `LineChart` with `accessibilityLayer={false}`, hidden numeric `XAxis` and `YAxis`, dashed `--slate-5` baseline, two 3 px lines with `connectNulls={false}` and `isAnimationActive={false}`, HTML word row 80 px (`px-2` matches the plot margin 8) with two 6 px bars per word (`--original` / `--you`, `aria-hidden`), 12 px labels with `truncate` + `title`, top-stress label 700 `--foreground`.
- Pause marker: for each EXTRA_PAUSE issue two 2 px `--issue` ReferenceLines about 3 px apart at `wordBounds[wordIndex + 1]` plus the label `ngắt thừa` (11/600 `--issue-text`) 6 px to the right. Non-issue pauses are not drawn.
- E2 empty: fewer than 10 non-null points on either side renders the neutral `Alert` `Không đo được đủ cao độ ở lượt này để vẽ biểu đồ.` instead of plot and word row; toggle and legend stay.
- `ResultPanel`: chart block between `ScoreHero` and the tip block (`border-t pt-6`, gap 10), `Collapsible` whose trigger is an outline 44 px `Button` with `ChartLine` + `So sánh ngữ điệu` (`aria-expanded` from the Radix primitive, closed by default), heading `Ngữ điệu` inside the open region, legend `Bản gốc` / `Bạn` (16x3 swatches, gap 14, swatch gap 6) only when open.
- `PracticeRoom` keeps `chartOpen` at `LoadedRoom` level: not keyed by sentence, not persisted.
- `globals.css`: `--issue: var(--red-9)`, `--issue-text: var(--red-11)`.

### Notes for downstream plans

- **IntonationChart props (03-08 adds `highlight`):** `{ prosody: Prosody; words: WordScore[]; issues: Issue[]; tipsText: string }`. 03-08 should add a `highlight` prop and render `ReferenceArea` behind the lines using `contour.wordBounds` (the lines are the last children of the `LineChart`, so an area must be placed before the `ReferenceLine`s / `Line`s).
- **RESEARCH A4 (CSS variable as Recharts stroke):** the lines use `style={{ stroke: "var(--original)" }}` / `"var(--you)"` exactly as planned. The Next 14 build, tsc and eslint pass, so the API accepts it. I could NOT confirm in a browser that the variable is honoured: a server-side render of a bare `LineChart` emits no path markup (Recharts 3 draws after layout), so the check was inconclusive. It stays an open item for the 03-11 human check; if the lines come out in Recharts' default blue, switch to a className-based stroke as the plan describes.

## Task Commits

1. **Task 1: Tracer, contour in ScoreResult -> Recharts inside the So sánh ngữ điệu disclosure** (TDD, tracer)
   - RED: `abb1eaf` (test) - chartData tests against a behaviour-less stub
   - GREEN: `75b2b0f` (feat) - chartData helpers, IntonationChart plot + no-data Alert, ResultPanel Collapsible, PracticeRoom state
2. **Task 2: Word row, stress bars, pause marker, legend, aria label** (TDD)
   - RED: `194270d` (test) - tests for the five new helpers against a stub
   - GREEN: `8915462` (feat) - helpers, word row, pause marker, legend, `--issue` tokens

**Plan metadata:** docs commit for this SUMMARY follows (hash not embedded to avoid self-reference).

Tracer gate: `human_verify_mode` is `end-of-phase`, `auto_advance` is false and the tracer `<verify>` is automated-only, so the verify (vitest 7/7 and `pnpm --filter @shadowenglab/web build`) was re-run after the commit and passed. Logged: "Tracer verified end-to-end - expanding", then Task 2.

## TDD Gate Compliance

- **RED 1** (`abb1eaf`): with an empty-behaviour stub, 5 of 7 `chartData` tests failed on assertions (`expected [] to deeply equal [...]`, `expected [ +0, +0 ] to deeply equal [ -6, 6 ]`, `expected false to be true`); the 2 that passed (empty contour -> `[]`, 9 voiced points -> not drawable) agree with the stub by coincidence. Semantic assessment: failures are the missing behaviour, not import or fixture faults. `gsd_run check tdd-red-evidence` was not run (default vitest reporter, same as 03-01 and 03-04).
- **GREEN 1** (`75b2b0f`): chartData 7/7, web suite 199/199, build, eslint, tsc exit 0.
- **RED 2** (`194270d`): 13 of 22 tests failed on assertions against the stub (e.g. `wordCells` returned `[]`, `pauseMarkerXs` returned `[-1]`, `chartAriaLabel` returned `""`); the 9 that passed were Task 1 tests plus the empty-input case of `stressBarHeights`.
- **GREEN 2** (`8915462`): chartData 22/22, web suite 214/214, build, eslint, tsc, prettier, hex-literal grep exit 0.
- **REFACTOR:** none.

## Files Created/Modified

- `apps/web/lib/chartData.ts` (+ `chartData.test.ts`) - pure helpers
- `apps/web/components/IntonationChart.tsx` - Recharts plot, word row, pause marker, no-data Alert
- `apps/web/components/ResultPanel.tsx` - toggle, content, legend, new props
- `apps/web/components/PracticeRoom.tsx` - `chartOpen` state
- `apps/web/app/globals.css` - `--issue`, `--issue-text`

## Decisions Made

- The label of the pause marker flips left near the right plot edge (not in the spec, small addition so the text is never clipped).
- `wordCells` guards against duplicate bounds with a floor and renormalisation (spec only requires widths > 0 and sum 1 for a normal 25-word sentence).
- The offset between the two `‖` strokes is converted from 3 px to x-axis units using the container width reported by `ResponsiveContainer`'s `onResize`; before the first measurement the two strokes coincide for one frame.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `topStressWord` parameter type rejected the plan's own test input**
- **Found during:** Task 2 (`tsc --noEmit` after GREEN)
- **Issue:** the parameter was typed `readonly { ref: number }[]`; the test passes `{ ref, user }` literals, so excess-property checking failed (`TS2353`) while vitest still passed
- **Fix:** typed it `readonly { ref: number; user: number }[]`, consistent with `stressBarHeights` and `StressEntry`
- **Files modified:** `apps/web/lib/chartData.ts`
- **Verification:** tsc, vitest 22/22, build, eslint exit 0
- **Committed in:** `8915462`

---

**Total deviations:** 1 auto-fixed (1 Rule 1)
**Impact on plan:** type-only correction; no behaviour or scope change.

## Issues Encountered

- The worktree had no `node_modules`; ran `pnpm install --frozen-lockfile` (no package added, lockfile unchanged).
- The per-plan commit ledger file could not be written into the shared git directory from the worktree sandbox, so `plan_head_before` is the HEAD recorded at start (`b3a35fb`, verified against the worktree base check) and `commits: 4` was measured with `git rev-list --count b3a35fb..HEAD`.

## Known Stubs

None. The RED-phase stubs in `chartData.ts` were replaced in the GREEN commits.

## Threat Flags

None. T-03-17 mitigated as planned: word labels render as React text nodes and a `title` attribute, never as HTML (no `dangerouslySetInnerHTML`). T-03-16 accepted (animation disabled, contour is server-downsampled). No new package installed (T-03-SC).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 03-08 can add `highlight` to `IntonationChart` (see Notes) and the `TipList` branch in `ResultPanel`.
- Pending human check (03-11 UAT): open a scored sentence, press `So sánh ngữ điệu` and compare with `docs/design/screens/S3-S4-phong-tap.png` (teal/orange lines actually coloured by the CSS variables, dashed baseline, word labels, `‖ ngắt thừa` when a pause issue exists, a 1-word and a ~25-word sentence for the E2 zero-one-many backstop).

## Self-Check: PASSED

- FOUND: apps/web/lib/chartData.ts, apps/web/lib/chartData.test.ts, apps/web/components/IntonationChart.tsx
- FOUND commits abb1eaf, 75b2b0f, 194270d, 8915462 on this branch (4 commits since b3a35fb)
- Acceptance: `connectNulls={false}`, `isAnimationActive={false}`, `var(--original)`, `var(--you)` in IntonationChart.tsx; `<IntonationChart` and `So sánh ngữ điệu` in ResultPanel.tsx; `chartOpen` in PracticeRoom.tsx; `--issue: var(--red-9)` and `--issue-text: var(--red-11)` in globals.css; `role="img"`, `ngắt thừa` and the no-data copy in IntonationChart.tsx; no hex literal in the chart files
- Verification: `vitest run lib/chartData.test.ts` 22/22, web suite 214/214, `pnpm --filter @shadowenglab/web build`, `pnpm exec eslint apps/web`, `tsc --noEmit`, prettier check all exit 0

---
*Phase: 03-p2-ch-m-ng-i-u*
*Completed: 2026-10-09*
