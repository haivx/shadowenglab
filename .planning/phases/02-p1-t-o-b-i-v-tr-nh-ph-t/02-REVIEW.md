---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
reviewed: 2026-10-08T00:00:00Z
depth: standard
files_reviewed: 157
files_reviewed_list:
  - CLAUDE.md
  - Makefile
  - apps/web/app/globals.css
  - apps/web/app/layout.tsx
  - apps/web/app/lessons/[id]/page.tsx
  - apps/web/app/page.tsx
  - apps/web/app/providers.tsx
  - apps/web/app/settings/page.tsx
  - apps/web/app/tokens.css
  - apps/web/components.json
  - apps/web/components/AppHeader.tsx
  - apps/web/components/AttemptStrip.tsx
  - apps/web/components/Banner.tsx
  - apps/web/components/CreateLessonDialog.tsx
  - apps/web/components/JobSteps.tsx
  - apps/web/components/KeyField.tsx
  - apps/web/components/LessonCard.tsx
  - apps/web/components/LevelMeter.tsx
  - apps/web/components/MicSection.tsx
  - apps/web/components/ModelStatusList.tsx
  - apps/web/components/PlayerControls.tsx
  - apps/web/components/PracticeDefaults.tsx
  - apps/web/components/PracticeHeader.tsx
  - apps/web/components/PracticeRoom.tsx
  - apps/web/components/RangePicker.tsx
  - apps/web/components/ResultActionBar.tsx
  - apps/web/components/ReviewBlock.tsx
  - apps/web/components/SentenceStatePanel.tsx
  - apps/web/components/SpokenIpa.tsx
  - apps/web/components/SystemBanners.tsx
  - apps/web/components/TranscriptList.tsx
  - apps/web/components/VideoPane.tsx
  - apps/web/components/ui/alert.tsx
  - apps/web/components/ui/badge.tsx
  - apps/web/components/ui/button.tsx
  - apps/web/components/ui/card.tsx
  - apps/web/components/ui/dialog.tsx
  - apps/web/components/ui/input.tsx
  - apps/web/components/ui/kbd.tsx
  - apps/web/components/ui/label.tsx
  - apps/web/components/ui/progress.tsx
  - apps/web/components/ui/select.tsx
  - apps/web/components/ui/skeleton.tsx
  - apps/web/components/ui/slider.tsx
  - apps/web/components/ui/sonner.tsx
  - apps/web/components/ui/tabs.tsx
  - apps/web/components/ui/tooltip.tsx
  - apps/web/lib/api.test.ts
  - apps/web/lib/api.ts
  - apps/web/lib/audio/level.test.ts
  - apps/web/lib/audio/level.ts
  - apps/web/lib/audio/micPermission.ts
  - apps/web/lib/audio/mime.test.ts
  - apps/web/lib/audio/mime.ts
  - apps/web/lib/audio/recorder.test.ts
  - apps/web/lib/audio/recorder.ts
  - apps/web/lib/ipaLine.test.ts
  - apps/web/lib/ipaLine.ts
  - apps/web/lib/lessonView.test.ts
  - apps/web/lib/lessonView.ts
  - apps/web/lib/player/listenActors.test.ts
  - apps/web/lib/player/listenActors.ts
  - apps/web/lib/player/playRange.test.ts
  - apps/web/lib/player/playRange.ts
  - apps/web/lib/player/playerMachine.test.ts
  - apps/web/lib/player/playerMachine.ts
  - apps/web/lib/player/shortcuts.test.ts
  - apps/web/lib/player/shortcuts.ts
  - apps/web/lib/player/useShortcuts.ts
  - apps/web/lib/queries.ts
  - apps/web/lib/segmentCache.test.ts
  - apps/web/lib/segmentCache.ts
  - apps/web/lib/settingsForm.test.ts
  - apps/web/lib/settingsForm.ts
  - apps/web/lib/time.test.ts
  - apps/web/lib/time.ts
  - apps/web/lib/tokens.test.ts
  - apps/web/lib/utils.ts
  - apps/web/package.json
  - apps/web/postcss.config.js
  - apps/web/tailwind.config.ts
  - apps/web/tsconfig.json
  - docs/decisions/0004-bo-iframe-video-tu-host.md
  - docs/decisions/0005-job-runner-attempts-settings-p1.md
  - docs/product.md
  - packages/contracts/fixtures/ApiError.json
  - packages/contracts/fixtures/AppSettings.json
  - packages/contracts/fixtures/AttemptAck.json
  - packages/contracts/fixtures/CreateLessonRequest.json
  - packages/contracts/fixtures/LessonListItem.json
  - packages/contracts/fixtures/LessonProgress.json
  - packages/contracts/fixtures/OpenAiKeyCheckRequest.json
  - packages/contracts/fixtures/OpenAiKeyCheckResult.json
  - packages/contracts/fixtures/SystemStatus.json
  - packages/contracts/fixtures/UpdateSegmentTextRequest.json
  - packages/contracts/fixtures/VideoPreview.json
  - packages/contracts/schema/contracts.schema.json
  - packages/contracts/src/api.ts
  - packages/contracts/src/attempt.ts
  - packages/contracts/src/contracts.test.ts
  - packages/contracts/src/index.ts
  - packages/contracts/src/settings.ts
  - scripts/smoke_jobs.py
  - scripts/smoke_lesson.py
  - services/audio/pyproject.toml
  - services/audio/src/audio_service/config.py
  - services/audio/src/audio_service/contracts_gen.py
  - services/audio/src/audio_service/db.py
  - services/audio/src/audio_service/errors.py
  - services/audio/src/audio_service/lesson/download.py
  - services/audio/src/audio_service/lesson/ipa.py
  - services/audio/src/audio_service/lesson/jobs.py
  - services/audio/src/audio_service/lesson/normalize.py
  - services/audio/src/audio_service/lesson/pipeline.py
  - services/audio/src/audio_service/lesson/segment.py
  - services/audio/src/audio_service/lesson/segment_ops.py
  - services/audio/src/audio_service/lesson/store.py
  - services/audio/src/audio_service/lesson/transcribe.py
  - services/audio/src/audio_service/lesson/translate.py
  - services/audio/src/audio_service/lesson/urls.py
  - services/audio/src/audio_service/lesson/vad.py
  - services/audio/src/audio_service/main.py
  - services/audio/src/audio_service/models.py
  - services/audio/src/audio_service/routers/attempts.py
  - services/audio/src/audio_service/routers/lesson.py
  - services/audio/src/audio_service/routers/library.py
  - services/audio/src/audio_service/routers/media.py
  - services/audio/src/audio_service/routers/segments.py
  - services/audio/src/audio_service/routers/settings.py
  - services/audio/src/audio_service/routers/system.py
  - services/audio/src/audio_service/routers/translate.py
  - services/audio/src/audio_service/secrets_env.py
  - services/audio/src/audio_service/settings_store.py
  - services/audio/src/audio_service/system_status.py
  - services/audio/tests/conftest.py
  - services/audio/tests/test_api.py
  - services/audio/tests/test_attempts_api.py
  - services/audio/tests/test_config.py
  - services/audio/tests/test_db.py
  - services/audio/tests/test_download.py
  - services/audio/tests/test_extend_end.py
  - services/audio/tests/test_ipa.py
  - services/audio/tests/test_jobs.py
  - services/audio/tests/test_lessons_api.py
  - services/audio/tests/test_library_api.py
  - services/audio/tests/test_media_api.py
  - services/audio/tests/test_normalize.py
  - services/audio/tests/test_openai_key.py
  - services/audio/tests/test_pipeline.py
  - services/audio/tests/test_segment.py
  - services/audio/tests/test_segment_edit.py
  - services/audio/tests/test_settings_api.py
  - services/audio/tests/test_smoke_jobs.py
  - services/audio/tests/test_system_status.py
  - services/audio/tests/test_translate.py
  - services/audio/tests/test_urls.py
  - services/audio/tests/test_vad.py
findings:
  critical: 0
  warning: 8
  info: 9
  total: 17
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-10-08
**Depth:** standard
**Files Reviewed:** 157
**Status:** issues_found

## Summary

I read the Python service (`services/audio/src`, plus the `features`, `audio_io`, `separate`, `timing` and `quality` modules the pipeline imports), the web app (`apps/web/{app,components,lib}`), the Zod contracts and both smoke scripts. Tests, fixtures and docs got a scan for reliability problems only. I did not execute any code; every finding below comes from reading the source.

Overall the code is solid on the paths that matter for security:
- Ids are checked by regex and the resolved path is confirmed to sit inside DATA_DIR.
- yt-dlp only ever receives a canonical URL.
- Uploads are capped, sniffed by magic bytes, and sent to ffmpeg with an explicit `-f`.
- The Host and Origin guards cover DNS rebinding and CSRF.
- The API key never reaches logs or responses.
- No `any` or `eslint-disable` was found in non-test web code.
- `contracts_gen.py` carries the GENERATED header and looks machine-written. It was not hand-edited as far as I can tell. I did not run `make contracts-check`.

I found no data-loss or security defect that would block shipping. The warnings below are real behaviour defects, mostly at API-contract and state-machine boundaries.

Already recorded in `02-SECURITY.md`, not repeated here: `extract_audio` has no ffmpeg timeout, `GET /lessons` returns 500 on a schema-valid non-ULID id, and error toasts show generic `Error.message`.

## Warnings

### WR-01: First-use mic permission prompt eats the recording window and yields a near-empty clip

**File:** `apps/web/lib/player/playerMachine.ts:376` (with `apps/web/lib/audio/recorder.ts:161,241`)
**Issue:** The `recording` state arms `after: { recordDelay: stopRecorder }` on entry. The recorder actor only starts `MediaRecorder` after `await openMic()` resolves. On a first run the browser shows a permission prompt, and a user who needs longer than `recordDelay` (about 4.5 s for a 3 s sentence at x1.5) triggers the auto-stop before any audio exists.
- The `STOP` sets `stopRequested`, and line 241 calls `requestStop()` right after `start()`, so the clip is a few milliseconds long.
- The upload then fails with 415, or `is_voiced` returns false and the user sees "Không nghe thấy gì trong lượt vừa rồi".
- Either result blames the user or the mic, not the permission timing.

**Fix:** Start the delay only once the mic is actually recording. Have the actor send a `RECORDING_STARTED` event, move the `after` timer into a child state entered on that event, and keep `STOP` and `SILENCE` handled in both. Sketch:
```ts
recording: {
  initial: "opening",
  states: {
    opening: { on: { RECORDING_STARTED: "active" } },
    active: { after: { recordDelay: { actions: "stopRecorder" } } },
  },
  on: { STOP: ..., SILENCE: ..., LEVEL: ..., STOPPED: ..., RECORD_FAILED: ... },
}
```

### WR-02: Several backend error paths do not use the `ApiError` envelope, so the web shows "Backend trả lỗi không đọc được"

**File:** `services/audio/src/audio_service/routers/lesson.py:99,101,106` (and `errors.py:47-58`)
**Issue:** `GET /lessons/{id}` raises `HTTPException(404/500, detail=...)`. `install_error_handlers` only handles `ApiErrorException` and `RequestValidationError`, so the body is `{"detail": "..."}`. `api.ts` (`ApiError.safeParse`) rejects it and replaces it with `{code: "internal_error", message: "Backend trả lỗi không đọc được."}`.
- Opening a deleted or missing lesson URL, the main 404 case for S3, therefore shows the misleading text through `PracticeRoom` (`lesson.error.message`).
- The code `not_found` is never seen by the client.
- Every other router uses `ApiErrorException`, so this one is inconsistent.
- Unknown routes (404/405) and unhandled 500s also bypass the contract.

**Fix:** In `get_lesson`, raise `ApiErrorException(404, "not_found", "Không tìm thấy bài.")` and `ApiErrorException(500, "internal_error", ...)` instead of `HTTPException`. Also register a handler for `StarletteHTTPException` and for `Exception` in `install_error_handlers` that returns `error_response(...)` with fixed Vietnamese text.

### WR-03: A stale `dataDir` in settings.json makes every Practice-defaults save fail with 422

**File:** `services/audio/src/audio_service/settings_store.py:41-55,58-62` (with `apps/web/components/PracticeDefaults.tsx:127-141`)
**Issue:** `read_settings()` returns the stored `dataDir` verbatim after contract validation only. At startup, `config._saved_data_dir()` ignores a path that is no longer a directory (for example an unplugged external drive) and falls back to the default. `GET /settings` still reports the stale path.
- `PracticeForm.persist` PUTs back the whole object (`{...current, ...patch}`).
- `put_app_settings` calls `validate_data_dir(body.data_dir)` and rejects the stale path with 422.
- Changing the playback rate, repeat or record factor then shows "Không lưu được. Thử lại." forever, with nothing pointing at the cause.

**Fix:** Either validate `dataDir` in the PUT handler only when it differs from the stored or active value, or make `read_settings()` replace an unusable stored `dataDir` with `str(data_root())`:
```python
# settings_store.read_settings, after validate
if not Path(parsed.data_dir).is_dir():
    parsed = parsed.model_copy(update={"data_dir": str(data_root())})
```

### WR-04: `POST /lessons` accepts live, upcoming and unavailable videos and gives the wrong error

**File:** `services/audio/src/audio_service/routers/lesson.py:42-58`
**Issue:** `GET /videos/preview` rejects `live_status in LIVE_STATUSES` and non-open `availability`. `POST /lessons` does neither.
- For a livestream, `fetch_info` returns `duration_sec == 0.0`, so `resolve_range` raises and the user gets 422 `invalid_range` ("Khoảng thời gian không hợp lệ."), which is wrong.
- A direct API call, a retry or a stale preview can create a lesson for a `needs_auth` or private video that then fails at the download stage.

**Fix:** Factor the live and availability checks from `media.preview_video` into a shared helper and call it in `create_lesson` before `resolve_range`:
```python
if info.live_status in LIVE_STATUSES:
    raise ApiErrorException(422, "live_video", VIDEO_UNAVAILABLE_MESSAGE)
if info.availability not in _OPEN_AVAILABILITY:
    raise ApiErrorException(404, "video_unavailable", VIDEO_UNAVAILABLE_MESSAGE)
```

### WR-05: No server-side cap on lesson range length (OOM risk on the 8 GB target)

**File:** `services/audio/src/audio_service/lesson/pipeline.py:183-203` (called from `routers/lesson.py:56`)
**Issue:** `resolve_range` only enforces `0 <= start < end <= duration`. The UI shows only a soft warning above 5 minutes (`RangePicker.tsx`), and the API accepts any range, including a full hour.
- Demucs on a 44.1 kHz stereo float32 slice plus whole-file reads in `read_audio` for that range can exceed memory on the 8 GB machine described in the pipeline comments.
- The model worker runs inside the API process, so an OOM kill takes the whole service down and interrupts every other lesson.

**Fix:** Add a hard maximum (a constant, for example `MAX_RANGE_S`, chosen by Liam since it is a product threshold) in `resolve_range` and map it to `invalid_range`. Alternatively document the absence of a cap as an accepted risk in an ADR.

### WR-06: `_real_separate` / `_warm_demucs` can raise `UnboundLocalError` that hides the real failure

**File:** `services/audio/src/audio_service/lesson/pipeline.py:84-93` (same pattern in `system_status.py:123-128`)
**Issue:** After an MPS failure the code does `del separator`, then `separator = separate.load_separator("cpu")`. If the CPU load raises, the `finally` runs `del separator` on an unbound name and raises `UnboundLocalError`, replacing the original exception. The user-facing message is the generic unexpected-error text either way, but the log shows `UnboundLocalError` as the cause (the real error appears only as chained context).

**Fix:** Do not `del` before reassigning. Use a sentinel and guard the cleanup:
```python
separator: Separator | None = separate.load_separator(device)
try:
    ...
finally:
    separator = None
    separate.free_accelerator_memory()
```

### WR-07: `DownloadError` is always reported as "limited by region, private or downloads disabled"

**File:** `services/audio/src/audio_service/lesson/pipeline.py:308-309` (message at line 52)
**Issue:** yt-dlp raises `DownloadError` for network drops, HTTP 429/5xx, merge failures and format-not-available, as well as for the restricted-video cases. All of them are shown as `DOWNLOAD_BLOCKED_MESSAGE`. A transient network error then tells the user the video is blocked, and "Thử lại" looks pointless.

**Fix:** Keep the specific message only for known restriction signals (inspect `exc.msg` / `exc.exc_info` for private, unavailable, geo-restricted, sign-in required), and use a neutral "Không tải được video, kiểm tra mạng rồi Thử lại" otherwise. Keep the raw text out of `lesson.json`, as is done today.

### WR-08: Retrying a failed lesson bypasses the duplicate-lesson rule

**File:** `services/audio/src/audio_service/lesson/jobs.py:156-177` (rule at `routers/lesson.py:62-75`)
**Issue:** The duplicate check ignores `failed` lessons, so a user can create a new lesson for the same video and range while an old one is failed. `retry_lesson` has no such check. Retrying the old one yields two non-failed lessons with identical `(videoId, range)`. Both are processed, doubling the heavy work, and the library shows duplicates that `POST /lessons` was designed to prevent.

**Fix:** In `retry_lesson`'s `rebuild`, or in the router before calling it, scan `store.iter_lessons()` under `_create_lock` for another non-failed lesson with the same `(video_id, range)` and raise `ApiErrorException(409, "duplicate_lesson", ..., lesson_id=...)`.

## Info

### IN-01: Stale `lastError` can show the wrong error panel

**File:** `apps/web/lib/player/playerMachine.ts:214-215` (UI choice at `PracticeRoom.tsx:438-451`)
**Issue:** `micFailed` sets `lastError: "mic"` and `sampleFailed` sets `"sample"`, and neither is cleared on leaving the `error` state. If a segment B has `lastError === "mic"` from an earlier failure and the user returns to segment A that holds a *failed upload*, entering `error` through `backToRecordingState` or `LISTEN_*` renders the mic-error panel instead of the upload-error panel.
**Fix:** Clear `lastError` on `RECORD`/`PLAY` entry and on `goTo`/`goNext`/`goPrev`, or store the error kind per recording rather than globally.

### IN-02: `_store_eval_clip` failure leaves an already-counted attempt row

**File:** `services/audio/src/audio_service/routers/attempts.py:200-205`
**Issue:** `create_attempt` inserts the attempt row first and only then copies the eval clip. If the copy raises `OSError`, the client gets 500 while the DB already holds a voiced attempt. A client retry then creates a second one and inflates `voicedAttempts`. The web client currently always sends `saveForEval=false`, so this is latent.
**Fix:** Either store the clip before `insert_attempt` (using the next attempt number computed under the same lock), or catch `OSError` around `_store_eval_clip`, return 201 with `savedForEval=false`, and let the client use the PUT route.

### IN-03: `dotenv_values` can raise on a non-UTF-8 `.env`, breaking `/system/status`

**File:** `services/audio/src/audio_service/secrets_env.py:51`
**Issue:** Only `OSError` is caught. A `.env` with invalid bytes raises `UnicodeDecodeError` (a `ValueError`). `get_openai_key()` is called from `build_status()` (endpoint documented as "Luôn 200") and from the translate route, so both return 500.
**Fix:** `except (OSError, ValueError): return None`.

### IN-04: `load_ppg_model` uses `from_pretrained` without `local_files_only`, unlike `load_inv_vocab`

**File:** `services/audio/src/audio_service/lesson/features.py:62-63` (compare `lesson/ipa.py:105`)
**Issue:** The IPA vocab is loaded with `local_files_only=True`, but the PPG model and extractor are loaded from the hub client in the default mode. Offline, or on a flaky network, each load can stall on connection retries before falling back to the cache. That conflicts with the "app never fetches models itself" claim in `system_status.py`.
**Fix:** Pass `local_files_only=True` to both `from_pretrained` calls, after confirming `ensure_hf_snapshot` guarantees the cache is complete.

### IN-05: `safeThumbnailUrl` accepts any https host

**File:** `apps/web/lib/lessonView.ts:163`
**Issue:** T-02-21 intends a safe image source, but any `https://` URL from `lesson.json` or the preview is rendered as `<img src>`. A tampered or odd thumbnail host leaks the user's IP and referrer. The risk is low because the value comes from yt-dlp metadata.
**Fix:** Restrict to YouTube image hosts (`i.ytimg.com`, `i9.ytimg.com`) and add `referrerPolicy="no-referrer"` on the `<img>`.

### IN-06: Duplicated helpers across web components

**File:** `apps/web/components/ResultActionBar.tsx:16,35`, `apps/web/components/PlayerControls.tsx:46,51`, `apps/web/components/PracticeRoom.tsx:107`, `apps/web/lib/player/shortcuts.ts:107`; `readSavedDeviceId` in `lib/audio/recorder.ts` and `components/MicSection.tsx`
**Issue:** `topLevelState` exists four times and `asPlayerEvent` twice, and `RATE_OPTIONS` / `RECORD_FACTOR_OPTIONS` are redefined in `PracticeRoom.tsx`, `PlayerControls.tsx` and `lib/settingsForm.ts`. The copies can drift apart, for example if a new top-level state is added.
**Fix:** Export one `topLevelState` and `asPlayerEvent` from `lib/player/shortcuts.ts`, export `readSavedDeviceId` from `recorder.ts`, and import the option lists from `settingsForm.ts`.

### IN-07: Dead exports and an unused UI component

**File:** `apps/web/components/ui/slider.tsx` (no importer), `apps/web/lib/time.ts:94` (`clampThumb`, referenced only by tests), `apps/web/lib/settingsForm.ts:37` (`optionLabel`, referenced only by tests)
**Issue:** `RangePicker` uses the Radix primitive directly, so the `Slider` wrapper and `clampThumb` are unused in production code. The slider's keyboard behaviour comes from Radix, not from `clampThumb`.
**Fix:** Delete the unused wrapper and helpers, or switch `RangePicker` to the shared `Slider` and drop the duplication.

### IN-08: Attempt label can show the previous count until progress refetches

**File:** `apps/web/components/PracticeRoom.tsx:491`
**Issue:** `attemptLabel` is taken from `voicedAttempts` (from the progress query). On entering `reviewing` the invalidation is still in flight, so the second attempt briefly reads "Đã ghi lượt 1" and then flips to 2.
**Fix:** Optimistically bump the cached progress for the segment on `scoring -> reviewing`, or derive the label from `recording.attempt` when it is a voiced upload.

### IN-09: Timing-based assertions in tests

**File:** `services/audio/tests/test_jobs.py:106,111`, `test_pipeline.py:423`, `test_system_status.py:153,180`, `test_download.py:275`, `test_lessons_api.py:144`
**Issue:** Several tests order threads with `time.sleep(0.02-0.2)` ("bài nộp đầu tải xong SAU hai bài còn lại" depends on a 150 ms sleep). They will flake under CI or machine load.
**Fix:** Replace sleeps with `threading.Event` handshakes so ordering is deterministic.

---

_Reviewed: 2026-10-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
