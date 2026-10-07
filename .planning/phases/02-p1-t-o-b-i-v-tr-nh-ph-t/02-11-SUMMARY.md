---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 11
subsystem: api
tags: [fastapi, settings, openai-key, dotenv, httpx, warm-up, hf-cache, tdd]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-01 approved shapes (SystemStatus, AppSettings, OpenAiKeyCheck*, item G dataDir precedence); 02-03 JobRunner.model_gate, ApiErrorException, create_app, empty settings/system router shells; 02-06 config path helpers"
provides:
  - "GET /system/status: SystemStatus {models, hasKey, maskedKey?, activeDataDir}, always 200 (also without a key)"
  - "GET/PUT /settings backed by ~/.config/shadowenglab/settings.json (atomic), 422 invalid_settings for an unusable dataDir"
  - "POST /settings/openai-key/check: httpx GET /v1/models; .env written (0600, other lines kept) and hot-loaded only on 200"
  - "Model warm-up at startup: load -> 1 inference -> release, one model at a time under model_gate"
  - "config.get_settings applies the saved dataDir over DATA_DIR once per process; lifespan pins it at startup"
  - "autouse conftest isolation (config dir, env file, OPENAI_API_KEY, warm-up state)"
affects: [02-12, 02-13, 02-14, 02-15, 02-16, 02-17, 02-18, 02-19]

actuals:
  tokens: 15700
  tasks: 3
  commits: 5

plan_head_before: dd556e3d20e358aa260d8144b8a281d9c52762d5
plan_head_after: 508bf72a173b6fdb511a46e68074695c74211c14

tech-stack:
  added: []
  patterns:
    - "Machine state behind env-overridable paths (SHADOWENGLAB_CONFIG_DIR, SHADOWENGLAB_ENV_FILE) so tests never touch ~/.config or the repo .env"
    - "Warm-up holder (WarmUp) is a process singleton reset by tests; real loaders import heavy libs lazily inside the loader"
    - "OpenAI reached through a FastAPI dependency (get_http_client) so tests inject httpx.MockTransport; no openai SDK (D-23)"
    - "Secrets: fixed messages, no exc_info on key-adjacent errors, regex gate before any write or network call"

key-files:
  created:
    - services/audio/src/audio_service/system_status.py
    - services/audio/src/audio_service/secrets_env.py
    - services/audio/src/audio_service/settings_store.py
    - services/audio/tests/conftest.py
    - services/audio/tests/test_system_status.py
    - services/audio/tests/test_settings_api.py
    - services/audio/tests/test_openai_key.py
  modified:
    - services/audio/src/audio_service/config.py
    - services/audio/src/audio_service/routers/system.py
    - services/audio/src/audio_service/routers/settings.py
    - services/audio/src/audio_service/main.py
    - services/audio/tests/test_api.py

key-decisions:
  - "dataDir precedence for ADR 0005: settings.json dataDir (absolute, existing directory) > DATA_DIR from env/.env > ~/shadowenglab-data, resolved once per process inside lru_cache get_settings; the lifespan calls get_settings() first thing so a PUT /settings can never change the active dir before a restart; data is never moved"
  - "OpenAiKeyCheckResult.saved means 'a verified key is stored after this call': true exactly when valid is true (also when the saved key was re-tested), false otherwise; maskedKey is only sent when valid is true"
  - "A malformed apiKey (any whitespace/newline/=, <20 or >256 chars, non-ASCII) answers 200 {valid:false, saved:false, reason:'invalid'} with zero HTTP calls; apiKey '' or absent tests the saved key; the key is never stripped (a trailing newline is rejected, per the plan)"
  - "KEY_RE ends with \\Z, not $, so a trailing newline cannot slip through"
  - "create_app(warm_up=None) is on only when no deps are injected; the conftest also resets the shared warm-up holder to 'all missing' so even a deps-less lifespan in tests never loads a real model"

patterns-established:
  - "Tests that need the saved dataDir behaviour call cfg.data_root() first to simulate the startup resolution (or enter the lifespan)"

requirements-completed: [SET-01, SET-02, SET-03, SET-04]

coverage:
  - id: D1
    description: "GET /system/status reports each model missing (not in HF cache, cache-only check, never downloads) or loading/ready, hasKey and maskedKey only with a key, and the active data dir; 200 without a key"
    requirement: "SET-01"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_system_status.py#test_cached_models_start_loading_and_uncached_are_missing"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_system_status.py#test_status_without_key_is_200_with_no_masked_key"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_openai_key.py#test_missing_key_never_blocks_the_rest_of_the_api"
        status: pass
    human_judgment: false
  - id: D2
    description: "Warm-up loads, runs one inference and releases each cached model one at a time under model_gate; a failing loader marks only that model missing; no model object survives"
    requirement: "SET-01"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_system_status.py#test_warm_up_goes_loading_to_ready_one_model_at_a_time_under_the_gate"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_system_status.py#test_a_failing_loader_marks_only_that_model_missing_and_logs"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_system_status.py#test_warm_up_waits_while_a_lesson_job_holds_the_model_gate"
        status: pass
    human_judgment: false
  - id: D3
    description: "Real warm-up against the real Demucs / mlx-whisper / wav2vec2 weights on the 8 GB machine (memory stays low, state reaches ready, S1 banner clears)"
    requirement: "SET-01"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_system_status.py#test_demucs_loader_loads_infers_then_frees_even_when_inference_fails"
        status: pass
    human_judgment: true
    rationale: "Loader call order and release are unit-tested with fakes; no real model was run in this worktree, so memory behaviour and timings need a real run (make dev) before they are trusted."
  - id: D4
    description: "GET/PUT /settings: defaults when no file, atomic save, 422 invalid_settings for relative/missing/file/unwritable dataDir, contract violations rejected, corrupt file -> defaults; dataDir applies only after restart without moving files; precedence settings.json > DATA_DIR > default"
    requirement: "SET-04"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_settings_api.py#test_put_new_data_dir_applies_only_after_restart"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_settings_api.py#test_data_dir_precedence_file_over_env_over_default"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_settings_api.py#test_lifespan_pins_the_data_dir_at_startup"
        status: pass
    human_judgment: false
  - id: D5
    description: "Key check: 200 saves to .env (0600, other lines kept) and hot-loads; 401/403 and network/5xx write nothing; malformed keys (newline, =, spaces, short) make zero HTTP calls; the key never appears in a response or log record"
    requirement: "SET-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_openai_key.py#test_valid_key_is_saved_to_env_and_hot_loaded"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_openai_key.py#test_malformed_key_never_reaches_the_network_or_the_env_file"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_openai_key.py#test_the_key_never_appears_in_any_log_record"
        status: pass
    human_judgment: false
  - id: D6
    description: "Checking a real OpenAI key against api.openai.com from S8"
    requirement: "SET-03"
    verification: []
    human_judgment: true
    rationale: "Tests use httpx.MockTransport and never call the real OpenAI API; only a live run with Liam's key proves the real response mapping."

duration: about 50 min
completed: 2026-10-07
status: complete
---

# Phase 2 Plan 11: System status, settings and OpenAI key Summary

**Backend for S1 banners and S8: `/system/status` (HF-cache model state with a load-infer-release warm-up under the model gate), `/settings` persisted outside DATA_DIR with restart-time `dataDir` precedence, and `/settings/openai-key/check` that writes `.env` (0600, hot-loaded) only after OpenAI answers 200.**

## Performance

- **Duration:** about 50 min (wall-clock estimate; start time was not captured)
- **Tasks:** 3 (Task 1 tracer, Tasks 2 and 3 TDD)
- **Files:** 7 created, 5 modified (12 in the diff)
- **Tests:** `uv run --project services/audio --frozen pytest services/audio/tests -q` -> 613 passed (556 after Task 2); `ruff check` and `ruff format` clean

## Accomplishments

- Tracer (Task 1, `27e51ac`): `GET /system/status` end to end. Models are `missing` when the cache-only check (`download=False`, never a network call) finds no snapshot, otherwise `loading`; `maskedKey` is absent without a key; the endpoint is 200 with no key (SET-02).
- Settings (Task 2): `config_dir()` / `settings_file_path()`, `get_settings()` applies a valid saved `dataDir` over `DATA_DIR` once per process, `settings_store` (defaults, tolerant read, `validate_data_dir`, atomic write), `GET`/`PUT /settings`. A new `dataDir` changes nothing until restart and no file is moved.
- Key flow (Task 3): `KEY_RE` gate before any write or network call, `set_openai_key` (creates the file 0600, `dotenv.set_key` keeps other lines, chmod 600, `os.environ` hot load), `check_openai_key` (httpx, 10 s, 200/401/403/other mapping), and the router mapping to `{valid, saved, maskedKey?, reason?}`.
- Warm-up (Task 3): `start_warm_up(gate, loaders=None, *, warm_up=None)` daemon thread, demucs -> whisper -> wav2vec2, each loader under `with gate`, skipped when missing from the cache, failure -> `missing` + `logger.exception`. Real loaders run one inference on 1 s of silence and release (Demucs with an MPS->CPU retry like `_real_separate`; Whisper via `release_whisper`; wav2vec2 via `del` + `free_accelerator_memory`). `main.py` starts it after `runner.start()`.
- Test isolation: an autouse fixture redirects `SHADOWENGLAB_CONFIG_DIR` and `SHADOWENGLAB_ENV_FILE`, removes `OPENAI_API_KEY` (restored even if a test sets it directly), clears the settings cache and resets the warm-up holder to "all missing".

## Exact precedence rule (for ADR 0005, 02-19)

`dataDir` = `settings.json` `dataDir` if it is an absolute path to an existing directory, else `DATA_DIR` from env/`.env`, else `~/shadowenglab-data`. Resolved once per process: `config.get_settings()` is `lru_cache`d and the lifespan calls it before anything else. `GET /settings` returns the saved (pending) value, `GET /system/status.activeDataDir` returns the one in use. A saved `dataDir` that is no longer a directory is ignored with a warning (falls back to `DATA_DIR`/default).

## Warm-up timings

Not measured. No real model was run in this worktree (the tests use fake loaders and a monkeypatched cache check). RESEARCH footprints (2.5 / 4.6 / 6.0 GB) are the only numbers; a real `make dev` run is needed to time warm-up and confirm memory returns to baseline (coverage D3).

## Task Commits

1. **Task 1 (tracer): GET /system/status** - `27e51ac` (feat)
2. **Task 2 RED: settings tests and conftest isolation** - `5542c16` (test)
3. **Task 2 GREEN: settings GET/PUT, dataDir precedence, lifespan pinning** - `042c4cd` (feat)
4. **Task 3 RED: key check and warm-up tests** - `ba301af` (test)
5. **Task 3 GREEN: key check/save, warm-up, lifespan wiring** - `508bf72` (feat)

No REFACTOR commits.

## TDD Gate Compliance

- **Task 2 RED (`5542c16`):** `pytest test_settings_api.py` -> 25 failed, 0 passed. Failures: `AttributeError: module 'audio_service.config' has no attribute 'settings_file_path' / 'config_dir'`, `assert 404 == 200/422` for the absent `/settings` routes, `ImportError: cannot import name 'settings_store'`. Semantic assessment: every target test executed and failed on the planned absence of the feature (no syntax, collection or fixture faults). pytest output is not a format `gsd_run check tdd-red-evidence` parses, so no classifier verdict exists; the assessment is manual (same as 02-06).
- **Task 2 GREEN (`042c4cd`):** full suite 556 passed.
- **Task 3 RED (`ba301af`):** 54 failed, 10 passed. Failures: `AttributeError` for `routers.settings.get_http_client`, `secrets_env.InvalidKeyError / KEY_RE / set_openai_key / check_openai_key` and `system_status.start_warm_up / real_loaders`. The 10 passing tests are the 7 Task 1 status tests plus tests of behaviour that already held (`no openai import`, two others), so they are not RED evidence. Semantic assessment: the failing targets executed and failed on the planned absence of the symbols.
- **Task 3 GREEN (`508bf72`):** full suite 613 passed.
- **REFACTOR:** none.

## Decisions Made

See `key-decisions` in the frontmatter. In short: precedence rule above; `saved` is true exactly when `valid` is true (the contract does not define it more precisely, so this is an interpretation worth a glance); malformed key -> `valid false` / `invalid` with no network call; no whitespace stripping.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `PUT /settings` could change the active data dir before a restart**
- **Found during:** Task 2 GREEN (`test_put_new_data_dir_applies_only_after_restart` failed)
- **Issue:** `get_settings()` is lazy, so if nothing had called `data_root()` before the PUT, the first call after it read the new `dataDir` immediately, breaking the D-12 restart semantics. In production the lifespan happened to call it early only by accident (`recover_interrupted()`).
- **Fix:** `main.py` lifespan calls `get_settings()` first thing so the resolution is pinned at startup; added `test_lifespan_pins_the_data_dir_at_startup`; the `client` test fixture resolves the data dir up front to mimic startup.
- **Files modified:** `services/audio/src/audio_service/main.py`, `services/audio/tests/test_settings_api.py`
- **Committed in:** `042c4cd`

**2. [Rule 3 - Blocking] `tests/test_api.py` shell test no longer lists `system` and `settings`**
- **Found during:** Task 1 and Task 2 verify
- **Issue:** `test_p1_router_shells_exist_and_are_mounted_empty` asserts the shell routers are empty; filling them breaks it (the plan's verify runs test_api.py).
- **Fix:** removed only `"system"` (Task 1) and `"settings"` (Task 2) from the parametrize list, as the orchestrator note asked. Expect a trivial textual conflict with sibling plans at merge; the resolution is to remove every filled name.
- **Files modified:** `services/audio/tests/test_api.py` (outside `files_modified`)
- **Committed in:** `27e51ac`, `042c4cd`

**3. [Rule 2 - Missing critical] conftest also resets the shared warm-up holder**
- **Found during:** Task 1/3 design
- **Issue:** `test_api.py` enters the lifespan with no deps (`with TestClient(create_app())`), which now starts a real warm-up and would load real models whenever they are cached on the machine.
- **Fix:** the autouse fixture sets the warm-up holder to "all models missing" (nothing to load) and resets it afterwards.
- **Files modified:** `services/audio/tests/conftest.py`
- **Committed in:** `5542c16`

**4. [Rule 2 - Missing critical] Demucs warm-up retries once on CPU after an MPS error**
- **Found during:** Task 3
- **Issue:** the plan's loader had no fallback; an MPS failure would mark Demucs `missing` and show the wrong "run make setup" banner.
- **Fix:** same retry pattern as `pipeline._real_separate`.
- **Files modified:** `services/audio/src/audio_service/system_status.py`
- **Committed in:** `508bf72`

### Notes

- Added small helpers beyond the artifact list: `env_path()`, `InvalidKeyError`, `InvalidDataDirError`, `reset_warm_up`, `get_warm_up`, `real_loaders`, `real_cache_check`. No contract type, field or error code was added: every response is built from the approved generated models and only existing `ApiErrorCode` values are used (`invalid_settings`, `internal_error`, `invalid_request`).
- A contract violation on `PUT /settings` (repeat 4, accent "UK") answers 422 `invalid_request` (the global validation handler), not `invalid_settings`; `invalid_settings` is reserved for an unusable `dataDir`.
- `mypy`/`pyright` are not installed in the project venv; only `ruff` was run.

**Total deviations:** 4 auto-fixed (1 Rule 1, 1 Rule 3, 2 Rule 2). **Impact:** none on scope or contract.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-02-30 (KEY_RE, 0600, written only after 200), T-02-31 (key never in response/log/exception; tests check responses and captured log records), T-02-32 (absolute + existing + directory + writable, no moves), T-02-33 (settings.json parsed through `AppSettings`, invalid -> defaults) and T-02-34 (one model at a time under `model_gate`, released after one inference) are implemented and tested. T-02-SC: no dependency added (`httpx` and `python-dotenv` were already locked); `uv sync --frozen` only.

## User Setup Required

None - no external service configuration required. (A real OpenAI key is only needed to try the key check live from S8.)

## Next Phase Readiness

- S1/S8 UI plans can read `GET /system/status`, `GET/PUT /settings` and `POST /settings/openai-key/check` with the approved shapes.
- 02-19 (ADR 0005) can copy the precedence rule and the D-18 warm-up reading from this summary.
- Open for a real run: warm-up timings and memory on the 8 GB machine, and one live key check.

## Self-Check: PASSED

- FOUND: system_status.py, secrets_env.py, settings_store.py, tests/conftest.py, test_system_status.py, test_settings_api.py, test_openai_key.py
- FOUND commits (ancestors of HEAD): 27e51ac, 5542c16, 042c4cd, ba301af, 508bf72
- Acceptance greps re-run: `"/system/status"`, `def build_status`, `download=False`, `KEY_RE`, `set_key`, `0o600`, `def check_openai_key`, `https://api.openai.com/v1/models`, `"/settings/openai-key/check"`, `def start_warm_up`, `with gate`, `start_warm_up` in main.py, zero `openai` imports; full audio suite 613 passed; `git show --diff-filter=D` on HEAD lists no deletions

---
*Phase: 02-p1-t-o-b-i-v-tr-nh-ph-t*
*Completed: 2026-10-07*
