---
phase: 03-p2-ch-m-ng-i-u
plan: 06
subsystem: scoring
tags: [rule-engine, prominence, theil-sen, tips, vietnamese-templates, numpy, scipy]

requires:
  - phase: 03-p2-ch-m-ng-i-u
    provides: "03-01 item E thresholds and ScoreResult contract; 03-03 score_prosody, ProsodyFeatures, Alignment, metrics, synth.py"
provides:
  - "scoring/prominence.py: word_prominence, user_word_frames, stress_entries, silent_mask/silent_runs, ref_row_at_user_frame, pause_entries, ms_to_frames"
  - "rules/engine.py: RuleIssue, RuleInput, five rule functions, run_rules (fixed order)"
  - "rules/tips.py: PRIORITY, MAX_TIPS, render_tip, select_tips (Vietnamese template tips, D-14)"
  - "score_prosody now fills stress, pauses, issues, tips and timing_ms['rules'] (signature unchanged)"
  - "tests/synth.py: word_f0_offset_st and word_level_db options"
affects: [03-05, 03-07, 03-08, 03-09, 03-11]

actuals:
  tokens: 24000
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Certainty gate per rule, all numbers from thresholds.py; word-level rules return nothing when alignment is not ok (D-02)"
    - "Tip selection: one per code, most deviant issue, priority order, max 3; issueRef is the index in the unfiltered issues list"
    - "Untrusted word text: every * removed before insertion into a *word* template (T-03-14)"

key-files:
  created:
    - services/audio/src/audio_service/scoring/prominence.py
    - services/audio/src/audio_service/rules/__init__.py
    - services/audio/src/audio_service/rules/engine.py
    - services/audio/src/audio_service/rules/tips.py
    - services/audio/tests/test_scoring_prominence.py
    - services/audio/tests/test_scoring_rules.py
    - services/audio/tests/test_scoring_tips.py
  modified:
    - services/audio/src/audio_service/scoring/scorer.py
    - services/audio/tests/synth.py

key-decisions:
  - "thresholds.py untouched (git log lists only the 03-03 commit); every rule threshold is imported from it"
  - "Geometry constants of EXTRA_PAUSE (3 frames from the ends, +-10 frames ref window) are named module constants in engine.py, taken from the plan text, not added to thresholds.py"
  - "EXTRA_PAUSE maps the silent-run centre through the DTW path (symmetric stretch lands on the gap), skips when the original has a >= 100 ms pause in +-10 frames, and requires exactly one word end within 100 ms"
  - "stress and pauses are always filled, also when the alignment is not ok (literal must_have); only issues are restricted by D-02"

patterns-established:
  - "RuleInput hand-built in tests to exercise each gate independently of F0/DTW details"
  - "Synthetic perturbations: extra_gap_after, word_f0_offset_st, word_level_db, flat_f0, f0_scale, reversed last word"

requirements-completed: [RUL-01, RUL-02, PRO-02]

duration: about 55min (estimate, start time was not captured)
completed: 2026-10-09
status: complete
plan_head_before: b3a35fb47508c0ada98d441f61d9136dbc0e0ceb
plan_head_after: 83163883e356c9acb058f8d55ac1c7d0dd58585d
commits: 6
---

# Phase 3 Plan 06: Rule engine and template tips Summary

**Layer C for P2: word prominence, stress and pause entries, five intonation rules (STRESS_MISMATCH, FINAL_CONTOUR via Theil-Sen, EXTRA_PAUSE through the DTW path, PITCH_DEVIATION at 3 st, FLAT_PITCH) with the 03-01 item E certainty gates, and Vietnamese template tips chosen by D-14, all wired into `score_prosody` so the API returns issues and tips with no further work.**

## Performance

- **Duration:** about 55 min (estimate; start time not captured)
- **Completed:** 2026-10-09
- **Tasks:** 3 (tracer, rules, templates), all TDD
- **Files:** 7 created, 2 modified (4 source files, 5 test files)
- **Tests:** full `services/audio/tests` 994 passed; ruff check and format clean

`commits: 6` is measured from `plan_head_before` (b3a35fb) to `plan_head_after`: three RED commits and three GREEN commits. The SUMMARY docs commit follows.

## Accomplishments

- `score_prosody` (signature unchanged, backward compatible for 03-05) now returns `stress` (one entry per word, z-score prominence for ref and user), `pauses` (inter-word gaps with `max(refMs, userMs) >= 100`), `issues`, `tips`, and measures `timing_ms["rules"]`.
- Five rules with the certainty gates of 03-01 item E; self-compare gives zero issues and zero tips; a flat original never yields FLAT_PITCH; a sentence-wide shift of +4 st gives zero issues.
- Alignment not ok (D-02): STRESS_MISMATCH, PITCH_DEVIATION and EXTRA_PAUSE return nothing; FLAT_PITCH and FINAL_CONTOUR still run (tested with a forced not-ok aligner over five perturbations).
- Tips: at most 3, one per code, order STRESS_MISMATCH > FINAL_CONTOUR > EXTRA_PAUSE > PITCH_DEVIATION > FLAT_PITCH, most deviant issue inside a code, `source: "template"`, `issueRef` indexes an issue of the same code, `issues` never filtered.

## Task Commits

1. **Task 1 (tracer): prominence, pauses, FLAT_PITCH, tip, ScoreResult**
   - RED `b76d15c` (test), GREEN `25b933b` (feat)
2. **Task 2: FINAL_CONTOUR, PITCH_DEVIATION, EXTRA_PAUSE, STRESS_MISMATCH with gates and D-02**
   - RED `f9ff77a` (test), GREEN `4f80ccb` (feat)
3. **Task 3: Vietnamese templates and D-14 selection**
   - RED `920d104` (test), GREEN `8316388` (feat)

**Tracer gate:** `human_verify_mode` is `end-of-phase` and the tracer `<verify>` is automated only, so it was re-run after the tracer commit (24 passed) and the run continued: "Tracer verified end-to-end - expanding".

## Synthetic detection table

Reference is `synth_sentence(DEFAULT_WORDS)` (alpha, bravo, charlie, delta, echo; 227 trimmed frames) unless noted. Values measured at `8316388` with `/private/tmp/.../measure.py` style runs (seeds fixed in the tests).

| Rule | Perturbation | Fired? | Measured values |
|------|--------------|--------|-----------------|
| (none) | self-compare | no issue, no tip | overall 1.000; stress ref = user per word; pauses [] |
| EXTRA_PAUSE | +500 ms after word 0 | yes, wordIndex 0 | refMs 30, userMs 530 (align cost 0.456) |
| EXTRA_PAUSE | +500 ms after word 1 / word 3 | yes, wordIndex 1 / 3 | userMs 530 each |
| EXTRA_PAUSE | +300 ms after word 2 | yes, wordIndex 2 | userMs 330 |
| EXTRA_PAUSE | same 500 ms pause in the original too | no | gate: original pause >= 100 ms |
| FINAL_CONTOUR | last word rises instead of falls | yes | refSlope -16.5, userSlope 13.8 st/s (both inside [6, 30]) |
| PITCH_DEVIATION | +4 st on word 2 | yes, wordIndex 2 | meanDiffSt 3.2 |
| PITCH_DEVIATION | +4 st on word 0 / -4 st on word 3 | yes | 3.1 / -3.3 |
| PITCH_DEVIATION | +2 st on word 2 | no | below 3 st |
| PITCH_DEVIATION | whole sentence +4 st (f0_scale) | no issue at all | sentence offset removed |
| STRESS_MISMATCH | ref word 1 boosted (+5 st, +6 dB); learner boosts word 3 (+6 st, +6 dB) | yes, wordIndex 1 | refWord bravo, userWord delta; ref z bravo 1.48, user z delta 1.14 (the swap also raises PITCH_DEVIATION on words 1 and 3: -4.3, +5.5) |
| STRESS_MISMATCH | learner repeats the original pattern | no | tops agree |
| FLAT_PITCH | learner flat 180 Hz | yes, only issue | pitchRange 0.0015; tip "Giọng hơi phẳng; ..." issueRef 0 |
| FLAT_PITCH | flat original (180 Hz) vs flat learner (185 Hz) | no | std(ref) below 2 st gate |
| D-02 | pause, +4 st, stress swap, flat, reversed glide with forced not-ok alignment | only FLAT_PITCH (flat) and FINAL_CONTOUR (glide) | word-level rules silent |

All expectations of the plan were met with the approved thresholds. Note for Liam: the +4 st perturbation is measured as 3.1 to 3.3 st because F0 smoothing and the per-word median shave a little off a step edge, so it clears the 3.0 st threshold narrowly. That is the precision-first behaviour of D-13, not a sign of a bug; Phase 4 tunes it on real clips. Recall on real speech for STRESS_MISMATCH and FINAL_CONTOUR is low by design (RESEARCH Pitfalls 4 and 8); these synthetic cases only prove each rule is correct when its condition is true.

## Final template strings for Liam's PR review (P3-G18)

`*word*` marks a word (client underlines it); every `*` inside an inserted word is removed first.

| Code | Template |
|------|----------|
| STRESS_MISMATCH | `Nhấn vào *{refWord}*, không phải *{userWord}*.` |
| EXTRA_PAUSE | `Đọc liền qua *{word}*, đừng ngắt ({userMs} ms).` (`word` = word at `wordIndex`; ms rounded to an integer) |
| FINAL_CONTOUR (original falls) | `Xuống giọng ở cuối câu, ở *{lastWord}*; bạn đang lên giọng.` |
| FINAL_CONTOUR (original rises) | `Lên giọng ở cuối câu, ở *{lastWord}*; bạn đang xuống giọng.` |
| PITCH_DEVIATION (meanDiffSt > 0) | `Bạn đang đọc cao hơn bản gốc ở *{word}*; hạ giọng xuống.` |
| PITCH_DEVIATION (meanDiffSt < 0) | `Bạn đang đọc thấp hơn bản gốc ở *{word}*; nâng giọng lên.` |
| FLAT_PITCH | `Giọng hơi phẳng; lên xuống rõ hơn theo bản gốc.` |

## TDD Gate Compliance

- **Task 1 RED** (`b76d15c`): `pytest tests/test_scoring_rules.py` gave 4 failed / 3 passed. Failing targets, all on planned assertions against interface skeletons that return empty values: self-compare (`assert [] == ['alpha', 'bravo', ...]`, stress entries absent), flat learner (`assert [] == ['FLAT_PITCH']`), result validates (`assert [] == ['FLAT_PITCH']`), `flat_pitch` fires (`assert None is not None`). The 3 passing tests are the negative gate cases (flat original skipped, pitchRange not low, learner not flatter); they hold trivially against the skeleton and are recorded as characterization, not red-to-green. **GREEN** `25b933b`: 24 passed (rules + pipeline).
- **Task 2 RED** (`f9ff77a`): rules tests 14 failed / 32 passed with assertion failures on the positive cases of the four rules (for example `assert None is not None` for `final_contour`, `assert [] == [...]` for `pitch_deviation`/`extra_pause`, and the D-02 test missing FINAL_CONTOUR); the 32 passing are negative gate cases and Task 1 cases against skeletons. `test_scoring_prominence.py` (12 tests) passes immediately because it characterizes the prominence code from Task 1; it was not red-to-green. **GREEN** `4f80ccb`: 58 passed (rules + prominence), 126 across all scoring tests.
- **Task 3 RED** (`920d104`): tips tests 11 failed / 7 passed; failures are assertion mismatches (`render_tip` returned None, `select_tips` returned only FLAT_PITCH tips); passing ones are the render-nothing and empty cases. **GREEN** `8316388`: 64 passed (tips + rules); full suite 994 passed.
- **REFACTOR:** none needed.
- The `gsd_run check tdd-red-evidence` classifier was not run (pytest default output; plan is `type: execute`, `tdd_mode` not enabled).

## Decisions Made

- No threshold, model or contract changed. `thresholds.py` was not edited; `git log` for it lists only `4f95d44` (03-03). `score.ts` untouched.
- The 3-frame edge margin and the +-10 frame original-pause window of EXTRA_PAUSE come from the plan text and are not in item E, so they are named constants in `engine.py` (`_PAUSE_EDGE_FRAMES`, `_PAUSE_REF_WINDOW_FRAMES`), not new thresholds. Flag for Liam if he wants them in the versioned file in a later plan.
- `pause_entries` assigns a learner silent run to the inter-word gap nearest to the mapped centre (within 100 ms), so the chart pause list and the EXTRA_PAUSE rule agree on the DTW stretch behaviour measured in this plan (a 530 ms pause is compressed 2:1 across about 26 reference frames and its centre lands on the word end).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] FLAT_PITCH needs a voiced-frame gate**
- **Found during:** Task 1
- **Issue:** `pitchRange` returns 0.0 when a side has fewer than `MIN_COMMON_VOICED_FRAMES` pitch frames, so an unvoiced or whispered attempt would be told "Giọng hơi phẳng" when the pitch simply could not be measured. The plan's prohibition lists the voiced-frame gate.
- **Fix:** `flat_pitch` returns None unless both sides have at least `MIN_COMMON_VOICED_FRAMES` finite frames (existing threshold, no new number).
- **Files modified:** `services/audio/src/audio_service/rules/engine.py`
- **Verification:** Task 1 and silent/empty-learner pipeline tests pass.
- **Committed in:** `25b933b`

**2. [Rule 2 - Missing critical] EXTRA_PAUSE ambiguity and tip render fallbacks**
- **Found during:** Task 2 and Task 3
- **Issue:** RESEARCH Pitfall 7 (a tip naming the wrong word is worse than none): when two word ends lie within the snap distance of a pause the word is ambiguous; and a tip must never be built from a missing or empty word.
- **Fix:** EXTRA_PAUSE is skipped unless exactly one word end is within `PAUSE_WORD_SNAP_MS`; `render_tip` returns None for a missing/blank word or odd data, and `select_tips` then uses the best renderable issue of that code.
- **Files modified:** `rules/engine.py`, `rules/tips.py`
- **Verification:** `test_an_issue_without_a_safe_wording_renders_nothing`, `test_an_unrenderable_issue_falls_back_...`
- **Committed in:** `4f80ccb`, `8316388`

---

**Total deviations:** 2 auto-fixed (both Rule 2, precision gates). **Impact on plan:** none on scope, contract or thresholds; both only make the rules say less when unsure.

## Issues Encountered

- The worktree had no `.venv`; ran `uv sync --frozen` from the existing lockfile (no packages added, lockfile unchanged).
- Shell guard of the harness rejected compound git and heredoc commands; commands were split. No effect on results.

## Known Stubs

None.

## Threat Flags

None. T-03-14 (word text inside `Tip.text`) is mitigated and tested (asterisks stripped, blank words skipped); T-03-15 (false positives) is mitigated by the gates, the D-02 restriction and the zero-issue self-compare test. No new endpoint, file access or schema change.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 03-05 receives `issues` and `tips` from `score_prosody` with no change to its call; `timing_ms["rules"]` is now a real measurement.
- 03-07/03-08 can render `prosody.stress` (z-scores, may be negative, NaN words written as 0.0), `prosody.pauses`, and tips with `*word*` markers.
- 03-11 smoke on real recordings is still the first contact with real voices; alignment threshold and rule recall on Vietnamese-accented speech are unmeasured (RESEARCH A1, A2, A10). Phase 4 tunes thresholds with `make eval`; this plan changed no threshold, so no metric table applies (03-01 item K).

## Self-Check: PASSED

- FOUND: all 9 files listed under key-files (7 created, 2 modified)
- FOUND commits b76d15c, 25b933b, f9ff77a, 4f80ccb, 920d104, 8316388 on this branch
- `uv run --frozen pytest tests -q`: 994 passed; `ruff check` and `ruff format --check` clean
- `git log -- scoring/thresholds.py` lists no 03-06 commit; engine.py imports thresholds, uses `PITCH_DEVIATION_ST`, `STRESS_MARGIN_Z` and `theilslopes`

---
*Phase: 03-p2-ch-m-ng-i-u*
*Completed: 2026-10-09*
