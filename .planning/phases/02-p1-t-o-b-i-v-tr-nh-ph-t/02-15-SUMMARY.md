---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 15
subsystem: api
tags: [fastapi, segments, ipa, model-gate, nfc, tdd, tracer]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-01 approved UpdateSegmentTextRequest + item E; 02-03 store.update_lesson, ApiErrorException, runner.model_gate, app.state.deps; 02-12 load_range_vocals16, analyze_segment"
provides:
  - "PATCH /lessons/{id}/segments/{index}: edit sentence text, keep word/audio alignment, drop translation"
  - "POST /lessons/{id}/segments/{index}/extend-end: endExtraMs += 300 saved at once, then F0/energy/PPG + IPA recomputed under the model gate"
  - "lesson/segment_ops.py: normalize_text, apply_text_edit, edit_segment_text, EXTEND_STEP_MS, EXTEND_MAX_MS, RECOMPUTE_TIMEOUT_S, bump_end_extra, merge_ipa, recompute_segment, Busy, ExtendLimit"
affects: [02-16, 02-17, 02-18, 02-19]

tech-stack:
  added: []
  patterns:
    - "Long model work never holds the per-lesson lock: it runs under model_gate, then merges only its own result (ipa) into the latest lesson.json via update_lesson, so concurrent PATCH / extend-end / translate keep their writes"
    - "Server-side normalization (NFC, trim, collapse) happens before the length check; the length rule lives in the router, not in a pydantic max_length on the raw string"
    - "Fixed Vietnamese ApiError messages for every failure; unexpected recompute errors are logged and returned as internal_error without detail"

key-files:
  created:
    - services/audio/src/audio_service/lesson/segment_ops.py
    - services/audio/tests/test_segment_edit.py
    - services/audio/tests/test_extend_end.py
  modified:
    - services/audio/src/audio_service/routers/segments.py
    - services/audio/tests/test_api.py

key-decisions:
  - "EXTEND_MAX_MS = 3000 is a planner-proposed guard, not in CONTEXT; surfaced to Liam here (one constant to change). 2900 + 300 clamps to 3000; at 3000 the call is 409 invalid_state"
  - "The PATCH body is parsed with a local {text: string} model instead of the generated UpdateSegmentTextRequest: the generated class enforces min/max length on the RAW string, which would reject a 600-code-point NFD text that is only 300 after NFC. Wire shape is identical to the approved contract; no field was added"
  - "After recompute only `ipa` is taken from the fresh analysis (merge_ipa); text, translation and endExtraMs are re-read under the lesson lock, so an edit made while the model was running is never overwritten"

patterns-established:
  - "Tests that need the lifespan (app.state.runner/deps) use `with TestClient(create_app(deps=fakes), base_url='http://127.0.0.1')`; a real threading.Lock (runner.model_gate) is held by the test thread to simulate a busy gate"

requirements-completed: [PLY-04, PLY-05]

duration: 40 min
completed: 2026-10-08
status: complete
plan_head_before: 389eec0efbdc8edf93811761c877c07073bafbcc
plan_head_after: 057c0e08c1771838c597a0160f5e65b4b03fd84b
actuals:
  tokens: 8900
  tasks: 2
  commits: 3

coverage:
  - id: D1
    description: "PATCH saves normalized text, removes translation, keeps timings/asrProb/ipa when the token count matches, leaves words untouched otherwise; empty / >500 code points -> 422 invalid_request"
    requirement: "PLY-04"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_segment_edit.py (27 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "extend-end adds 300 ms saved before recompute, recomputes features + IPA under the model gate, caps at 3000 ms, returns 503 busy after the gate wait and 409 for lessons without range stems; the extension stays saved in both cases"
    requirement: "PLY-05"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_extend_end.py (17 tests, incl. real analyze_segment .npz window and video-duration clamp)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Concurrent PATCH / extend-end never lose each other's writes"
    requirement: "PLY-05"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_extend_end.py#test_a_text_edit_during_recompute_is_not_lost"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_extend_end.py#test_concurrent_bumps_never_lose_a_write"
        status: pass
    human_judgment: false
  - id: D4
    description: "Whether 300 ms steps and the 3000 ms cap feel right in real use for 'Mất chữ cuối?' on actual videos"
    requirement: "PLY-05"
    verification: []
    human_judgment: true
    rationale: "Coverage not determined by tests: step size and cap are proposed defaults; Liam judges them in the 02-19 UAT with a real lesson"
---

# Phase 2 Plan 15: Sentence edit and "Mất chữ cuối?" backend Summary

**PATCH edits a sentence's text without breaking the word/audio alignment (NFC, token-count-aware, translation dropped) and POST extend-end lengthens the sentence by 300 ms immediately, then recomputes its F0/energy/PPG and IPA under the single model gate (waits up to 150 s, then 503 busy), never losing concurrent writes.**

## Performance

- **Duration:** about 40 min
- **Started:** 2026-10-08T01:45:00Z (approx.)
- **Completed:** 2026-10-08T02:25:00Z
- **Tasks:** 2 (Task 1 tracer, Task 2 tdd)
- **Files:** 3 created, 2 modified

## Accomplishments

- Tracer (Task 1): `PATCH /lessons/{id}/segments/{index}` -> `lesson.json` -> `Segment`. Text is NFC-normalized, trimmed and whitespace-collapsed; length 1-500 code points counted after normalization. Same token count replaces each `words[k].text` and keeps start/end/asrProb/ipa/refConfidence/prominence; different count leaves `words` untouched (they describe the audio). `translation` is removed (D-16). Optional keys are never written as null.
- Task 2: `POST .../extend-end`. `bump_end_extra` saves `endExtraMs + 300` (cap 3000) under `update_lesson` before any model work; `recompute_segment` does `gate.acquire(timeout=150)`, loads the range stem (`load_range_vocals16`), loads the PPG model once, runs `analyze_segment`, frees memory in `finally`, and releases the gate in `finally`.
- Errors (all fixed Vietnamese text, no paths): 404 `not_found` / `invalid_segment`, 409 `invalid_state` (not ready, cap reached `Đã nới tối đa cho câu này.`, old lesson without stems `Bài này tạo bằng bản cũ, hãy tạo lại bài để nới câu.`), 422 `invalid_request`, 503 `busy` `Đang xử lý bài khác, thử lại sau.`, 500 `internal_error` (logged, no detail).
- The recomputed window is clamped to the video duration by the existing `features.segment_window` (verified: lesson of 4.0 s, sentence ending at 3.8 s, window end is exactly 4.0).

## Task Commits

1. **Task 1 (tracer): PATCH sentence text** - `a959ec3` (feat)
2. **Task 2 RED: failing extend-end tests** - `a4f3475` (test)
3. **Task 2 GREEN: extend-end implementation** - `057c0e0` (feat)

No REFACTOR commit was needed. Tracer gate (end-of-phase mode, automated-only verify): `pytest test_segment_edit.py` was re-run after the commit and passed (27 passed), then expansion proceeded: "Tracer verified end-to-end - expanding".

## Verification

- `uv run --project services/audio --frozen pytest services/audio/tests/test_extend_end.py services/audio/tests/test_segment_edit.py -q` -> 44 passed.
- Plan-level: `uv run --project services/audio --frozen pytest services/audio/tests -q` -> 786 passed.
- `ruff check` / `ruff format --check` clean on every file touched.
- Acceptance criteria: segment_ops.py contains `def normalize_text`, `def apply_text_edit`, `unicodedata`, `EXTEND_STEP_MS = 300`, `EXTEND_MAX_MS = 3000`, `acquire(timeout=`; segments.py contains the PATCH route on `"/lessons/{lesson_id}/segments/{index}"` and `"/lessons/{lesson_id}/segments/{index}/extend-end"`, and maps `Busy` to 503 `busy`. All PASS.

## TDD Gate Compliance

Plan type is `execute` (not `type: tdd`), so the plan-level gate sequence is not mandated, but Task 2 (`tdd="true"`) followed it: `test(02-15)` `a4f3475` precedes `feat(02-15)` `057c0e0`.

- **RED:** `pytest services/audio/tests/test_extend_end.py` -> 17 failed, 0 passed (after strengthening one test that passed vacuously because the missing route returned 404 and its assertions were still true). Failures are the planned absence of the feature: `404 != 200` for the missing route and `AttributeError` on `segment_ops.bump_end_extra` / `RECOMPUTE_TIMEOUT_S`, not import, syntax or fixture faults. The `gsd check tdd-red-evidence` classifier was not run: pytest's console output is not one of its supported report formats (TAP, JUnit from Maven, swift-testing, unittest), so the semantic assessment above stands in for it.
- **GREEN:** 44 passed in the two files, 786 in the full suite.
- **REFACTOR:** none.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Unexpected recompute errors map to a fixed `internal_error`**
- **Found during:** Task 2
- **Issue:** a model-load or analysis failure after the extension was saved would surface as Starlette's plain-text 500, breaking the ApiError envelope and risking exception text reaching the client (T-02-07).
- **Fix:** `extend_end` catches `Exception`, logs it with `logger.exception`, and returns 500 `internal_error` `Không tính lại được câu này. Phần nới vẫn được lưu.`; memory and gate are already released by `finally`. Covered by `test_memory_is_freed_and_gate_released_when_analysis_fails`.
- **Files modified:** `services/audio/src/audio_service/routers/segments.py`
- **Commit:** `057c0e0`

**2. [Rule 1 - Bug avoided] PATCH body model is local, not the generated `UpdateSegmentTextRequest`**
- **Found during:** Task 1
- **Issue:** the generated class validates 1-500 length on the raw string (Zod trims, pydantic does not), so a decomposed (NFD) text of 600 code points that is 300 after NFC would be rejected, contradicting "length as counted by the server (authoritative)" after normalization; whitespace-only input would also pass the raw check.
- **Fix:** `_EditBody {text: str}` has the same wire shape; the router normalizes and then enforces 1-500, returning 422 `invalid_request` with `Câu không được để trống hoặc dài quá 500 ký tự.` Tested with 600-code-point NFD input (accepted), 501 chars (rejected), whitespace-only (rejected).
- **Files modified:** `services/audio/src/audio_service/routers/segments.py`
- **Commit:** `a959ec3`

**3. [Plan instruction] `test_api.py` shell parametrize** - removed only `"segments"` from `["segments", "translate"]`, as the orchestrator instructed (file is outside `files_modified`; the orchestrator resolves merges with siblings).
- **Commit:** `a959ec3`

**Total deviations:** 2 auto-fixed (1 Rule 2, 1 Rule 1-style) plus 1 instructed edit. **Impact:** none on the approved contract; no field, code, model or threshold was added or changed.

## Decisions and flags for Liam

- `EXTEND_MAX_MS = 3000` (planner assumption, not in CONTEXT): confirm or change the single constant in `segment_ops.py`. A sentence can therefore be lengthened ten times by 300 ms.
- `Segment.text` may differ from the joined `words` after "Sửa" when the token count changes (already recorded as ADR 0005 content in 02-01 item H).
- `recompute_segment` trusts that `Segment.words` never change in count after lesson creation (true for `apply_text_edit`); if a future plan changes that, `merge_ipa` skips the ipa merge rather than misaligning it.

## Issues Encountered

None. The worktree started without a venv; `uv sync --project services/audio --frozen` was run from the existing lockfile (no package added or resolved).

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-02-42 (NFC + trim + 500 code-point limit, stored as a JSON string) and T-02-43 (3000 ms cap, single gate with 150 s timeout -> 503) are implemented and tested. T-02-SC: `uv sync --frozen` only.

## User Setup Required

None.

## Next Phase Readiness

- 02-16 (translate) can call `segment_ops.normalize_text`/`store.update_lesson` the same way; an edit already clears `translation`.
- The UI (02-17/02-18) can use PATCH and extend-end with the Segment response shape; `extend-end` may take up to 150 s when the model gate is busy, so the client should show a pending state and treat 503 `busy` as "extension saved, features refresh next time".

## Self-Check: PASSED

- FOUND: services/audio/src/audio_service/lesson/segment_ops.py, services/audio/src/audio_service/routers/segments.py, services/audio/tests/test_segment_edit.py, services/audio/tests/test_extend_end.py
- FOUND commits: a959ec3, a4f3475, 057c0e0 (ancestors of HEAD)
- Full audio suite: 786 passed; `git status` shows no uncommitted code.

---
*Phase: 02-p1-t-o-b-i-v-tr-nh-ph-t*
*Completed: 2026-10-08*
