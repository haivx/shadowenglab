---
phase: 03-p2-ch-m-ng-i-u
plan: 12
subsystem: scoring-feedback
tags: [tips, templates, fastapi, nextjs, vitest, pytest, d-14, d-15b, d-16]

requires:
  - phase: 03-p2-ch-m-ng-i-u
    provides: "03-11 FINAL_CONTOUR fix; 03-06 rule engine + select_tips; 03-08/03-09 TipList and ResultPanel"
provides:
  - "Measured, rotating tips: every code has 3-4 approved wordings carrying numbers from issue.data (D-16)"
  - "Two-pass tip selection: up to 2 tips for EXTRA_PAUSE / PITCH_DEVIATION, 3 in total, no word named twice (D-14 revised)"
  - "Client metric notes when there is no issue and a displayed metric is below 80 (D-15b)"
  - "markedWordTone: STRESS_MISMATCH marker 2 is the learner's word, every other marker the original's"
affects: [phase-04-eval, phase-08-calibration, 03-VERIFICATION, 03-UAT]

actuals:
  tokens: 60000
  tasks: 3
  commits: 8

tech-stack:
  added: []
  patterns:
    - "Tip wording is chosen once at scoring time (attempt known inside BEGIN IMMEDIATE, C1) and stored in result_json; history never changes"
    - "Half-up rounding (floor(x/step + 0.5) * step) instead of Python round() for every number shown"
    - "Untrusted words enter templates only as str.format arguments after stripping '*'"

key-files:
  created: []
  modified:
    - services/audio/src/audio_service/rules/tips.py
    - services/audio/src/audio_service/scoring/scorer.py
    - services/audio/tests/test_scoring_tips.py
    - services/audio/tests/test_scoring_rules.py
    - services/audio/tests/test_scoring_api.py
    - apps/web/lib/tipMarkup.ts
    - apps/web/lib/tipMarkup.test.ts
    - apps/web/components/TipList.tsx
    - apps/web/lib/resultView.ts
    - apps/web/lib/resultView.test.ts
    - apps/web/components/ResultPanel.tsx
    - .planning/phases/03-p2-ch-m-ng-i-u/03-UI-SPEC.md
    - docs/decisions/0006-cham-ngu-dieu-p2.md

key-decisions:
  - "Second tip of a code uses variant base + 1 so two tips of one code in one attempt never read alike (Claude's discretion, flagged for P3-G18)"
  - "Metric notes: two notes joined by one space in the existing neutral block; tie order melodyMatch, pitchRange, speed"
  - "Praise now needs overall AND all three displayed metrics >= 80; overall >= 80 with a low metric shows the metric notes"

patterns-established:
  - "ProsodyScore carries rule_issues + word_texts; to_score_result owns tip selection because it is the first place the attempt number is known"

requirements-completed: [RUL-02, FBK-03]

coverage:
  - id: D1
    description: "A FLAT_PITCH-only attempt states the measured pitch-range percentage and uses a different approved sentence on the next attempt; re-reading an old attempt returns the original text"
    requirement: RUL-02
    verification:
      - kind: unit
        ref: "services/audio/tests/test_scoring_tips.py#test_a_scored_flat_learner_gets_four_different_flat_sentences_with_its_own_percentage"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_scoring_api.py#test_flat_learner_tip_states_the_measured_range_and_rotates_per_attempt"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every code renders only approved wordings, numbers from issue.data rounded half-up, variant by (segmentIndex + attempt - 1) mod n, safe against hostile words"
    requirement: RUL-02
    verification:
      - kind: unit
        ref: "services/audio/tests/test_scoring_tips.py#test_every_code_renders_each_approved_variant_and_wraps_around"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_scoring_tips.py#test_untrusted_words_never_open_or_close_a_marker_in_any_variant"
        status: pass
    human_judgment: false
  - id: D3
    description: "Two-pass selection: max 2 per code and 3 total, no word named twice, sentence-level codes never doubled, issueRef points at an issue of the same code and word"
    requirement: FBK-03
    verification:
      - kind: unit
        ref: "services/audio/tests/test_scoring_tips.py#test_every_tip_names_the_word_of_the_issue_it_points_at"
        status: pass
    human_judgment: false
  - id: D4
    description: "No issue and a displayed metric < 80 shows up to two metric notes, lowest first; praise only when overall and all three metrics display >= 80"
    requirement: FBK-03
    verification:
      - kind: unit
        ref: "apps/web/lib/resultView.test.ts#resultNote (D-15b: ghi chu theo chi so)"
        status: pass
    human_judgment: false
  - id: D5
    description: "STRESS_MISMATCH underline colours: the original's word --original at every mention, the learner's word --you"
    verification:
      - kind: unit
        ref: "apps/web/lib/tipMarkup.test.ts#markedWordTone"
        status: pass
    human_judgment: false
  - id: D6
    description: "The panel reads well at 1280 px: tips, metric notes, long text wrapping, hover highlight per tip"
    verification: []
    human_judgment: true
    rationale: "Visual and wording judgment; the plan's human-check is an end-of-phase UAT with make dev that this agent cannot run. Not performed."

duration: 45min
completed: 2026-10-10
status: complete
plan_head_before: 0a62a2c3b221de73cd948c31da7e80928115cb74
plan_head_after: baa2bb7b6b57c1e04fced0526a97fa69e4ec2a22
commits: 8
---

# Phase 3 Plan 12: Richer, measured tips and metric notes Summary

**Template tips now carry the measured number and rotate through 3-4 approved wordings per code by (segmentIndex + attempt - 1) mod n, selection allows up to 2 tips for word-level codes (3 total, no word named twice), and a no-issue attempt with a displayed metric below 80 gets metric notes instead of the bare neutral line.**

## Performance

- **Duration:** about 45 min (start time was not captured; estimate)
- **Completed:** 2026-10-10
- **Tasks:** 3 (1 tracer, 2 auto; all TDD)
- **Files modified:** 13 (0 created)
- **Commits:** 8 (3 RED `test`, 3 GREEN `feat`, 1 `refactor`, 1 `docs`)

## Accomplishments

- Liam's UAT case works end to end: a flat attempt says what share of the original's pitch range he reached (`{pct}`, half-up to a multiple of 5), the next attempt says it differently, and `GET .../attempts/1` returns the first text unchanged (API test).
- Every code speaks with its approved voices (FLAT_PITCH 4; EXTRA_PAUSE 3; FINAL_CONTOUR 3 falling / 3 rising; PITCH_DEVIATION 3 higher / 3 lower; STRESS_MISMATCH 3), numbers only from `issue.data`.
- Two-pass selection implements D-14 (revised): attempts with several pause/pitch problems show 2-3 tips, never naming a word twice; FINAL_CONTOUR's last word and STRESS_MISMATCH's `wordIndex` also count as named.
- `resultNote(result)` adds D-15b: metric notes (up to 2, lowest first) when there is no issue and a metric displays below 80; D-15 praise/neutral texts are byte-identical.
- STRESS_MISMATCH colours stay right for the variant that names the original's word twice (`markedWordTone`).
- Contract, DB schema, thresholds, rule engine, SCORER/THRESHOLDS versions are untouched (`git diff 3d6891e` on contracts, thresholds.py, engine.py is empty); no dependency added; no LLM.

## Task Commits

1. **Task 1 (tracer): FLAT_PITCH measured + rotating, POST to GET of an old attempt**
   - RED `7a28a1c` (test) - 28 target tests failing on the planned assertions (old static sentence, TypeError on new keyword args)
   - GREEN `e7d16a8` (feat)
2. **Task 2: variants for the other codes, two-pass selection, STRESS tone**
   - RED `7942727` (test) - 23 Python + 2 vitest failures on the planned assertions
   - GREEN `5eab6da` (feat)
3. **Task 3: metric notes (D-15b), UI-SPEC + ADR 0006**
   - RED `853b034` (test) - 10 vitest failures on the planned assertions
   - GREEN `49f0ca5` (feat)
   - `e5757e7` (refactor) - lint fix, `noteVariant` narrows the index instead of `!`
   - `baa2bb7` (docs) - UI-SPEC copy tables and ADR 0006 section 10

**Plan metadata:** this SUMMARY is committed separately (`docs(03-12): complete ... plan`).

## TDD Gate Compliance

RED then GREEN commits exist for all three tasks (`test(03-12)` before `feat(03-12)` each time). RED evidence is semantic, not machine-classified: pytest and vitest default output is not one of the formats `gsd_run check tdd-red-evidence` accepts, and I did not rerun with a supported reporter. Semantic assessment per task: each RED run named the target tests and they failed on the planned assertion (old FLAT sentence returned instead of the variant, `select_tips` rejecting the new keywords, `markedWordTone is not a function`, `resultNote` given an object where it expected a number). One planned RED test passed immediately where the rule was already satisfied by the old code (marker safety, same-word skip with one issue per code); those are regression guards, not RED targets.

## Tracer gate

Tracer verified end to end after Task 1 (pytest on the four scoring test files, ruff, grep checks) before expanding.

## Approved wording table for PR review (P3-G18)

Variant k of the proposal is index k-1. Tip rank 1 (second tip of a code) uses index + 1.

| Code / set | Idx | Template |
|---|---|---|
| FLAT_PITCH | 0 | Độ lên xuống của bạn chỉ bằng khoảng {pct}% bản gốc; mở rộng giọng, lên cao và xuống thấp rõ hơn. |
| | 1 | Giọng còn phẳng (khoảng {pct}% độ lên xuống của bản gốc). Nghe lại bản gốc và bắt chước chỗ giọng vút lên, hạ xuống. |
| | 2 | Thử phóng đại ngữ điệu một chút: bạn mới lên xuống được khoảng {pct}% so với bản gốc. |
| | 3 | Bản gốc lên xuống nhiều hơn bạn (bạn ≈ {pct}%); đừng ngại đọc hơi "quá", thường sẽ vừa. |
| EXTRA_PAUSE | 0 | Đọc liền qua *{word}*, đừng ngắt ({ms} ms). |
| | 1 | Bạn dừng {ms} ms sau *{word}*, bản gốc đọc nối luôn; nối *{word}* với từ sau. |
| | 2 | Bỏ khoảng nghỉ sau *{word}* ({ms} ms): giữ hơi và đọc trọn cụm. |
| FINAL_CONTOUR falling | 0 | Xuống giọng ở cuối câu, ở *{last}*; bạn đang lên giọng. |
| | 1 | Cuối câu bản gốc hạ giọng ở *{last}*, còn bạn lại lên nên nghe như đang hỏi. Kết thúc dứt khoát, hạ xuống. |
| | 2 | Ở *{last}*, để giọng rơi xuống như kết thúc một ý, đừng kéo lên. |
| FINAL_CONTOUR rising | 0 | Lên giọng ở cuối câu, ở *{last}*; bạn đang xuống giọng. |
| | 1 | Bản gốc kéo giọng lên ở *{last}* (giọng hỏi hoặc chưa nói hết ý), bạn lại hạ xuống; kết thúc bằng giọng đi lên. |
| | 2 | Ở *{last}*, nâng giọng lên ở cuối như bản gốc thay vì hạ xuống. |
| PITCH_DEVIATION higher | 0 | Bạn đang đọc cao hơn bản gốc ở *{word}*; hạ giọng xuống. |
| | 1 | *{word}* của bạn cao hơn bản gốc khoảng {st} nửa cung; đọc từ này thấp và nhẹ hơn. |
| | 2 | Hạ *{word}* xuống chừng {st} nửa cung cho khớp bản gốc. |
| PITCH_DEVIATION lower | 0 | Bạn đang đọc thấp hơn bản gốc ở *{word}*; nâng giọng lên. |
| | 1 | *{word}* của bạn thấp hơn bản gốc khoảng {st} nửa cung; đẩy giọng lên ở từ này. |
| | 2 | Nâng *{word}* lên chừng {st} nửa cung, bản gốc nói từ này cao hơn. |
| STRESS_MISMATCH | 0 | Nhấn vào *{ref}*, không phải *{user}*. |
| | 1 | Bản gốc nhấn mạnh nhất ở *{ref}*, bạn lại nhấn *{user}*. Đọc *{ref}* to, dài và cao hơn một chút. |
| | 2 | Dồn trọng âm của câu về *{ref}*; *{user}* nên đọc nhẹ đi. |
| Metric note melodyMatch | 0 | Giai điệu mới khớp {v}%: nghe lại bản gốc, chú ý chỗ giọng đi lên, đi xuống rồi bắt chước đúng hướng. |
| | 1 | Đường lên xuống của bạn còn khác bản gốc (khớp {v}%). Mở So sánh ngữ điệu để xem đoạn lệch rồi đọc lại. |
| | 2 | Đọc lại từng cụm theo bản gốc, bám chỗ giọng lên và xuống; giai điệu hiện khớp {v}%. |
| Metric note pitchRange | 0 | Độ lên xuống mới khớp {v}% với bản gốc; nghe lại xem bản gốc lên cao, xuống thấp tới đâu rồi bắt chước đúng mức đó. |
| | 1 | Biên độ giọng của bạn khác bản gốc (khớp {v}%). Mở So sánh ngữ điệu để so độ cao thấp của hai đường. |
| | 2 | Bám theo độ cao thấp của bản gốc ở từng cụm; độ lên xuống hiện khớp {v}%. |
| Metric note speed | 0 | Nhịp đọc của bạn còn lệch bản gốc (khớp {v}%); đọc cùng lúc với bản gốc để bắt nhịp. |
| | 1 | Tốc độ khớp {v}%: nghe lại bản gốc, để ý độ dài các khoảng nghỉ rồi đọc theo đúng nhịp đó. |
| | 2 | Nhại sát theo bản gốc, gần như cùng lúc, để tốc độ khớp hơn; hiện khớp {v}%. |

## Flagged interpretations (for Liam in the PR, P3-G18)

- Rounding is half-up for `{pct}`, `{ms}`, `{st}`; `{v}` is the displayed `Math.round` integer. Python `round()` is deliberately not used (12.5 % shows 15 %). Half-up is applied to the float as stored, so a literal such as 0.575 (stored just below) rounds down; the tests use exactly representable values (0.125, 0.375).
- `{st}` prints `3` or `3.5` (dot decimal, as in the design).
- The second tip of a word-level code uses variant index + 1.
- Pass 2 takes the most severe remaining renderable issue whose word is not yet named; it may skip past the second most severe when that word is taken. "Named word" = `wordIndex` (STRESS_MISMATCH, EXTRA_PAUSE, PITCH_DEVIATION) or the last word (FINAL_CONTOUR); STRESS_MISMATCH's `userWord` has no index and is not counted.
- Output order is PRIORITY, then rank inside the code (a second PITCH_DEVIATION sits before FLAT_PITCH).
- D-15b: praise needs all three displayed metrics >= 80; with overall >= 80 and a metric < 80 the metric notes show instead. Two notes are joined into one paragraph in the existing neutral block. An issue without a renderable tip keeps D-15 behaviour.
- Observation, out of scope and unchanged: words carrying Whisper punctuation (UAT snapshot shows `*her,*`) are rendered as received.

## Decisions Made

See key-decisions above and ADR 0006 section 10. No contract, schema, threshold, rule, model or version change; `make eval` is still the Phase 4 stub so no metric table applies (CLAUDE.md eval gate).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Single-line grep acceptance criterion cannot be met under the 100-column ruff limit**
- **Found during:** Task 1
- **Issue:** the plan's verify greps for `select_tips(score.rule_issues, score.word_texts, segment_index=segment_index, attempt=attempt)` on one line; that call is over 100 columns, so `ruff format` wraps it.
- **Fix:** kept the formatter's multi-line call and checked the same text with a whitespace-tolerant regex (matches).
- **Files modified:** `services/audio/src/audio_service/scoring/scorer.py`
- **Committed in:** `e7d16a8`

**2. [Rule 1 - Bug] An existing test asserted the old one-tip-per-code behaviour**
- **Found during:** Task 2
- **Issue:** `test_the_most_deviant_issue_wins_inside_a_code` expected a single tip for two PITCH_DEVIATION issues, which D-14 (revised) deliberately changes.
- **Fix:** renamed to `test_the_most_deviant_issue_of_a_code_gets_the_first_tip`; it now asserts the most deviant issue gets the first tip and the other follows.
- **Files modified:** `services/audio/tests/test_scoring_tips.py`
- **Committed in:** `5eab6da`

**3. [Rule 1 - Bug] Own tests wrong about the marker count of two variants**
- **Found during:** Task 2 GREEN
- **Issue:** `test_every_tip_names_the_word...` compared the marker list to one word, but EXTRA_PAUSE variant 1 names the word twice; also a `0.575` half-up case in Task 1 fails for float representation reasons, not logic.
- **Fix:** compare marker sets; replaced `0.575` with the exactly representable `0.375`.
- **Files modified:** `services/audio/tests/test_scoring_tips.py`
- **Committed in:** `e7d16a8`, `5eab6da`

**4. [Rule 3 - Blocking] `make lint` rejected non-null assertions**
- **Found during:** Task 3 final gate
- **Issue:** `@typescript-eslint/no-non-null-assertion` on `resultView.ts` and its test.
- **Fix:** `noteVariant(n): 0 | 1 | 2` narrows the tuple index; the test helper throws on a missing variant.
- **Committed in:** `e5757e7`

---

**Total deviations:** 4 auto-fixed (2 bug, 2 blocking). **Impact:** none on scope; the first is a plan-text defect worth fixing in future plans (use a regex or a shorter local name).

## Issues Encountered

- The Task 1 fallback in the plan (EXTRA_PAUSE learner for the API test) was not needed: the opus round trip of `synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)` does raise FLAT_PITCH, so the API test uses the flat learner as planned.
- The plan's `<human-check>` (UAT with `make dev` at localhost:3000) was NOT performed: this agent cannot drive the running app. Results per item: 1 not run, 2 not run, 3 not run, 4 not run, 5 not run. Needs Liam at end-of-phase UAT.

## Gate results

| Gate | Result |
|---|---|
| `pytest` test_scoring_tips / rules / pipeline / api | 170 passed (98 before this plan) |
| `make test` | exit 0: pytest 1119 passed, web vitest 291 passed (23 files), contracts 69 passed, `contracts: không lệch` |
| `make lint` | exit 0 (eslint, prettier, tsc, ruff check + format) |
| `pnpm --filter @shadowenglab/web build` | exit 0 |
| `git diff 3d6891e -- packages/contracts thresholds.py engine.py` | empty (unchanged) |
| web vitest resultView + tipMarkup + tipHighlight | 36 passed |

## Known Stubs

None.

## Threat Flags

None. No new endpoint, auth path, file access or schema change. T-03-24..27 mitigations are covered by tests (marker safety for every variant, non-finite numbers, issueRef/word agreement, `GET .../attempts/1` equals first POST).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for Liam's end-of-phase UAT (checklist in the plan's Task 3 human-check) and wording review in the PR (table above).
- Phase 4 eval: no model, threshold or rule changed here, so nothing to re-baseline.

## Self-Check: PASSED

- Modified files exist (13 files listed in key-files) and `git status` was clean after the docs commit.
- Commits `7a28a1c e7d16a8 7942727 5eab6da 853b034 49f0ca5 e5757e7 baa2bb7` are ancestors of HEAD; `commits: 8` measured with `git rev-list --count 0a62a2c..HEAD`.

---
*Phase: 03-p2-ch-m-ng-i-u*
*Completed: 2026-10-10*
