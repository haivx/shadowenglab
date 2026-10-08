---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
fixed_at: 2026-10-08T22:25:00+07:00
review_path: .planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-10-08
**Source review:** `.planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (WR-01..WR-08; no Critical; Info excluded by `fix_scope: critical_warning`)
- Fixed: 8
- Skipped: 0

No fix touched `packages/contracts`, the SQLite schema, scoring thresholds or models. All error codes used already exist in `ApiErrorCode`.

## Fixed Issues

### WR-01: First-use mic permission prompt eats the recording window and yields a near-empty clip

**Files modified:** `apps/web/lib/player/playerMachine.ts`, `apps/web/lib/audio/recorder.ts`, `apps/web/lib/player/playerMachine.test.ts`, `apps/web/lib/audio/recorder.test.ts`, `apps/web/lib/player/playRange.test.ts`
**Commit:** 2dce7c6
**Applied fix:** The recorder actor now sends a new actor event `RECORDING_STARTED` right after `MediaRecorder.start()`. The `recording` state has substates `opening` (waits for the event) and `active` (holds the `recordDelay` auto-stop timer), so the timer no longer counts the time spent on the permission prompt. `STOP`, `SILENCE`, `LEVEL`, `STOPPED` and `RECORD_FAILED` stay handled at the `recording` level. Tests: the auto-stop test now sends `RECORDING_STARTED`; new tests assert no auto-stop while `opening`, and that the recorder does not emit `RECORDING_STARTED` while the mic is still pending. `playRange.test.ts` compared `snapshot.value === "recording"`, which no longer holds with a nested state, so it now uses `matches("recording")`. Production UI already reads the top-level state via `topLevelState`, so it needed no change.

### WR-02: Several backend error paths do not use the `ApiError` envelope, so the web shows "Backend trả lỗi không đọc được"

**Files modified:** `services/audio/src/audio_service/routers/lesson.py`, `services/audio/src/audio_service/errors.py`, `services/audio/tests/test_api.py`
**Commit:** 66bd6ec
**Applied fix:** `get_lesson` now raises `ApiErrorException` (404 `not_found`, 500 `internal_error`). `install_error_handlers` also registers a `StarletteHTTPException` handler (404 -> `not_found`; other 4xx -> `invalid_request`; 5xx -> `internal_error`; `detail` is never echoed) and an `Exception` handler (500 `internal_error` with a fixed Vietnamese message). Starlette re-raises after sending the unhandled-exception response, so uvicorn still logs the stack. Tests cover missing lesson, unknown route, wrong method, unhandled exception, and the corrupt-file 500.

### WR-03: A stale `dataDir` in settings.json makes every Practice-defaults save fail with 422

**Files modified:** `services/audio/src/audio_service/settings_store.py`, `services/audio/tests/test_settings_api.py`
**Commit:** 7c1bc97
**Applied fix:** `read_settings()` replaces a stored `dataDir` that is no longer a directory with `str(data_root())`, the same fallback `config._saved_data_dir()` applies at startup. The UI then PUTs back a valid path. Test: save a dir, delete it, GET reports the active dir, PUT back with `repeat=3` returns 200. A saved dir that still exists is untouched, so the "applies after restart" behaviour (D-12) is unchanged.

### WR-04: `POST /lessons` accepts live, upcoming and unavailable videos and gives the wrong error

**Files modified:** `services/audio/src/audio_service/routers/media.py`, `services/audio/src/audio_service/routers/lesson.py`, `services/audio/tests/test_lessons_api.py`
**Commit:** d5262f7
**Applied fix:** (Owner-approved.) Extracted `ensure_video_usable(info)` in `media.py` (live/upcoming -> 422 `live_video`; non-open availability -> 404 `video_unavailable`), used by `preview_video` and called in `create_lesson` before `resolve_range`. No contract change. Tests: live/upcoming and private/needs_auth/subscriber_only return the right code and write nothing to disk.

### WR-05: No server-side cap on lesson range length (OOM risk on the 8 GB target)

**Files modified:** `services/audio/src/audio_service/lesson/pipeline.py`, `services/audio/tests/test_lessons_api.py`
**Commit:** 0fa1236
**Applied fix:** (Owner-decided.) Added `MAX_RANGE_S = 360.0` (6 minutes, LES-02) enforced in `resolve_range`; exceeding it raises `ValueError`, which the router already maps to 422 `invalid_range`. Default ranges (whole video <= 360 s, otherwise 0-300 s) are unaffected. Tests: 361 s, 361 s offset, and open-ended range on a 1 h video are rejected; exactly 360 s inside a long video is accepted.
**Follow-up for Liam:** `RangePicker.tsx` still only shows a soft warning above 5 minutes and does not stop the user selecting more than 6 minutes, so such a request now gets the generic "Khoảng thời gian không hợp lệ." from the API. Capping the slider at 6 minutes in the UI is not part of this review and was left alone.

### WR-06: `_real_separate` / `_warm_demucs` can raise `UnboundLocalError` that hides the real failure

**Files modified:** `services/audio/src/audio_service/lesson/pipeline.py`, `services/audio/src/audio_service/system_status.py`, `services/audio/tests/test_pipeline.py`, `services/audio/tests/test_system_status.py`
**Commit:** 902530e
**Applied fix:** Replaced the `del separator` / reassign / `finally: del separator` pattern with a helper that loads, runs and frees on one device (`_separate_on` in the pipeline, a local `run_on` in `_warm_demucs`). The MPS-to-CPU retry is now a plain `try/except RuntimeError` around the helper, so there is no name that can be unbound in a `finally`. This differs slightly from the suggested sentinel sketch (no `None` variable, so no typing workaround for `separate_vocals`) but fixes the same defect. One side effect: a `RuntimeError` raised while loading on MPS now also falls back to CPU. Tests assert the real `OSError` from a failing CPU load propagates; both fail against the old code.

### WR-07: `DownloadError` is always reported as "limited by region, private or downloads disabled"

**Files modified:** `services/audio/src/audio_service/lesson/pipeline.py`, `services/audio/tests/test_lessons_api.py`
**Commit:** fd8ca01
**Applied fix:** New `download_failure_message(exc)` classifies yt-dlp text against a list of restriction markers (private, video unavailable, "in your country", geo, sign in/log in, members-only, age-restricted, copyright, removed, HTTP 403/forbidden). A match keeps `DOWNLOAD_BLOCKED_MESSAGE`; anything else gets the neutral `DOWNLOAD_FAILED_MESSAGE` ("không tải được video lúc này. Hãy kiểm tra mạng rồi bấm Thử lại"). The yt-dlp text is used only for classification and never stored in `lesson.json`. Status: **fixed: requires human verification**. The marker list is a heuristic over yt-dlp message wording, so an unlisted restriction message would show the neutral text (conservative direction). Tests cover restricted and transient (DNS, 429, format-not-available) cases and check no raw text leaks.

### WR-08: Retrying a failed lesson bypasses the duplicate-lesson rule

**Files modified:** `services/audio/src/audio_service/routers/lesson.py`, `services/audio/tests/test_jobs.py`
**Commit:** 214fcc5
**Applied fix:** Extracted `_find_duplicate(video_id, start, end, exclude_id)` and `_duplicate_error`, used by `create_lesson` and by the `retry` route. `retry` now holds `_create_lock`, loads the lesson, and if it is `failed` and another non-failed lesson has the same video and range, returns 409 `duplicate_lesson` with that lesson's id (the failed lesson stays failed). Otherwise it calls `retry_lesson` as before; 404/409 `invalid_state` mapping is unchanged. Test: fail A, create B with the same link and range (allowed), retry A returns 409 pointing to B and A is still `failed`.

## Verification

Verification ran in the **main checkout** (`/Users/xuanhai/Documents/shadowenglab`) after the review-fix branch was fast-forwarded into `gsd/phase-01-p0-n-n-t-ng` and the temporary worktree was removed, so the numbers are reproducible from the tree you are looking at. Per-finding checks (targeted pytest/vitest, ruff, prettier, eslint, `tsc --noEmit` for `apps/web`) ran earlier inside the worktree.

- `make test`: exit 0. Contracts drift gate passed; `packages/contracts` vitest 58 passed; `apps/web` vitest 174 passed (14 files); pytest 846 passed, 1 warning (starlette `httpx` deprecation, pre-existing).
- `make lint`: exit 0. eslint, prettier, contracts `tsc`, `ruff check`, `ruff format --check` all clean. Note `make lint` does not run `tsc` on `apps/web`; I ran `pnpm exec tsc --noEmit` there separately in the worktree and it was clean.

Logic-bug caveat: tests cover each behaviour, but WR-01 (state machine timing against a real browser permission prompt) and WR-07 (heuristic classifier) cannot be fully confirmed without a manual run; WR-01 deserves a quick first-run mic-prompt check in the browser.

## Skipped Issues

None.

---

_Fixed: 2026-10-08_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

## Orchestrator verification note (2026-10-08)

Chạy lại `make test` trên checkout chính sau khi fixer xong: **1 failed, 845 passed** — `tests/test_db.py::test_concurrent_inserts_get_distinct_numbers` báo `OperationalError('database is locked')`. Chạy lẻ test này 8 lần: 6 pass, 2 fail (fail ngay ~0.1 s, không chờ hết `timeout=5`). Không commit fix nào chạm `db.py` hay `test_db.py`, nên đây là test chập chờn có sẵn từ trước (ghi `PRAGMA journal_mode=WAL` đồng thời trên DB mới / nâng khoá trong transaction), không phải hồi quy do WR-01..08. `make lint` sạch.
