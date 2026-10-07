---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 12
subsystem: audio-pipeline
tags: [ipa, ppg, wav2vec2, segmentation, demucs, stems-cache, smoke, tracer]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-03 job runner stages (separating..analyzing, model gate) and PipelineDeps; 02-06 config.stems_dir(video_id, start_ms, end_ms); 02-01 approved Word.ipa (optional) contract field"
provides:
  - "lesson/ipa.py: decode_phones, ipa_for_segment, load_inv_vocab (IPA_MIN_CONF 0.7, IPA_TOL_FRAMES 2, PPG_FPS 50)"
  - "pipeline.analyze_segment(lesson_id, seg, vocals16, base_offset, duration_sec, pad_ms, ppg_model, vocab, deps, timer) -> Segment with Word.ipa on confident words (reused by 02-15)"
  - "pipeline.load_range_vocals16(lesson) -> (16 kHz mono vocals, base_offset) from the cached range stem"
  - "PipelineDeps.load_vocab (real = ipa.load_inv_vocab)"
  - "Range-only Demucs separation with stems cached at videos/{id}/stems/{startMs}-{endMs}/{vocals,no_vocals}.wav"
  - "D-21 sentence heuristic: MIN_DUR_S 3.0, MAX_MERGED_S 8.0, MAX_MERGED_WORDS 18"
  - "scripts/smoke_lesson.py: sentence_length_stats + 'Phan bo do dai cau' block"
affects: [02-13, 02-15, 02-19]

tech-stack:
  added: []
  patterns:
    - "IPA only from the original speaker's PPG argmax inside each word span (+-2 frames); words below mean phone prob 0.7 or without a phone omit the `ipa` key (never null)"
    - "Stem cache dir name is the rounded integer ms range; base/stop derived from those same integers so any lesson of the same range reads the stem with an identical base_offset"
    - "Optional vocab: a missing HF vocab cache degrades to no IPA (logged), never fails lesson creation"

key-files:
  created:
    - services/audio/src/audio_service/lesson/ipa.py
    - services/audio/tests/test_ipa.py
  modified:
    - services/audio/src/audio_service/lesson/pipeline.py
    - services/audio/src/audio_service/lesson/segment.py
    - scripts/smoke_lesson.py
    - docs/product.md
    - services/audio/tests/test_pipeline.py
    - services/audio/tests/test_segment.py
    - services/audio/tests/test_lessons_api.py

key-decisions:
  - "D-21 reading (for Liam to confirm at PR review): the 15-word split rule is unchanged and 18 is the merge cap and visible maximum. Consequence: an 18-word run that is cut by the word rule but whose halves are both < 3 s is merged back into one 18-word sentence (pinned by a test)"
  - "load_vocab has a default of an empty vocab on PipelineDeps (default_deps sets the real loader) so every existing PipelineDeps(...) construction in other test modules keeps working"
  - "load_range_vocals16 raises StepError(STEMS_MISSING_MESSAGE) with a fixed Vietnamese message (no path) when the stem is absent"

patterns-established:
  - "Tests-first without stubs: new behavior tests were written and run red (collection ImportError / assertion failures) before implementation"

requirements-completed: [LES-04, LES-05, PLY-06, LES-02]

duration: 18 min
completed: 2026-10-07
status: complete
plan_head_before: dd556e3d20e358aa260d8144b8a281d9c52762d5
plan_head_after: 194b27fca08c89ebf0edbf265d0f5f56b6bdef81
actuals:
  tokens: 13200
  tasks: 3
  commits: 3

coverage:
  - id: D1
    description: "Word.ipa = greedy-decoded wav2vec2-espeak phones of the speaker's audio inside each word span (+-2 frames), no stress marks; words without a phone or with mean phone prob < 0.7 have no ipa key (never null); no G2P anywhere"
    requirement: "PLY-06"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_ipa.py (15 tests incl. test_ipa_module_has_no_text_to_phoneme_import)"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_pipeline.py#test_confident_words_get_ipa_from_the_ppg_and_the_rest_have_no_key"
        status: pass
    human_judgment: true
    rationale: "Whether the ~30% hidden words and the recognised phones are useful to Liam is a product judgement (RESEARCH measured 0.7 hides ~32%; surfaced again in the 02-19 UAT checklist)"
  - id: D2
    description: "Sentence splitting uses MIN_DUR_S 3.0 / MAX_MERGED_S 8.0 / MAX_MERGED_WORDS 18; merging never yields a span over 8 s or 18 words; product.md M1 updated"
    requirement: "LES-04"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_segment.py (constants, word-cap, second-cap and property tests)"
        status: pass
      - kind: other
        ref: "make smoke END=300 -> 46 sentences, 7 < 3 s, 39 in 3-8 s, 0 > 8 s, max 18 words"
        status: pass
    human_judgment: false
  - id: D3
    description: "Vocal separation runs only on [range.start-1 s, range.end+1 s]; stems cached per (videoId, startMs, endMs) and reused only for the same range; cut points are stem-relative while windows/.npz stay absolute"
    requirement: "LES-02"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_pipeline.py#test_separation_input_is_the_range_plus_one_second_each_side"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_pipeline.py#test_stems_are_cached_per_range_and_reused_only_for_the_same_range"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_pipeline.py#test_transcribe_gets_the_range_slice_and_windows_stay_absolute"
        status: pass
    human_judgment: false
  - id: D4
    description: "Entering analyzing removes the lesson's previous seg/ directory; load_range_vocals16 returns the cached stem or a clear error"
    requirement: "LES-04"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_pipeline.py#test_entering_analyzing_removes_stale_segment_features"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_pipeline.py#test_load_range_vocals16_without_stems_raises_a_clear_error"
        status: pass
    human_judgment: false
  - id: D5
    description: "A real 5-minute run (make smoke END=300 BUDGET=300) finishes within 300 s with IPA and range separation; a 60-120 s range run separates only that range"
    requirement: "LES-05"
    verification:
      - kind: other
        ref: "make smoke END=300 BUDGET=300 -> BUDGET OK: 102.2 s <= 300.0 s, SELF-CHECK OK (fresh DATA_DIR)"
        status: pass
      - kind: other
        ref: "make smoke START=60 END=120 BUDGET=300 -> BUDGET OK: 39.2 s, stems/60000-120000 created, first segment start 60.0, window [59.85, 64.11]"
        status: pass
    human_judgment: false
---

# Phase 2 Plan 12: IPA from PPG, D-21 sentence length, range-only separation Summary

**Per-word IPA decoded from the speaker's own wav2vec2 PPG (hidden below 0.7), a 3 s / 8 s / 18-word sentence heuristic that moves the smoke video from 35 of 59 sentences under 3 s to 7 of 46, and Demucs limited to the chosen range plus 1 s with stems cached per range, all inside the 5-minute budget (102 s measured).**

## Performance

- **Duration:** 18 min
- **Started:** 2026-10-07T15:17:00Z
- **Completed:** 2026-10-07T15:35:00Z
- **Tasks:** 3 (1 tracer, 2 tdd)
- **Files modified:** 9 (plus this SUMMARY)

## Accomplishments

- `ipa.py` (pure, array in, dict out): `decode_phones` (CTC greedy, blank/special dropped, a blank separates repeated tokens), `ipa_for_segment` (phones assigned to the word that strictly contains the frame, else the nearest within +-2 frames; confidence is the mean probability of the emitting frames; keep at 0.7 and above), `load_inv_vocab` (`hf_hub_download(..., local_files_only=True)`, no new download). Stress marks are filtered defensively although the vocab has none.
- `analyze_segment` extracted from the analyzing loop; it writes `seg/{index:04d}.npz` (same keys as before) and returns the Segment with `ipa` only on confident words (words rebuilt from dumped dicts, so unknown stays absent, never null). `stage_model` saves the returned segments together with `ready`.
- D-21 constants and word cap in `segment.py`, measured before/after on the smoke video (table below) and documented in `docs/product.md` M1.
- Range separation: `[range.start-1 s, range.end+1 s]` is sliced from the cached whole-video `audio.wav` and separated; stems land in `videos/{id}/stems/{startMs}-{endMs}/`. `load_range_vocals16(lesson)` is the shared reader (02-15). The old whole-video `vocals.wav`/`no_vocals.wav` are no longer produced or read.

## Before/after sentence-length distribution (smoke video `dUDi-F6eAvk`, `make smoke END=300`)

Before = a real run of this branch with the old constants (taken before editing `segment.py`; this run is the baseline, RESEARCH's 62-sentence baseline differs only by Whisper nondeterminism). After = real runs with the D-21 constants (two independent runs gave the identical distribution).

| Metric | Before (MIN 1.5 s / MERGED 9 s / no word cap) | After (MIN 3.0 s / MERGED 8 s / MAX_MERGED_WORDS 18) |
|---|---|---|
| sentences | 59 | 46 |
| < 3 s | 35 | 7 |
| 3-8 s | 23 | 39 (85%) |
| > 8 s | 1 | 0 |
| median length | 2.50 s | 4.06 s |
| max words | 23 | 18 |
| sentences over 18 words | 3 | 0 |

46 sentences over 5 minutes is about 9.2 per minute, inside the 8-12 per minute of product.md M1.

## Real smoke timing (fresh DATA_DIR, `make smoke END=300 BUDGET=300`)

```
step              seconds
download             3.18
write                0.03
extract_audio        0.22
demucs              41.81
quality              0.09
resample             0.13
whisper             41.16
segment              0.00
ppg                 13.70
f0                   0.42
write_features       1.05
ipa                  0.02
total              101.81   wall 102.2 s (0.34x realtime)   BUDGET OK: 102.2 s <= 300.0 s   SELF-CHECK OK
```

Baseline run before the changes: total 137.35 s, wall 138.2 s (demucs 53.7 s, whisper 55.7 s; machine load differed between runs, so compare shapes, not absolute seconds). IPA adds 0.02 s for the whole video.

A 60-120 s range run (`START=60 END=120`) separated only [59, 121): demucs 10.47 s, total 38.9 s, `stems/60000-120000/` created next to `stems/0-300000/`, first segment `start` 60.0 with `.npz` window `[59.85, 64.11]` (absolute video seconds).

## Share of words with IPA (smoke video, 580 words)

- Fresh final run: 409 of 580 words (70.5%) carry `ipa`; the pre-change baseline run: 401 of 580 (69.1%). Consistent with RESEARCH (68% at threshold 0.7); about 30% of words are hidden by design (D-20), to be surfaced in the 02-19 UAT checklist rather than tuned here.
- 60-120 s range run: 85 of 120 words (71%).

## Task Commits

1. **Task 1: Tracer, IPA from PPG (analyzing -> ipa_for_segment -> Word.ipa)** - `2602121` (feat)
2. **Task 2: D-21 sentence heuristic, smoke distribution block, product.md M1** - `d2b04b5` (feat)
3. **Task 3: Range-only separation, per-range stems, load_range_vocals16** - `194b27f` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

Tracer gate (end-of-phase mode, automated-only verify): the tracer `<verify>` (`pytest test_ipa.py test_pipeline.py` plus the no-G2P-import grep) was re-run after the commit and passed, then expansion proceeded: "Tracer verified end-to-end - expanding".

## Files Created/Modified

- `services/audio/src/audio_service/lesson/ipa.py` - D-14/D-20 IPA decoding and vocab loader (new)
- `services/audio/src/audio_service/lesson/pipeline.py` - `analyze_segment`, `load_range_vocals16`, range stems, `PipelineDeps.load_vocab`
- `services/audio/src/audio_service/lesson/segment.py` - D-21 constants and word cap in `_merge_short`
- `scripts/smoke_lesson.py` - `sentence_length_stats`, `format_sentence_length_stats`, distribution block
- `docs/product.md` - M1 sentence rule (3-8 s, at most 18 words)
- `services/audio/tests/test_ipa.py` (new), `test_pipeline.py`, `test_segment.py`, `test_lessons_api.py`

## Decisions Made

- D-21 is implemented as the plan states: 15-word split rule unchanged, 18 is the merge cap. Flag for Liam at PR review: because merging is allowed up to 18 words, a run that the word rule cuts into two halves both shorter than 3 s is merged back into one sentence of up to 18 words (4.45 s, 18 words in the test). That is the behaviour RESEARCH evaluated (38/46 in 3-8 s, none over 18 words).
- `load_range_vocals16` raises `StepError` with a fixed message rather than a new exception type (callers already map `StepError`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Word fixture in `test_lessons_api.py` lengthened**
- **Found during:** Task 3 (full-suite run)
- **Issue:** `test_lessons_api.py` (and `test_jobs.py`, which imports its `Fakes`) used a `_WORDS` fixture of two sentences shorter than 3 s; under D-21 they merge into one segment and two tests expecting 2 segments failed. The file is outside the plan's `files_modified`.
- **Fix:** replaced `_WORDS` with the same two 3 s+ sentences used in `test_pipeline.py`.
- **Files modified:** `services/audio/tests/test_lessons_api.py`
- **Verification:** `pytest services/audio/tests` 616 passed
- **Commit:** `194b27f`

**2. [Rule 2 - Missing critical] `PipelineDeps.load_vocab` defaults to an empty vocab; a missing vocab degrades to no IPA**
- **Found during:** Task 1
- **Issue:** `test_lessons_api.py` and `test_media_api.py` construct `PipelineDeps(...)` without the new field, and a missing HF vocab cache would otherwise fail lesson creation with "unexpected error" although IPA is optional (CLAUDE.md: app must keep working; precision before recall).
- **Fix:** trailing default `load_vocab = lambda: {}`; `default_deps()` sets `ipa.load_inv_vocab`; `_load_vocab` logs a warning and returns `{}` if loading raises. Covered by `test_missing_vocab_degrades_to_no_ipa_without_failing_the_lesson`.
- **Files modified:** `services/audio/src/audio_service/lesson/pipeline.py`, `services/audio/tests/test_pipeline.py`
- **Commit:** `2602121`

### Other notes (not defects)

- Plan type is `execute`, not `type: tdd`, with one commit per task. For the `tdd="true"` tasks the tests were written and run red first (Task 2: collection ImportError on `MAX_MERGED_WORDS` plus 14 failing assertions; Task 3: collection ImportError on `load_range_vocals16`), then the implementation, committed once per task as the plan specifies. No separate `test(...)` commits exist, so no TDD gate sequence is claimed.
- The `seg/` cleanup (`shutil.rmtree` on entering `analyzing`) already existed from 02-03; this plan adds the test that proves a stale `seg/0009.npz` disappears.
- The per-worktree sentinel files (`gsd-plan-head-before-*`, spawn toplevel) could not be written because the sandbox refuses commands naming the git dir; `commits:` is measured against the orchestrator-recorded base SHA `dd556e3` (`git rev-list --count dd556e3..HEAD` = 3 before this SUMMARY commit).
- The D-21 "after" run reused a cached whole-video stem, so its timing table (demucs 0.15 s) is not comparable; the timing table above is from a fresh DATA_DIR.
- Lint: `ruff check` is clean for every file touched except one pre-existing `RUF100` unused `noqa` in `scripts/smoke_lesson.py` (line of the `except BaseException` handler) and 3 pre-existing format diffs in files this plan did not touch; both left alone (out of scope).

**Total deviations:** 2 auto-fixed (1 Rule 3, 1 Rule 2). **Impact:** none on scope; both keep unrelated tests and runtime behaviour intact.

## Issues Encountered

None blocking. The first executor was killed by an API rate limit after the Task 3 commit (194b27f), before committing this SUMMARY; a continuation stalled with no changes. The orchestrator then re-verified in this worktree: full audio suite 616 passed, ruff clean, Task 3 acceptance greps present, and a fresh `make smoke END=300 BUDGET=300` printed SELF-CHECK OK and BUDGET OK: 105.8 s <= 300.0 s (7 sentences < 3 s). Whisper is not deterministic between runs, so the baseline sentence count differs by a few from RESEARCH (59 vs 62).

## Known Stubs

None.

## Threat Flags

None. `stems_dir` validates the video id and integer ms bounds and checks containment (T-02-35); `shutil.rmtree` targets `lesson_dir(lesson_id)/seg` from a validated ULID only (T-02-36); no packages were added (`uv sync --frozen`), the vocab comes from the existing HF cache with `local_files_only=True` (T-02-SC).

## Next Phase Readiness

- 02-15 ("Mat chu cuoi?") can call `load_range_vocals16(lesson)` and `analyze_segment(...)` directly.
- 02-19 UAT should still surface that about 30% of words show no IPA by design (D-20).
- Old whole-video `vocals.wav`/`no_vocals.wav` files from earlier lessons are simply ignored (never read or deleted).

## Self-Check: PASSED

- Commits 2602121, d2b04b5, 194b27f present on the plan branch.
- `pytest services/audio/tests -q`: 616 passed; `ruff check services/audio`: clean.
- `pipeline.py` contains `stems_dir(`, `def load_range_vocals16`, `rmtree`.
- `make smoke END=300 BUDGET=300`: SELF-CHECK OK, BUDGET OK 105.8 s.
