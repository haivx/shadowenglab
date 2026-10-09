---
phase: 03-p2-ch-m-ng-i-u
plan: 10
subsystem: ui
tags: [react, tanstack-query, vitest, attempt-history, shortcuts]

requires:
  - phase: 03-p2-ch-m-ng-i-u
    provides: "AttemptSummary contract (03-01), GET attempts list/detail endpoints (03-05), ResultPanel + MetricSkeleton (03-04), tip hover state inside ResultPanel (03-08), bestBySegment memo in PracticeRoom (03-09)"
provides:
  - "lib/attemptChips.ts: attemptChips (ordinal labels, best mark, cap 6, server + session merge)"
  - "lib/viewedAttempt.ts: nextViewedAttempt, resolveViewedResult, yoursAvailable (pure)"
  - "lib/player/shortcuts.ts: allowShortcutAction (video-ready + yours-enabled gates)"
  - "lib/api.ts listAttempts / getAttemptResult; lib/queries.ts useAttempts / useAttemptResult"
  - "AttemptStrip scored-attempt chips; past-attempt result with skeleton / error; M/B gated on the viewed attempt"
affects: [03-11-uat, 03-verify, ui-review]

actuals:
  tokens: 12000
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Viewed-attempt rules live in a pure reducer (nextViewedAttempt) fed by render-time events in PracticeRoom, so there is no stale frame after a sentence change or a new result"
    - "All shortcut gating (video ready, yours enabled) goes through one pure allowShortcutAction"

key-files:
  created:
    - apps/web/lib/attemptChips.ts
    - apps/web/lib/attemptChips.test.ts
    - apps/web/lib/viewedAttempt.ts
    - apps/web/lib/viewedAttempt.test.ts
  modified:
    - apps/web/lib/api.ts
    - apps/web/lib/api.test.ts
    - apps/web/lib/queries.ts
    - apps/web/lib/player/shortcuts.ts
    - apps/web/lib/player/shortcuts.test.ts
    - apps/web/lib/player/useShortcuts.ts
    - apps/web/components/AttemptStrip.tsx
    - apps/web/components/PracticeRoom.tsx
    - apps/web/components/ResultActionBar.tsx

key-decisions:
  - "Per-sentence session results are kept in PracticeRoom state (the machine holds only the latest blob/result per sentence); the machine's current scored result is merged into the list at render time so the new chip exists in the same frame"
  - "Cap rule: take the last 6 chips; if the best is not among them, show best + the last 5 (best first)"
  - "A failed past-result load keeps the plain sentence above the neutral Alert (spec only fixes the loading layout)"

patterns-established:
  - "Session results + server list merged by attempt number (session wins) so ordinals are recomputed over every scored attempt before the cap"

requirements-completed: [FBK-06, FBK-04]

coverage:
  - id: D1
    description: "AttemptStrip lists scored attempts as 44 px ghost chips 'Lượt k · score' (k = ordinal), viewed chip aria-current, best marked 'tốt nhất' only with >= 2 attempts (tie -> later), max 6 chips, session-only fallback while the list loads/fails"
    requirement: FBK-06
    verification:
      - kind: unit
        ref: "apps/web/lib/attemptChips.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "listAttempts / getAttemptResult Zod-parse server bodies; an invalid body rejects (feeds the E9 error)"
    requirement: FBK-06
    verification:
      - kind: unit
        ref: "apps/web/lib/api.test.ts#listAttempts"
        status: pass
      - kind: unit
        ref: "apps/web/lib/api.test.ts#getAttemptResult"
        status: pass
    human_judgment: false
  - id: D3
    description: "Viewed-attempt selection (sentence change -> latest attempt, list refresh keeps a pick, R result becomes viewed, chip click) and result source (session / stored / none with chip ordinal)"
    requirement: FBK-06
    verification:
      - kind: unit
        ref: "apps/web/lib/viewedAttempt.test.ts#nextViewedAttempt"
        status: pass
      - kind: unit
        ref: "apps/web/lib/viewedAttempt.test.ts#resolveViewedResult"
        status: pass
    human_judgment: false
  - id: D4
    description: "M/B never play another recording: yoursAvailable + allowShortcutAction gate buttons and shortcuts; O, R, arrows unaffected; P1 video gate preserved"
    requirement: FBK-04
    verification:
      - kind: unit
        ref: "apps/web/lib/viewedAttempt.test.ts#yoursAvailable"
        status: pass
      - kind: unit
        ref: "apps/web/lib/player/shortcuts.test.ts#allowShortcutAction"
        status: pass
    human_judgment: false
  - id: D5
    description: "Browser behaviour: past-attempt skeleton and error Alert with Thử lại, aria-disabled M/B tooltip text, chip row wrap and 'tốt nhất' staying on the better chip after a worse attempt, chips restored after reload"
    verification: []
    human_judgment: true
    rationale: "Rendering and interaction in the browser were not exercised in this plan; collected in the 03-11 UAT (plan human-check)"

duration: 11min
completed: 2026-10-09
status: complete
plan_head_before: 11a9b99cdf5d3be7d52f41b02815328862413c90
plan_head_after: c60ae140e00dba14915019574a953a42cdee2775
---

# Phase 3 Plan 10: Attempt chips, past-attempt result and M/B gating Summary

**AttemptStrip now lists the sentence's scored attempts as `Lượt k · score` chips with the best marked `tốt nhất`, a chip click opens that attempt's saved ScoreResult (skeleton and retryable error), `R` adds a new viewed attempt without losing the best, and M/B only play the recording of the attempt on screen.**

## Performance

- **Duration:** about 11 min
- **Completed:** 2026-10-09
- **Tasks:** 3 (1 tracer, 2 auto, all TDD)
- **Files modified:** 13 (4 new)

## Accomplishments

- `attemptChips` merges the server list with this session's results by attempt number, numbers chips by ordinal among scored attempts, marks the best (tie goes to the later attempt, only with 2 or more) and caps the row at 6 (older best first, then the 5 most recent).
- `listAttempts` / `getAttemptResult` parse with `AttemptSummary.array()` / `ScoreResult`; `useAttempts` / `useAttemptResult` (`staleTime: Infinity`, enabled only for a stored, non-session attempt). After scoring, the detail cache is primed and the list invalidated.
- `PracticeRoom` drives the viewed attempt with `useReducer(nextViewedAttempt)`, reads the result source from `resolveViewedResult`, shows `MetricSkeleton` inside `aria-busy` while a stored result loads, and a neutral Alert `Không tải được kết quả của lượt này.` with an outline `Thử lại` on any failure (including Zod). The 03-04 interim `voicedAttempts` label is replaced by the chip ordinal (result region label and live announcement).
- `allowShortcutAction` now owns both the video-ready gate (moved unchanged from `useShortcuts`) and the new yours-enabled gate; `ResultActionBar` takes `yoursAvailable` and shows `Bản ghi của lượt này không còn trong phiên.` on the `aria-disabled` M/B buttons. `Bản gốc (O)` is never affected.

## Task Commits

1. **Task 1 (tracer): chips from the attempt list**
   - RED `b9633bb` test(03-10): add failing tests for attempt chips and attempt list/detail client
   - GREEN `ffc29f8` feat(03-10): list scored attempts as chips in AttemptStrip
2. **Task 2: past-attempt view and new attempt becomes viewed**
   - RED `43a7cfe` test(03-10): add failing tests for viewed-attempt selection and result source
   - GREEN `98be680` feat(03-10): view a past attempt's saved result and make new attempts the viewed one
3. **Task 3: M/B gating**
   - RED `5aafe0d` test(03-10): add failing tests for M/B gating on the viewed attempt
   - GREEN `c60ae14` feat(03-10): gate M/B on the viewed attempt having an in-session recording

Tracer gate: `<verify>` is automated-only (vitest + build), re-run end-to-end after Task 1 and passed, so expansion continued.

## TDD Gate Compliance

Each task has a `test(03-10)` commit before its `feat(03-10)` commit. RED evidence: the stubbed implementations were run and the named tests failed on assertions for the planned behaviour (Task 1: 11 failing of 21, Task 2: 7 of 11, Task 3: 3 of 42, the others being cases the stub satisfies by returning the neutral value). No RED record was fed to `check tdd-red-evidence` (the plan is `type: execute`, not `type: tdd`); the semantic check was read from the vitest output. No REFACTOR commits.

## Files Created/Modified

- `apps/web/lib/attemptChips.ts` and test - chip model and merge/cap/best rules
- `apps/web/lib/viewedAttempt.ts` and test - viewed-attempt reducer, result source, M/B availability
- `apps/web/lib/api.ts`, `api.test.ts`, `queries.ts` - attempt list/detail client, keys, hooks
- `apps/web/lib/player/shortcuts.ts`, `shortcuts.test.ts`, `useShortcuts.ts` - `allowShortcutAction`, `yoursEnabled`
- `apps/web/components/AttemptStrip.tsx`, `PracticeRoom.tsx`, `ResultActionBar.tsx` - chips, viewed result, gating UI

## Decisions Made

- Session results are accumulated in `LoadedRoom` state because the machine only keeps the latest result and blob per sentence; the machine's current scored result is also merged at render time so a fresh chip never lags a frame behind the viewed attempt.
- Viewed-attempt events (`sentenceChanged`, `chipsLoaded`, `scored`) are dispatched during render (state-from-previous-render pattern) rather than in effects, avoiding a frame that shows a stale attempt or fires a wrong detail fetch. `selected` comes from the strip.
- On a failed past-result load the plain sentence stays visible above the Alert (UI-SPEC only specifies the loading layout).

## Deviations from Plan

None - plan executed exactly as written. Two judgment calls inside the plan's latitude: the cap rule when the best is already among the most recent chips (show the last 6), and keeping the sentence text above the E9 error Alert.

**Total deviations:** 0 auto-fixed. **Impact:** none.

## Issues Encountered

None. The RED-phase stubs briefly violated eslint (`no-unused-vars` on underscore params) in the test commits; the GREEN commits are clean (eslint, tsc, prettier, build and the full web suite of 275 tests pass).

## Known Stubs

None.

## Threat Flags

None. T-03-20 is mitigated (both new bodies go through Zod before render, failure shows the E9 error) and T-03-21 is mitigated (6-chip cap, detail fetched only on chip click, `staleTime: Infinity`).

## User Setup Required

None.

## Next Phase Readiness

Ready for 03-11 (UAT). Browser checks to collect there: score a sentence twice (second worse) and click `Lượt 1`; confirm `tốt nhất` stays on the better chip; M/B disabled with the tooltip when the blob is from another attempt; reload and open a scored sentence to see chips restored from the server.

## Self-Check: PASSED

All created/modified files exist; commits b9633bb, ffc29f8, 43a7cfe, 98be680, 5aafe0d, c60ae14 are on the branch; `commits: 6` matches `git rev-list --count 11a9b99..HEAD` before this SUMMARY commit.
