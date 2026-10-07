---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 07
subsystem: api
tags: [fastapi, fileresponse, range, yt-dlp, ffmpeg, h264, threading, adr, tdd]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-01 contract (VideoPreview, ApiError codes); 02-03 store helpers, ApiErrorException, PipelineDeps, media router shell"
provides:
  - "GET /lessons/{id}/video: self-hosted video.mp4 with Range (206/416) for ready lessons"
  - "GET /videos/preview?url=: VideoPreview with channel_url / invalid_url / video_unavailable / live_video errors and existingLessonId"
  - "POST /lessons/{id}/video/reload (204): delete + re-download, old file restored on failure"
  - "download.py: VideoInfo.channel/live_status/availability, avc1+mp4a selector, probe_video_codec, ensure_h264, per-video RLock, reload_video"
  - "urls.is_channel_url"
  - "ADR 0004 (D-17, D-19 codec); product.md M2 + section 8 and PLY-01 no longer promise an IFrame fallback"
affects: [02-13, 02-14, 02-16, 02-19]

actuals:
  tokens: 36000
  tasks: 3
  commits: 5

plan_head_before: 57cd5d456e98a0b3a8ee370782f8e5fd2d4f211b
plan_head_after: 4ddd76105ec1f5b6c496c53df68651015b6435bf

tech-stack:
  added: []
  patterns:
    - "Video endpoints read videoId only from lesson.json and answer with fixed Vietnamese ApiError messages; yt-dlp/ffmpeg text is logged, never returned"
    - "Download into video.dl.*, transcode, then os.replace to video.mp4 under a per-video RLock (partial file never visible)"
    - "reload_video moves the old file to video.mp4.old and restores it when the download fails"

key-files:
  created:
    - services/audio/tests/test_media_api.py
    - services/audio/tests/test_download.py
    - docs/decisions/0004-bo-iframe-video-tu-host.md
  modified:
    - services/audio/src/audio_service/routers/media.py
    - services/audio/src/audio_service/lesson/download.py
    - services/audio/src/audio_service/lesson/urls.py
    - services/audio/tests/test_urls.py
    - services/audio/tests/test_api.py
    - docs/product.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Preview/reload use app.state.deps.fetch_info/download_video (same injection as POST /lessons) rather than monkeypatching download.fetch_info; behavior is identical and tests inject fakes via create_app(deps=...)"
  - "Livestream/upcoming videos have no duration: fetch_info returns duration 0 with live_status set and does NOT cache info.json (live status changes over time); any other missing duration still raises"
  - "Per-video lock is an RLock because reload_video holds it while calling download_video, which takes it again"
  - "reload_video renames the old file to video.mp4.old and restores it on a failed download, so a network failure never costs Liam a working video (plan said delete-then-download; the file is absent at download time either way)"
  - "Unexpected (non-DownloadError) failures in preview/reload map to 502 upstream_error with a fixed message; only DownloadError maps to video_unavailable"

patterns-established:
  - "Fixed S2 copy lives as module constants in routers/media.py (CHANNEL_URL_MESSAGE, INVALID_URL_MESSAGE, VIDEO_UNAVAILABLE_MESSAGE)"

requirements-completed: [PLY-01, LES-01, LES-04]

coverage:
  - id: D1
    description: "S3 can seek in the self-hosted video: Range request returns 206 + Content-Range, unsatisfiable range 416, not-ready or missing file 404 ApiError, videoId never from the client"
    requirement: "PLY-01"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_media_api.py#test_video_range_request_returns_206_with_content_range"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_media_api.py#test_video_unsatisfiable_range_returns_416"
        status: pass
    human_judgment: false
  - id: D2
    description: "S2 preview returns VideoPreview or a precise fixed-text error for channel, invalid, unavailable, live links, plus existingLessonId"
    requirement: "LES-01"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_media_api.py#test_preview_channel_link_is_400_channel_url"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_media_api.py#test_preview_flags_existing_lesson_for_default_range"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_urls.py#test_is_channel_url_true_for_channel_links"
        status: pass
    human_judgment: false
  - id: D3
    description: "New downloads select avc1/mp4a, are transcoded to H.264/AAC when needed, and video.mp4 is only published when complete; same-video downloads serialized, different videos parallel"
    requirement: "LES-04"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_download.py#test_ensure_h264_transcodes_av1_to_temp_then_replaces"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_download.py#test_two_threads_downloading_the_same_video_download_once"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_download.py#test_different_videos_download_in_parallel"
        status: pass
    human_judgment: false
  - id: D4
    description: "POST /lessons/{id}/video/reload re-downloads a ready lesson's video (204), 409 when not ready, 502 on failure"
    requirement: "PLY-01"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_media_api.py#test_reload_redownloads_after_removing_the_old_file"
        status: pass
    human_judgment: false
  - id: D5
    description: "ADR 0004 recorded and product.md / REQUIREMENTS no longer promise an IFrame fallback"
    requirement: "PLY-01"
    verification:
      - kind: other
        ref: "test -s docs/decisions/0004-bo-iframe-video-tu-host.md && grep -q D-17 ... && grep -q 'ADR 0004' docs/product.md .planning/REQUIREMENTS.md"
        status: pass
    human_judgment: true
    rationale: "Wording of the ADR and the product.md edits needs Liam's read; a grep only proves they exist"
  - id: D6
    description: "A real YouTube video downloads as H.264/AAC through the real yt-dlp selector and plays in Chrome with seeking"
    requirement: "LES-04"
    verification: []
    human_judgment: true
    rationale: "All tests use fake yt-dlp/ffmpeg (no network); the real selector result and Chrome playback were not exercised here (UAT on Chrome, D-19)"

duration: multi-step single session
completed: 2026-10-07
status: complete
---

# Phase 2 Plan 07: Video serving, link preview and H.264 downloads Summary

**Lesson videos are served with HTTP Range from the self-hosted file, S2 link preview answers with precise fixed-text errors (channel, invalid, private/removed, live) and duplicate detection, new downloads are H.264/AAC (selector plus ffprobe/ffmpeg fallback, per-video lock, no partial `video.mp4`), a broken file can be reloaded, and ADR 0004 drops the IFrame fallback.**

## Performance

- **Tasks:** 3 of 3 (Task 1 tracer, Tasks 2 and 3 TDD with RED then GREEN commits)
- **Files modified:** 10 (3 new, 7 modified)
- **Tests:** `uv run --project services/audio --frozen pytest services/audio/tests -q` -> 476 passed; `ruff check` and `ruff format --check` clean

## Accomplishments

- Tracer (Task 1): `GET /lessons/{id}/video` returns `FileResponse(video.mp4, media_type="video/mp4")` for a ready lesson: 200 + `accept-ranges: bytes`, `Range: bytes=0-99` gives 206 + `content-range: bytes 0-99/4096` + 100 bytes, `bytes=9000-` gives 416, queued lesson / missing file / unknown or malformed id give 404 `not_found` with fixed text; the tmp DATA_DIR path never appears in a response. ⚡ Tracer verified end-to-end (12 tests) before expansion.
- `GET /videos/preview?url=`: channel link (`/@`, `/channel/`, `/c/`, `/user/`) -> 400 `channel_url`; any other bad link -> 400 `invalid_url`; `DownloadError` or availability outside {None, public, unlisted} -> 404 `video_unavailable`; `is_live` / `is_upcoming` -> 422 `live_video`; other failures -> 502 `upstream_error`. All messages are the fixed UI-SPEC S2 text; a test proves yt-dlp exception text and paths are never returned. `url` longer than 2048 -> 422 `invalid_request`.
- `existingLessonId`: set when a non-failed lesson has the same videoId and `pipeline.default_range(durationSec)` (whole video <= 360 s, else 0-300 s); absent for failed lessons, other ranges, other videos.
- `fetch_info` carries `channel`, `live_status`, `availability` (cache keys `channel`, `liveStatus`, `availability` written only when present); old `info.json` without them reads fine.
- Downloads: `_FORMAT` starts with `bv*[height<=480][vcodec^=avc1]+ba[acodec^=mp4a]/...` and keeps the old selector last; `probe_video_codec` (ffprobe, timeout 30) and `ensure_h264` (`ffmpeg -nostdin ... libx264 ... aac`, temp file then `os.replace`, timeout 600) are argv lists with no shell; `download_video` stages into `video.dl.*` and only renames to `video.mp4` after the codec check; a failed transcode leaves the folder empty.
- Concurrency (PLY-01): per-video `RLock` around cache check + download; test proves two threads on one id download once and two ids run in parallel (a `Barrier(2)` would time out if serialized).
- `POST /lessons/{id}/video/reload` -> 204; not ready 409 `invalid_state`; unknown id 404; `DownloadError` 502 `video_unavailable`; other errors 502 `upstream_error`. `audio.wav` / stems untouched; the old video is restored if the re-download fails.
- ADR 0004 written (D-17 + D-19 codec); `docs/product.md` M2 and section 8 row and `.planning/REQUIREMENTS.md` PLY-01 no longer mention an IFrame fallback.

## Task Commits

1. **Task 1 (tracer): GET /lessons/{id}/video with Range** - `8393f34` (feat)
2. **Task 2 RED: failing tests for preview, channel URLs, info fields** - `7a8222a` (test)
3. **Task 2 GREEN: GET /videos/preview** - `ff4e220` (feat)
4. **Task 3 RED: failing tests for H.264 download, lock, reload** - `d10bcac` (test)
5. **Task 3 GREEN: H.264/AAC downloads, lock, reload, ADR 0004, doc edits** - `4ddd761` (feat)

No REFACTOR commits were needed. Plan metadata: the SUMMARY docs commit follows this file.

## TDD Gate Compliance

- **RED (Task 2):** `7a8222a`. `pytest test_urls.py test_media_api.py test_download.py` -> 54 failed, 72 passed. Failures were the target behavior: `NotImplementedError` from the `is_channel_url` stub (parametrized true/false cases), 404/405 from the missing `/videos/preview` route, `VideoInfo` missing `channel`/`live_status`/`availability`. Semantic assessment: tests executed and failed on the planned absence of the feature, not on syntax/import/fixture faults. `gsd_run check tdd-red-evidence` was not applied (plan is `type: execute` with `tdd` tasks, pytest output is not one of its supported report formats).
- **RED (Task 3):** `d10bcac`. 21 failed, 45 passed: `AttributeError` for the missing `download.subprocess`, `_video_lock`, `probe_video_codec`, `ensure_h264`, `reload_video`, `_FORMAT` assertion on the old selector, and 404 from the missing reload route.
- **GREEN:** `ff4e220` and `4ddd761`; full audio suite 476 passed.
- **REFACTOR:** none.

## Decisions Made

See `key-decisions` above. The ADR itself records D-17 and D-19 (codec part) for the project.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Empty-shell test broke when the media router got routes**
- **Found during:** Task 2 (full suite run)
- **Issue:** `tests/test_api.py::test_p1_router_shells_exist_and_are_mounted_empty[media]` asserts every P1 shell is empty; `media` now has routes (broken since the Task 1 commit `8393f34`).
- **Fix:** removed `"media"` from that parametrize list (one token on one line). Sibling plans filling other shells (02-06, 02-08, 02-09) will edit the same line, so expect a trivial merge conflict there.
- **Files modified:** `services/audio/tests/test_api.py`
- **Committed in:** `ff4e220`

**2. [Rule 2 - Missing critical] Livestream/upcoming videos made `fetch_info` raise before preview could report `live_video`**
- **Found during:** Task 2 (design for the `live_video` truth)
- **Issue:** `fetch_info` raised `RuntimeError` whenever yt-dlp returned no duration, which is exactly the case for live/upcoming videos, so preview would have answered 502 instead of 422 `live_video`.
- **Fix:** live/upcoming statuses return `VideoInfo` with `duration_sec=0.0` and `live_status` set, and are not cached; other missing durations still raise.
- **Files modified:** `services/audio/src/audio_service/lesson/download.py`, test in `test_download.py`
- **Committed in:** `ff4e220`

**3. [Rule 2 - Missing critical] Failed reload no longer destroys a working video**
- **Found during:** Task 3
- **Issue:** the plan's "delete video.mp4 then download" would lose a playable file when the network is down.
- **Fix:** `reload_video` renames the old file to `video.mp4.old` under the video lock, restores it on any failure, deletes it on success. The old file is still absent when the download runs (test asserts it).
- **Files modified:** `services/audio/src/audio_service/lesson/download.py`
- **Committed in:** `4ddd761`

**4. [Plan interpretation] Fakes injected via `PipelineDeps`, not monkeypatch of `download.fetch_info`**
- Routers use `request.app.state.deps` like the existing `POST /lessons`; the behavior under test is the same and needs no module-level patching. Tests use `with TestClient(create_app(deps=...))` so the lifespan sets `app.state.deps`.

---

**Total deviations:** 3 auto-fixed (1 bug, 2 missing critical) plus 1 interpretation note.
**Impact on plan:** all necessary for correctness; no scope or contract change (no new type, field, code or column).

## Issues Encountered

None blocking. The tool sandbox rejected some compound shell commands, so commands were split; no effect on the result.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-02-17 (videoId only from lesson.json, `video_asset_path` containment, ready-only, bad-id tests), T-02-18 (URL allow-list and `is_channel_url` before yt-dlp, yt-dlp only gets `canonical_watch_url`), T-02-19 (per-video lock, ffprobe/ffmpeg timeouts, argv lists) and T-02-20 (fixed messages, tests that yt-dlp/ffmpeg text and paths never leak) are implemented and tested. T-02-SC: only `uv sync --frozen`, no package added.

## User Setup Required

None - no external service configuration required.

## Notes for follow-up plans

- `POST /lessons` (02-03) still resolves a live video to `duration 0` and answers 422 `invalid_range` instead of `live_video`; the S2 flow calls preview first so the dialog blocks live links, but the create endpoint's own error code for that case is for 02-06 or later to decide.
- Old Phase 1 caches may hold AV1 `video.mp4`; "Tải lại video" (reload) fixes them one by one.
- The real yt-dlp selector (135+140) and Chrome playback are verified only by fakes here; the Chrome UAT in verify-work should exercise a real download and seeking in S3.

## Next Phase Readiness

S3 (02-14 or later) can point `<video src>` at `/lessons/{id}/video`, S2 (02-13) can call `/videos/preview`, and the "Tải lại video" button can call `POST /lessons/{id}/video/reload`. ADR 0005 (job runner and others, plan 02-19) is still to be written.

## Self-Check: PASSED

- FOUND: services/audio/tests/test_media_api.py, services/audio/tests/test_download.py, docs/decisions/0004-bo-iframe-video-tu-host.md, services/audio/src/audio_service/routers/media.py
- FOUND commits: 8393f34, 7a8222a, ff4e220, d10bcac, 4ddd761 (all ancestors of HEAD; `git rev-list --count` from the base = 5)
- Acceptance greps pass (urls/download/media symbols, ADR + doc greps); full audio suite 476 passed; ruff clean

---
*Phase: 02-p1-t-o-b-i-v-tr-nh-ph-t*
*Completed: 2026-10-07*
