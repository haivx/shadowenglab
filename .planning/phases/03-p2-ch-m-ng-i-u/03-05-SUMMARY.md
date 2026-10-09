---
phase: 03-p2-ch-m-ng-i-u
plan: 05
subsystem: api
tags: [fastapi, sqlite, migration, scoring, prosody, cache, pydantic, numpy]

requires:
  - phase: 03-p2-ch-m-ng-i-u
    plan: 01
    provides: "no_speech (422), AttemptSummary, SegmentProgress.bestOverall/bestAttempt, decision table A-K (C1 numbering, F sidecar, H timingMs keys)"
  - phase: 03-p2-ch-m-ng-i-u
    plan: 03
    provides: "prepare_features, score_prosody, to_score_result, RefWord"
provides:
  - "POST /lessons/{id}/segments/{index}/attempts -> 201 ScoreResult, stored with the four scores and result_json in one BEGIN IMMEDIATE transaction (D-09, D-10)"
  - "SQLite user_version 2 migration (five ALTER ADD COLUMN, CHECK 0..1), P1 rows kept with NULL scores"
  - "scoring/ref_cache.py sidecar seg/NNNN.prosody.npz (allow_pickle=False, atomic, feat_version + window validity)"
  - "pipeline.ref_prosody_for_segment (cache hit or lazy compute from the vocals stem slice) and RefAudioMissing"
  - "GET .../attempts (AttemptSummary[], scored only) and GET .../attempts/{n} (re-validated ScoreResult)"
  - "progress bestOverall/bestAttempt (highest overall, tie -> later attempt)"
  - "New lessons write the reference sidecar during analyzing (PipelineDeps.prosody_features)"
affects: [03-06, 03-07, 03-08, 03-10, 03-11]

actuals:
  tokens: 18400
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Scored row is built inside the numbering transaction: insert_scored_attempt(build=lambda n: ScoreResult) so the stored attempt always equals the response attempt"
    - "I/O edge for reference features lives in scoring/ref_cache.py; pure scoring code stays file-free"
    - "Sidecar validity = feat_version and window match; any read error means recompute, never a 500"
    - "Reference slice read with soundfile start/stop at the file's own sample rate, then to_mono_16k"

key-files:
  created:
    - services/audio/src/audio_service/scoring/ref_cache.py
    - services/audio/tests/test_scoring_api.py
  modified:
    - services/audio/src/audio_service/config.py
    - services/audio/src/audio_service/db.py
    - services/audio/src/audio_service/lesson/pipeline.py
    - services/audio/src/audio_service/routers/attempts.py
    - services/audio/src/audio_service/routers/library.py
    - services/audio/tests/test_attempts_api.py
    - services/audio/tests/test_db.py
    - services/audio/tests/test_library_api.py
    - services/audio/tests/test_pipeline.py

key-decisions:
  - "ref_features timing includes the lazy backfill; ref_backfill is reported separately as the contained portion, and total sums every key except ref_backfill so it is not double counted"
  - "A no_speech upload stores no eval clip even with saveForEval (nothing was scored); the row is still inserted (C1)"
  - "GET detail treats attempt < 1 or > 2^53-1 as 404 before touching SQLite (avoids an OverflowError 500)"

patterns-established:
  - "Test helpers (sentence, scoring_lesson, write_stem) in test_scoring_api.py are imported by test_attempts_api.py and test_library_api.py reuses test_db.result_for"
  - "ApiErrorException with fixed Vietnamese messages for no_speech, invalid_state (A6), not_found and corrupted result"

requirements-completed: [PRO-04, FBK-05, FBK-06, PRO-03]

coverage:
  - id: D1
    description: "POST of the reference sentence answers 201 ScoreResult stored in SQLite (scores + result_json), attempt equals the stored row number"
    requirement: PRO-03
    verification:
      - kind: integration
        ref: "services/audio/tests/test_scoring_api.py#test_self_upload_is_scored_stored_and_numbered"
        status: pass
    human_judgment: false
  - id: D2
    description: "Cached scoring is learner-only work: timingMs.total 61 ms and wall 66 ms on the synthetic stem, first call reports ref_backfill, second does not"
    requirement: PRO-04
    verification:
      - kind: integration
        ref: "services/audio/tests/test_scoring_api.py#test_first_scoring_backfills_the_sidecar_and_second_is_cached_and_fast"
        status: pass
    human_judgment: true
    rationale: "Synthetic 3 s stem on an idle machine; real Vietnamese-accented voices, a busy model worker (RESEARCH A7) and real stems are measured in the 03-11 UAT"
  - id: D3
    description: "no_speech answers 422 and stores a voiced=0 NULL-score row (C1); scoring exception answers 500 with no row, no temp file, no leak; missing reference answers 409 with the A6 message"
    requirement: FBK-05
    verification:
      - kind: integration
        ref: "services/audio/tests/test_scoring_api.py#test_silent_recording_is_422_no_speech_and_keeps_an_unvoiced_row"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_scoring_api.py#test_scoring_failure_is_500_with_no_row_no_temp_file_and_no_leak"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_scoring_api.py#test_missing_reference_audio_is_409_invalid_state_without_a_row"
        status: pass
    human_judgment: false
  - id: D4
    description: "v1 database migrates to v2 keeping P1 rows, idempotent, CHECK rejects out-of-range scores, concurrent scored inserts get distinct numbers"
    requirement: FBK-06
    verification:
      - kind: unit
        ref: "services/audio/tests/test_db.py#test_v1_database_migrates_to_v2_keeping_rows_and_is_a_noop_afterwards"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_db.py#test_check_constraints_reject_bad_rows"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_db.py#test_concurrent_scored_inserts_get_distinct_numbers"
        status: pass
    human_judgment: false
  - id: D5
    description: "History lists scored attempts only (ascending), detail re-reads the stored ScoreResult byte-equal to the POST body, 404 for unknown/unscored, 500 fixed message for corrupted JSON; progress carries the best attempt without losing it when a later attempt scores lower"
    requirement: FBK-06
    verification:
      - kind: integration
        ref: "services/audio/tests/test_scoring_api.py#test_history_lists_scored_attempts_only_and_detail_rereads_the_stored_result"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_scoring_api.py#test_corrupted_stored_result_is_500_internal_error_without_echoing_it"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_library_api.py#test_progress_carries_best_overall_and_attempt_only_for_scored_sentences"
        status: pass
    human_judgment: false
  - id: D6
    description: "New lessons write seg/NNNN.prosody.npz in analyzing with the .npz window; stale window or stale feat_version is ignored and rewritten on the next scoring"
    requirement: PRO-04
    verification:
      - kind: unit
        ref: "services/audio/tests/test_pipeline.py#test_every_segment_gets_a_prosody_sidecar_with_the_npz_window"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_scoring_api.py#test_sidecar_with_a_different_window_is_ignored_and_rewritten"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_scoring_api.py#test_sidecar_with_a_different_feat_version_is_ignored_and_rewritten"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-10-09
status: complete
plan_head_before: b3a35fb47508c0ada98d441f61d9136dbc0e0ceb
plan_head_after: 5011a28da97ce2e87a16478b8a6ce0fa5caf3e9a
commits: 6
---

# Phase 3 Plan 05: Scoring API, SQLite v2 and reference sidecar Summary

**A real upload now runs normalise -> reference prosody (sidecar cache or lazy compute from the vocals stem slice, no model) -> learner features -> `score_prosody` and answers 201 `ScoreResult`; the same transaction numbers the attempt and stores the four scores plus `result_json` in SQLite `user_version` 2, with `no_speech`, history, re-read and best-attempt progress on top.**

## Performance

- **Duration:** about 11 min
- **Started:** 2026-10-09T07:24:47Z
- **Completed:** 2026-10-09T07:36:13Z (production commits); SUMMARY committed after
- **Tasks:** 3 (Task 1 tracer, Tasks 2 and 3 TDD)
- **Files modified:** 11 (2 created, 9 modified), `git diff` +1257 / -71

`commits: 6` is measured from `plan_head_before` (3 RED + 3 GREEN); the SUMMARY docs commit follows `plan_head_after`.

## Measured values (synthetic stem, this machine, idle)

Reference = `synth_sentence(DEFAULT_WORDS)` written as `vocals.wav`; learner = the same sentence encoded to webm/opus by real ffmpeg and uploaded through the real route.

| Call | overall | timingMs (ms) | request wall |
|------|---------|---------------|--------------|
| 1st (no cache, lazy backfill) | 0.9996 | normalize 46.2, ref_features 11.6, ref_backfill 10.9, user_features 8.6, align 2.4, metrics 0.4, rules 0.0, total 69.2 | n/a |
| 2nd (sidecar cached) | 0.9996 | normalize 46.4, ref_features 2.4, user_features 9.4, align 2.4, metrics 0.4, rules 0.0, total 61.0 (no `ref_backfill` key) | 66 ms |
| 44.1 kHz stereo stem (slice read + resample, double resample) | >= 0.9 asserted | n/a | n/a |

PRO-03: the reference uploaded against itself scores overall 0.9996 (>= 0.95 required). PRO-04: well under the 3 s budget (61 ms total, 66 ms wall); this is a 3 s synthetic sentence with an idle model worker, so the 3 s claim on real voices and under Demucs load (RESEARCH A7) stays on the 03-11 UAT.

## Final endpoint list

| Method and path | Response | Errors |
|-----------------|----------|--------|
| `POST /lessons/{id}/segments/{index}/attempts` (multipart `audio`, optional `saveForEval`) | 201 `ScoreResult` | 413, 415, 422 `recording_too_long`, 422 `no_speech`, 409 `invalid_state` (lesson not ready, or reference audio missing), 404, 500 `internal_error` |
| `GET /lessons/{id}/segments/{index}/attempts` | `AttemptSummary[]`, scored only, ascending | 404, 409 |
| `GET /lessons/{id}/segments/{index}/attempts/{attempt}` | `ScoreResult` re-validated from `result_json` | 404 `not_found`, 500 `internal_error` (corrupted) |
| `PUT /lessons/{id}/segments/{index}/attempts/{attempt}/eval-clip` | `AttemptAck` (unchanged) | unchanged |
| `GET /lessons/{id}/progress` | `SegmentProgress` now with optional `bestOverall`, `bestAttempt` | unchanged |

Files on disk: `DATA_DIR/lessons/{id}/seg/NNNN.prosody.npz` (keys `feat_version`, `window`, `trim`, `f0_st`, `voiced`, `energy_db`, `mfcc`).

## Accomplishments

- Tracer: upload -> `ScoreResult` stored and numbered by the same transaction; first scoring of a sentence without cache backfills the sidecar (`timingMs.ref_backfill`), later scorings do not.
- Migration v1 -> v2 inside the existing `BEGIN IMMEDIATE` re-check pattern; fresh databases run the v1 DDL then the v2 ALTERs so column order is the same in both paths; re-running is a no-op.
- `no_speech`, scoring failure, missing reference, history, detail, corrupted-JSON and best-attempt paths all answer with fixed Vietnamese messages and never echo a DATA_DIR path or exception text.
- `analyze_segment` precomputes the sidecar with the `.npz` window, so "Mất chữ cuối?" refreshes it and a stale window or `feat_version` is ignored and rewritten.

## Task Commits

1. **Task 1: Tracer API** (TDD)
   - RED: `b73efb4` (test) - 4 end-to-end tests; `ref_prosody_path` committed with it so the tests collect
   - GREEN: `405e3e7` (feat) - ref_cache, pipeline reference helpers, db v2 + `insert_scored_attempt`, attempts router
2. **Task 2: no_speech, history, re-read, best attempt, migration tests** (TDD)
   - RED: `9755881` (test)
   - GREEN: `c2ef236` (feat)
3. **Task 3: sidecar at analyzing, stale cache handling** (TDD)
   - RED: `31890cc` (test)
   - GREEN: `5011a28` (feat)

**Plan metadata:** docs commit for this SUMMARY follows (hash not embedded to avoid self-reference).

Tracer gate: `human_verify_mode` is `end-of-phase` (default) and the tracer `<verify>` is automated-only, so `pytest tests/test_scoring_api.py` was re-run after the Task 1 commit and passed (4 passed); "Tracer verified end-to-end - expanding", then Task 2.

## TDD Gate Compliance

- **RED 1** (`b73efb4`): `test_self_upload_is_scored_stored_and_numbered` failed on `assert "scores" in body` (the route still answered the P1 `AttemptAck`). Run with `-x`, so the other tests of the file were not listed; they target the same absent behaviour. Semantic assessment: target ran and failed on the planned assertion for the intended reason.
- **GREEN 1** (`405e3e7`): 4 passed. Eleven pre-existing tests (P1 `AttemptAck` assertions, v1 schema assertions) failed at this commit by design and are rewritten in Task 2 as the plan assigns; the full suite was green again at `c2ef236`.
- **RED 2** (`9755881`): 16 failed, 62 passed across the four files. The 16 are the new/changed cases failing on absent behaviour (`db.list_scored_attempts`, `get_attempt_result_json`, best fields, 404/500/422 branches). The 62 passing include characterization cases of behaviour Task 1 already shipped (409 missing reference, 500 on scoring failure, v1 -> v2 migration, no leftover temp files); recorded here instead of pretending they were red.
- **GREEN 2** (`c2ef236`): 78 passed across the four files.
- **RED 3** (`31890cc`): 3 failed (`TypeError: PipelineDeps.__init__() got an unexpected keyword argument 'prosody_features'`, `FileNotFoundError` on the missing sidecar, and the `*.npz` glob assertion), 106 passed. The ref_cache and stale-window/version API tests passed already because Task 1 had implemented the cache semantics; they are regression guards.
- **GREEN 3** (`5011a28`): 109 passed in the four Task 3 files; full `services/audio` suite 946 passed.
- **REFACTOR:** none. `gsd_run check tdd-red-evidence` was not run (pytest default output, `type: execute`, `tdd_mode` not enabled), same as 03-01 and 03-03.

## Files Created/Modified

- `services/audio/src/audio_service/scoring/ref_cache.py` - `read_feature_window`, `read_ref_prosody`, `write_ref_prosody`
- `services/audio/src/audio_service/config.py` - `ref_prosody_path`
- `services/audio/src/audio_service/lesson/pipeline.py` - `RefAudioMissing`, `RefProsody`, `ref_prosody_for_segment`, `PipelineDeps.prosody_features`, timer step `prosody`
- `services/audio/src/audio_service/db.py` - `SCHEMA_VERSION = 2`, `_V2_ALTERS`, `insert_scored_attempt`, `AttemptSummaryRow`, `list_scored_attempts`, `get_attempt_result_json`, best fields in `segment_progress`
- `services/audio/src/audio_service/routers/attempts.py` - POST scoring flow, GET list, GET detail
- `services/audio/src/audio_service/routers/library.py` - progress `bestOverall` / `bestAttempt`
- tests: new `test_scoring_api.py`; updated `test_attempts_api.py`, `test_db.py`, `test_library_api.py`, `test_pipeline.py`

## Decisions Made

- `ref_features` includes the backfill time; `ref_backfill` is the contained portion and `total` excludes it from the sum (no double count). Keys follow 03-01 item H.
- A silent upload with `saveForEval=true` does not store an eval clip: nothing was scored, and the row (C1) is still created.
- `GET .../attempts/{n}` answers 404 for `n < 1` or `n > 2^53 - 1` before querying, so an absurd path value cannot become a 500 from SQLite.
- Reference words are `RefWord(text, start - window_start, end - window_start)`; the window comes from `seg/NNNN.npz` when present, else `segment_window(..., lo=base, hi=stop)` for old lessons.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `Scores.sound` is a pydantic `RootModel`, not a float**
- **Found during:** Task 2 (db tests with the contract fixture, whose `sound` is 0.82)
- **Issue:** `insert_scored_attempt` bound `scores.sound` to SQLite and failed with `type 'Sound' is not supported`. The Task 1 path only ever stored `None`, so it was not caught earlier.
- **Fix:** bind `None if scores.sound is None else scores.sound.root`.
- **Files modified:** `services/audio/src/audio_service/db.py`
- **Verification:** `test_insert_scored_attempt_stores_scores_and_validated_json` passes (sound 0.82 stored and read back).
- **Committed in:** `c2ef236`

**2. [Rule 1 - Bug] Existing glob assertion counted the new sidecars**
- **Found during:** Task 3 (`test_entering_analyzing_removes_stale_segment_features`)
- **Issue:** the plan says to keep test_pipeline.py's assertions, but `glob("*.npz")` also matches `NNNN.prosody.npz`, so the test expected only `0000.npz`/`0001.npz`.
- **Fix:** the expected list now includes `0000.prosody.npz` and `0001.prosody.npz`; the orphan-removal intent (stale file gone, only current files remain) is unchanged.
- **Files modified:** `services/audio/tests/test_pipeline.py`
- **Committed in:** `31890cc` (test), `5011a28` makes it pass

**3. [Ordering note, not a code deviation] Task 1 GREEN left 11 P1 tests failing until Task 2**
- The P1 `AttemptAck` assertions and the `user_version == 1` assertions necessarily break when the POST contract changes (D-09) and the schema reaches v2. The plan assigns their rewrite to Task 2, so Task 1's commit is not an independently green suite; `c2ef236` restores it.

---

**Total deviations:** 2 auto-fixed (2 Rule 1), 1 ordering note. **Impact on plan:** none on scope, contract, schema, thresholds or models.

## Issues Encountered

- The worktree had no `.venv`; ran `uv sync --frozen` from the existing lockfile (no packages added, lockfile unchanged).
- A macOS `sed -i` call and a heredoc append were rejected/misparsed by the sandbox or BSD sed; replaced with Edit/Write. No repository content was affected.

## Known Stubs

None. `ProsodyScore.stress/pauses/issues/tips` are still empty lists coming from `score_prosody` until 03-06 fills them; this plan stores whatever `to_score_result` returns, so no change is needed here when 03-06 merges.

## Threat Flags

None beyond the plan's register. Mitigations implemented and tested: T-03-09 (only `?` parameters, `_check_lesson_id`, CHECK bounds proven by `test_check_constraints_reject_bad_rows`), T-03-10 (`model_validate_json` on read, fixed 500 message, test asserts no echo), T-03-11 (`allow_pickle=False`, feat_version + window check, `.part` + `os.replace`, tampered-sidecar test), T-03-12 (existing size/duration caps, reference slice read with `start`/`stop`, temp dir removed in `finally` and asserted empty after every path), T-03-13 (no path or exception text in any error body, asserted).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 03-06 fills `stress/pauses/issues/tips` inside `score_prosody`; this router already merges `score.timing_ms` (`align`, `metrics`, `rules`) and passes everything through `to_score_result`. If 03-06 changes the `score_prosody` signature, `routers/attempts.py:create_attempt` is the one call site to adapt.
- 03-07/03-08/03-10 can read `ScoreResult` from the POST and from `GET .../attempts/{n}` (byte-equal), the scored-attempt list from `GET .../attempts`, and `bestOverall/bestAttempt` from progress.
- 03-11 UAT: re-measure PRO-04 with real stems and a busy Demucs worker; `ref_prosody_for_segment(..., write_cache=False)` is ready for the read-only smoke.
- Open flagged assumptions unchanged: PRO-04 budget under load (RESEARCH A7), FBK-06 numbering C1 (chosen by Liam).

## Self-Check: PASSED

- FOUND: `services/audio/src/audio_service/scoring/ref_cache.py`, `services/audio/tests/test_scoring_api.py`
- FOUND commits b73efb4, 405e3e7, 9755881, c2ef236, 31890cc, 5011a28 on this branch (`git rev-list --count` from `plan_head_before` = 6)
- Acceptance greps: `response_model=ScoreResult` and `insert_scored_attempt` in attempts.py; `SCHEMA_VERSION = 2`, `ADD COLUMN result_json TEXT` and the `ROW_NUMBER() OVER (PARTITION BY segment_index ORDER BY overall DESC, attempt DESC)` line in db.py; `def ref_prosody_for_segment`, `class RefAudioMissing`, `prosody_features:` and `timer.step("prosody")` in pipeline.py; `allow_pickle=False` and `os.replace` in ref_cache.py; `"no_speech"` with 422 and `response_model=list[AttemptSummary]` in attempts.py; `bestOverall` set only when a best exists in library.py
- `cd services/audio && uv run --frozen pytest`: 946 passed; `ruff check` and `ruff format --check` (services/audio and scripts) clean
- No edits to `scoring/scorer.py`, `tests/synth.py`, `apps/web`, `packages/contracts`, STATE.md or ROADMAP.md

---
*Phase: 03-p2-ch-m-ng-i-u*
*Completed: 2026-10-09*
