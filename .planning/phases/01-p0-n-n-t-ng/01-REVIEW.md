---
phase: 01-p0-n-n-t-ng
reviewed: 2026-10-06T00:00:00Z
depth: standard
files_reviewed: 65
files_reviewed_list:
  - .prettierignore
  - .prettierrc
  - Makefile
  - apps/eval/app/layout.tsx
  - apps/eval/app/page.tsx
  - apps/eval/next.config.mjs
  - apps/eval/package.json
  - apps/eval/tsconfig.json
  - apps/web/app/layout.tsx
  - apps/web/app/page.tsx
  - apps/web/next.config.mjs
  - apps/web/package.json
  - apps/web/tsconfig.json
  - eslint.config.mjs
  - package.json
  - pnpm-workspace.yaml
  - tsconfig.base.json
  - packages/contracts/package.json
  - packages/contracts/tsconfig.json
  - packages/contracts/src/common.ts
  - packages/contracts/src/lesson.ts
  - packages/contracts/src/score.ts
  - packages/contracts/src/eval.ts
  - packages/contracts/src/index.ts
  - packages/contracts/src/generate.ts
  - packages/contracts/src/cli-parse.ts
  - packages/contracts/src/contracts.test.ts
  - scripts/check_deps.sh
  - scripts/contracts_check.sh
  - scripts/contracts_gen.sh
  - scripts/dev_smoke.sh
  - scripts/smoke_lesson.py
  - services/audio/pyproject.toml
  - services/audio/src/audio_service/__init__.py
  - services/audio/src/audio_service/config.py
  - services/audio/src/audio_service/contract_io.py
  - services/audio/src/audio_service/main.py
  - services/audio/src/audio_service/models.py
  - services/audio/src/audio_service/setup_models.py
  - services/audio/src/audio_service/routers/__init__.py
  - services/audio/src/audio_service/routers/lesson.py
  - services/audio/src/audio_service/routers/scoring.py
  - services/audio/src/audio_service/lesson/__init__.py
  - services/audio/src/audio_service/lesson/audio_io.py
  - services/audio/src/audio_service/lesson/download.py
  - services/audio/src/audio_service/lesson/features.py
  - services/audio/src/audio_service/lesson/pipeline.py
  - services/audio/src/audio_service/lesson/quality.py
  - services/audio/src/audio_service/lesson/segment.py
  - services/audio/src/audio_service/lesson/separate.py
  - services/audio/src/audio_service/lesson/timing.py
  - services/audio/src/audio_service/lesson/transcribe.py
  - services/audio/src/audio_service/lesson/urls.py
  - services/audio/tests/test_api.py
  - services/audio/tests/test_config.py
  - services/audio/tests/test_contract_io.py
  - services/audio/tests/test_contracts_drift.py
  - services/audio/tests/test_contracts_roundtrip.py
  - services/audio/tests/test_features.py
  - services/audio/tests/test_pipeline.py
  - services/audio/tests/test_quality.py
  - services/audio/tests/test_segment.py
  - services/audio/tests/test_setup.py
  - services/audio/tests/test_urls.py
findings:
  critical: 0
  warning: 6
  info: 5
  total: 11
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-10-06
**Depth:** standard
**Files Reviewed:** 65
**Status:** issues_found

## Summary

Reviewed the P0 foundation: workspace config, the Zod contracts and codegen gate, the FastAPI
service, the lesson pipeline (yt-dlp, ffmpeg, Demucs, Whisper, segmentation, F0/PPG) and the
dev/smoke scripts. No structural (fallow) findings were supplied. External reviewer evidence was
not supplied.

The security-sensitive boundaries hold up. `parse_youtube_url` is strict. All path helpers
validate ids by regex and also check containment after `resolve()`. ffmpeg runs with an argv list,
yt-dlp only ever receives `canonical_watch_url`, and the HTTP surface is GET-only with a CORS
allow-list. No hardcoded secrets or dangerous calls were found. Locked values from 01-01-SUMMARY
(thresholds, Demucs knobs, contract bounds) all match the code, and I report none against them.

I found no BLOCKER-class issues. Several robustness defects will surface in real use, though.
The main ones are:
- the data directory can silently resolve to the wrong place;
- F0, energy and PPG tracks are saved without the time axis a consumer needs to align them;
- some error-handling paths mask or misclassify real failures.

Verified by experiment in `services/audio/.venv`:
- `DATA_DIR=` (empty) gives `data_root() == services/audio`.
- `DATA_DIR=data` gives `services/audio/data`.
- For 1 s of audio, `extract_f0` returns 97 frames starting at t=0.02 s, while `frame_energy` returns 100 frames starting at t=0.

## Warnings

### WR-01: Empty or relative `DATA_DIR` resolves against the current working directory

**File:** `services/audio/src/audio_service/config.py:31,39-41`
**Issue:** `data_dir: Path` is read from `.env`, and `.env.example` ships other keys as empty
placeholders (`OPENAI_API_KEY=`). A user who leaves `DATA_DIR=` empty gets `Path("")`, which is
`.`. `data_root()` then resolves to the process CWD. I confirmed `DATA_DIR=` gives
`/…/services/audio`, so videos, stems and lessons are written inside the source tree. A relative
value such as `DATA_DIR=data` is also resolved against CWD. `make dev-api` runs with
`cd services/audio`, while `make smoke` and `dev_smoke.sh` run from the repo root. The same
`.env` therefore yields two different data roots: a lesson created by `make smoke` returns 404 from
the API. `_contained` cannot catch this, because it only compares against the already-wrong root.
**Fix:** Reject empty values and anchor relative paths to the repo root.
```python
from pydantic import field_validator

model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore", env_ignore_empty=True)

@field_validator("data_dir")
@classmethod
def _anchor(cls, v: Path) -> Path:
    v = v.expanduser()
    return v if v.is_absolute() else REPO_ROOT / v
```
With `env_ignore_empty=True`, an empty value falls back to the `~/shadowenglab-data` default.

### WR-02: Saved F0, energy and PPG tracks have different frame counts and no time origin

**File:** `services/audio/src/audio_service/lesson/features.py:23-29,32-48`; `pipeline.py:279-288`
**Issue:** The three tracks are saved to the `.npz` as independent arrays. They are not
frame-aligned, and the file stores only `f0_hop_s=0.01` and `ppg_fps=50`.
- Praat's first pitch frame is not at t=0. Measured on 1 s of audio: 97 F0 frames starting at 0.02 s.
- `frame_energy` yields `ceil(n/hop)`, so 100 frames centred from t=0.
- PPG has about 49 frames at 20 ms.

A Phase 3/5 consumer that indexes `f0[i]` against `energy[i]` or word boundaries (the contour and
`wordBounds` contract) will be off by about 20 ms. That error is silent, and it comes from the
reference side, which must be trustworthy under the precision-first rule. The first-frame time is
derivable only by re-running Praat. No test pins the alignment.
**Fix:** Persist the time origin from Praat and the frame-centre convention, and add a test that
the origin is correct.
```python
pitch = sound.to_pitch_ac(...)
f0 = np.asarray(pitch.selected_array["frequency"], dtype=np.float32)
t0 = float(pitch.xs()[0])  # return it, or put it in the npz as f0_t0_s
```
Alternatively, resample F0 onto the same `ceil(n/hop)` grid as `frame_energy` before saving.
Do the same for PPG, with `ppg_t0_s`.

### WR-03: `_real_separate` can mask the real error with `UnboundLocalError`

**File:** `services/audio/src/audio_service/lesson/pipeline.py:60-77`
**Issue:** In the MPS-fallback branch, `del separator` unbinds the name, then
`separate.load_separator("cpu")` runs. If that load raises (for example an HF/network or
out-of-memory error), the `finally: del separator` runs on an unbound local. It raises
`UnboundLocalError`, which replaces the original exception, so `lesson.json` records
`UnboundLocalError: cannot access local variable 'separator'…` instead of the actual cause.
**Fix:** Do not use `del` for control flow. Assign `separator = None` and guard the cleanup.
```python
separator: Any = separate.load_separator(device)
try:
    ...
        separator = None
        separate.free_accelerator_memory()
        separator = separate.load_separator("cpu")
        return separate.separate_vocals(stereo, sr, separator)
finally:
    separator = None
    separate.free_accelerator_memory()
```

### WR-04: `smoke_lesson.py` reports pipeline `ValueError`s as "bad URL or range" (exit 2)

**File:** `scripts/smoke_lesson.py:72-74`
**Issue:** `except (InvalidYoutubeUrl, ValueError)` is meant to catch input errors. But
`pydantic.ValidationError` and `json.JSONDecodeError` both subclass `ValueError`, and the pipeline
raises plain `ValueError` itself (`span rỗng`, empty or mismatched stems in `non_vocal_ratio`,
NaN in `write_json_atomic`). Any of those after the first write is a pipeline failure where
`lesson.json` already holds `failed` plus `error.step`. The script instead prints
`ERROR: …`, hides the step, and exits 2, which the README documents as "URL or range wrong". A
CI or budget wrapper that distinguishes 1 from 2 gets the wrong answer.
**Fix:** Catch only input errors that can occur before the first write, or make the pipeline's
pre-write validation raise a dedicated exception type.
```python
class InvalidRange(ValueError): ...  # raised in run_lesson before the first write
...
except (InvalidYoutubeUrl, InvalidRange) as exc:
```

### WR-05: Download fallback format can yield a non-mp4 file and then fail after a full download

**File:** `services/audio/src/audio_service/lesson/download.py:22,88-98`
**Issue:** `_FORMAT` ends with `/b`, and the `b[height<=480]` and `b` branches select a single
pre-merged stream. `merge_output_format="mp4"` only applies when yt-dlp merges, so a single-file
fallback keeps its native extension (for example `video.webm`). The code then checks only for
`video.mp4`, raises `RuntimeError("yt-dlp chạy xong nhưng không có video.mp4")` after the full
download, and the next run downloads it all again. The final `/b` branch can also pull a stream
well above 480p, contrary to the comment on `_FORMAT`.
**Fix:** Have yt-dlp normalise the container, and drop the unbounded fallback.
```python
opts = _base_opts() | {
    "format": _FORMAT,                       # "bv*[height<=480]+ba/b[height<=480]"
    "merge_output_format": "mp4",
    "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}],
    "outtmpl": str(video_dir(video_id) / "video.%(ext)s"),
}
```
Or resolve the real path from `info["requested_downloads"][0]["filepath"]` and rename it to `video.mp4`.

### WR-06: `cli-parse.ts` returns the same exit code for invalid JSON as for a Zod rejection

**File:** `packages/contracts/src/cli-parse.ts:17-26`; consumer `services/audio/tests/test_contracts_roundtrip.py:62-65`
**Issue:** The header comment documents exit 1 for "Zod refused the data". `JSON.parse(text)` sits
inside the same `try`, but a `SyntaxError` is not a `ZodError`, so it is re-thrown. Node's
uncaught-exception exit code is also 1. `zod_accepts` asserts `returncode in (0, 1)` and treats 1
as "rejected". An empty or garbled payload (for example a truncated pipe) is therefore counted as
a legitimate Zod rejection, and a negative test passes for the wrong reason.
**Fix:** Parse outside the Zod handling and give it its own code.
```ts
let json: unknown;
try { json = JSON.parse(text); } catch { process.stderr.write("Invalid JSON input\n"); process.exit(3); }
try { process.stdout.write(JSON.stringify(Schemas[name as SchemaName].parse(json))); }
catch (e) { if (e instanceof ZodError) { …; process.exit(1); } throw e; }
```
Update the test helper to assert `in (0, 1)` while treating 3 as a crash.

## Info

### IN-01: `_merge_short` never tries the other neighbour, and can exceed `MAX_WORDS`

**File:** `services/audio/src/audio_service/lesson/segment.py:113-134`
**Issue:** The docstring says a short span is merged into the neighbour with the smaller gap
"nếu kết quả <= MAX_MERGED_S". If that preferred merge is too long (line 129 `continue`), the
other neighbour is never tried. The short fragment stays under `MIN_DUR_S` even when merging with
the other side would fit. Merging also checks only duration, so a merged segment can exceed
`MAX_WORDS`. This is a tuning and quality issue, not a correctness bug, and the thresholds are
documented as starting values.
**Fix:** Try both neighbours in order of gap, and optionally cap the merged word count.

### IN-02: `make lint` type-checks only the contracts package, not the apps

**File:** `Makefile:46-51`
**Issue:** `tsc --noEmit` runs only for `@shadowenglab/contracts`. `apps/web` and `apps/eval`
(strict `tsconfig`s that import the contracts) are never type-checked by `make lint`. The apps'
Next config sets `eslint.ignoreDuringBuilds`, so type errors surface only in `next build`. That is
fine for P0's stubs but will hide TS regressions as soon as Phase 2 adds real UI.
**Fix:** Add `pnpm --filter @shadowenglab/web exec tsc --noEmit` (and the same for eval) to `lint`.

### IN-03: Feature `.npz` files are written non-atomically

**File:** `services/audio/src/audio_service/lesson/pipeline.py:279-288`
**Issue:** `lesson.json` and the wavs use a temp file plus `os.replace`, but `np.savez_compressed`
writes straight to the final path. `lesson.json` already lists `segments` during `analyzing`, so a
reader that opens `seg/NNNN.npz` early can see a half-written zip. This is harmless while status is
not `ready`, but it is inconsistent with the stated atomic-writes convention.
**Fix:** Write to `out.with_name(out.name + ".part")` via a file object, then `os.replace` it.

### IN-04: `smoke_lesson._self_check` uses `assert` for runtime validation

**File:** `scripts/smoke_lesson.py:49-54,115`
**Issue:** The self-check relies on `assert` and catches `AssertionError`. Under `python -O` all of
these checks vanish and the script prints `SELF-CHECK OK` without checking anything.
**Fix:** Raise an explicit `RuntimeError` (and catch it) instead of using `assert`.

### IN-05: Global `data/` and `*.wav`/`*.mp4` ignores will swallow test fixtures

**File:** `.gitignore:22-30` (outside the reviewed file list, found while verifying `DATA_DIR`)
**Issue:** `data/` and `models/` match at any depth. `git check-ignore` confirms that
`services/audio/tests/data/x.json` is ignored. A fixtures directory named `data`, or any committed
`.wav`/`.mp4` test clip, is silently dropped from commits. The golden-fixture work in later phases
will hit this.
**Fix:** Anchor the patterns (`/data/`, `/models/`) and add negations for test-fixture paths if needed.

---

_Reviewed: 2026-10-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
