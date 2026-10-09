---
phase: 03-p2-ch-m-ng-i-u
plan: 04
subsystem: ui
tags: [xstate, zod, react, tailwind, scoring, vitest]

requires:
  - phase: 03-p2-ch-m-ng-i-u
    plan: 01
    provides: "ApiErrorCode no_speech (422), POST attempts -> ScoreResult, decision table A-K (scoreLevel in apps/web/lib, P3 UI gaps accepted)"
  - phase: 03-p2-ch-m-ng-i-u
    plan: 02
    provides: "Collapsible primitive and recharts (not used by this plan; the chart attaches in 03-07)"
provides:
  - "playerMachine scoring actor returns a Zod-validated ScoreResult; scoring -> reviewing keeps recordings[i].result; no_speech -> noVoice; other errors -> error + RETRY_UPLOAD"
  - "lib/scoreLevel.ts: scoreLevel, scorePercent, SCORE_TEXT_CLASS, SCORE_FILL_CLASS"
  - "lib/resultView.ts: resultNote (D-15), wordsMatchSegment (E4)"
  - "ScoreHero and ResultPanel (S3 reviewing result region), ReviewBlock removed"
  - "SentenceStatePanel variant scoring with exported MetricSkeleton and 5 s slow caption"
affects: [03-07, 03-08, 03-09, 03-10, 03-11]

actuals:
  tokens: 11300
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Pure view-decision helpers (resultNote, wordsMatchSegment) tested in node and called from components, no inline conditions"
    - "Score colour only through scoreLevel() + literal class lookup, on the displayed rounded integer"
    - "Machine error classification by duck typing (isNoSpeechError) so playerMachine.ts imports no api client"

key-files:
  created:
    - apps/web/lib/scoreLevel.ts
    - apps/web/lib/scoreLevel.test.ts
    - apps/web/lib/resultView.ts
    - apps/web/lib/resultView.test.ts
    - apps/web/components/ScoreHero.tsx
    - apps/web/components/ResultPanel.tsx
  modified:
    - apps/web/lib/api.ts
    - apps/web/lib/api.test.ts
    - apps/web/lib/player/playerMachine.ts
    - apps/web/lib/player/playerMachine.test.ts
    - apps/web/components/PracticeRoom.tsx
    - apps/web/components/SentenceStatePanel.tsx
  deleted:
    - apps/web/components/ReviewBlock.tsx

key-decisions:
  - "ScoreHero renders exactly three indices and never a fourth 'âm' column, with or without scores.sound (D-07: Phase 5 adds it); no placeholder"
  - "ResultPanel owns the sentence in reviewing (words row or plain fallback) and the IPA block; PracticeRoom renders the standalone sentence and SpokenIpa only outside a scored reviewing"
  - "The tip block renders only when resultNote is non-null; when tips exist nothing is drawn there until 03-08 adds TipList"

patterns-established:
  - "Result region = one labelled section 'Kết quả lượt k' with internal gap 32 matching the right column"
  - "Interim attempt label voicedAttempts >= 1 ? voicedAttempts : 1 until 03-10 switches to the ordinal among scored attempts"

requirements-completed: [FBK-01, FBK-04, FBK-05]

coverage:
  - id: D1
    description: "Recording -> scoring request -> reviewing: the machine holds the Zod-validated ScoreResult in context.recordings[i].result"
    requirement: FBK-05
    verification:
      - kind: unit
        ref: "apps/web/lib/player/playerMachine.test.ts#idle -> playing -> recording -> scoring -> reviewing, lưu bản ghi và kết quả chấm"
        status: pass
      - kind: unit
        ref: "apps/web/lib/api.test.ts#uploadAttempt parses the 201 body as a ScoreResult and posts multipart audio"
        status: pass
    human_judgment: false
  - id: D2
    description: "no_speech lands on the noVoice panel; any other failure lands on error with RETRY_UPLOAD keeping the blob"
    requirement: FBK-05
    verification:
      - kind: unit
        ref: "apps/web/lib/player/playerMachine.test.ts#uploadAttempt reject với error.code no_speech -> noVoice"
        status: pass
      - kind: unit
        ref: "apps/web/lib/api.test.ts#rejects with ApiRequestError carrying code no_speech on a 422"
        status: pass
    human_judgment: false
  - id: D3
    description: "scoreLevel rounds to the displayed integer first (0.795 good, 0.794 ok, 0.595 ok, 0.594 bad)"
    requirement: FBK-01
    verification:
      - kind: unit
        ref: "apps/web/lib/scoreLevel.test.ts#scoreLevel"
        status: pass
    human_judgment: false
  - id: D4
    description: "Praise only at a displayed overall >= 80, neutral line otherwise, nothing when tips exist (D-15); sentence falls back to plain text when words do not match (E4)"
    requirement: FBK-01
    verification:
      - kind: unit
        ref: "apps/web/lib/resultView.test.ts#resultNote (D-15)"
        status: pass
      - kind: unit
        ref: "apps/web/lib/resultView.test.ts#wordsMatchSegment (E4)"
        status: pass
    human_judgment: false
  - id: D5
    description: "ScoreHero visual match to S3-S4-phong-tap.png (72/800 overall, 24/700 indices, colours per scoreLevel, flex-wrap), scoring skeleton with 5 s slow caption, and the three E1/E8 states"
    requirement: FBK-01
    verification:
      - kind: other
        ref: "pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web (compile and lint only)"
        status: pass
    human_judgment: true
    rationale: "Pixel layout, colour and timing of the skeleton caption are visual; collected at end of phase in the 03-11 UAT"
  - id: D6
    description: "FBK-04: Bản gốc (O), Của bạn (M), Lần lượt cả hai (B) still play from reviewing"
    requirement: FBK-04
    verification:
      - kind: unit
        ref: "apps/web/lib/player/playerMachine.test.ts#reviewing: LISTEN_ORIGINAL -> original -> idle khi xong; LISTEN_YOURS -> yours; LISTEN_BOTH -> both"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-09
status: complete
plan_head_before: 0b260a770957bf00026117e41786a8badbdb4ad9
plan_head_after: 1afd9a62b369af8cfac0d9b25ee258e0531c794e
commits: 4
---

# Phase 3 Plan 04: Web tracer, scoring result in reviewing Summary

**After a recording, the upload actor now resolves a Zod-validated `ScoreResult`; the machine goes scoring -> reviewing and the result region shows the sentence by words, IPA, a `ScoreHero` (overall + tốc độ / lên xuống / giai điệu coloured through `scoreLevel()`), the D-15 praise or neutral line and `Lưu clip cho eval`; `no_speech` lands on the noVoice panel and other failures on the error panel with `Thử lại`.**

## Performance

- **Duration:** about 12 min
- **Started:** 2026-10-09T14:05Z (approx.)
- **Completed:** 2026-10-09T14:15Z (approx.)
- **Tasks:** 2 (Task 1 tracer, Task 2 auto, both TDD)
- **Files modified:** 13 in `apps/web` (6 created, 6 modified, 1 deleted)

`commits: 4` is measured from `plan_head_before` and counts RED + GREEN for each task; the SUMMARY docs commit follows `plan_head_after`.

## Accomplishments

- Machine shape unchanged (PLY-02); only the scoring actor output changed from `AttemptAck` to `ScoreResult`. `isNoSpeechError(error)` duck-types `error.error.code === "no_speech"` so `playerMachine.ts` stays free of React, DOM and network imports. `RecordingStatus` is now `pending | scored | noVoice | failed`, guard `hasUploaded` renamed `hasScored`, `PlayerRecording.result?: ScoreResult`.
- `lib/scoreLevel.ts` (decision I): colour follows the displayed integer; `SCORE_TEXT_CLASS` / `SCORE_FILL_CLASS` are literal class lookups, the Tailwind score utilities already existed in `tailwind.config.ts` so no config change was needed.
- New props: `ScoreHero { scores, prosody (speed/pitchRange/melodyMatch), attemptLabel }`; `ResultPanel { lessonId, segmentIndex, segment, result, attemptLabel, ipaOn, blob: Blob | null, saved, onSaved }`.
- `SentenceStatePanel` variant `processing` renamed `scoring`: three 72 px `MetricSkeleton` blocks (exported, reused by 03-10), caption `Đang so với bản gốc… Bạn có thể nghe lại bản ghi của mình` + `M` kbd, 5 s timer switches to `Đang so với bản gốc… Lần đầu của câu này có thể lâu hơn một chút.`, `aria-busy="true"` kept.
- `lib/resultView.ts` helpers for 03-08: `resultNote(overall, tipCount)` returns `null` whenever `tipCount > 0`, so the TipList branch added by 03-08 never coexists with the praise/neutral line; `wordsMatchSegment(words, text)` drives the E4 plain-paragraph fallback.
- `ReviewBlock.tsx` deleted; the P1 title, duration and "Chưa chấm điểm ở bản này" copy are gone with it.

## Task Commits

1. **Task 1: Tracer web (ghi xong -> chấm -> reviewing có ScoreHero)** (TDD)
   - RED: `c800917` (test) - scoreLevel tests + machine tests for ScoreResult / no_speech
   - GREEN: `d7eb189` (feat) - machine, api, scoreLevel, ScoreHero, ResultPanel, PracticeRoom, ReviewBlock removed
2. **Task 2: Trạng thái đang chấm thật, câu theo words, dòng khen/trung tính** (TDD)
   - RED: `61407e4` (test) - resultView tests with a behaviour-less stub so failures are assertions
   - GREEN: `1afd9a6` (feat) - resultView, scoring panel, full ResultPanel, api tests

**Plan metadata:** docs commit for this SUMMARY follows (hash not embedded to avoid self-reference).

Tracer gate: `human_verify_mode` is `end-of-phase` and the tracer `<verify>` is automated-only, so the verify (vitest, machine purity grep, web build) was re-run after the commit and passed; "Tracer verified end-to-end - expanding" then Task 2.

## TDD Gate Compliance

- **RED 1** (`c800917`): `scoreLevel.test.ts` failed at import (module absent) and the machine tests failed or timed out on the target assertions (the old `voiced` guard never matched a `ScoreResult`, so the machine went to `noVoice` instead of `reviewing`; `isNoSpeechError` was undefined). Semantic assessment: the failures are the missing feature, not a fixture or syntax fault in the test files (the other 12 machine tests ran). `gsd_run check tdd-red-evidence` was not run (default vitest reporter, same as 03-01).
- **GREEN 1** (`d7eb189`): scoreLevel + machine vitest 27/27.
- **RED 2** (`61407e4`): with an empty-behaviour stub, 6 of 9 `resultView` tests failed on assertions (`expected null to deeply equal {...}`, `expected false to be true`); the 3 that passed (tips present -> null, empty words -> false, mismatched words -> false) agree with the stub by coincidence.
- **GREEN 2** (`1afd9a6`): resultView, api, scoreLevel, playerMachine 44/44; full web suite 192/192.
- **REFACTOR:** none.

## Files Created/Modified

- `apps/web/lib/scoreLevel.ts` (+ test) - level / percent / literal class lookups
- `apps/web/lib/resultView.ts` (+ test) - D-15 note and E4 words check
- `apps/web/components/ScoreHero.tsx` - overall 72/800 + three 24/700 indices, `flex-wrap`, `role="group"` with full-name `aria-label` and `title`
- `apps/web/components/ResultPanel.tsx` - sentence by words (or plain), IPA, ScoreHero, praise/neutral line, save clip, visually hidden `role="status"` announcement
- `apps/web/components/SentenceStatePanel.tsx` - `scoring` variant, `MetricSkeleton`
- `apps/web/components/PracticeRoom.tsx` - actor typed `ScoreResult`, `variant="scoring"`, `ResultPanel` render, `isLast` removed
- `apps/web/lib/api.ts` (+ test) - `uploadAttempt(): Promise<ScoreResult>`; `AttemptAck` import kept for `saveEvalClip`
- `apps/web/lib/player/playerMachine.ts` (+ test) - see Accomplishments
- `apps/web/components/ReviewBlock.tsx` - deleted (authorized)

## Decisions Made

- No fourth "âm" column even when `scores.sound` is non-null: the plan only specifies the null case, UI-SPEC says exactly three indices in P2 and D-06/D-07 forbid Lớp A UI, so Phase 5 adds the column.
- The empty tip block (tips exist, before 03-08) renders nothing instead of an empty bordered row.
- The live announcement is a static `role="status"` span per mounted result (the `key` remounts per attempt).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Skeleton radius class**
- **Found during:** Task 2 (`MetricSkeleton`)
- **Issue:** The plan text says `rounded-xl`, but in `tailwind.config.ts` `xl` maps to `--radius-xl` = 16 px, while the UI-SPEC and S3s call for radius 12
- **Fix:** Used `rounded-lg` (`--radius-lg` = 12 px), the class the existing 12 px panels already use
- **Files modified:** `apps/web/components/SentenceStatePanel.tsx`
- **Verification:** build + eslint pass; spec value 12 px matches
- **Committed in:** `1afd9a6`

**2. [Rule 1 - Lint] Non-null assertion in the test fixture loader**
- **Found during:** Task 1 (eslint after GREEN)
- **Issue:** `[0]!.data` violates `no-non-null-assertion`
- **Fix:** The fixture is parsed with the contract `ScoreResult` Zod schema, which also fails the test if the fixture drifts
- **Files modified:** `apps/web/lib/player/playerMachine.test.ts`
- **Committed in:** `d7eb189`

---

**Total deviations:** 2 auto-fixed (2 Rule 1)
**Impact on plan:** Both are corrections of plan wording or test hygiene; no scope change.

## Issues Encountered

- The worktree had no `node_modules`; ran `pnpm install --frozen-lockfile` from the existing lockfile (no package added, lockfile unchanged).
- A first scripted edit of `PracticeRoom.tsx` matched the wrong `</main>` (the skeleton's) and duplicated the file; it was reverted with `git checkout -- apps/web/components/PracticeRoom.tsx` (a single file, not a blanket reset) before anything was committed, then redone with a scoped search.

## Known Stubs

None. The tip block shows nothing when `tips.length > 0` until 03-08 adds `TipList`; this is by plan (D-15 note is `null` then) and not a data stub.

## Threat Flags

None. The only new surface is the Zod-parsed `ScoreResult` response, already covered by T-03-07 (mitigated: `request(..., ScoreResult)` parses every 2xx body, a parse failure rejects and the machine goes to `error`, covered by `api.test.ts#rejects when a 201 body fails ScoreResult validation`). T-03-08 accepted as planned.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 03-07 (chart), 03-08 (TipList: add the `note === null` branch in `ResultPanel`), 03-09 (list colours via `scoreLevel`), 03-10 (attempt chips, ordinal label, reuse `MetricSkeleton`) can attach to `ResultPanel`.
- Human check collected at end of phase (03-11 UAT): in `make dev` record one sentence and compare with `docs/design/screens/S3-S4-phong-tap.png`; a silent take shows "Không nghe thấy gì trong lượt vừa rồi".
- Depends on 03-03 (backend scoring) being merged for a real end-to-end run; this plan is verified against the contract fixture and a mocked fetch.

## Self-Check: PASSED

- FOUND: apps/web/lib/scoreLevel.ts, scoreLevel.test.ts, resultView.ts, resultView.test.ts, components/ScoreHero.tsx, components/ResultPanel.tsx
- MISSING (expected, deleted): apps/web/components/ReviewBlock.tsx; no import of it remains
- FOUND commits c800917, d7eb189, 61407e4, 1afd9a6 on this branch
- Verification: web vitest 192/192, `pnpm --filter @shadowenglab/web build`, `pnpm exec eslint apps/web`, `tsc --noEmit`, prettier check, machine purity grep and design guard (no `shadow-*`, no `hsl(var(`) all exit 0

---
*Phase: 03-p2-ch-m-ng-i-u*
*Completed: 2026-10-09*
