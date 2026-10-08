---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
verified: 2026-10-08T12:00:00Z
status: human_needed
score: 9/11 must-haves verified
covered_files:
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-01-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-01-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-02-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-02-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-03-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-03-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-04-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-04-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-05-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-05-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-06-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-06-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-07-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-07-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-08-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-08-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-09-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-09-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-10-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-10-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-11-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-11-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-12-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-12-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-13-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-13-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-14-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-14-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-15-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-15-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-16-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-16-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-17-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-17-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-18-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-18-SUMMARY.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-19-PLAN.md"
  - ".planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-19-SUMMARY.md"
  - "Makefile"
  - "apps/web/components/LessonCard.tsx"
  - "apps/web/components/PracticeRoom.tsx"
  - "apps/web/components/SystemBanners.tsx"
  - "apps/web/lib/audio/recorder.ts"
  - "apps/web/lib/lessonView.ts"
  - "apps/web/lib/player/playerMachine.ts"
  - "apps/web/lib/player/shortcuts.ts"
  - "docs/decisions/0005-job-runner-attempts-settings-p1.md"
  - "scripts/smoke_jobs.py"
  - "services/audio/src/audio_service/lesson/jobs.py"
  - "services/audio/src/audio_service/lesson/pipeline.py"
  - "services/audio/src/audio_service/routers/attempts.py"
  - "services/audio/src/audio_service/routers/lesson.py"
  - "services/audio/src/audio_service/routers/segments.py"
covered_digest: "v3:sha256:d2150fa8befa1740e5685fcec67f6ae1289233f3493d34ca5c840394b4ca0bc9"
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "LES-04 clause: pre-compute word-level prominence for each sentence (F0, energy and PPG are computed; prominence is not)"
    addressed_in: "Phase 3"
    evidence: "ADR 0003 D-04 (Liam, Phase 1): 'Word.prominence để trống ở P0, Phase 3 tính'; features.py header repeats it; Phase 3 requirement PRO-02 'prominence từng từ' and ROADMAP Phase 3 scope 'Lớp B (... prominence)'"
human_verification:
  - test: "SC3 mouse only: practise 30 sentences end to end in Chrome (hear sample, record, listen back, next) using only buttons and the transcript list"
    expected: "No dead end; no greyed button without a way out; every action reachable by a labelled 44-48 px button"
    why_human: "Manual criterion defined in ROADMAP/CONTEXT; needs a real microphone, Chrome playback and a human"
  - test: "SC3 keyboard only: the same 30 sentences using only Space, R, Left/Right, O, M, B, I, T"
    expected: "Focus never trapped in a dialog or input; Space never scrolls the page; the full loop completes"
    why_human: "Manual criterion; shortcut table and state-machine transitions are unit-tested but end-to-end keyboard flow with real media is not automatable here"
  - test: "SC5 UI fidelity: compare S1, S2, S3, S8 side by side with docs/design/screens (S1-thu-vien, S2-tao-bai, S3-S4-phong-tap, S3-trang-thai-cau, S8-settings) in Chrome"
    expected: "Matches design apart from approved deviations G1-G24 and D-09; Figtree and Vietnamese diacritics render; no box shadows; footer wrap at 1024 px; 20-word sentence at 1280 px"
    why_human: "Visual fidelity; 02-UI-REVIEW.md (21/24) was a code-only audit with no screenshots"
  - test: "SC4 UI pass without a key: remove OPENAI_API_KEY from .env, restart make dev"
    expected: "Yellow banner shows and does not block; a lesson can be created and practised; Dich is aria-disabled with the 'Can OPENAI_API_KEY' tooltip; S8 still accepts a key"
    why_human: "Pipeline half is proven by make smoke-jobs; banner/tooltip/S8 flow is UI"
  - test: "First-run microphone permission (review finding WR-01): clear the site's mic permission, press Space on a short sentence and take longer than the countdown to click Allow"
    expected: "The attempt is still recorded normally (or Liam accepts the behaviour); the recording window should not be consumed by the permission prompt"
    why_human: "Code reading shows the recordDelay timer starts when the recording state is entered, before getUserMedia resolves; browser permission prompt cannot be exercised by tests"
  - test: "Recording with the real mic: quiet-but-spoken attempt counts as voiced; silence or a tap does not; auto-stop after 1 s of silence; mic light off after leaving S3; upload failure toast with Thu lai keeps the recording; 'Luu clip cho eval' writes .wav + .json to DATA_DIR/eval_clips/"
    expected: "As stated; thresholds in level.ts and vad.py (flagged assumption A1) feel right"
    why_human: "Hardware and perceptual thresholds"
  - test: "Remaining 02-19 UAT groups C-F: IPA glyph rendering in Noto Sans (no tofu), real-key translation spot check, Sua cau, Mat chu cuoi? (300 ms step, 3000 ms cap pending Liam), real yt-dlp playback and seeking in Chrome, AV1/VP9 cache from Phase 1 plus 'Tai lai video', live-video code on POST /lessons, S2 and S1 edge cases, real warm-up on the 8 GB machine, real key check, data-dir change, gap-copy strings"
    expected: "Per checklist in 02-19-SUMMARY.md"
    why_human: "Real network, real key, real media and subjective copy review; Liam must also confirm EXTEND_MAX_MS = 3000"
---

# Phase 2: P1 · Tao bai va trinh phat Verification Report

**Phase Goal:** Liam tạo bài từ link YouTube và tập trọn một video theo từng câu, đến bước ghi âm (chưa chấm điểm).
**Verified:** 2026-10-08
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

All code paths for the goal exist, are substantive and are wired end to end, and every automated check passes. No must-have is FAILED. Two ROADMAP success criteria (SC3, SC5) are manual by definition and are routed to human verification, together with the consolidated UAT checklist. There are also several real defects found by the code review and by this verification that Liam should triage before ship (see Warnings in Gaps Summary).

### Observable Truths

| #  | Truth | Status | Evidence |
| -- | ----- | ------ | -------- |
| 1  | SC1: a 5-minute video becomes a ready lesson in at most 5 minutes | ✓ VERIFIED | Pipeline stages in `services/audio/src/audio_service/lesson/pipeline.py` (download, Demucs on range +/- 1 s, Whisper, D-21 segmentation, F0/PPG/IPA per sentence). Recorded cold run in 02-19-SUMMARY: `make smoke END=300 BUDGET=300` on a fresh DATA_DIR gave `BUDGET OK: 102.9 s <= 300.0 s`, `SELF-CHECK OK`, 46 segments; orchestrator re-ran at HEAD with 103-106 s. Budget logic has unit tests (`test_smoke_jobs.py`, 6 passing). Not re-run by the verifier (needs network and models, writes to DATA_DIR). |
| 2  | SC2: two lessons created back to back do not block each other (Liam can practise another lesson while waiting) | ✓ VERIFIED | `JobRunner` (`lesson/jobs.py`): 2-slot download pool plus a single FIFO `model-worker` under `model_gate`; `POST /lessons` only writes `queued` and returns. Tests `test_download_of_job_b_starts_while_job_a_is_still_in_its_model_step` and `test_never_two_model_steps_at_once_and_model_order_is_submission_order` pass in the 822-test run. `make smoke-jobs` timeline in 02-19-SUMMARY: lesson B was `downloading` at 1.4 s while A was not ready until 69.9 s; slowest `GET /lessons` 151 ms over 235 polls; both ready; `JOBS OK`. A real race (`audio.wav.part`) found by that smoke is fixed under `video_lock` with regression test `test_two_lessons_of_one_video_extract_the_audio_once`. |
| 3  | SC3: Liam practises 30 sentences using only the mouse, and also 30 using only the keyboard | ? UNCERTAIN | Manual criterion. Supporting code is present and wired: every action has a labelled button (`PlayerControls`, `ResultActionBar`, `TranscriptList`), shortcut table with input/dialog guards (`lib/player/shortcuts.ts`, `useShortcuts`), machine transitions covered by `playerMachine.test.ts` and `shortcuts.test.ts`. Routed to human verification (items 1 and 2). |
| 4  | SC4: with no OPENAI_API_KEY the app still runs: yellow non-blocking banner, lessons still created and practised | ✓ VERIFIED | `SystemBanners.tsx` renders a warning banner (`Chưa có OpenAI key: gợi ý dùng template, đọc chậm (TTS) tắt...` with `Thêm key` link to `/settings`) only when `!system.hasKey`, and it blocks nothing. `make smoke-jobs` runs with OPENAI_API_KEY removed and a temp `.env` and ends `JOBS OK`. Translation is the only key-dependent feature and degrades to a disabled `Dịch`. The visual/UX pass is still listed in human verification (item 4). |
| 5  | SC5: UI matches `docs/design/` | ? UNCERTAIN | Manual criterion. `02-UI-REVIEW.md` scores 21/24 from code only (no screenshots captured, no dev server). `tokens.test.ts` guards token drift. Routed to human verification (item 3). |
| 6  | Library S1: four-state cards with live job steps, sentence count, audio-quality badge, system banners, failure card with Thử lại (LES-03, LES-06, LES-07, SET-01) | ✓ VERIFIED | `app/page.tsx`, `LessonCard.tsx` (badges `Audio sạch` / `Có nhạc nền`, `Thử lại` calling `retryLesson`), `JobSteps.tsx` + `lessonView.ts` (five steps Tải video, Tách giọng, Phiên âm, Chia câu, Phân tích bản gốc), `SystemBanners.tsx` (models missing/loading, no key, mic denied, backend down). Backend: `recover_interrupted` and `retry_lesson` in `jobs.py` with passing tests (`test_retry_*`, `test_recover_interrupted_*`, `test_lifespan_recovers_interrupted_lessons_before_serving`). Quality label from Demucs stems via `quality.py` (`test_quality.py`, 11 passing). |
| 7  | Player state machine in its own file, with tests of the main transitions before UI (PLY-02) | ✓ VERIFIED | `apps/web/lib/player/playerMachine.ts` (XState v5; imports no React/DOM/fetch) with states idle, previewing, playing, recording, scoring, reviewing, noVoice, error and RETRY_UPLOAD. `playerMachine.test.ts` has 19 behavioural tests covering idle to playing to recording to scoring to reviewing, noVoice, upload failure keeps blob and retries, navigation guards and listen sub-states; all 172 web tests pass. Machine is consumed by `PracticeRoom.tsx` via `useActorRef` with real actors (`makePlaySample`, `makeRecordActor`, `uploadAttempt`). |
| 8  | Sentence playback: self-hosted `<video>` (no IFrame), 150 ms pad, x1/x2/x3 repeat, rate, opens at first unpracticed sentence, transcript list with practised dots (PLY-01, PLY-03, PLY-04) | ✓ VERIFIED | `VideoPane.tsx` renders `<video src=...>` served by `routers/media.py` (Starlette `FileResponse`, Range 206/416 tested in `test_media_api.py`, 44 tests); grep finds no IFrame usage in web code; `playRange.ts` applies `padMs` and per-repeat seeking at `rate`; `PracticeRoom` starts at `progress.firstUnpracticedIndex`; `TranscriptList` shows the practised mark (grey neutral dot by design D-08, since no scores exist yet). Download selector prefers H.264/AAC <= 480p with `ensure_h264` fallback (`download.py`). |
| 9  | Recording: countdown = sentence x factor, level meter, Space or 1 s silence stops, backend normalises to WAV 16 kHz mono, VAD voiced/no-voice, attempt row, no long-term audio unless saved for eval, error toast with Thử lại keeps the blob (REC-01..REC-04) | ✓ VERIFIED | `recorder.ts` + `level.ts` (level loop, SILENCE event) wired through the machine's `recordDelay` and `STOP`/`SILENCE`; `routers/attempts.py`: magic-byte sniff, 10 MB cap, explicit ffmpeg `-f`, 60 s limit, `vad.is_voiced`, `db.insert_attempt`, `shutil.rmtree(workdir)` in `finally`, eval clip only when `saveForEval` or the PUT route. `PracticeRoom` toast `Thử lại` sends `RETRY_UPLOAD`; `noVoice` panel offers re-record. Covered by `test_attempts_api.py`, `test_normalize.py`, `test_vad.py`, `recorder.test.ts`, `level.test.ts`. Caveat: first-use permission timing (WR-01, see Gaps Summary). |
| 10 | Create (S2) and Settings (S8): preview with clear errors, range picker above 6 min defaulting to 0-5 min, key check, practice defaults, data dir, US accent locked (LES-01, LES-02, SET-03, SET-04) | ✓ VERIFIED | `CreateLessonDialog.tsx`, `RangePicker.tsx`, `lib/time.ts` (`LONG_VIDEO_SEC = 360`, `DEFAULT_RANGE_END_SEC = 300`; mirrored server-side by `default_range` in `pipeline.py`); `urls.py` allow-list and `GET /videos/preview` reject channel/live/unavailable (`test_urls.py` 82 and `test_media_api.py`); `KeyField.tsx` (`Kiểm tra`, `Key hợp lệ · đã lưu`), `PracticeDefaults.tsx` (`Giọng mục tiêu: Anh Mỹ (US)` locked, auto-save), settings router with `validate_data_dir` and `.env` 0600 writer (`test_openai_key.py` 45, `test_settings_api.py` 26 passing). |
| 11 | Sentence tools: IPA from the speaker's audio with auto-recognition note and toggle, edit sentence, "Mất chữ cuối?" extends 300 ms and persists, translation cached (PLY-04, PLY-05, PLY-06) | ✓ VERIFIED | `ipa.py` derives IPA from the original's PPG, written per word at analyse time (`analyze_segment`), uncertain words stay `—`; `SpokenIpa.tsx` badge `IPA từ audio mẫu` plus helper text, `I` toggles; `routers/segments.py` PATCH edit and POST extend-end (`bump_end_extra`, `EXTEND_MAX_MS = 3000`, recompute under `model_gate`, 503 busy) with `test_segment_edit.py` (27) and `test_extend_end.py`; `routers/translate.py` + `translate.py` via httpx, cached in `lesson.json`, 30 tests. |

**Score:** 9/11 truths verified (2 awaiting manual human checks: SC3, SC5); 0 present-but-behavior-unverified.

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | LES-04 clause "prominence theo từ" precomputed at lesson creation | Phase 3 | ADR 0003 D-04 (decided by Liam in Phase 1) leaves `Word.prominence` empty until Phase 3; `features.py` docstring states it; Phase 3 PRO-02 covers per-word prominence. F0, energy and PPG per sentence are computed and written to `seg/NNNN.npz`. |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `scripts/smoke_jobs.py` | Two-lesson concurrency smoke | ✓ VERIFIED | `verify.artifacts` for 02-19: 3/3 pass (script, ADR 0005, Makefile); 6 unit tests on verdict logic |
| `docs/decisions/0005-job-runner-attempts-settings-p1.md` | ADR for Phase 2 architecture | ✓ VERIFIED | Present; EXTEND_MAX_MS flagged as pending Liam's confirmation |
| `apps/web/lib/player/playerMachine.ts` | XState machine | ✓ VERIFIED | 507 lines, real states, wired in PracticeRoom |
| `apps/web/components/{PracticeRoom,PlayerControls,ResultActionBar,SentenceStatePanel,TranscriptList,ReviewBlock,AttemptStrip,SpokenIpa,VideoPane}.tsx` | S3 | ✓ VERIFIED | Substantive (50-515 lines), imported and used |
| `apps/web/components/{LessonCard,JobSteps,SystemBanners,CreateLessonDialog,RangePicker,KeyField,PracticeDefaults,MicSection,ModelStatusList}.tsx` | S1/S2/S8 | ✓ VERIFIED | Substantive and wired from `app/page.tsx`, `app/settings/page.tsx` |
| `services/audio/src/audio_service/routers/{lesson,library,media,attempts,segments,translate,settings,system}.py` | API | ✓ VERIFIED | All included in `main.py`; `routers/scoring.py` is a 4-line placeholder by design (Phase 3) |
| `services/audio/src/audio_service/lesson/{pipeline,jobs,download,segment,ipa,normalize,vad,translate,segment_ops}.py` | Pipeline | ✓ VERIFIED | Real implementations, no stub markers |
| `packages/contracts` (Zod) + generated pydantic | Contracts | ✓ VERIFIED | Drift gate green inside `make test`; 58 contract tests |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `scripts/smoke_jobs.py` | `main.py` | `uvicorn.Server(create_app())` in a thread, httpx polling | WIRED | `verify.key-links` 2/2 |
| `Makefile` | `scripts/smoke_jobs.py` | `smoke-jobs` target | WIRED | |
| `main.py` lifespan | `JobRunner` / `recover_interrupted` / warm-up | `runner.start()` | WIRED | `app.state.runner` consumed by `routers/lesson.py` and `routers/segments.py` |
| `PracticeRoom` | `playerMachine` actors | `playerMachine.provide({ actors })` | WIRED | `makePlaySample`, `makePlayBlob`, `makePlayBoth`, `makeRecordActor`, `uploadAttempt` |
| `PracticeRoom` | `POST /lessons/{id}/segments/{i}/attempts` | `uploadAttempt` in `lib/api.ts` | WIRED | Response parsed with Zod `AttemptAck` |
| `stage_download` | `download.video_lock` | audio extraction under per-video lock | WIRED | race regression test passes |
| `segments.extend_end` | `JobRunner.model_gate` | `recompute_segment(..., runner.model_gate)` | WIRED | |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| S1 library | `useLessons()` | `GET /lessons` reading `lesson.json` + SQLite `attempts` | Yes | ✓ FLOWING |
| `SpokenIpa` | `segment.words[].ipa` | PPG argmax over original vocals in `ipa_for_segment` | Yes (about 70% of words; the rest `—` by design D-20) | ✓ FLOWING |
| Transcript practised dots / header progress | `useLessonProgress` | `GET /lessons/{id}/progress` from `attempts` where voiced | Yes | ✓ FLOWING |
| `AttemptStrip` "Lượt k" | `voicedAttempts` | same progress query, invalidated on scoring to reviewing/noVoice | Yes (IN-08: label can lag one refetch) | ✓ FLOWING |
| `VideoPane` | `<video src>` | `GET /lessons/{id}/video` over cached `video.mp4` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Whole test gate (drift + vitest + pytest) | `make test` | contracts 58, web 172 (14 files), pytest 822 passed in 62.6 s, exit 0 | ✓ PASS |
| Lint gate (eslint, prettier, tsc, ruff check, ruff format) | `make lint` | exit 0 | ✓ PASS |
| Plan 02-19 artifacts and key links | `gsd-tools verify.artifacts` / `verify.key-links` on 02-19-PLAN.md | 3/3 and 2/2 | ✓ PASS |
| Debt markers in phase sources | `grep -E "\b(TBD|FIXME|XXX)\b"` over web, service, scripts, contracts, ADRs | no matches | ✓ PASS |
| 5-minute budget, two-lesson smoke | `make smoke END=300 BUDGET=300`, `make smoke-jobs` | Not re-run by the verifier (network, models, writes to DATA_DIR). Relied on recorded output in 02-19-SUMMARY and the orchestrator's re-run at HEAD | ? SKIP (evidence accepted, see truths 1-2) |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| `scripts/smoke_jobs.py`, `scripts/smoke_lesson.py` | Declared as phase gates, not `scripts/*/tests/probe-*.sh` probes; no conventional probe files exist | Verdict logic covered by `test_smoke_jobs.py` (6 passing); model runs documented above | ? SKIP (model and network gate) |

### Requirements Coverage

Every requirement id appearing in the 19 PLAN frontmatters was cross-referenced against REQUIREMENTS.md and the ROADMAP list. The union is exactly the 22 ids for Phase 2; no id is missing and no REQUIREMENTS.md id mapped to Phase 2 is orphaned.

| Requirement | Source Plan(s) | Description | Status | Evidence |
| ----------- | -------------- | ----------- | ------ | -------- |
| SET-01 | 02-01, 02-08, 02-11, 02-17 | S1 system-status banners (models, key, mic) | ✓ SATISFIED | `SystemBanners.tsx`, `system_status.py`, `GET /system/status` (19 tests) |
| SET-02 | 02-08, 02-11, 02-16, 02-19 | Missing key gives non-blocking yellow banner with button to S8; app still creates and practises | ✓ SATISFIED | Banner with `Thêm key` to `/settings`; `make smoke-jobs` with no key. UI pass in human list |
| SET-03 | 02-01, 02-02, 02-11, 02-17 | Paste key in S8, press Kiểm tra, see valid/invalid | ✓ SATISFIED | `KeyField.tsx`, `routers/settings.py`, `test_openai_key.py` (45). Real-key check in human list |
| SET-04 | 02-01, 02-11, 02-17 | Defaults for rate, repeat, record time, data dir; US accent locked | ✓ SATISFIED | `PracticeDefaults.tsx`, `settings_store.py`. See WR-03 (stale dataDir) |
| LES-01 | 02-01, 02-07, 02-13 | Paste link, preview, clear errors | ✓ SATISFIED | `CreateLessonDialog`, `GET /videos/preview`, `urls.py` |
| LES-02 | 02-03, 02-12, 02-13 | > 6 min range picker (default first 5 min); <= 6 min whole video | ✓ SATISFIED | `time.ts`, `RangePicker.tsx`, `pipeline.default_range`. See WR-05 (no server cap) |
| LES-03 | 02-01, 02-03, 02-04, 02-06, 02-08, 02-13, 02-19 | Background creation with per-step progress; two lessons do not block | ✓ SATISFIED | Truth 2, truth 6 |
| LES-04 | 02-07, 02-12 | Pipeline incl. precomputed F0, energy, prominence, PPG | ✓ SATISFIED (prominence deferred) | Truth 1; prominence clause deferred to Phase 3 by ADR 0003 D-04 and PRO-02 |
| LES-05 | 02-12, 02-19 | 5-minute video ready in <= 5 minutes | ✓ SATISFIED | 102.9 s cold run |
| LES-06 | 02-06, 02-08 | Card shows sentence count and Audio sạch / Có nhạc nền | ✓ SATISFIED | `LessonCard.tsx`, `quality.py` |
| LES-07 | 02-03, 02-08 | Failed job shows on card with retry | ✓ SATISFIED | `failureText`, `Thử lại`, `retry_lesson`. See WR-07 (generic download message) |
| PLY-01 | 02-07, 02-09 | Self-hosted `<video>`, lesson opens only when ready | ✓ SATISFIED | `VideoPane.tsx`, `PracticeRoom` not-ready guard, ADR 0004 |
| PLY-02 | 02-02, 02-05 | XState machine in its own file with transition tests | ✓ SATISFIED | Truth 7 |
| PLY-03 | 02-09 | Pad, x1/x2/x3, rate, prev/replay/play/next | ✓ SATISFIED | `playRange.ts`, `PlayerControls.tsx` |
| PLY-04 | 02-01, 02-06, 02-09, 02-15, 02-16, 02-18 | Open at first unpracticed sentence, list highlight, dots, Sửa | ✓ SATISFIED | Dots are neutral grey (no score before Phase 3, D-08) |
| PLY-05 | 02-15, 02-18 | Mất chữ cuối? extends end by 300 ms and saves | ✓ SATISFIED | `segments.py`, `segment_ops.py`; cap 3000 ms pending Liam |
| PLY-06 | 02-12, 02-18 | IPA of the speaker, auto-recognition note, toggle | ✓ SATISFIED | Truth 11 |
| PLY-07 | 02-04, 02-05, 02-09, 02-14, 02-19 | Labelled buttons with secondary shortcuts; 30 sentences mouse-only and keyboard-only | ✓ SATISFIED (code) / manual pass pending | Buttons and shortcuts present; the 30-sentence run is SC3 in human verification. REQUIREMENTS.md already ticks this id |
| REC-01 | 02-05, 02-14 | Auto Lượt của bạn with countdown x 1.5 and level meter; Space or 1 s silence stops | ✓ SATISFIED | Machine `recordDelay`, `SILENCE`, `LevelMeter`; see WR-01 |
| REC-02 | 02-02, 02-10 | Backend normalises webm/mp4 to WAV 16 kHz mono | ✓ SATISFIED | `normalize.py`, `test_normalize.py`, `test_attempts_api.py` |
| REC-03 | 02-01, 02-10, 02-14 | No-voice state and re-record; backend error gives toast with retry, recording kept | ✓ SATISFIED | `noVoice` and `uploadError` panels, toast with `Thử lại` |
| REC-04 | 02-01, 02-10, 02-14 | Recordings not kept unless flagged for eval | ✓ SATISFIED | `rmtree(workdir)` in `finally`; eval clip only via `saveForEval` / PUT |

Administrative gap: `.planning/REQUIREMENTS.md` still shows 20 of the 22 ids unchecked and "Pending" in the traceability table (only LES-03 and PLY-07 are `[x]`/Complete). The orchestrator should update the checkboxes and table when closing the phase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (all phase sources) | n/a | TBD / FIXME / XXX / TODO / HACK / PLACEHOLDER | none found | Debt-marker gate passes |
| `apps/web/lib/player/playerMachine.ts` | 376 | `after: { recordDelay }` armed on entry to `recording`, while the `record` actor only starts after `await openMic()` (`recorder.ts` lines 161, 241) | ⚠️ Warning (WR-01, confirmed by reading) | First-run mic permission prompt can consume the window, producing a near-empty clip that is reported as no voice or 415 |
| `services/audio/src/audio_service/routers/lesson.py` | 99, 101, 106 | `HTTPException` instead of `ApiErrorException` in `GET /lessons/{id}` (confirmed) | ⚠️ Warning (WR-02) | Missing lesson on S3 shows "Backend trả lỗi không đọc được" instead of the 404 message |
| `services/audio/src/audio_service/routers/lesson.py` | 42-58 | `POST /lessons` does not reject live/unavailable videos (confirmed) | ⚠️ Warning (WR-04) | Direct API/stale-preview case gives `invalid_range` or a late failure; S2 blocks it through preview |
| `services/audio/src/audio_service/lesson/pipeline.py` | 183-203 | No server-side maximum range length | ⚠️ Warning (WR-05) | A very long range could exhaust memory on the 8 GB target; needs a Liam-chosen constant or an ADR note |
| `services/audio/src/audio_service/settings_store.py` | 41-62 | Stale `dataDir` makes defaults PUT fail with 422 | ⚠️ Warning (WR-03) | Practice-defaults save broken until the folder returns |
| `services/audio/src/audio_service/lesson/pipeline.py` | 308-309 | Every `DownloadError` reported as blocked/private | ⚠️ Warning (WR-07) | Misleading message on transient network failures |
| `services/audio/src/audio_service/lesson/jobs.py` | 156-177 | Retry skips the duplicate-lesson rule | ⚠️ Warning (WR-08) | Possible duplicate processing |
| `services/audio/src/audio_service/lesson/pipeline.py` | 84-93 | `UnboundLocalError` can mask the real Demucs failure | ⚠️ Warning (WR-06) | Log clarity only |
| various (IN-01 to IN-09) | n/a | See 02-REVIEW.md | ℹ️ Info | 0 critical findings; all 17 review items are still `open` in 02-REVIEW-DISPOSITION.md |

None of the warnings is a blocker for the phase goal: each affects an edge path, a message, or an unlikely load, not the main create, practise and record loop. WR-01 is the one most likely to be hit in normal use (first recording after clearing mic permission).

### Human Verification Required

#### 1. SC3 mouse only

**Test:** In Chrome with `make dev` (no code edits during the session), practise 30 sentences end to end using only buttons and the transcript list.
**Expected:** No dead end or greyed button without an exit; every action reachable by a labelled button.
**Why human:** Manual criterion; real microphone, playback and human judgement.

#### 2. SC3 keyboard only

**Test:** The same 30 sentences using only Space, R, Left/Right, O, M, B, I, T.
**Expected:** Focus never trapped; Space never scrolls the page; the loop completes.
**Why human:** Manual criterion; unit tests cover the key table and transitions, not the live media flow.

#### 3. SC5 design fidelity

**Test:** Compare S1, S2, S3 and S8 against `docs/design/screens/` side by side.
**Expected:** Match, allowing approved deviations G1-G24 and D-09.
**Why human:** Visual; the UI audit was code-only.

#### 4. SC4 UI pass without a key

**Test:** Remove `OPENAI_API_KEY`, restart `make dev`, create and practise a lesson.
**Expected:** Yellow banner non-blocking, `Dịch` disabled with tooltip, S8 can save a key.
**Why human:** UI behaviour; the pipeline half is proven by `make smoke-jobs`.

#### 5. First-run microphone permission (WR-01)

**Test:** Reset the site's microphone permission and start a recording on a short sentence; delay clicking Allow beyond the countdown.
**Expected:** The attempt is still captured normally. If not, fix WR-01 before ship (start the delay after the recorder reports started).
**Why human:** Browser permission prompt cannot be driven by tests.

#### 6. Real-mic recording behaviours and the rest of the 02-19 UAT

**Test:** Work through groups B-F of the checklist in `02-19-SUMMARY.md`.
**Expected:** As listed there (VAD thresholds, auto-stop, mic release, upload failure retry, eval clip, IPA glyphs, translation quality, Sửa câu, Mất chữ cuối? and the 3000 ms cap, Chrome seeking, AV1/VP9 cache and Tải lại video, live link on `POST /lessons`, S1/S2/S8 edge cases, warm-up on the 8 GB machine, real key, data dir, gap-copy strings).
**Why human:** Hardware, real network and key, perceptual and copy judgement.

### Gaps Summary

There are no FAILED must-haves and no blocker gaps, so the status is `human_needed` rather than `gaps_found`.

What is proven by evidence in the codebase and by commands run in this verification: the full test gate (contracts 58, web 172, pytest 822), the lint gate, wiring of every screen to the API and state machine, the job-runner concurrency invariants (behavioural tests plus the recorded `make smoke-jobs` run), the 5-minute budget (recorded 102.9 s cold run, re-run by the orchestrator), recording normalisation and no-retention, and requirement-level coverage of all 22 ids.

What needs a person: SC3 (30 sentences by mouse and by keyboard) and SC5 (design fidelity), both manual by the roadmap's own definition, plus the consolidated UAT and the SC4 UI pass.

Items for Liam to decide or triage (warnings, not blockers):

1. WR-01 first-run mic permission eats the recording window. Confirmed in `playerMachine.ts:376` and `recorder.ts`. It sits on the main practice path the first time a browser asks for the mic; recommended fix before ship (small, in the machine).
2. WR-02, WR-03, WR-04, WR-05, WR-07, WR-08, WR-06 and IN-01..IN-09 are all still `open`. WR-05 needs a product threshold (maximum range length) chosen by Liam; WR-04 and WR-02 are one-line consistency fixes.
3. `EXTEND_MAX_MS = 3000` (ADR 0005) is pending Liam's confirmation.
4. `POST /lessons` for a live link returns `invalid_range`, not `live_video` (same root as WR-04).
5. The phase is marked `Mode: mvp` in ROADMAP.md but its goal is not in the "As a ..., I want to ..., so that ..." form (`user-story.validate` returned false; Phase 1 has the same shape). Verification was done against the ROADMAP goal and success criteria. If Liam wants true MVP-mode verification, rewrite the goal as a user story with `/gsd-mvp-phase 2`.
6. Housekeeping: REQUIREMENTS.md checkboxes and traceability table still list 20 of the 22 ids as Pending; ROADMAP progress line for Phase 2 is unticked.
7. LES-04's "prominence per word" is deliberately deferred to Phase 3 (recorded under Deferred Items).

---

_Verified: 2026-10-08_
_Verifier: Claude (gsd-verifier)_
