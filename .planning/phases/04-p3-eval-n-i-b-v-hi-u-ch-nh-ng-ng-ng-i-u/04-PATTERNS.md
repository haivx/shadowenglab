# Phase 4: P3 Eval nội bộ và hiệu chỉnh ngưỡng ngữ điệu - Pattern Map

**Mapped:** 2026-10-11
**Files analyzed:** 14
**Analogs found:** 12 / 14 (all analogs verified git-tracked: `scripts/smoke_score.py`, `eval/README.md`; others under tracked src dirs)

Note: no RESEARCH.md; file list derived from CONTEXT.md. `eval/` currently holds only `README.md` (no `export_clips.py` exists, despite the README). `eval/` is NOT a Python package and not under the uv project `services/audio`; run scripts with `uv run --project services/audio --frozen python eval/<x>.py` (same as `smoke-score`).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `packages/contracts/src/eval.ts` (add `ErrorType`, `EvalCase`) | contract | transform | same file (`Label`, `ClipManifest`) + `score.ts` `IssueCode` | exact |
| `packages/contracts/src/index.ts` (add to `Schemas`) | config | transform | itself (`Schemas` registry, line ~33) | exact |
| `packages/contracts/schema/contracts.schema.json`, `services/audio/src/audio_service/contracts_gen.py` | generated | transform | `make contracts` output | generated, never hand-edit |
| `packages/contracts/src/contracts.test.ts` + fixtures (roundtrip) | test | request-response | `services/audio/tests/test_contracts_roundtrip.py` (fixtures dir of `*.json` with `{name,data}`) | role-match |
| `services/audio/src/audio_service/scoring/thresholds.py` (rule enable flags, bump `THRESHOLDS_VERSION`) | config | transform | itself | exact |
| `services/audio/src/audio_service/rules/engine.py` (honor flags in `run_rules`) | service | transform | itself, `run_rules` L292-306 | exact |
| `eval/evalkit.py` (shared module: load cases, resolve clips, rescore, counting, Wilson CI) | utility | batch | `scripts/smoke_score.py` | role-match |
| `eval/analyze.py` | CLI/batch | batch, file-I/O | `scripts/smoke_score.py` (`verdict`, `_run`, `main`) | role-match |
| `eval/sweep.py` | CLI/batch | batch | `scripts/smoke_score.py` | role-match |
| `eval/tag_clips.py` | CLI | file-I/O | `routers/attempts.py::_store_eval_clip` (sidecar format) + `smoke_score._choose_lesson` | partial |
| `eval/cases.jsonl`, `eval/report.md` | data | file-I/O | none (new artifact) | none |
| `Makefile` (`eval`, `eval-sweep`, `eval-tag`) | config | - | `smoke-score` target L61-62; stub `eval` L48-50 | exact |
| `.gitignore` | config | - | existing "Eval" block | exact |
| tests: `services/audio/tests/test_eval_*.py`, `test_scoring_rules.py` additions | test | - | `test_smoke_score.py` (loads script by path), `test_scoring_rules.py` | exact |
| `docs/decisions/0007-*.md` | doc | - | `docs/decisions/0006-cham-ngu-dieu-p2.md` | exact |

## Pattern Assignments

### `packages/contracts/src/eval.ts` (contract)

**Analog:** same file lines 1-54, plus `score.ts` lines 4-15.

Header and convention (every schema has `.meta({ id })`, otherwise `generate.ts` throws "thiếu .meta({ id })"; also type export at bottom):
```typescript
import * as z from "zod";
import { IsoTimestamp, Milliseconds, Score01 } from "./common";

export const ClipWord = z
  .object({ i: z.number().int().min(0), text: z.string() })
  .meta({ id: "ClipWord" });
...
export type ClipWord = z.infer<typeof ClipWord>;
```
Enum style (reuse for `ErrorType`; Python gets `--enum-field-as-literal all`, so it becomes a `Literal[...]`):
```typescript
export const IssueCode = z
  .enum(["STRESS_MISMATCH", "EXTRA_PAUSE", ...])
  .meta({ id: "IssueCode" });
```
Rules: give `ErrorType` its own `.meta({ id: "ErrorType" })` (anonymous `__schemaN` defs make generation fail). Optional fields use `.optional()`. Do not use `z.default` unless intended: generation uses `io: "input"`. Values per D-03: `wrong_stress, flat, extra_pause, final_rise, pitch_off, weak_form, final_drop`.

**Registration** (`packages/contracts/src/index.ts` L33 `export const Schemas = {...}`, `export * from "./eval"` already present L23): add `ErrorType` and `EvalCase` to `Schemas` or they do not reach the JSON Schema / pydantic output. Then run `make contracts`, commit `contracts.schema.json` and `contracts_gen.py`; `make test` -> `scripts/contracts_check.sh` diffs regenerated output against committed files (drift gate).

### `services/audio/src/audio_service/scoring/thresholds.py` (config)

**Analog:** itself. Constants are flat module-level, grouped by `# --- Rule ... ---` banners, each with a Vietnamese comment citing the decision.
```python
THRESHOLDS_VERSION = "p2-1"  # 03-01 mục E
SCORER_VERSION = "prosody-2"
...
# --- Rule Lớp C: FLAT_PITCH (product.md §3 Lớp C, D-12) ---
FLAT_RATIO = 0.6
FLAT_REF_MIN_STD_ST = 2.0
```
Add a new banner section, e.g. `RULES_ENABLED: dict[str, bool]` or one `RULE_<CODE>_ENABLED = True` per rule (D-15), and bump `THRESHOLDS_VERSION` whenever any value or flag changes (module docstring requires it). Docstring currently says values are "không sửa" outside the Phase 4 eval process; update it to reference ADR 0007. Existing tests that assert version strings may need updating (grep `p2-1` in `services/audio/tests`).

### `services/audio/src/audio_service/rules/engine.py` (service)

**Analog:** itself. Imports thresholds by name (L27-44); `run_rules` (L292-306) is the single place to gate:
```python
def run_rules(inp: RuleInput) -> list[RuleIssue]:
    issues: list[RuleIssue] = []
    for single in (stress_mismatch(inp), final_contour(inp)):
        if single is not None:
            issues.append(single)
    issues.extend(extra_pause(inp))
    issues.extend(pitch_deviation(inp))
    flat = flat_pitch(inp)
    if flat is not None:
        issues.append(flat)
    return issues
```
Keep the fixed order STRESS_MISMATCH, FINAL_CONTOUR, EXTRA_PAUSE, PITCH_DEVIATION, FLAT_PITCH (it is the basis of `issueRef`). Gate each rule call by its flag (skip the call, do not filter afterwards, so disabled rules produce no issue and no tip). File docstring says "file này không có số ngưỡng nào": flags live in `thresholds.py`, not here. Individual rule functions (`flat_pitch`, `final_contour`, `stress_mismatch` return `RuleIssue | None`; `pitch_deviation`, `extra_pause` return `list[RuleIssue]`) stay ungated so unit tests keep calling them directly. For `sweep.py`, thresholds are module constants imported by name into `engine.py`, so sweeping needs `monkeypatch`-style patching of `audio_service.rules.engine.<NAME>` (and `prominence`/`metrics` if they import constants), not `thresholds.<NAME>`; verify with grep which module binds each constant.

### `eval/evalkit.py` + `eval/analyze.py` + `eval/sweep.py` (batch scorer)

**Analog:** `scripts/smoke_score.py`.

Module layout to copy: top docstring (usage, what it reads, exit codes), `from __future__ import annotations`, heavy imports (`audio_service.*`) deferred into the run function AFTER setting env, `NamedTuple` rows, a pure `verdict(...) -> (message, exit_code)` function, `main()` + `sys.exit(code)` with flush.

Environment and data-root pattern (L236-257):
```python
if args.data_dir is not None:
    os.environ["DATA_DIR"] = str(args.data_dir)
    os.environ["SHADOWENGLAB_CONFIG_DIR"] = str(root / "config")
# Import sau khi đặt biến môi trường: get_settings() phân giải DATA_DIR một lần.
from audio_service import config
from audio_service.lesson import audio_io, features, pipeline, vad
from audio_service.scoring import ref_cache
from audio_service.scoring.features import prepare_features
from audio_service.scoring.scorer import score_prosody

config.get_settings.cache_clear()
data_root = config.data_root()
if not data_root.is_dir():
    return _usage_error(f"DATA_DIR không tồn tại: {data_root}")
```
Exit codes: 0 ok, 1 verdict failed, 2 usage/missing data (D-05 "báo lỗi và dừng" maps to exit 2 with a clear message via `_usage_error`).

Ref features + words for a segment, read-only (L275-280):
```python
vocals16, base = pipeline.load_range_vocals16(lesson)
refs = {i: pipeline.ref_prosody_for_segment(lesson, i, write_cache=False) for i in selected}
```
`refs[i].features` is the `ProsodyFeatures`, `refs[i].words` the `RefWord` list. `write_cache=False` keeps the script read-only (T-03-22); keep that property for eval.

Self-compare (D-18a) generation: slice vocals window then pad/encode/normalize exactly like an upload (L134-166, L294-319):
```python
window = ref_cache.read_feature_window(lesson.id, i) or features.segment_window(
    seg.start, seg.end, lesson.pad_ms, seg.end_extra_ms, lo=base, hi=stop
)
clip = audio_io.slice_seconds(vocals16, audio_io.TARGET_SR, window[0] - base, window[1] - base)
src = _encode_like_a_browser(_pad_like_a_recording(clip), root, name)
mono = _normalize_like_an_upload(src, root, name)
if not vad.is_voiced(mono): ...
user = prepare_features(mono)
score = score_prosody(refs[i].features, user, refs[i].words)
```
`stop = pipeline._stem_span(lesson)[3]` is a private-API use in the analog; either copy it or (preferred) import the helpers from `scripts/smoke_score.py` via the `importlib` loader technique, or move shared helpers into `eval/evalkit.py`. Do not duplicate `_encode_like_a_browser`/`_normalize_like_an_upload` divergently.

Rescoring a saved eval WAV (D-06): the saved WAV is already normalized 16 kHz (it is `copyfile` of the normalized upload), so use `audio_io.read_audio(wav)` + `audio_io.to_mono_16k(...)` (as in `_normalize_like_an_upload` last two lines) then `prepare_features` then `score_prosody`. Result fields used by smoke: `score.overall`, `score.issues` (list; each element is a `RuleIssue`-derived item, check `scorer.ProsodyScore` L38-58 for the exact shape before writing the TP/FP matcher: it must expose code, wordIndex), `score.alignment.ok/.cost/.ratio` (feeds D-11b "align failure" = `not alignment.ok`). For issue code strings and `issue` dict keys (camelCase `code`, `wordIndex`) read `rules/engine.py` issue construction (L89-257) before coding the matcher.

Stats: no existing Wilson/ICC helper in the repo (see No Analog). `statistics.median`, `np.percentile` usage is in `smoke_score.verdict`.

Pure verdict pattern (copy shape for D-21 gate, `analyze.verdict(rows) -> (message, code)`), L74-102 shown above in the file: collect `problems: list[str]`, return `"... FAILED: " + "; ".join(problems), 1`.

Lesson lookup: `store.load_lesson(lesson_id)` wrapped in `except (InvalidIdError, OSError, ValueError)` (L222-226), then verify `lesson.status == "ready"`. For D-05 identity check, compare `lesson.segments[idx].start/end/text` against the case's stamp and stop with exit 2 on mismatch.

### `eval/tag_clips.py` (CLI, file-I/O)

**Analog:** `routers/attempts.py::_store_eval_clip` (L172-196) for the artifact format it consumes:
```python
stem = f"{lesson.id}_{index:04d}_{attempt:02d}"
clips = eval_clips_dir()
wav = clips / f"{stem}.wav"
write_json_atomic(
    clips / f"{stem}.json",
    {"lessonId": lesson.id, "segmentIndex": index, "attempt": attempt, "text": lesson.segments[index].text},
)
```
Sidecar keys exactly: `lessonId`, `segmentIndex`, `attempt`, `text`. Clip stem = `{lessonId}_{NNNN}_{AA}`; this is what `EvalCase.clip` stores. WAV is written last (after sidecar), so enumerate clips via `*.wav` and read the sibling `.json`. Resolve the directory with `config.eval_clips_dir()` (L115-119; it mkdirs). Match unlabelled clips (no case with that `clip`) to pending cases (same `lessonId` + `segmentIndex`, no `clip` yet), confirm interactively, and write `cases.jsonl` atomically (reuse the `write_json_atomic` idea: write `.part` then `os.replace`, see L184-194). Validate each line with the generated pydantic model: `from audio_service.contracts_gen import EvalCase` then `EvalCase.model_validate_json(line)`.

### `Makefile`

**Analog:** L48-50 (stub to replace) and L61-62:
```make
smoke-score:
	uv run --project services/audio --frozen python scripts/smoke_score.py $(if $(LESSON),--lesson $(LESSON))
```
Pattern for variables: top-of-file `?=` defaults (L4-7); conditional flag via `$(if $(HOLDOUT),--holdout)`. Add new targets to the `.PHONY` list (L12). Makefile is GNU Make 3.81, POSIX sh recipes, no `.ONESHELL`. `make lint` runs ruff on `../../scripts` only (`ruff check ... . ../../scripts`): extend that line to include `../../eval` or the new Python will not be linted/formatted. Also note `make test` runs `pytest` only in `services/audio` (testpaths `["tests"]`).

### `.gitignore`

Existing block:
```
# Eval: audio và nhãn thô của người chấm
eval/clips/
eval/labels.jsonl
eval/manifest.json
```
`eval/cases.jsonl` and `eval/report.md` must remain tracked (D-04, D-20): do not add them. `*.wav` is already ignored globally. Any scratch output of sweep should go outside the repo or to a new ignored path.

### Tests (`services/audio/tests/`)

**Analog 1:** `test_smoke_score.py` L1-60: loads a script that is not on the import path via `importlib.util.spec_from_file_location` + `sys.modules` registration, fixture pops it afterwards; pure functions (`verdict`) tested with hand-built `NamedTuple` rows; end-to-end uses a synthetic `ready` lesson on a temp `DATA_DIR` (`get_settings`, `REPO_ROOT` from `audio_service.config`). Use the same loader for `eval/analyze.py` / `eval/evalkit.py` (`Path(REPO_ROOT) / "eval" / "analyze.py"`).

**Analog 2:** `test_scoring_rules.py` L1-40: `from synth import DEFAULT_WORDS, SynthWord, synth_sentence` (tests dir is on path via conftest), module-scope `reference` fixture `(audio, marks, prepare_features(audio))`, `ScoreResult`/`RuleInput` built directly; use for "disabled flag yields no issue" tests via `run_rules` / `score_prosody`.

**Analog 3:** `test_contracts_roundtrip.py` L20-40: `FIXTURE_DIR.glob("*.json")` each file a list of `{name, data}` cases validated by both pydantic and Zod (`pnpm ... exec tsx src/cli-parse.ts <Type>`); add an `EvalCase` fixture file there (check the fixture dir path at the top of that file) so Zod and pydantic agree. Pure unit tests to add: Wilson CI, TP/FP counting (D-08 ±1 word for EXTRA_PAUSE, D-10 primary/secondary codes), deterministic split hash (D-12), align-failure counted as FN (D-11b).

### `docs/decisions/0007-*.md` (ADR)

**Analog:** `docs/decisions/0006-cham-ngu-dieu-p2.md`. Title format `# 0006 · <topic>`, then `Ngày: YYYY-MM-DD · Trạng thái: Chấp nhận · Người quyết: Liam`, sections `## Bối cảnh`, `## Quyết định` with numbered `### N. <title> (D-xx)` subsections, values quoted from merged code. Vietnamese. Must record: counting rules (D-08..D-11b), split rule and held-out lock (D-12, D-16), rule off flags (D-15), gate (D-21).

## Shared Patterns

### Contract-first flow
Zod (`eval.ts`) -> register in `index.ts` `Schemas` -> `make contracts` (`scripts/contracts_gen.sh`: tsx `generate.ts` -> `datamodel-codegen` with `--enum-field-as-literal all --snake-case-field --allow-population-by-field-name`) -> commit generated files -> `make test` drift gate. Pydantic fields become snake_case (`case_id`, `lesson_id`, `segment_index`, `word_index`, `also_present`); JSON on disk stays camelCase, so parse with `EvalCase.model_validate_json` and dump with `by_alias=True`. Per CLAUDE.md, Liam approves contract shape at a PR checkpoint before use; `cases.jsonl` is hard to migrate (D-02 costly).

### Offline scoring entry (read-only, no HTTP)
Source: `scripts/smoke_score.py` L245-257 (env then import, `config.get_settings.cache_clear()`, `config.data_root()`), plus guard `if root.resolve().is_relative_to(data_root)` against temp dir inside DATA_DIR. Apply to analyze, sweep, tag_clips.

### Versions in report header (D-20)
`from audio_service.scoring.thresholds import SCORER_VERSION, THRESHOLDS_VERSION`; `FEAT_VERSION` lives in `scoring/features.py` (ADR 0006 mentions `FEAT_VERSION = "pf-2"`; confirm import path with grep before use). Git sha via `subprocess.run(["git","rev-parse","HEAD"])` (no existing helper).

### Error / exit convention
`_usage_error(msg)` -> stderr + return 2; `_failed(reason)` -> prints `X FAILED: ...` + return 1; success prints `X OK`, returns 0; `main()` ends with `sys.stdout.flush(); sys.stderr.flush(); sys.exit(code)`.

### Language, style, tooling
Docstrings/comments Vietnamese, identifiers English, line length 100, ruff check + format (config in `services/audio/pyproject.toml`), type hints everywhere, pure audio functions (array in, result out; file reading only at the script edge). No `any` in TS.

## No Analog Found

| File / need | Role | Reason |
|---|---|---|
| Wilson 95% CI, ICC, test-retest stats | utility | No stats helpers in repo; implement as pure functions in `eval/evalkit.py` (numpy/scipy are available: `scipy.stats` is already imported by `rules/engine.py`) |
| `eval/cases.jsonl` | data | New artifact; JSONL of `EvalCase`, one object per line, with `split` precomputed deterministically by hash of `lessonId:segmentIndex` (use `hashlib.sha256`, never Python `hash()`) and committed before any clip is scored (D-12) |
| `eval/report.md` generation | output | No existing report writer; `smoke_score._format_table` (L169-188) is the nearest fixed-width table formatter, but the report needs Markdown tables |
| Held-out open log (D-16) | utility | No analog; append (time, THRESHOLDS_VERSION, git sha) into report; remember `report.md` is committed |
| `eval/export_clips.py` | script | Referenced by `eval/README.md` but does not exist; out of scope for Phase 4 (Phase 6), update README to describe `analyze.py`, `sweep.py`, `tag_clips.py`, `cases.jsonl` |

## Gotchas for the planner

- Constants imported by name into `engine.py` (and possibly `scorer.py`, `prominence.py`, `metrics.py`, `align.py`) mean `sweep.py` must patch the consumer module namespace; centralizing via attribute access is a refactor the Phase 3 tests may not expect.
- `to_score_result` and tip selection (`rules/tips.py`) consume issues; disabling a rule in `run_rules` automatically drops its tips, no change needed in `tips.py`.
- `make lint` and `pytest` do not cover `eval/` unless extended (see Makefile section).
- `eval/` is not importable from tests; use the path-loader fixture (test_smoke_score.py) or place pure logic that tests need in `services/audio/src/audio_service/` (violates "eval is out of the service" intent, so prefer the loader).
- Disabling flags changes `ScoreResult.versions` via `THRESHOLDS_VERSION`; bump it.

## Metadata

**Analog search scope:** `scripts/`, `eval/`, `services/audio/src/audio_service/{scoring,rules,routers,config.py}`, `services/audio/tests/`, `packages/contracts/src/`, `Makefile`, `.gitignore`, `docs/decisions/`
**Files scanned:** ~25
**Pattern extraction date:** 2026-10-11
