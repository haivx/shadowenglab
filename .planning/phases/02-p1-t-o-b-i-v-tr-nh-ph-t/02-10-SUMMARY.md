---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 10
subsystem: api
tags: [fastapi, ffmpeg, vad, upload, sqlite, eval-clip, tdd, security]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-01 AttemptAck + items C/D; 02-03 ApiErrorException, create_app, store; 02-06 db DAO (insert_attempt, get_attempt, mark_saved_for_eval), tmp_dir, eval_clips_dir"
provides:
  - "POST /lessons/{id}/segments/{i}/attempts: browser recording -> WAV 16 kHz mono -> VAD -> attempts row -> AttemptAck (201)"
  - "PUT /lessons/{id}/segments/{i}/attempts/{n}/eval-clip: re-send blob, store eval clip + sidecar, no new attempt (200)"
  - "lesson/normalize.py: sniff_demuxer, normalize_to_wav16k (explicit -f whitelist, -t limit)"
  - "lesson/vad.py: voiced_ms, is_voiced (energy VAD on frame_energy)"
affects: [02-14, 02-19, phase-03-scoring, phase-04-eval]

tech-stack:
  added: []
  patterns:
    - "Upload hardening at route level: custom APIRoute (route_class) caps the body before Starlette parses multipart, because FastAPI parses the form before running the handler"
    - "Recording lifecycle: mkdtemp under DATA_DIR/tmp, rmtree in finally on every path; eval clip written .part -> sidecar -> rename so a clip never exists without its sidecar"
    - "saved_for_eval flag is set only after the clip is on disk (insert with false, store, then mark)"

key-files:
  created:
    - services/audio/src/audio_service/lesson/normalize.py
    - services/audio/src/audio_service/lesson/vad.py
    - services/audio/tests/test_normalize.py
    - services/audio/tests/test_vad.py
    - services/audio/tests/test_attempts_api.py
  modified:
    - services/audio/src/audio_service/routers/attempts.py
    - services/audio/tests/test_api.py

key-decisions:
  - "Body cap is a route_class (_BoundedBodyRoute) in attempts.py, not middleware: content-length is checked first, then bytes are counted in receive() so chunked bodies are cut too; MAX_BODY = 10 MB + 64 KB for multipart framing, file itself capped at exactly 10 MB while streaming"
  - "AttemptAck uses attempt numbering from db.insert_attempt (every upload, voiced or not, 02-01 item C); the PUT builds its ack from the stored row (durationMs, voiced) so it never recomputes a different VAD verdict"
  - "ffmpeg failure, unreadable WAV, bad magic, empty upload all map to one fixed 415 message; stderr is discarded (DEVNULL) and never echoed"

patterns-established:
  - "Synthetic voice for tests: 200 Hz tone with fades in the middle of a low-noise clip (tone at both ends would raise the 10th-percentile noise estimate)"

requirements-completed: [REC-02, REC-03, REC-04]

duration: ~45 min
completed: 2026-10-07
status: complete
plan_head_before: dd556e3d20e358aa260d8144b8a281d9c52762d5
plan_head_after: d5cc43da2944952dec744fb1296c9c614d810db5
actuals:
  tokens: 21000
  tasks: 3
  commits: 5

coverage:
  - id: D1
    description: "Chrome webm/opus, Safari mp4/AAC and fragmented mp4 are normalized to 16 kHz mono PCM16 and recorded as an attempt with a voiced flag; silent recording still records an attempt with voiced false"
    requirement: "REC-02"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_attempts_api.py#test_spoken_then_silent_recording_are_recorded"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_normalize.py#test_normalizes_browser_containers_to_16k_mono_pcm16"
        status: pass
    human_judgment: false
  - id: D2
    description: "VAD behaves on synthetic signals (silence, -60 dBFS noise, steady loud noise, 60 ms click, 0.5 s tone)"
    requirement: "REC-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_vad.py"
        status: pass
    human_judgment: true
    rationale: "Thresholds are starting values (RESEARCH A1); whether they fit Liam's real microphone is judged in the end-of-phase UAT (02-19)"
  - id: D3
    description: "No recording stays on disk unless saveForEval; temp dir empty after success, 4xx and ffmpeg failure"
    requirement: "REC-04"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_attempts_api.py#assert_api_error (tmp_files == [] on every error test)"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_attempts_api.py#test_upload_without_save_for_eval_leaves_no_clip"
        status: pass
    human_judgment: false
  - id: D4
    description: "Upload hardening: m3u8/text/wav/empty -> 415 without ffmpeg, >10 MB -> 413 (content-length and chunked), >60 s -> 422, error bodies leak no path"
    requirement: "REC-02"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_attempts_api.py#test_m3u8_playlist_is_415_and_ffmpeg_never_runs"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_attempts_api.py#test_chunked_body_over_10_mb_is_413_while_streaming"
        status: pass
    human_judgment: false
  - id: D5
    description: "Eval clip saved on upload or via PUT: WAV 16 kHz mono + JSON sidecar named from validated values, saved_for_eval 1, no new attempt"
    requirement: "REC-04"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_attempts_api.py#test_save_for_eval_on_upload_stores_clip_and_sidecar"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_attempts_api.py#test_put_eval_clip_stores_the_blob_without_a_new_attempt"
        status: pass
    human_judgment: false
---

# Phase 2 Plan 10: Attempt upload backend Summary

**Browser recordings (webm/opus, mp4/AAC, fragmented mp4) become a recorded attempt with a voiced flag via ffmpeg (explicit `-f` demuxer, magic-byte whitelist) and an energy VAD, bounded to 10 MB / 60 s, deleted after the request unless saved for eval, with a PUT route to keep a clip afterwards.**

## Performance

- **Tasks:** 3 (Task 1 tracer, Tasks 2 and 3 TDD)
- **Files:** 5 created, 2 modified
- **Tests:** `uv run --project services/audio --frozen pytest services/audio/tests -q` -> 564 passed; `ruff check` and `ruff format` clean
- **Tracer gate:** `test_attempts_api.py` re-run green (5 passed) before expansion

## VAD constants used (starting values, RESEARCH A1)

| Constant | Value | Meaning |
| -------- | ----- | ------- |
| frame step | 10 ms (`frame_energy` default, 25 ms window) | RMS per frame |
| `FLOOR_DB` | -50.0 dB | below this a frame is never voice |
| `NOISE_PERCENTILE` | 10 | noise = 10th percentile of the clip's frame dB |
| `MARGIN_DB` | 12.0 | voiced frame when dB > max(-50, noise + 12) |
| `MIN_VOICED_MS` | 150 | minimum total voiced time |
| `MIN_RUN_MS` | 100 | minimum contiguous voiced run |

Not retuned: the synthetic tests passed with the documented values. Known property worth checking in the UAT with Liam's microphone: because the noise floor is the clip's own 10th percentile, a recording that is loud for more than 90% of its length (no leading or trailing silence) raises the threshold, so only its loudest frames count. A steady loud noise is correctly never "voiced"; a continuous loud tone is the same case.

## Accomplishments

- `POST /lessons/{id}/segments/{i}/attempts` (201 `AttemptAck`): lesson not found 404 `not_found`, not ready 409 `invalid_state`, index out of range 404 `invalid_segment`; every upload (voiced or not) records one row, attempt numbers per (lesson, segment) from `db.insert_attempt`.
- `normalize.py`: `sniff_demuxer` (EBML magic -> `matroska,webm`; bytes 4..8 `ftyp` -> `mov,mp4,m4a,3gp,3g2,mj2`; else None), `normalize_to_wav16k` argv list with `-f <demuxer>` before `-i`, `-t 61`, `pcm_s16le`, 16000 Hz, mono, timeout 30 s, stdout/stderr discarded, no shell, no loudnorm. A demuxer outside the two whitelisted names raises `ValueError`.
- `vad.py`: pure `voiced_ms` / `is_voiced` on `features.frame_energy`.
- Hardening: route-level body cap (header and counted `receive()`), 10 MB streaming cap, magic-byte sniff before ffmpeg, ffmpeg or WAV read failure -> fixed 415, > 60 s -> 422 `recording_too_long`. Error bodies carry only `{code, message}` (test asserts no data-dir path and no "ffmpeg").
- `PUT .../attempts/{n}/eval-clip` (200 `AttemptAck`): re-normalizes the re-sent blob, writes `eval_clips/{lessonId}_{index:04d}_{attempt:02d}.wav` + `.json` sidecar `{lessonId, segmentIndex, attempt, text}`, sets `saved_for_eval = 1`, creates no attempt. Missing attempt 404 `not_found`, not-ready lesson 409.
- POST with `saveForEval=true` stores the clip through the same helper (`_store_eval_clip`); without it `eval_clips/` stays empty.

## Task Commits

1. **Task 1 (tracer):** `4c20069` feat - upload -> WAV -> VAD -> attempts row, temp dir removed
2. **Task 2 RED:** `7b2e4fd` test - limits, whitelist, normalize and VAD tests
3. **Task 2 GREEN:** `0a04b83` feat - body cap, 413/415/422, always-cleaned temp dir
4. **Task 3 RED:** `e3ca9aa` test - eval-clip tests
5. **Task 3 GREEN:** `d5cc43d` feat - `_store_eval_clip`, saveForEval, PUT route

No REFACTOR commits.

## TDD Gate Compliance

- **Task 2 RED (`7b2e4fd`):** `pytest test_normalize.py test_vad.py test_attempts_api.py` -> 4 failed, 30 passed. Failing targets: `test_body_over_10_mb_is_413` (415 != 413), `test_chunked_body_over_10_mb_is_413_while_streaming` (415 != 413), `test_recording_longer_than_60_s_is_422` (201 != 422), `test_failed_uploads_do_not_create_an_attempt` (attempt 2 != 1). Semantic assessment: each target ran and failed on the planned absence of the size and duration limits; no import, syntax or fixture error. The sniff/normalize/VAD unit tests and the 415 cases passed at RED because the tracer (Task 1) already shipped sniff, the whitelist and the VAD, so they are regression coverage, not RED evidence. pytest output is not a format `gsd_run check tdd-red-evidence` parses, so no classifier verdict exists; the assessment is manual.
- **Task 2 GREEN:** 63 passed (including `test_api.py`).
- **Task 3 RED (`e3ca9aa`):** 5 failed, 15 passed. Failing: POST with `saveForEval` returned `savedForEval` False, PUT returned 404 (`{'detail': 'Not Found'}`, route absent) in four tests. Semantic assessment: planned absence of the feature, no collection or fixture faults.
- **Task 3 GREEN:** 20 passed in `test_attempts_api.py`; full suite 564 passed.
- **REFACTOR:** none.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Body-size limit implemented as a custom `APIRoute` in `attempts.py`**
- **Found during:** Task 2
- **Issue:** the plan asks to reject on `content-length` and while streaming inside the endpoint, but FastAPI/Starlette parse the whole multipart form before the handler runs, so an in-handler check would run after a 100 MB body was already read (and spooled to disk).
- **Fix:** `route_class=_BoundedBodyRoute` checks `content-length` first and counts bytes in `receive()` (covers chunked bodies); `_receive` still enforces exactly 10 MB on the file while copying. Stays inside the plan's `files_modified`; `main.py` untouched.
- **Files modified:** `services/audio/src/audio_service/routers/attempts.py`
- **Commit:** `0a04b83`

**2. [Rule 3 - Blocking] `tests/test_api.py` shell list**
- **Found during:** Task 1
- **Issue:** `test_p1_router_shells_exist_and_are_mounted_empty[attempts]` asserts no routes; filling the shell breaks it.
- **Fix:** removed only `"attempts"` from the parametrize list (as instructed). I left the original 3-line formatting of that decorator untouched (did not run ruff format on the file) so the expected textual conflict with siblings stays a one-line conflict.
- **Files modified:** `services/audio/tests/test_api.py`
- **Commit:** `4c20069`

**3. [Plan interpretation] eval-clip order in POST**
The plan lists `insert_attempt(..., voiced, saved_for_eval)`. The row is inserted with `saved_for_eval = 0` and marked via `db.mark_saved_for_eval` only after the clip and sidecar are on disk, so a failed clip write never leaves a row claiming a clip exists.

**4. [Plan interpretation] Tracer ignores `saveForEval`**
Task 1 accepts the form field but returns `savedForEval: false` and stores nothing; Task 3 completed it. Failing closed on a privacy flag.

**Total deviations:** 2 auto-fixed (Rule 3), 2 interpretations. **Impact:** none on contract, DDL or thresholds.

## Notes for downstream plans

- Starlette's multipart parser spools a file part larger than 1 MB to the system temp directory (not `DATA_DIR/tmp`) until the request finishes, then deletes it. Nothing persists, but the bytes briefly pass through the OS temp dir before `_receive` copies them into the private `DATA_DIR/tmp` directory. The 10 MB cap bounds this.
- `AttemptAck` response is built from `exclude_unset`; all six fields are always set, so the wire shape matches the approved contract.
- 02-14 (UI) can rely on: 413 `payload_too_large`, 415 `unsupported_media`, 422 `recording_too_long`, 409 `invalid_state`, 404 `invalid_segment` / `not_found` with Vietnamese messages from `ApiError`.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-02-25 (magic-byte sniff, explicit `-f`, argv, no shell; m3u8 test proves ffmpeg never runs), T-02-26 (10 MB header and stream caps, `-t 61` plus 60 s check, 30 s timeout), T-02-27 (private mkdtemp, `finally` rmtree, tmp dir asserted empty after every path), T-02-28 (names from validated ULID and ints only) are implemented and tested. T-02-29 (Origin guard, TrustedHost) applies through `create_app`.

## Issues Encountered

None.

## Self-Check: PASSED

- FOUND: normalize.py, vad.py, routers/attempts.py, test_normalize.py, test_vad.py, test_attempts_api.py
- FOUND commits (ancestors of HEAD): 4c20069, 7b2e4fd, 0a04b83, e3ca9aa, d5cc43d
- Acceptance greps: normalize.py has `"-f"`, `matroska,webm`, `pcm_s16le`, `16000`, no `shell=True`; attempts.py has `UploadFile`, `Form`, `insert_attempt`, `rmtree` in `finally`, `payload_too_large`, `unsupported_media`, `recording_too_long`, the eval-clip route string, `mark_saved_for_eval`, `eval_clips_dir`; vad.py imports `frame_energy` and opens no files
- Full audio suite: 564 passed
