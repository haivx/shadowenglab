---
phase: 03-p2-ch-m-ng-i-u
reviewed: 2026-10-11T01:50:00Z
depth: standard
files_reviewed: 84
files_reviewed_list:
  - CLAUDE.md
  - Makefile
  - apps/web/app/globals.css
  - apps/web/components/AttemptStrip.tsx
  - apps/web/components/IntonationChart.tsx
  - apps/web/components/PracticeHeader.tsx
  - apps/web/components/PracticeRoom.tsx
  - apps/web/components/ResultActionBar.tsx
  - apps/web/components/ResultPanel.tsx
  - apps/web/components/ScoreHero.tsx
  - apps/web/components/SentenceStatePanel.tsx
  - apps/web/components/TipList.tsx
  - apps/web/components/TranscriptList.tsx
  - apps/web/components/ui/collapsible.tsx
  - apps/web/lib/api.test.ts
  - apps/web/lib/api.ts
  - apps/web/lib/attemptChips.test.ts
  - apps/web/lib/attemptChips.ts
  - apps/web/lib/chartData.test.ts
  - apps/web/lib/chartData.ts
  - apps/web/lib/player/playerMachine.test.ts
  - apps/web/lib/player/playerMachine.ts
  - apps/web/lib/player/shortcuts.test.ts
  - apps/web/lib/player/shortcuts.ts
  - apps/web/lib/player/useShortcuts.ts
  - apps/web/lib/progressView.test.ts
  - apps/web/lib/progressView.ts
  - apps/web/lib/queries.ts
  - apps/web/lib/resultView.test.ts
  - apps/web/lib/resultView.ts
  - apps/web/lib/scoreLevel.test.ts
  - apps/web/lib/scoreLevel.ts
  - apps/web/lib/tipHighlight.test.ts
  - apps/web/lib/tipHighlight.ts
  - apps/web/lib/tipMarkup.test.ts
  - apps/web/lib/tipMarkup.ts
  - apps/web/lib/viewedAttempt.test.ts
  - apps/web/lib/viewedAttempt.ts
  - apps/web/package.json
  - docs/decisions/0006-cham-ngu-dieu-p2.md
  - packages/contracts/fixtures/ApiError.json
  - packages/contracts/fixtures/AttemptSummary.json
  - packages/contracts/fixtures/LessonProgress.json
  - packages/contracts/schema/contracts.schema.json
  - packages/contracts/src/api.ts
  - packages/contracts/src/attempt.ts
  - packages/contracts/src/contracts.test.ts
  - packages/contracts/src/index.ts
  - pnpm-lock.yaml
  - scripts/README.md
  - scripts/smoke_score.py
  - services/audio/src/audio_service/config.py
  - services/audio/src/audio_service/contracts_gen.py
  - services/audio/src/audio_service/db.py
  - services/audio/src/audio_service/lesson/pipeline.py
  - services/audio/src/audio_service/lesson/vad.py
  - services/audio/src/audio_service/routers/attempts.py
  - services/audio/src/audio_service/routers/library.py
  - services/audio/src/audio_service/rules/__init__.py
  - services/audio/src/audio_service/rules/engine.py
  - services/audio/src/audio_service/rules/tips.py
  - services/audio/src/audio_service/scoring/__init__.py
  - services/audio/src/audio_service/scoring/align.py
  - services/audio/src/audio_service/scoring/features.py
  - services/audio/src/audio_service/scoring/metrics.py
  - services/audio/src/audio_service/scoring/prominence.py
  - services/audio/src/audio_service/scoring/ref_cache.py
  - services/audio/src/audio_service/scoring/scorer.py
  - services/audio/src/audio_service/scoring/thresholds.py
  - services/audio/tests/synth.py
  - services/audio/tests/test_attempts_api.py
  - services/audio/tests/test_db.py
  - services/audio/tests/test_library_api.py
  - services/audio/tests/test_pipeline.py
  - services/audio/tests/test_scoring_align.py
  - services/audio/tests/test_scoring_api.py
  - services/audio/tests/test_scoring_features.py
  - services/audio/tests/test_scoring_metrics.py
  - services/audio/tests/test_scoring_pipeline.py
  - services/audio/tests/test_scoring_prominence.py
  - services/audio/tests/test_scoring_rules.py
  - services/audio/tests/test_scoring_tips.py
  - services/audio/tests/test_smoke_score.py
  - services/audio/tests/test_vad.py
findings:
  critical: 0
  warning: 7
  info: 6
  total: 13
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-11T01:50:00Z
**Depth:** standard
**Files Reviewed:** 84
**Status:** issues_found

## Summary

The review covered the whole Phase 3 scope. The scoring and rules pipeline got the most attention, followed by the attempts router, the DB layer and the web result and tip rendering. `apps/web/components/AppHeader.tsx` is the user's in-progress edit, so it was not reviewed. `pnpm-lock.yaml`, the JSON fixtures and the schema got only a sanity glance.

Verification run during the review:
- `vitest run` in `apps/web` passed 291 of 291.
- The scoring, tips, rules, metrics, prominence, align, db and attempts-api pytest modules passed 226 of 226.
- I wrote scratch probes for DTW path validity, tip selection and the two edge cases behind WR-03 and WR-04. Both are confirmed by direct execution.

Overall the scoring core is sound. The DTW backtracking is consistent, the paths are monotone and cover every reference frame, and the rule gates are conservative (precision first). Scores are clamped and finite, tips never render HTML, uploads are bounded and whitelisted, and every SQL statement is parameterised.

I found no data-loss or security blockers. The defects are:
- robustness gaps on the request path (a cache-write race, an unvalidated integer path parameter, a header-parsing crash);
- one precision-first violation in a tip;
- a layout misalignment in the intonation chart;
- a few contract and consistency issues.

## Warnings

### WR-01: Sidecar cache write uses a fixed `.part` name, so concurrent first scorings race and can fail the request

**File:** `services/audio/src/audio_service/scoring/ref_cache.py:80-101` (called from `services/audio/src/audio_service/lesson/pipeline.py:481-482`)
**Issue:** `write_ref_prosody` always writes to `<name>.part`, then calls `os.replace`. `create_attempt` is a sync endpoint, so it runs in a thread pool. Two requests for the same segment that both miss the cache (two tabs, a double submit, or a retry racing a slow first request) interleave as follows:
1. Both open the same `.part` with `"wb"`, and the second truncates the first writer's file.
2. The first `os.replace` moves the file away.
3. The second `os.replace` raises `FileNotFoundError`.

That exception is not caught anywhere on the path (`ref_prosody_for_segment` only catches `OSError` and `LibsndfileError` around the stem read). The user gets a 500 for a score that was fully computable. A failing cache write, such as a full disk or read-only data directory, also fails the whole attempt, even though the cache is only an optimisation. `_store_eval_clip` has the same fixed-name `.part` pattern.
**Fix:** Use a unique temp name and treat the cache write as best-effort.
```python
# ref_cache.py
import tempfile
fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=out.name + ".", suffix=".part")
try:
    with os.fdopen(fd, "wb") as handle:
        np.savez_compressed(handle, ...)
    os.replace(tmp, out)
finally:
    Path(tmp).unlink(missing_ok=True)

# pipeline.py, around line 481
if write_cache:
    try:
        ref_cache.write_ref_prosody(lesson.id, index, window, feats)
    except OSError:
        logger.warning("không ghi được sidecar prosody của bài %s câu %d", lesson.id, index)
```

### WR-02: `PUT .../eval-clip` does not bound `attempt`, so a huge value gives a 500 (`OverflowError`)

**File:** `services/audio/src/audio_service/routers/attempts.py:320-325`
**Issue:** `get_attempt` guards the path parameter with `1 <= attempt <= MAX_ATTEMPT_NUMBER`. `save_eval_clip` passes the raw path integer straight to `db.get_attempt`. Python ints are unbounded, and sqlite3 raises `OverflowError: Python int too large to convert to SQLite INTEGER` above 2^63-1 (reproduced). The result is a generic 500 instead of the documented 404. There is no test for this.
**Fix:** Apply the same bound as `get_attempt`.
```python
row = (
    db.get_attempt(lesson.id, index, attempt)
    if 1 <= attempt <= MAX_ATTEMPT_NUMBER
    else None
)
if row is None:
    raise ApiErrorException(404, "not_found", "Không tìm thấy lượt này.")
```
Better still, move the bound into `db.get_attempt`, `get_attempt_result_json` and `mark_saved_for_eval`, so no caller can forget it.

### WR-03: `content-length` check uses `str.isdigit()`, so a non-ASCII digit header crashes the route with a 500

**File:** `services/audio/src/audio_service/routers/attempts.py:71-73`
**Issue:** `declared.isdigit()` is true for Unicode digits such as `"\xb2"`, which Starlette can deliver because headers are decoded as latin-1. `int(declared)` then raises `ValueError` (reproduced), outside any `try`. An untrusted client can turn the size guard into an unhandled 500. This is the T-02-26 guard, which is supposed to be the first line of defence for untrusted input.
**Fix:**
```python
if declared.isascii() and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
    raise _too_large()
```

### WR-04: `STRESS_MISMATCH` can produce a nonsensical tip when the two words are textually identical

**File:** `services/audio/src/audio_service/rules/engine.py:278-289`, `services/audio/src/audio_service/rules/tips.py:124-129`
**Issue:** The rule compares word positions (`ref_top == user_top`) but never the word text. In a sentence with a repeated word, such as "the ... The", the issue is emitted with `refWord == userWord`. I reproduced the tip text "Nhấn vào *the*, không phải *The*." That is wrong to show, which violates the precision-first principle in CLAUDE.md.

On the client, `tipHighlight.ts:53-57` resolves `you` by `findWord(userWord)`, which returns the first match. The same word can then be painted as both "original" and "you", and the user cannot tell which occurrence is meant. The contract carries only text and no user index, so the client cannot disambiguate.
**Fix:** Do not report an issue the tip cannot express.
```python
# engine.stress_mismatch, after computing ref_top/user_top
if inp.words[ref_top].strip().lower() == inp.words[user_top].strip().lower():
    return None
```
Alternatively, add the check in `tips.render_tip` for `STRESS_MISMATCH` so such an issue yields no tip. Raising the issue to the contract with word indexes needs Liam's approval, since contracts are frozen.

### WR-05: Word row in `IntonationChart` is not aligned with the plot when the first word does not start at x = 0

**File:** `apps/web/lib/chartData.ts:62-82`, used at `apps/web/components/IntonationChart.tsx:91-94,214-250`
**Issue:** `wordCells` normalises widths over `pointCount - wordBounds[0]`. The first cell therefore starts at the left edge of the row. The plot, the `ReferenceArea` highlights and the pause markers all place things at absolute x (`wordBounds[i]` on a `[0, lastX]` axis). `wordBounds[0]` is the first word's start on the trimmed reference axis. After trimming (5 frames of margin) and Whisper offsets it is generally greater than 0, roughly 2 to 5 contour points out of about 100 to 200. The word labels and stress bars then sit slightly left of the plot region they describe, and the error accumulates across the row. The last cell also divides by `pointCount` where the axis uses `lastX = pointCount - 1`. The unit tests only use `wordBounds[0] === 0`, so this is untested.
**Fix:** Make the word row share the plot's coordinate system by adding a leading spacer, and compute shares against the same denominator as the axis.
```ts
export function wordCells(wordBounds, pointCount) {
  const first = wordBounds[0];
  if (first === undefined || pointCount <= 1) return { lead: 0, widths: [] };
  const span = pointCount - 1; // = lastX
  const edges = [...wordBounds, span];
  const widths = wordBounds.map((_, i) => Math.max((edges[i + 1]! - edges[i]!) / span, MIN_SHARE));
  return { lead: first / span, widths };
}
```
Render `lead` as an empty `div` before the cells. Add a test with `wordBounds[0] > 0`.

### WR-06: Sidecar validation does not check the MFCC width or finiteness, so a bad file turns into a 500 later

**File:** `services/audio/src/audio_service/scoring/ref_cache.py:64-77`
**Issue:** `read_ref_prosody` checks the frame count `n` against `f0_st`, `voiced`, `energy_db` and `mfcc.shape[0]`. It does not check `mfcc.shape[1] == 12`, that `trim_start <= trim_end`, or that the arrays are finite or `f0_st`-compatible. A hand-edited, truncated or older-layout sidecar that still has a matching `feat_version` and window passes validation. `pairwise_dist` then fails with a broadcasting `ValueError` inside `align`, which gives a 500 instead of the documented "recompute" fallback. The module docstring promises that any bad file is treated as no cache.
**Fix:** Add `feats.mfcc.shape[1] == 12` (export `N_MFCC` from `features.py`), `0 <= trim_start <= trim_end`, and `np.isfinite(feats.energy_db).all()` to the `consistent` condition.

### WR-07: With `saveForEval=true` a failed clip write returns 500 after the attempt is already committed

**File:** `services/audio/src/audio_service/routers/attempts.py:243-269`
**Issue:** `insert_scored_attempt` commits the attempt first. If `_store_eval_clip` then fails (disk full, permissions), the handler raises a 500 even though the attempt exists and was scored. The client treats it as an upload failure and offers "Thử lại", which creates a duplicate attempt and consumes another attempt number. The web client currently always sends `saveForEval: false`, so this is latent. The server contract still allows it, and the ADR states that a scoring failure inserts nothing, which does not hold for this path.
**Fix:** Catch `OSError` around `_store_eval_clip` and `mark_saved_for_eval`, log it, and return the `ScoreResult` anyway. The client can retry through the dedicated `PUT .../eval-clip`. Alternatively, write the clip before the transaction and mark it afterwards.

## Info

### IN-01: Retry after a lost or unparseable 201 duplicates the attempt

**File:** `apps/web/lib/api.ts:86-93`, `apps/web/lib/player/playerMachine.ts:452-469`
**Issue:** If the server commits the attempt but the response is lost (network drop, timeout) or `ScoreResult.parse` throws a `ZodError`, the machine goes to `error`. "Thử lại" (`RETRY_UPLOAD`) re-uploads the blob and creates a second attempt. The result is an extra chip and a skewed "Lượt k". There is no idempotency key.
**Fix:** Accept it as a documented limitation, or have `RETRY_UPLOAD` refresh `listAttempts` first and adopt a newer attempt. Also catch `ZodError` in `request` and surface it as a distinct code, so a parse failure is not presented as "upload failed".

### IN-02: `word_bounds` is not strictly increasing when there are more words than contour points

**File:** `services/audio/src/audio_service/scoring/metrics.py:146-160`
**Issue:** The clamp loop `max(0, min(bounds[i], limit))` goes negative on `limit` when `len(bounds) > length`. Reproduced: `word_bounds([(0,0)]*5, 2, length=3)` returns `[0, 0, 0, 1, 2]`. The docstring and the contract consumers (the chart, `pauseMarkerXs`) assume strictly increasing bounds. This needs a degenerate clip, such as a very short reference with many zero-length words, so it is an edge case only.
**Fix:** Skip the clamp, or cap the bounds count at `length`, when `len(frames) > length`.

### IN-03: Query-key prefix overlap causes unnecessary refetches

**File:** `apps/web/lib/queries.ts:16-26`, `apps/web/components/PracticeRoom.tsx:444-446`, `apps/web/components/AttemptStrip.tsx:62-64`
**Issue:** `attemptResult(...)` is a key extension of `attempts(...)`, and both are extensions of `lesson(id)`. `invalidateQueries({queryKey: queryKeys.attempts(...)})` after each scoring also marks every cached stored `attemptResult` stale. Those entries are meant to be immutable (`staleTime: Infinity`) and are about to be re-fetched when viewed. `invalidateQueries({queryKey: queryKeys.lesson(id)})` in `AttemptStrip` invalidates progress and attempts as well.
**Fix:** Use disjoint key roots for the list and the detail (for example `["attemptResults", ...]`), or pass `exact: true` where only the list is meant.

### IN-04: Stale docstring in `thresholds.py`

**File:** `services/audio/src/audio_service/scoring/thresholds.py:8-10`
**Issue:** The header says the trailing constants (Layer C rules and prominence) are "chưa dùng ở 03-03; chúng nằm sẵn đây để 03-06 import". They are now used by `engine.py`, `prominence.py` and `metrics.py`, so the comment is misleading.
**Fix:** Drop that paragraph.

### IN-05: Cross-module private import and duplicated silence-mask logic

**File:** `services/audio/src/audio_service/scoring/prominence.py:15`, `services/audio/src/audio_service/scoring/metrics.py:44-55`
**Issue:** `prominence` imports the private `_true_runs` from `metrics`. `metrics.speech_frames` re-implements the same "dB ≤ p95 − 35" mask that `prominence.silent_mask` defines. The two copies can drift apart, and `speed` and the pause rules should agree on what counts as silence.
**Fix:** Make `true_runs` public (or move it to a small `_frames.py`), and have `speech_frames` reuse `silent_mask`.

### IN-06: Unmeasured word prominence is encoded as 0.0 in `stress`

**File:** `services/audio/src/audio_service/scoring/prominence.py:94-105`, `apps/web/lib/chartData.ts:90-117`
**Issue:** NaN prominence (a word with fewer than 3 voiced frames) is written as `0.0` to satisfy the contract's `z.number()`. A z-score of 0 is also a legitimate "average" value, so the UI draws a mid-height bar for an unmeasured word. In rare cases `topStressWord` can bold it. The rules already exclude NaN, but the client cannot.
**Fix:** This needs a contract change (`ref`/`user` nullable) or a sentinel agreed with Liam. Until then, document the conflation in `chartData.ts`.

---

_Reviewed: 2026-10-11T01:50:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
