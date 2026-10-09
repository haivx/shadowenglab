---
phase: 03-p2-ch-m-ng-i-u
plan: 09
subsystem: ui
tags: [react, tailwind, tanstack-query, vitest, scoreLevel]

requires:
  - phase: 03-p2-ch-m-ng-i-u
    provides: "LessonProgress.bestOverall/bestAttempt (03-01 contract, 03-05 endpoint), scoreLevel helpers (03-04)"
provides:
  - "lib/progressView.ts: bestBySegment, transcriptScoreCell, segmentFillClass"
  - "TranscriptList right cell shows the best score per sentence, coloured by scoreLevel"
  - "SegmentedProgress segments coloured by the best attempt's scoreLevel"
affects: [03-verify, ui-review]

actuals:
  tokens: 5200
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Pure view-model helpers in lib/progressView.ts feed components; colours only via scoreLevel() + literal class maps"

key-files:
  created:
    - apps/web/lib/progressView.ts
    - apps/web/lib/progressView.test.ts
  modified:
    - apps/web/components/TranscriptList.tsx
    - apps/web/components/PracticeHeader.tsx
    - apps/web/components/PracticeRoom.tsx

key-decisions:
  - "progressView.ts imports ./scoreLevel relatively because vitest has no @ alias configured (components keep using @/ imports)"

patterns-established:
  - "bestBySegment(progress) memo in PracticeRoom is the single source for list and header colouring"

requirements-completed: [FBK-05, FBK-06]

coverage:
  - id: D1
    description: "TranscriptList shows Math.round(bestOverall*100) per sentence, coloured by scoreLevel, with aria-label 'Điểm tốt nhất {n}'; P1-only sentences keep the grey dot; untouched sentences empty"
    requirement: FBK-06
    verification:
      - kind: unit
        ref: "apps/web/lib/progressView.test.ts#transcriptScoreCell"
        status: pass
      - kind: unit
        ref: "apps/web/lib/progressView.test.ts#bestBySegment"
        status: pass
    human_judgment: false
  - id: D2
    description: "SegmentedProgress segment fills: current --foreground, scored --score-{level}, practiced-unscored --muted-foreground, untouched --slate-4"
    requirement: FBK-05
    verification:
      - kind: unit
        ref: "apps/web/lib/progressView.test.ts#segmentFillClass"
        status: pass
    human_judgment: false
  - id: D3
    description: "Visual result in the browser (recolour after a new result without remount, 100 fitting the 28 px cell, P3-G16 contrast of 12 px amber/green text)"
    verification: []
    human_judgment: true
    rationale: "Rendering and contrast are visual; no browser test was run in this plan"

duration: 6min
completed: 2026-10-09
status: complete
plan_head_before: 9fdf2210e79179d781003cebdaf3e892cedab364
plan_head_after: e75718d
---

# Phase 3 Plan 09: Best-score colouring in sentence list and progress bar Summary

**Sentence list and segmented progress bar now show/colour each sentence's best attempt (`bestOverall`) through `scoreLevel()` and literal class maps, with the P1 grey dot kept for unscored practice.**

## Performance

- **Duration:** ~6 min
- **Tasks:** 2 (both TDD: RED test commit, then GREEN implementation commit)
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- `lib/progressView.ts`: `bestBySegment` (Map of segmentIndex to bestOverall, only for scored sentences), `transcriptScoreCell` (score / dot / empty), `segmentFillClass` (current > scoreLevel(best) > muted > slate-4).
- `TranscriptList` takes a `best` map; right 28 px cell renders `<span aria-label="Điểm tốt nhất {n}">` at mono 12 / 600 / tabular-nums with `SCORE_TEXT_CLASS`; dot and empty fallbacks preserved. Current row keeps its border and background.
- `SegmentedProgress` / `PracticeHeader` take `best` and use `segmentFillClass`; aria-label unchanged.
- `PracticeRoom` derives `best` via `useMemo(bestBySegment(progress))`; the existing scoring to reviewing|noVoice invalidation of the progress query recolours rows and segments without remounting. While the progress query is pending the room shows the skeleton (existing behaviour), and a failed refetch keeps TanStack data, so cells never flicker.
- Because the server returns the best (highest overall, later wins ties; D-11), a worse later attempt never lowers the shown number or colour.

## TDD Gate Compliance

- Task 1 RED `baebea5` (6 of 8 tests failing on behaviour assertions against a stub returning empty values; the 2 passing are the trivially-empty cases), GREEN `813d699`.
- Task 2 RED `e33ff14` (4 segmentFillClass assertions failing against a stub returning ""), GREEN `e75718d`.
- RED evidence was inspected manually from vitest output (target tests executed and failed on the planned assertions); `gsd_run check tdd-red-evidence` was not run. The RED commits include a signature-only stub of `progressView.ts` so the target tests fail on assertions rather than on import errors.
- No REFACTOR commit needed.

## Task Commits

1. Task 1 tracer RED: `baebea5` (test)
2. Task 1 tracer GREEN: `813d699` (feat)
3. Task 2 RED: `e33ff14` (test)
4. Task 2 GREEN: `e75718d` (feat)

**Plan metadata:** committed separately as `docs(03-09)` (SUMMARY only; STATE.md/ROADMAP.md left to the orchestrator).

## Verification

- `pnpm exec vitest run lib/progressView.test.ts` (apps/web): 12/12 pass.
- `pnpm build` (apps/web): compiled, type check and static generation OK.
- `pnpm exec eslint apps/web`: exit 0.
- Hex-colour grep over TranscriptList.tsx, PracticeHeader.tsx, progressView.ts: no matches.
- Tracer gate: Task 1 verify (vitest + build) re-passed before expansion to Task 2.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Relative import for scoreLevel inside progressView.ts**
- **Found during:** Task 1 GREEN
- **Issue:** vitest (no `@` alias configured) could not resolve `@/lib/scoreLevel` from a lib file.
- **Fix:** `import ... from "./scoreLevel"`, matching how other tested lib files import siblings.
- **Files modified:** apps/web/lib/progressView.ts
- **Committed in:** `813d699`

---

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** none on behaviour.

## Issues Encountered

- `pnpm install --frozen-lockfile` was needed in the fresh worktree; no package or lockfile changes.

## Known Stubs

None. (The RED-phase stubs were replaced in the GREEN commits.)

## Flagged for Liam

- The 12 px amber/green best-score text has contrast of 4.38 to 4.49:1 (P3-G16); this plan uses the `SCORE_TEXT_CLASS` tokens as specified and relies on Liam's acknowledgement in 03-01 item J.
- Visual check in a browser (recolour after a new result, `100` in the 28 px cell) was not performed here.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for wave verification; 03-08 owns the result panel pieces and does not overlap with these files.

---
*Phase: 03-p2-ch-m-ng-i-u*
*Completed: 2026-10-09*

## Self-Check: PASSED

- Files exist: progressView.ts, progressView.test.ts, TranscriptList.tsx, PracticeHeader.tsx, PracticeRoom.tsx
- Commits baebea5, 813d699, e33ff14, e75718d are ancestors of HEAD
- Acceptance criteria: TranscriptList contains `Điểm tốt nhất` and `transcriptScoreCell`; PracticeHeader uses `segmentFillClass`; vitest, build and eslint exit 0
