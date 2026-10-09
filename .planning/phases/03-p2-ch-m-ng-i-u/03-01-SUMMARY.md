---
phase: 03-p2-ch-m-ng-i-u
plan: 01
subsystem: contracts
tags: [zod, json-schema, pydantic, contract-gate, decision-record]

requires:
  - phase: 01-p0-foundation
    provides: "Zod -> JSON Schema -> pydantic pipeline, drift gate, ScoreResult lock (D-10..D-15)"
  - phase: 02-p1-lesson-creation
    provides: "ApiError envelope, SegmentProgress, AttemptAck, attempts table (user_version 1)"
provides:
  - "ApiErrorCode no_speech (HTTP 422, D-09)"
  - "SegmentProgress.bestOverall? / bestAttempt? (optional, never null)"
  - "AttemptSummary {attempt, overall, createdAt} with fixture and generated pydantic class"
  - "Quyet dinh da chot A1..K for the whole of Phase 3 (table below, approved by Liam 2026-10-09)"
affects: [03-02, 03-03, 03-04, 03-05, 03-06, 03-07, 03-08, 03-09, 03-10, 03-11]

actuals:
  tokens: 4000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Optional (absent, never null) for new additive contract fields so P1 rows and the current server stay valid"
    - "Contract changes only through Zod -> scripts/contracts_gen.sh; generated files committed, never hand-edited"

key-files:
  created:
    - packages/contracts/fixtures/AttemptSummary.json
  modified:
    - packages/contracts/src/api.ts
    - packages/contracts/src/attempt.ts
    - packages/contracts/src/index.ts
    - packages/contracts/src/contracts.test.ts
    - packages/contracts/fixtures/ApiError.json
    - packages/contracts/fixtures/LessonProgress.json
    - packages/contracts/schema/contracts.schema.json
    - services/audio/src/audio_service/contracts_gen.py

key-decisions:
  - "Liam approved A-K exactly as proposed, no overrides (2026-10-09): C1 and D-a chosen"
  - "no_speech travels only as ApiError code (HTTP 422); ScoreResult shape is untouched"
  - "AttemptSummary lists scored attempts only, ascending attempt; SegmentProgress.best* present together iff >= 1 scored attempt"

patterns-established:
  - "Decision table in 03-01-SUMMARY.md is the single source for Phase 3 thresholds, schema v2 and UI-gap acknowledgements"

requirements-completed: [FBK-05, FBK-06, RUL-01, PRO-03]

duration: 5min
completed: 2026-10-09
status: complete
plan_head_before: 4fd9f7c2eab147758549eb7fe6ee08a6822ab0c5
plan_head_after: ba0d02e7bebba511426f4fae64f73d46a881f758
commits: 2
---

# Phase 3 Plan 01: Contract and decision gate Summary

**Liam's one-stop approval of items A-K (no overrides) recorded below, plus the approved contract additions implemented in Zod, JSON Schema and pydantic: `no_speech` error code, optional `SegmentProgress.bestOverall/bestAttempt`, and `AttemptSummary`, with `ScoreResult` byte-identical and the drift gate green.**

## Performance

- **Duration:** about 5 min of resumed execution (continuation after the decision checkpoint)
- **Started:** 2026-10-09T03:27:34Z
- **Completed:** 2026-10-09T03:31:54Z (production commits); SUMMARY committed after
- **Tasks:** 2 (Task 1 decision checkpoint answered by Liam; Task 2 TDD)
- **Files modified:** 9 in code commits (8 modified, 1 created)

`commits: 2` counts the production commits (RED + GREEN) measured from `plan_head_before`; the SUMMARY docs commit follows `plan_head_after`.

## Accomplishments

- Decision gate closed: Liam answered `approved` for A-K on 2026-10-09 with C -> C1 and D -> D-a; every later Phase 3 plan reads the table below.
- `ApiErrorCode` gained `no_speech` (after `recording_too_long`), now 21 codes; the generated pydantic `ApiError.code` literal contains it, so `ApiErrorException("no_speech")` works in `errors.py`.
- `SegmentProgress` gained `bestOverall: Score01.optional()` and `bestAttempt: int >= 1 optional`; `null` is rejected on the Zod side, absent (P1 shape) still parses.
- `AttemptSummary` exists with meta id, fixture (`first`, `best-later`), `$defs` entry and generated pydantic `class AttemptSummary(BaseModel)`.
- `score.ts` is not modified; the schema diff is purely additive (AttemptSummary def, two SegmentProgress properties, one enum value).

## Task Commits

1. **Task 1: Liam approves contract, SQLite v2, thresholds, "wrong sentence" criterion, UI gaps** - no commit (decision only; answer recorded in the table below)
2. **Task 2: Implement approved contract (TDD)**
   - RED: `e6a1559` (test) - failing cases written first
   - GREEN: `ba0d02e` (feat) - implementation, fixtures, regenerated schema + pydantic
   - REFACTOR: none needed

**Plan metadata:** docs commit for this SUMMARY follows (hash not embedded to avoid self-reference).

## TDD Gate Compliance

- **RED** (`e6a1559`): `pnpm --filter @shadowenglab/contracts test` -> 9 failed / 56 passed. Target assertions that failed: `ApiError accepts no_speech` and `ApiErrorCode has exactly the 21 approved codes` (expected false to be true), `SegmentProgress.bestOverall ... never null` and `bestAttempt ... starts at 1` (expected true to be false, because the unknown keys were stripped), `covers all sixteen fixture files` (fixture absent), `has stable $defs ... AttemptSummary` (def absent). Three `AttemptSummary` cases failed with `TypeError: Cannot read properties of undefined` because the export did not exist yet; this is the feature being absent, not a syntax, load or fixture fault of the test file (the file parsed and 56 other tests ran). Semantic assessment: all failures are for the planned reasons. The `gsd_run check tdd-red-evidence` classifier was not run (vitest default reporter output was not captured as TAP); the failure list above is the observed evidence.
- **GREEN** (`ba0d02e`): contracts vitest 69/69 pass; `test_contracts_roundtrip.py` + `test_contracts_drift.py` 65 passed; full `services/audio/tests` 850 passed.
- **REFACTOR:** none.

## Files Created/Modified

- `packages/contracts/src/api.ts` - `no_speech` in `ApiErrorCode`; `SegmentProgress.bestOverall?` / `bestAttempt?`; imports `Score01`
- `packages/contracts/src/attempt.ts` - `AttemptSummary` + type; `AttemptAck` JSDoc narrowed to PUT eval-clip
- `packages/contracts/src/index.ts` - `AttemptSummary` added to `Schemas` after `AttemptAck`
- `packages/contracts/src/contracts.test.ts` - sixteen-fixture list, 21 codes, `phase 3 contract edges` block, `$defs` list
- `packages/contracts/fixtures/{ApiError,LessonProgress,AttemptSummary}.json` - new cases / new file
- `packages/contracts/schema/contracts.schema.json`, `services/audio/src/audio_service/contracts_gen.py` - generated (never hand-edited)

Generated pydantic names added/changed: `AttemptSummary` (fields `attempt`, `overall`, `created_at`), `SegmentProgress.best_overall`, `SegmentProgress.best_attempt`, `ApiError.code` literal with `"no_speech"`.

## Quyet dinh da chot (Liam, 2026-10-09: approved, no overrides)

Source column: "recommended" = accepted exactly as proposed in the plan. Field names are camelCase on the wire; `?` = optional (absent, never null). Later Phase 3 plans MUST follow these values; any change goes back to Liam.

| Item | Final value | Source |
|------|-------------|--------|
| A1 | `ApiErrorCode` gains `"no_speech"`, inserted after `"recording_too_long"`. HTTP 422, message "Không nghe thấy tiếng nói trong lượt vừa rồi." The web machine branches to "không thu được tiếng" on this code (RESEARCH Open Question 5). | recommended |
| A2 | `POST /lessons/{id}/segments/{index}/attempts` -> 201 `ScoreResult` (shape unchanged). `AttemptAck` stays only for `PUT .../attempts/{n}/eval-clip`. | recommended |
| A3 | `SegmentProgress` gains `bestOverall?: Score01` and `bestAttempt?: int >= 1`, present together iff the sentence has >= 1 scored attempt; best = highest `overall`, tie -> later attempt (D-11). Optional, so P1 rows and the current server stay valid. | recommended |
| A4 | New `AttemptSummary { attempt: int >= 1, overall: Score01, createdAt: string (ISO-8601 UTC "...Z") }`; `GET /lessons/{id}/segments/{index}/attempts` -> `AttemptSummary[]`, scored attempts only, ascending `attempt` (RESEARCH Open Question 3b). | recommended |
| A5 | `GET /lessons/{id}/segments/{index}/attempts/{attempt}` -> `ScoreResult` read from `result_json` and re-validated by pydantic; 404 `not_found` when the attempt does not exist or has no score; stored JSON that fails validation -> 500 `internal_error` with a fixed message (RESEARCH Open Question 3c). | recommended |
| A6 | Reference audio unavailable (no prosody cache and no vocals stem on disk) -> 409 `invalid_state` "Thiếu audio bản gốc của câu này. Hãy tạo lại bài." (no new code). | recommended |
| B | SQLite migration `user_version` 1 -> 2 (D-10). Table `attempts` gains `overall REAL CHECK (overall IS NULL OR (overall >= 0 AND overall <= 1))`, the same CHECK for `intonation`, `rhythm`, `sound`, and `result_json TEXT` (full `ScoreResult`, camelCase, unset fields excluded). P1 rows keep NULL. Migration runs inside the existing `BEGIN IMMEDIATE` + re-check pattern of `ensure_schema`: user_version 0 -> v1 DDL then the v2 ALTERs; user_version 1 -> the v2 ALTERs; then `PRAGMA user_version = 2`. | recommended |
| C | **C1.** A scored row is inserted only after scoring succeeds, in one `BEGIN IMMEDIATE` that allocates `attempt = MAX + 1`, builds the `ScoreResult` with that number and inserts it with the four scores and `result_json`. A `no_speech` upload still inserts a `voiced = 0` row with NULL scores (P1 behaviour, consumes an attempt number, not "đã tập"). A scoring exception inserts nothing -> 500 `internal_error`; the browser keeps the blob for `Thử lại` (REC-03). The UI label "Lượt k" = ordinal among scored attempts (UI-SPEC P3-G15). (C2 rejected.) | recommended (C1) |
| D | **D-a.** Keep D-04 verbatim. Verification criterion: a synthetic different-sentence pair has `alignment.ok` False and `overall <= 0.6`; real-data smoke (03-11): every cross-sentence pair has alignment not ok and the median cross-sentence `overall < 0.6`. (D-b and D-c rejected.) Measured basis: 20 real wrong-sentence pairs gave overall 0.40-0.78 (median 0.58), all with alignment not ok. | recommended (D-a) |
| E | Thresholds file `services/audio/src/audio_service/scoring/thresholds.py`; `THRESHOLDS_VERSION = "p2-1"`, `SCORER_VERSION = "prosody-1"`; both go into `ScoreResult.versions`. Values: see the threshold table below. Phase 4 recalibrates. | recommended |
| F | Prosody cache as a sidecar `seg/NNNN.prosody.npz` instead of rewriting `seg/NNNN.npz` (RESEARCH Pitfall 5, Open Question 2; deviates from the letter of D-03, recorded in ADR 0006). Written atomically (`.part` + `os.replace`), loaded with `allow_pickle=False`, valid only when its `feat_version` and `window` match the current segment window. New lessons write it during `analyzing` (and again on "Mất chữ cuối?" because `analyze_segment` is reused); old lessons compute it lazily on the first scoring from the vocals stem slice (no model), and that time is reported in `timingMs.ref_backfill`. | recommended |
| G | `WordScore.similarity` at P2 (D-06, RESEARCH A9): `1 - min(1, RMS(st_user - st_ref - sentence offset) / 6)` over the word's common voiced frames; fewer than 5 common frames -> the sentence `melodyMatch`. `status` always `"scored"`; `start`/`end` are seconds on the uploaded recording, mapped through the alignment path. | recommended |
| H | Alignment quality (`cost`, `ratio`, `ok`) is not stored in `ScoreResult` (no shape change, RESEARCH Open Question 6); it is logged at INFO with lessonId, index and attempt. `timingMs` keys: `normalize`, `ref_features`, `user_features`, `align`, `metrics`, `rules`, `total`, plus `ref_backfill` only when D-03 lazy compute ran. | recommended |
| I | `scoreLevel()` lives in `apps/web/lib/scoreLevel.ts` (RESEARCH Open Question 7); it rounds to the displayed integer before comparing (79.6 -> "80" -> good). | recommended |
| J | UI-SPEC gaps marked "Needs Liam = yes" are acknowledged and accepted: **P3-G2** (default-closed `So sánh ngữ điệu` button), **P3-G3** (paired stress bars), **P3-G4** (double-line marker + `--issue`/`--issue-text` alias tokens), **P3-G5** (STRESS_MISMATCH words teal/orange, other codes neutral), **P3-G7** (praise copy "Rất sát bản gốc. Qua câu tiếp, hoặc thử lại để sát hơn nữa."), **P3-G9** (three-block scoring skeleton + 5-second slow caption), **P3-G13** (chart-not-drawable and past-attempt error copy), **P3-G15** (scored-only chips, ordinal numbering, cap 6), **P3-G16** (TranscriptList score contrast 4.38-4.49:1 accepted), **P3-G17** (type sizes 72/800 and 24/700), **P3-G21** (spacing exceptions 2/3/6/10/14 px incl. inherited P2 G22). **P3-G18** (tip wording) is reviewed in the phase PR, not here. | recommended |
| K | Eval gate (CLAUDE.md, ROADMAP note): `make eval` stays a stub until Phase 4. The Phase 3 PR states "chưa có eval (make eval là stub tới Phase 4)" and pastes the self-compare, cross-sentence and timing output of `make smoke-score` (03-11) plus the synthetic rule tests instead of a metric table. No fabricated metrics. | recommended |

### E - threshold values (thresholds.py, `THRESHOLDS_VERSION = "p2-1"`, `SCORER_VERSION = "prosody-1"`)

| Key | Value | Note |
|-----|-------|------|
| ALIGN_COST_MAX | 1.10 | alignment ok limit |
| ALIGN_RATIO_MIN | 0.5 | |
| ALIGN_RATIO_MAX | 2.0 | |
| ALIGN_SLACK_FRAMES | 30 | |
| MIN_COMMON_VOICED_FRAMES | 10 | fewer -> `melodyMatch` 0 |
| PITCH_DEVIATION_ST | 3.0 | D-13 |
| PD_MIN_FRAMES | 10 | |
| PD_VOICED_RATIO | 0.5 | |
| PD_SIGN_CONSISTENCY | 0.8 | median of user - ref - sentence offset |
| PAUSE_USER_MS | 250 | |
| PAUSE_REF_MS | 100 | |
| PAUSE_SILENCE_DB_BELOW_P95 | 35 | |
| PAUSE_WORD_SNAP_MS | 100 | |
| FLAT_RATIO | 0.6 | |
| FLAT_REF_MIN_STD_ST | 2.0 | skip FLAT_PITCH when the original is flat |
| FINAL_WINDOW_FRAMES | 30 | |
| FINAL_MIN_VOICED_FRAMES | 15 | |
| FINAL_SLOPE_MIN_ST_S | 6.0 | |
| FINAL_SLOPE_MAX_ST_S | 30.0 | Theil-Sen, opposite signs |
| STRESS_MARGIN_Z | 0.5 | both sides |
| STRESS_MIN_WORDS | 5 | |
| PROMINENCE_MIN_VOICED_FRAMES | 3 | |
| SIMILARITY_RMS_ST | 6.0 | |
| SIMILARITY_MIN_FRAMES | 5 | |

## Decisions Made

- Followed the plan exactly; Liam's answer contained no overrides, so the table above equals the plan's recommended values.
- `null` stays rejected for `bestOverall`/`bestAttempt` on the Zod side. The generated pydantic fields are `float | None = None` / `int | None = None` (datamodel-codegen's standard output for optional fields, same as existing `Word.ipa`); this is a generator trait, not a contract change, and the drift gate keeps it stable.

## Deviations from Plan

None - plan executed exactly as written.

Environment note (not a deviation): the worktree had no `node_modules`/`.venv`; ran `pnpm install --frozen-lockfile` and `uv sync --frozen` from the existing lockfiles (no packages added, lockfiles unchanged, `git status` clean afterwards).

## Issues Encountered

None. A lint error (`no-unused-vars` on a destructured test helper) was fixed before the GREEN commit.

## Verification Results

- `UV_NO_SYNC=1 sh scripts/contracts_gen.sh` ok; `pnpm --filter @shadowenglab/contracts test` 69 passed
- `pytest test_contracts_roundtrip.py test_contracts_drift.py` 65 passed; full `services/audio/tests` 850 passed
- `sh scripts/contracts_check.sh` -> "contracts: không lệch" (exit 0)
- `tsc --noEmit`, `eslint packages/contracts/src`, `prettier --check packages/contracts` clean
- `packages/contracts/src/score.ts` not modified; 16 fixture files; no `__schema*` key in the bundle
- Acceptance greps: `"no_speech"` and `bestOverall: Score01.optional()` in api.ts, `meta({ id: "AttemptSummary" })` in attempt.ts, `class AttemptSummary(BaseModel)` and `no_speech` in contracts_gen.py

## Known Stubs

None.

## Threat Flags

None. The only new surface is the additive contract shapes already covered by T-03-01 (drift gate) and T-03-02 (fixed Vietnamese messages).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 03-02 onward can rely on `no_speech`, `AttemptSummary`, `SegmentProgress.best*`, schema v2 DDL (B), thresholds (E) and the cache/numbering rules (C1, F) exactly as tabled above.
- No blockers.

## Self-Check: PASSED

- FOUND: packages/contracts/fixtures/AttemptSummary.json
- FOUND commits e6a1559 (RED) and ba0d02e (GREEN) on this branch
- score.ts unchanged, drift gate green

---
*Phase: 03-p2-ch-m-ng-i-u*
*Completed: 2026-10-09*
