---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 19
subsystem: testing
tags: [smoke, job-runner, concurrency, uvicorn, httpx, adr, uat, race-condition]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-03 job runner and model gate; 02-07 per-video lock and H.264 download; 02-10 attempts; 02-12 range stems and IPA; 02-15 extend-end; 02-16 translation; 02-11 settings and key; 02-17/02-18 UI"
provides:
  - "scripts/smoke_jobs.py + make smoke-jobs: two lessons created back to back over HTTP against the real API on a temp DATA_DIR with no OPENAI_API_KEY; prints a status timeline and JOBS OK / JOBS FAILED"
  - "Fix: audio extraction per video now runs under the video lock (race found by the smoke)"
  - "ADR docs/decisions/0005-job-runner-attempts-settings-p1.md"
  - "Consolidated end-of-phase UAT checklist (below)"
affects: [verify-work, ship, phase-3]

estimate:
  tokens: 60000
  raw_tokens: 60000
  tasks: 2
  confidence: low

actuals:
  tokens: 9000
  tasks: 2
  commits: 4

plan_head_before: f5426aac306e76378a41ccfe86f4b5f5a29cd120
plan_head_after: 5f74b59087498daf866111c095c11bbdd1d98a8b

tech-stack:
  added: []
  patterns:
    - "Smoke harness isolates itself: DATA_DIR, SHADOWENGLAB_CONFIG_DIR and SHADOWENGLAB_ENV_FILE are set to a temp dir before audio_service is imported, OPENAI_API_KEY is popped, server bound to 127.0.0.1 on a free port, temp dir removed in finally"
    - "Verdict logic is a pure function (check_timeline) unit-tested without models; the model run itself is the make target"
    - "Any file written per videoId must be written under download.video_lock"

key-files:
  created:
    - scripts/smoke_jobs.py
    - services/audio/tests/test_smoke_jobs.py
    - docs/decisions/0005-job-runner-attempts-settings-p1.md
  modified:
    - Makefile
    - CLAUDE.md
    - services/audio/src/audio_service/lesson/pipeline.py
    - services/audio/src/audio_service/lesson/download.py
    - services/audio/tests/test_pipeline.py
    - scripts/smoke_lesson.py

key-decisions:
  - "Smoke asserts exactly the four plan conditions; lesson 2 'left queued for downloading' is read as: some poll shows lesson 2 downloading while lesson 1 is not ready"
  - "Hard os._exit at the end of the script (after cleanup) so leftover model/download threads on failure or timeout cannot keep the process alive; side effect is a harmless resource_tracker 'leaked semaphore' warning"
  - "make smoke END=300 BUDGET=300 was run on a fresh DATA_DIR (cold: download + Demucs + Whisper + PPG) so criterion 1 is measured as the worst case"
  - "EXTEND_MAX_MS = 3000 and TRANSLATE_MODEL = gpt-6-luna (reasoning.effort none) recorded in ADR 0005; the 3000 cap is flagged there as pending Liam's confirmation"

requirements-completed: [LES-03, LES-05, SET-02, PLY-07]

coverage:
  - id: D1
    description: "make smoke-jobs: two lessons through the real API, no key, never two in a model step at once, GET /lessons < 1 s throughout, both ready"
    requirement: "LES-03"
    verification:
      - kind: integration
        ref: "make smoke-jobs -> JOBS OK (second run, after the race fix)"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_smoke_jobs.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "A 5-minute video becomes a ready lesson in under 5 minutes with the Phase 2 pipeline (IPA, range stems, D-21 sentence heuristic)"
    requirement: "LES-05"
    verification:
      - kind: integration
        ref: "make smoke END=300 BUDGET=300 (fresh DATA_DIR) -> BUDGET OK: 102.9 s <= 300.0 s, SELF-CHECK OK"
        status: pass
    human_judgment: false
  - id: D3
    description: "The app works with no OPENAI_API_KEY (lessons are created and reach ready without it)"
    requirement: "SET-02"
    verification:
      - kind: integration
        ref: "make smoke-jobs (OPENAI_API_KEY removed from the environment, empty temp .env)"
        status: pass
    human_judgment: true
    rationale: "The pipeline half is proven; the yellow banner, disabled Dịch tooltip and S8 flow without a key are UI and need the SC4 pass in the UAT"
  - id: D4
    description: "Two lessons of one video no longer race on audio.wav.part"
    requirement: "LES-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_pipeline.py#test_two_lessons_of_one_video_extract_the_audio_once"
        status: pass
    human_judgment: false
  - id: D5
    description: "ADR 0005 records the P1 architecture decisions and CLAUDE.md lists make smoke-jobs"
    requirement: "LES-03"
    verification:
      - kind: other
        ref: "grep acceptance criteria on docs/decisions/0005-job-runner-attempts-settings-p1.md and CLAUDE.md; make test (822 passed); make lint (exit 0)"
        status: pass
    human_judgment: true
    rationale: "Liam must read the ADR (especially the EXTEND_MAX_MS flag and the translation section); grep only proves the sections exist"
  - id: D6
    description: "Success criteria 3 and 5 (30 sentences mouse-only and keyboard-only in Chrome; UI matches docs/design) plus every flagged assumption from plans 02-01..02-18"
    requirement: "PLY-07"
    verification: []
    human_judgment: true
    rationale: "Defined as manual checks in ROADMAP/CONTEXT; microphone hardware, Chrome playback and visual fidelity cannot be automated. Checklist is in this SUMMARY"

duration: 40min
completed: 2026-10-08
status: complete
---

# Phase 2 Plan 19: Smoke for concurrent jobs, ADR 0005 and end-of-phase UAT Summary

**`make smoke-jobs` drives two lessons back to back through the real API with no key and prints JOBS OK (and, on its first run, exposed a real audio.wav.part race that is now fixed); the 5-minute lesson is ready in 102.9 s cold; ADR 0005 records the phase's architecture; one UAT checklist covers criteria 3 and 5.**

## Performance

- **Duration:** about 40 min (start time not captured; estimated from tool timestamps), most of it model runs
- **Completed:** 2026-10-08
- **Tasks:** 2 (Task 1 tracer, Task 2 auto)
- **Commits (measured, excluding this SUMMARY):** 4 from base `f5426aa`
- **Files:** 3 created, 6 modified

## Accomplishments

- `scripts/smoke_jobs.py` starts `uvicorn.Server(create_app())` in a thread on a free 127.0.0.1 port over a temp DATA_DIR / config dir / `.env`, removes `OPENAI_API_KEY`, POSTs two ranges of the smoke video (0:150 and 150:300) back to back, polls both every 0.5 s while timing `GET /lessons`, prints the timeline, and returns JOBS OK only if the four plan conditions hold. `make smoke-jobs` and the CLAUDE.md `## Lệnh` entry exist.
- The first run failed with `JOBS FAILED` for a real reason (see Deviations). After the fix the run passed.
- Criterion 1 re-measured with the final pipeline: `make smoke END=300 BUDGET=300` on a fresh DATA_DIR printed `BUDGET OK: 102.9 s <= 300.0 s` (budget 300 s).
- ADR 0005 written in the ADR 0003 format, with the two extra items from the dispatch: `TRANSLATE_MODEL = "gpt-6-luna"` with `reasoning.effort "none"` (Liam, 2026-10-08, 02-16 checkpoint) and `EXTEND_MAX_MS = 3000` flagged as planner-proposed and pending Liam's confirmation.

## Task Commits

1. **Task 1 (tracer): make smoke-jobs** - `e4f08dd` (feat), preceded by the bug fix it uncovered - `b2baf9c` (fix)
2. **Task 2: ADR 0005 and UAT checklist** - `d5faeb0` (docs); checklist is in this SUMMARY
3. **Lint gate** - `5f74b59` (style): `ruff format` on `scripts/smoke_lesson.py`

**Plan metadata:** the docs commit with this SUMMARY follows.

Tracer gate (end-of-phase mode, automated-only verify): `make smoke-jobs` was re-run after the fix and passed end to end before the ADR task started: "Tracer verified end-to-end - expanding".

## Smoke output 1: `make smoke-jobs` (second run, after the fix)

```
API: 127.0.0.1:52777, DATA_DIR tạm: /var/folders/.../shadowenglab-smoke-jobs-wufa75uo/data, không có OPENAI_API_KEY
LESSON_A=01M4CNV8GH6NKYT0JXJSCX2M3M 0-150 s
LESSON_B=01M4CNV8GPW56PSTETNTZM2PYQ 150-300 s
  t (s)  bài 1          bài 2          GET /lessons max (ms)
     1.4  downloading    downloading        11
     4.3  queued         queued             12
     4.8  separating     queued              3
    28.2  transcribing   queued             15
    53.7  analyzing      queued            117
    69.9  ready          queued             42
    76.5  ready          separating         58
    96.8  ready          transcribing       10
   118.7  ready          segmenting        151
   119.2  ready          analyzing           3
   127.5  ready          ready               6

bài A xong sau 69.9 s, bài B xong sau 127.5 s
GET /lessons chậm nhất: 151 ms (235 mẫu)
JOBS OK
```

Reading: lesson 2 left `queued` for `downloading` within the first poll (1.4 s), long before lesson 1 was `ready` (69.9 s); the model steps ran strictly one lesson after the other; the slowest `GET /lessons` was 151 ms over 235 polls; both lessons ended `ready` with no key. A harmless `resource_tracker: leaked semaphore` warning follows the final line (the script ends with `os._exit` after cleanup).

First run (before the fix), for the record:

```
FileNotFoundError: [Errno 2] No such file or directory: '.../videos/dUDi-F6eAvk/audio.wav.part' -> '.../audio.wav'
JOBS FAILED: bài B lỗi ở bước 'downloading': lỗi không mong đợi (xem log của make dev)
```

## Smoke output 2: `make smoke END=300 BUDGET=300` (fresh DATA_DIR, cold)

```
step              seconds
--------------  ---------
download             2.78
write                0.03
extract_audio        0.22
demucs              40.83
quality              0.08
resample             0.13
whisper             42.81
segment              0.00
ppg                 13.96
f0                   0.55
write_features       0.96
ipa                  0.02
--------------  ---------
total              102.37

range            0.0-300.0 s (300.0 s)
wall time        102.9 s
realtime factor  0.34x
nonVocalRatio    1.774e-02 (-17.5 dB) -> clean
segments         46

Phân bố độ dài câu
  số câu        : 46
  < 3 s         : 7
  3-8 s         : 39
  > 8 s         : 0
  median        : 4.06 s
  nhiều từ nhất : 18
SELF-CHECK OK
BUDGET OK: 102.9 s <= 300.0 s
```

The downloaded `video.mp4` is H.264 per `ffprobe` (real yt-dlp selector, no transcode needed for this video).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two lessons of one video raced on `audio.wav.part`**
- **Found during:** Task 1 (first `make smoke-jobs` run)
- **Issue:** both lessons wait on the same per-video download lock; when lesson 1 finishes downloading, lesson 2 returns from `download_video` at once and both enter `stage_download`'s `if not audio_path.exists(): extract_audio(...)`. Both ran ffmpeg into the same `audio.wav.part`; the slower one failed at `os.replace` with `FileNotFoundError` and the lesson ended `failed`. This is a real user-facing bug (two lessons from one video created back to back) that no fake-stage test covered.
- **Fix:** `stage_download` holds `download.video_lock(video_id)` around the check and the ffmpeg run (the second lesson then sees `audio.wav` and skips). `download.video_lock` is a public alias of the existing `_video_lock`.
- **Files modified:** `services/audio/src/audio_service/lesson/pipeline.py`, `services/audio/src/audio_service/lesson/download.py`, `services/audio/tests/test_pipeline.py` (new test `test_two_lessons_of_one_video_extract_the_audio_once`, reproduced the same `FileNotFoundError` before the fix)
- **Verification:** new test red then green; `pytest` 822 passed; `make smoke-jobs` JOBS OK
- **Committed in:** `b2baf9c`

**2. [Rule 2 - Missing critical] Unit tests for the smoke verdict logic**
- **Issue:** the four JOBS OK conditions are the plan's only automated check of criterion 2; a mistake in them would silently pass or fail the phase gate.
- **Fix:** verdict and timeline formatting are pure functions (`check_timeline`, `format_timeline`) with `services/audio/tests/test_smoke_jobs.py` (6 tests). File is outside `files_modified` and touches no sibling's files.
- **Committed in:** `e4f08dd`

**3. [Rule 3 - Blocking] `make lint` failed on a pre-existing format diff in `scripts/smoke_lesson.py`**
- **Issue:** `ruff format --check` flagged `scripts/smoke_lesson.py` (left by an earlier plan, 02-12 noted it). The plan-level verification requires `make lint` to exit 0.
- **Fix:** `ruff format` applied to that file only (formatting, no behaviour change).
- **Committed in:** `5f74b59`

---

**Total deviations:** 3 auto-fixed (1 Rule 1, 1 Rule 2, 1 Rule 3). **Impact:** the Rule 1 fix is a genuine bug found by the plan's own smoke, which is what this plan exists to do. No contract, schema, threshold or model changed.

### Environment notes (not deviations)

- The sandbox refuses commands that name the shared git dir, so the `gsd-plan-head-before-02-19` ledger file could not be written; `commits:` was measured with `git rev-list --count f5426aac..HEAD` (= 4 before this SUMMARY commit), same approach as 02-12 and 02-13.
- The worktree had no `node_modules` or venv; `pnpm install --frozen-lockfile` and `uv sync --project services/audio --frozen` were run from the lockfiles. No package added or changed (T-02-SC).
- `make smoke` writes into the DATA_DIR in use; the 5-minute run used a throwaway `DATA_DIR` under the scratchpad (removed afterwards), so Liam's `~/shadowenglab-data` was not touched by this plan.

## Issues Encountered

- `make smoke-jobs` output only appears at the end when stdout is redirected unless `PYTHONUNBUFFERED=1` is set (long runs under the stall watchdog were run that way).
- The orchestrator note about "live-video code on POST /lessons" (02-07): the create endpoint still answers 422 `invalid_range` for a live link, not `live_video`; S2 blocks live links through preview first. It is queued for UAT below, no change made.

## Known Stubs

None. No placeholder data flows to a UI in this plan's files.

## Threat Flags

None. T-02-51 mitigated: DATA_DIR, SHADOWENGLAB_CONFIG_DIR and SHADOWENGLAB_ENV_FILE point to a temp dir set before importing the service, the temp dir is removed in `finally` (verified: none left under `$TMPDIR` after the runs), server bound to `127.0.0.1`. T-02-SC: no package added, `uv run --frozen` only.

## User Setup Required

None.

## UAT checklist (end-of-phase, Chrome, `make dev`, no code edits during the session)

Run with `make dev` (not while editing code: `uvicorn --reload` restarts mark running jobs "bị gián đoạn", RESEARCH Pitfall 8). Items marked (SC) are ROADMAP success criteria 3, 4 and 5; the rest are the `human_judgment: true` and "not verified" items from plans 02-01..02-18. Write follow-ups into `docs/feedback.md`.

### A. Success criteria

- [ ] **SC3 mouse only:** practise 30 sentences end to end (hear sample, record, listen back, next) using only buttons and the transcript list. No dead end, no state where a button is greyed with no way out (note: in 02-09 the room was unusable until 02-14 provided the recorder; confirm it is not now).
- [ ] **SC3 keyboard only:** the same 30 sentences using only keys (`Space`, `R`, `←/→`, `O`, `M`, `B`, `I`, `T`); focus is never trapped in a dialog or input; Space never scrolls the page.
- [ ] **SC4 no key:** remove `OPENAI_API_KEY` from `.env`, restart `make dev`. Yellow banner shows and does not block; create a lesson and practise it; Dịch is `aria-disabled` with the `Cần OPENAI_API_KEY` tooltip; S8 can still paste a key. (`make smoke-jobs` already proved the pipeline half.)
- [ ] **SC5 design match:** compare S1, S2, S3 and S8 side by side with `docs/design/screens/` (S1-thu-vien, S2-tao-bai, S3-S4-phong-tap, S3-trang-thai-cau, S8-settings) in Chrome. Approved deviations G1-G24 and D-09 (the extra "Lưu clip cho eval" ghost button) are accepted. Include: header and Figtree text, Vietnamese diacritics, no box shadows (02-04), footer wrap at 1024 px (02-14), a 20-word sentence at 1280 px (02-09), 120-character title clamp and a long error message wrap on S1 (02-08).

### B. Recording, VAD and silence (flagged assumption A1)

- [ ] With the real mic: a quiet but spoken attempt counts as voiced (`Lượt k` increments); silence or a tap on the desk does not (`noVoice` panel, attempt still recorded).
- [ ] Client auto-stop on 1 s of silence after speech (`SPEECH_MARGIN_DB 10`, `SILENCE_MS 1000`, `NOISE_WINDOW_MS 300` in `apps/web/lib/audio/level.ts`); server VAD (`vad.py`: floor −50 dB, margin 12 dB, ≥ 150 ms, run ≥ 100 ms). Also a recording that is loud for >90% of its length (no lead-in silence) raises the noise floor (02-10 note).
- [ ] Mic light turns off after leaving S3 and after S8 `Thử micro`; the mic device chosen in S8 is used on S3; `Chọn micro` link opens S8.
- [ ] Stop the API during an upload: the persistent toast appears with `Thử lại`, `M` still plays the kept recording, `Thử lại` re-sends it.
- [ ] `Lưu clip cho eval` once: a `.wav` and `.json` appear in `DATA_DIR/eval_clips/`, the button shows `Đã lưu clip`, no new attempt is created.

### C. IPA, translation, edit, extend

- [ ] **IPA glyphs in Noto Sans (RESEARCH A6):** press `I`; no tofu boxes for `ə ɪ ʊ ɑ θ ð ŋ ʃ ʒ` etc. If any appear, adding an IPA-capable font is a new design decision for Liam.
- [ ] **IPA hide rate:** about 30% of words show `—` by design (D-20: 409 of 580 words had IPA on the smoke video). Acceptable? A 20-word IPA line wraps properly; the all-uncertain fallback `Chưa nhận dạng chắc câu này.` reads well.
- [ ] **Translation (real key):** `T` / `Dịch` once with a real `OPENAI_API_KEY`: one Vietnamese spot-check on 3-4 sentences for naturalness (gpt-6-luna, effort none; no eval was run). Cached sentences show with no key. Note: `Dịch` re-translates an edited sentence automatically when on (one API call per edit).
- [ ] **Sửa câu:** edit and cancel (Enter / Esc), edit with same word count and with a different count; translation clears; reload keeps the edit.
- [ ] **Mất chữ cuối?:** press on a sentence whose last word is clipped; replay includes the extra 0.3 s; try several presses; judge the 300 ms step and the 3000 ms cap (ADR 0005 5.7, pending Liam's confirmation); with another lesson processing, the press answers 503 busy after waiting and the extension still holds.

### D. Video, download and caches

- [ ] **Real yt-dlp + Chrome seeking (D-19):** a freshly created lesson plays in Chrome, seeking works, audio starts about 150 ms before and ends about 150 ms after the sentence without an audible cut, 0.75x keeps the pitch. (The H.264 result of the real selector was confirmed with `ffprobe` in this plan; playback in Chrome was not.)
- [ ] **AV1/VP9 caches from Phase 1:** open a lesson created in Phase 1 (a cached `video.mp4` may be AV1/VP9); if it does not play, `Tải lại video` fixes it. Also delete `video.mp4` by hand and confirm S3 shows `Không phát được video của bài này.` and `Tải lại video` restores playback.
- [ ] **Live-video code on POST /lessons:** `POST /lessons` for a live link still returns 422 `invalid_range` (S2 blocks live via preview first). Decide whether the create endpoint should return `live_video`.
- [ ] **S2 checks:** channel link, invalid link, private/removed video, a 3-minute and a 20-minute video (range picker only above 6 minutes, default 00:00-05:00), thumbs by mouse and keyboard (arrow 1 s, Shift+arrow 10 s), typing `99:99`, creating the same video twice (duplicate notice with `Mở bài đã có`), a failed create (toast with `Thử lại`).
- [ ] **S1 checks:** empty `DATA_DIR`, ready / processing / failed lessons with live 2 s polling, API stopped (backend banner with `Tải lại`), no key (yellow banner), mic denied banner, retry of an interrupted lesson (kill the API while a lesson is `separating`, restart, card shows `Bị gián đoạn…` and `Thử lại` works).

### E. Settings and models (S8)

- [ ] **Real warm-up (D-18):** on the 8 GB machine, `Model đang nạp…` clears, memory returns to baseline after warm-up, and creating a lesson right after `make dev` is acceptable while warm-up holds the model gate. Note the time it takes.
- [ ] **Real key check:** paste a real key in S8, `Kiểm tra` shows `Key hợp lệ · đã lưu`, `.env` has the key (mode 0600, other lines kept), the S1 banner disappears without restart; a wrong key shows the invalid message and writes nothing; offline shows the network message.
- [ ] **Data dir:** change the folder to a valid path (restart note `Khởi động lại make dev để áp dụng; dữ liệu cũ vẫn ở …`), to a missing path (`Thư mục không tồn tại hoặc không ghi được.`), and confirm nothing moves.
- [ ] **Practice defaults auto-save:** change rate, repeat and record time; `Đã lưu` appears; with the API stopped the select reverts and `Không lưu được. Thử lại.` appears.

### F. Copy strings not in UI-SPEC (gap copy added by executors; review once)

- [ ] `Bài này chưa sẵn sàng để tập.` (02-09, opening a lesson that is not ready, with `Tải lại` and `Thư viện`)
- [ ] `Không nới được câu này. Thử lại.` (02-18, non-API failure of `Mất chữ cuối?`)
- [ ] Footer `Bản gốc` is disabled while playing, recording or processing (02-14; UI-SPEC says always enabled), so a button is disabled exactly where its key is ignored
- [ ] Backend fixed messages in `routers/segments.py` (e.g. `Đã nới tối đa cho câu này.`, `Đang xử lý bài khác, thử lại sau.`, `Bài này tạo bằng bản cũ, hãy tạo lại bài để nới câu.`) and `routers/translate.py` (`Không dịch được câu này. Bấm Dịch để thử lại.`)

## Next Phase Readiness

- Phase 2 automated criteria 1, 2 and 4 are proven with real models and network; 3 and 5 wait for the checklist above.
- Phase 3 must read ADR 0005: score against `words`, not `Segment.text`; `attempts` gets score columns; the upload response becomes `ScoreResult`.
- Open for Liam: confirm or change `EXTEND_MAX_MS = 3000`; read the UAT results into `docs/feedback.md`; decide on the live-video code at `POST /lessons`.

## Self-Check: PASSED

- FOUND: scripts/smoke_jobs.py, services/audio/tests/test_smoke_jobs.py, docs/decisions/0005-job-runner-attempts-settings-p1.md, Makefile (`smoke-jobs:`), CLAUDE.md (`make smoke-jobs`)
- FOUND commits (ancestors of HEAD): b2baf9c, e4f08dd, d5faeb0, 5f74b59
- Acceptance criteria re-run: script contains JOBS OK / JOBS FAILED / OPENAI_API_KEY / SHADOWENGLAB_CONFIG_DIR / uvicorn.Server; ADR has Bối cảnh, Quyết định, Hệ quả and D-01, D-02, D-03, D-10, D-11, D-12, D-18, D-19, D-20, D-21, D-23, attempts, TRANSLATE_MODEL
- Plan verification: `make smoke-jobs` JOBS OK; `make smoke END=300 BUDGET=300` BUDGET OK; `make test` 822 passed (exit 0); `make lint` exit 0
- STATE.md and ROADMAP.md intentionally not touched (orchestrator owns them)

---
*Phase: 02-p1-t-o-b-i-v-tr-nh-ph-t*
*Completed: 2026-10-08*
