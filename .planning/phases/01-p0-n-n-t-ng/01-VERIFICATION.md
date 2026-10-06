---
phase: 01-p0-n-n-t-ng
verified: 2026-10-06T22:40:00Z
status: human_needed
score: 4/4 must-haves verified
covered_files:
  - ".planning/phases/01-p0-n-n-t-ng/01-01-PLAN.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-01-SUMMARY.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-02-PLAN.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-02-SUMMARY.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-03-PLAN.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-03-SUMMARY.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-04-PLAN.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-04-SUMMARY.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-05-PLAN.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-05-SUMMARY.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-06-PLAN.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-06-SUMMARY.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-07-PLAN.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-07-SUMMARY.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-08-PLAN.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-08-SUMMARY.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-09-PLAN.md"
  - ".planning/phases/01-p0-n-n-t-ng/01-09-SUMMARY.md"
  - "Makefile"
  - "apps/eval/app/page.tsx"
  - "apps/web/app/page.tsx"
  - "packages/contracts/schema/contracts.schema.json"
  - "packages/contracts/src/eval.ts"
  - "packages/contracts/src/lesson.ts"
  - "packages/contracts/src/score.ts"
  - "scripts/check_deps.sh"
  - "scripts/contracts_check.sh"
  - "scripts/contracts_gen.sh"
  - "scripts/dev_smoke.sh"
  - "scripts/smoke_lesson.py"
  - "services/audio/src/audio_service/contracts_gen.py"
  - "services/audio/src/audio_service/lesson/pipeline.py"
  - "services/audio/src/audio_service/lesson/segment.py"
  - "services/audio/src/audio_service/main.py"
  - "services/audio/src/audio_service/routers/lesson.py"
  - "services/audio/tests/test_contracts_roundtrip.py"
covered_digest: "v3:sha256:84814c20f016204eb19b7631efa5ad61353125c2d32b0f748e5c7fff1e8cc38e"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run `make eval | grep stub` once"
    expected: "Prints the 'make eval: stub ...' line and exits 0"
    why_human: "The agent sandbox refuses any command containing the word 'eval'. Recipe is a single `echo` (Makefile line with `eval:`), read directly; never executed by an agent."
  - test: "Listen to segment boundaries from a 5-minute smoke run (e.g. `make smoke END=300`, then play segments with ffplay) and judge the `clean` audioQuality label"
    expected: "Segments start/end on natural phrase boundaries without clipped final words; the `clean` label is plausible for the video"
    why_human: "Judgment by ear. Measured stats (re-run by verifier): 62 segments, min 1.50 s, max 7.68 s, mean 3.03 s, 39/62 shorter than 3 s, 0 longer than 8 s. product.md says sentences are 3-8 s, the implemented heuristic (cut > 8 s / > 15 words, merge < 1.5 s) allows shorter. Source video is a Friends sitcom clip (not an interview as in ROADMAP SC3 wording), though Liam approved this URL in 01-01 item 10. Segmentation thresholds are RESEARCH A1 and Liam's call."
  - test: "Optional: `HF_HOME=$(mktemp -d) make setup` on an empty model cache / clean machine"
    expected: "Brew-tool check passes, ~3 GB of models download with progress bars, setup_models prints all rows OK, exit 0"
    why_human: "Needs an empty cache plus network and ~3 GB download. Verifier ran `make setup` only on a machine with warm HF cache (idempotent no-op path)."
---

# Phase 1: P0 Nền tảng Verification Report

**Phase Goal:** Dựng monorepo và contract, chứng minh pipeline audio chạy đầu-cuối bằng script.
**Verified:** 2026-10-06T22:40:00Z
**Status:** human_needed
**Re-verification:** No, initial verification

Phase mode is `mvp` in ROADMAP but the goal is not in "As a ..., I want ..., so that ..." form; verified against the plain goal and the four ROADMAP success criteria. Flagging for the orchestrator only (no change to the verdict).

## Goal Achievement

### Observable Truths (ROADMAP success criteria are the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `make setup && make dev` runs on Apple Silicon (deps, models, Next.js + FastAPI start) | VERIFIED (clean-machine part human) | Verifier ran `make setup`: check_deps 6 OK, `pnpm install --frozen-lockfile` and `uv sync --frozen` no-op, setup_models 6 rows OK (whisper turbo, wav2vec2, htdemucs, parselmouth, ffmpeg, MPS). `sh scripts/dev_smoke.sh` with a real lesson id: "API và web cùng lên sau 2s", "lesson ... status ready", `DEV-SMOKE OK` (script refuses to run if ports are busy and verifies ports closed after SIGTERM). Untested: empty model cache / clean machine (human item 3). |
| 2 | ScoreResult round-trip TS <-> JSON Schema <-> pydantic passes | VERIFIED | `make test` exit 0: drift gate "contracts: không lệch", vitest 20/20, pytest 306/306. `test_contracts_roundtrip.py` is not mocked: it spawns real Zod (`pnpm exec tsx src/cli-parse.ts`), validates with `Draft202012Validator` against the committed schema, then pydantic `TypeAdapter` dump (by_alias, exclude_unset) and compares. 33 cases including ScoreResult fixtures, boundary/null/non-ASCII/precision edges. Drift gate has a negative test (`test_detects_drift`). |
| 3 | `scripts/smoke_lesson.py <youtube_url>` on a clean-audio US video outputs `Lesson` JSON and prints per-step timing | VERIFIED (video choice noted) | Verifier ran `make smoke END=300 BUDGET=300` twice. Output: status transitions queued -> downloading -> separating -> transcribing -> segmenting -> analyzing -> ready, per-step table (download, write, extract_audio, demucs, quality, resample, whisper, segment, ppg, f0, write_features), `SELF-CHECK OK`. Resulting lesson.json read back: status ready, 62 segments, words with segment-local `i`, `padMs` 150, `endExtraMs` 0, `audioQuality.clean`, one `seg/NNNN.npz` per segment (f0_hz, energy, ppg, window). Video is a sitcom clip (Liam-approved URL), not an interview; see human item 2. |
| 4 | 5-minute video processed in <= 5 minutes | VERIFIED | Verifier cold run (fresh empty DATA_DIR, download + ffmpeg + Demucs + Whisper + PPG measured): wall 119.3 s, total step time 118.56 s (download 5.32, demucs 45.13, whisper 41.90, ppg 23.42), `BUDGET OK: 119.3 s <= 300.0 s`. Matches 01-08 SUMMARY (115.8 / 125.3 s). Models were warm in HF cache, as on any machine after `make setup`. No ML model was swapped (models.py ids unchanged, D-26 prohibition respected). |

**Score:** 4/4 roadmap truths verified; 0 behavior-unverified (behavior-dependent truths have exercising tests, see below).

### Plan-level truths (spot-checked beyond ROADMAP)

| Truth (plan) | Status | Evidence |
|--------------|--------|----------|
| 01-06: lesson.json rewritten atomically at every status transition; exception leaves `failed` + `{step,message}`; re-run reuses video/stems | VERIFIED | Behavioral tests exist and pass in `make test`: `test_pipeline.py::test_statuses_follow_the_order_and_each_is_on_disk_when_reported`, `::test_failure_leaves_failed_status_with_step_and_message_then_reraises`, `::test_second_run_reuses_video_audio_and_stems`, `test_contract_io.py::test_failed_replace_keeps_old_content_and_leaves_no_temp_file`. Cold run vs warm run in this verification also showed cache reuse (download 0.00 s, demucs 0.15 s on warm). |
| 01-02: GET /lessons/{id} serves contract-valid camelCase, 404 for bad/unknown id, /health, /scoring mounted, CORS only localhost:3000 | VERIFIED | `main.py`, `routers/lesson.py` read directly (`response_model=Lesson`, `exclude_unset`, `InvalidIdError -> 404`, corrupt file -> 500 without path); `test_api.py` 10 pass; live fetch through `make dev` of a freshly generated lesson returned status ready. |
| 01-07: web build prerenders `data-lesson-statuses="8"`; eval shell on port 3001 | VERIFIED | Verifier ran both `next build`s successfully; `grep` of prerendered `apps/web/.next/server/app/index.html` shows `data-lesson-statuses="8"`; `apps/eval/package.json` dev/start use `-p 3001`. |
| 01-08: `make test` drift gate; `make lint` green; `make eval` stub exits 0 | VERIFIED except eval | `make lint` exit 0; `make test` exit 0; `make eval` not executed (human item 1), recipe read directly. |
| 01-09: docs sync (ADR 0003, product.md 3-4, CLAUDE.md Lệnh, README, `.env.example`) | VERIFIED | ADR 0003 present (11 D-20..D-27 references); product.md contains `intonationOnly`; CLAUDE.md and README list real Makefile targets (setup, dev, test, lint, eval, smoke, contracts, dev-eval); `.env.example` has OPENAI_API_KEY, AZURE_SPEECH_KEY/REGION, DATA_DIR with empty secrets. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pnpm-workspace.yaml`, `package.json`, `pnpm-lock.yaml`, `services/audio/pyproject.toml`, `uv.lock` | monorepo manifests + lockfiles | VERIFIED | `make setup` installs frozen from both lockfiles with no diff. |
| `packages/contracts/src/{lesson,score,eval,index,generate,cli-parse}.ts`, `schema/contracts.schema.json` | Zod contracts + JSON Schema bundle | VERIFIED | Every object type carries `.meta({ id })`; index exports Schemas map for Segment, Lesson, ScoreResult, IssueCode, ClipManifest, Label; drift gate green. |
| `services/audio/src/audio_service/contracts_gen.py` | generated pydantic | VERIFIED | `class Lesson`, `ScoreResult`, `Issue` (7-way union), `Label`, `ClipManifest`, etc. all present; regenerated copy matches (drift gate). |
| `services/audio/src/audio_service/{main,config,models,setup_models,contract_io}.py`, `routers/{lesson,scoring}.py` | API + setup | VERIFIED | Substantive and wired (read directly). |
| `services/audio/src/audio_service/lesson/{urls,quality,segment,download,separate,transcribe,features,audio_io,timing,pipeline}.py` | pipeline | VERIFIED | `pipeline.py` (305 lines) chains all real stages through `default_deps()`; no stubs. |
| `scripts/{check_deps,contracts_gen,contracts_check,dev_smoke}.sh`, `smoke_lesson.py`, `smoke_video.url` | tooling | VERIFIED | All executed or exercised by verifier. |
| `Makefile`, `eslint.config.mjs`, `.prettierrc`, `.prettierignore` | command surface + lint | VERIFIED | `make lint` green on whole repo. |
| `apps/web`, `apps/eval` | Next.js shells | VERIFIED | Both build; imports `@shadowenglab/contracts` via transpilePackages. Bare shells only (Liam overrode ui.safety-gate, recorded in STATE.md). |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| Makefile `test` | `contracts_check.sh` -> `contracts_gen.sh` | `test: contracts-check` | WIRED (test run printed "contracts: không lệch") |
| Makefile `dev` | dev-api + dev-web | `$(MAKE) -j2 dev-api dev-web` | WIRED (dev_smoke OK) |
| Makefile `smoke` | `scripts/smoke_lesson.py` + `smoke_video.url` | URL default | WIRED (ran) |
| `pipeline.py` | `contract_io.write_contract_json`, `segment.split_sentences`, `features.*`, `download` -> `urls.canonical_watch_url` | imports and calls | WIRED |
| `routers/lesson.py` | `contracts_gen.Lesson`, `config.lesson_json_path` | response_model + path helper | WIRED |
| `test_contracts_roundtrip.py` | `cli-parse.ts` (real Zod) and `contracts_gen` | subprocess + TypeAdapter | WIRED |
| `apps/web/app/page.tsx` | `@shadowenglab/contracts` | workspace dep | WIRED (prerendered value 8) |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| lesson.json segments | words/segments | mlx-whisper on Demucs vocals of the real video | Yes (62 segments with Whisper asrProb) | FLOWING |
| `seg/NNNN.npz` | f0_hz, energy, ppg | parselmouth + wav2vec2 on segment-window slices | Yes (self-check reads every file) | FLOWING |
| GET /lessons/{id} | Lesson | `DATA_DIR/lessons/{id}/lesson.json` | Yes (fetched live in dev_smoke) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `make test` | exit 0; 306 pytest + 20 vitest + drift gate | PASS |
| Lint | `make lint` | exit 0 | PASS |
| System deps | `sh scripts/check_deps.sh` | exit 0, 6 OK | PASS |
| Setup (warm cache) | `make setup` | all rows OK | PASS |
| 5-min video, cold DATA_DIR | `DATA_DIR=<fresh> make smoke END=300 BUDGET=300` | 119.3 s, SELF-CHECK OK, BUDGET OK | PASS |
| make dev + live lesson | `DATA_DIR=<cold> LESSON_ID=<id> sh scripts/dev_smoke.sh` | DEV-SMOKE OK, status ready | PASS |
| Web/eval builds | `pnpm --filter ... build` | both succeed; marker 8 present | PASS |
| `make eval` | not run (sandbox refuses word) | n/a | SKIP -> human |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes declared or present. Not applicable.

### Requirements Coverage

All 7 requirement IDs declared in PLAN frontmatter, cross-referenced with REQUIREMENTS.md (each present as FND-0x, mapped to Phase 1). No orphans: REQUIREMENTS.md maps exactly FND-01..FND-07 to Phase 1 and every one is claimed by at least one plan (FND-01: 01-01, 01-07, 01-08; FND-02: 01-02, 01-05; FND-03: 01-02, 01-05; FND-04: 01-03, 01-08, 01-09; FND-05: 01-07, 01-08, 01-09; FND-06: 01-02; FND-07: 01-04, 01-06, 01-08).

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| FND-01 | pnpm workspace + uv, ESLint, Prettier, ruff, .gitignore | SATISFIED | Workspace installs frozen; `make lint` green; `.gitignore` covers .env, node_modules, .venv, .next, audio extensions, eval/clips, eval/labels.jsonl; `git ls-files` contains no audio/.env/labels/npz. |
| FND-02 | Zod for Segment, Lesson, ScoreResult, IssueCode, ClipManifest, Label + JSON Schema | SATISFIED | Contracts + schema bundle present, 20 vitest pass. Contract shapes were Liam-locked in Discuss (D-04..D-17). |
| FND-03 | pydantic matches schema; ScoreResult round-trip passes | SATISFIED | See truth 2. |
| FND-04 | `make setup` on a clean Mac, progress, checks parselmouth/espeak-ng/ffmpeg | SATISFIED on this machine; clean-machine run is human item 3 | `check_deps.sh` check-and-guide only (no auto-install, per D-25); setup_models downloads with progress and verifies parselmouth, ffmpeg, MPS; `test_setup.py` 23 pass. |
| FND-05 | `make dev` both servers, `make test` pytest+vitest, `make eval` exists (stub) | SATISFIED except `make eval` execution (human item 1) | dev_smoke OK; test OK; `eval:` target exists in Makefile as an echo stub. |
| FND-06 | FastAPI /health, lesson and scoring routers, contract-validated responses | SATISFIED | `main.py` + routers; live GET /lessons/{id}. |
| FND-07 | smoke_lesson.py yt-dlp -> Demucs -> mlx-whisper -> split 3-8 s -> F0+PPG -> Lesson JSON, timing, 5-min in <= 5 min | SATISFIED (segment-length quality is human item 2) | Real run, 119.3 s cold. Heuristic implements product.md rules (cut > 8 s or > 15 words, merge < 1.5 s) but does not enforce a 3 s lower bound; 39/62 segments < 3 s. |

### Prohibitions (must_haves.prohibitions)

| Prohibition | Tier | Result |
|-------------|------|--------|
| No .env / audio / eval clips / labels committed (01-01) | test | Verified by direct inspection: `.gitignore` entries present and `git ls-files` returns none of them. No dedicated automated test was found; enforcement is the gitignore. Acceptable, not flagged. |
| install no system packages; no extra models (01-03) | test | `check_deps.sh` only prints guidance; model ids come from a single `models.py`; `test_setup.py` passes. |
| No model swap to hit time budget (01-06, 01-08) | test/judgment | Budget met without model change; Demucs/whisper/wav2vec2 ids unchanged (01-08 diff of `services/audio/src` was empty). Judgment-tier, non-authoritative: no violation observed. |
| No change to locked contract shapes without Liam (01-02, 01-05) | judgment | unverified-prohibition, human review recommended: contract fields were not diffed against Liam's locked decisions by the verifier beyond the fixtures/round-trip tests; 01-01 SUMMARY records Liam's approval. Non-authoritative LLM judgment: no deviation seen. |
| No audio/transcripts/features sent to remote services (01-06) | judgment | unverified-prohibition, human review recommended: only yt-dlp download egress found in `download.py`/pipeline; no network client in transcribe/features. Non-authoritative. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `scripts/dev_smoke.sh`, `scripts/contracts_check.sh` | 17, 16 | `XXXXXX` in `mktemp` template | Info (false positive of the debt-marker grep) | None |
| `01-REVIEW.md` WR-01..WR-06, IN-01..IN-05 | n/a | 11 code-review findings, all disposition `open`, 0 critical | Warning | Not goal-blocking. WR-02 (F0/energy/PPG frame counts differ and no explicit time origin in npz; the npz does store `window`, `f0_hop_s`, `ppg_fps`) and WR-01 (relative `DATA_DIR`) are worth triage before Phase 3 scoring consumes these features. |

No TODO/FIXME/stub/placeholder markers in modified source. `make eval` stub is intentional (Phase 4, EVL-02).

### Human Verification Required

1. **`make eval` stub** - Run `make eval | grep stub`. Expected: stub message, exit 0. Why human: the agent sandbox refuses commands containing the word "eval".
2. **Listen check of segmentation and `clean` label** - Run `make smoke END=300`, play segments (ffplay). Expected: natural boundaries, no clipped final words, `clean` plausible. Why human: judgment by ear; 39/62 segments are under 3 s (spec says 3-8 s), and the smoke video is a sitcom clip rather than an interview. Liam decides whether to tune segmentation thresholds (RESEARCH A1) in P0 or leave for Phase 2.
3. **Optional clean-machine `make setup`** - `HF_HOME=$(mktemp -d) make setup`. Expected: ~3 GB download with progress, all rows OK, exit 0. Why human: needs empty cache and network.
4. **Triage 01-REVIEW-DISPOSITION.md** - 11 findings still `open`. Not a verification gate, but should be dispositioned (fix/defer) before ship.

### Gaps Summary

No gaps. All four ROADMAP success criteria and all seven requirement IDs (FND-01..FND-07) are backed by code and by commands the verifier executed in its own process: `make test` (306 pytest + 20 vitest + drift gate), `make lint`, `check_deps.sh`, `make setup`, `make dev` smoke with a live lesson, both Next builds, and a cold 5-minute pipeline run in 119.3 s against a 300 s budget. Status is `human_needed` only because three observations cannot be made by an agent: running the word-restricted `make eval` stub, listening to segment boundaries and the `clean` label (plus the 3-8 s expectation versus 39/62 short segments), and an optional clean-machine setup.

---

_Verified: 2026-10-06T22:40:00Z_
_Verifier: Claude (gsd-verifier)_
