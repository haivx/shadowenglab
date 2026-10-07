---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 03
subsystem: api
tags: [fastapi, job-runner, threading, tdd, cors, trustedhost, apierror, whisper]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-01 contract (CreateLessonRequest, ApiError codes, Lesson); 02-02 frozen lockfiles"
provides:
  - "JobRunner: download pool (2 slots) + one FIFO model worker holding model_gate"
  - "POST /lessons (201, queued) and POST /lessons/{id}/retry (202) with ApiError bodies"
  - "recover_interrupted() at startup, retry_lesson(), release_whisper()"
  - "API boundary: write CORS, TrustedHost, foreign-Origin guard, ApiError 422"
  - "Seven empty P1 router shells mounted"
affects: [02-06, 02-07, 02-10, 02-11, 02-12, 02-15, 02-16]

tech-stack:
  added: []
  patterns:
    - "job runner in-process: ThreadPoolExecutor for downloads, one daemon 'model-worker' thread, FIFO by awaiting submission-ordered download futures"
    - "lesson.json is the source of truth; every read-modify-write goes through store.update_lesson (per-lesson lock + atomic write)"
    - "ApiErrorException -> JSON body built from the generated ApiError model; absent lessonId stays absent"
    - "retry rebuilds from dump_contract() dict with error/audioQuality popped, never model_copy(update={'error': None})"

key-files:
  created:
    - services/audio/src/audio_service/lesson/jobs.py
    - services/audio/src/audio_service/lesson/store.py
    - services/audio/src/audio_service/errors.py
    - services/audio/src/audio_service/routers/library.py
    - services/audio/src/audio_service/routers/media.py
    - services/audio/src/audio_service/routers/attempts.py
    - services/audio/src/audio_service/routers/settings.py
    - services/audio/src/audio_service/routers/system.py
    - services/audio/src/audio_service/routers/segments.py
    - services/audio/src/audio_service/routers/translate.py
    - services/audio/tests/test_jobs.py
    - services/audio/tests/test_lessons_api.py
  modified:
    - services/audio/src/audio_service/lesson/pipeline.py
    - services/audio/src/audio_service/lesson/transcribe.py
    - services/audio/src/audio_service/main.py
    - services/audio/src/audio_service/routers/lesson.py
    - services/audio/tests/test_api.py
    - services/audio/tests/test_pipeline.py

key-decisions:
  - "FIFO of model steps is enforced by queueing (lesson_id, download_future) in submission order under a submit lock; the worker awaits each future, so a later job that downloads faster still waits its turn"
  - "A download that fails is marked failed and skipped; it never reaches the model step and never blocks later jobs"
  - "Origin guard is an HTTP middleware (not CORS) because multipart POST is a CORS simple request (Pitfall 7); requests without an Origin header (scripts, TestClient) pass"
  - "REQUIREMENTS.md not touched: LES-02, LES-03, LES-07 are backend-complete here but their UI halves (picker 02-13, S1 card progress/retry button) land in later plans"

patterns-established:
  - "Router shells: no prefix, tags=[name], no routes; later plans add endpoints without editing main.py"
  - "Tests that need the lifespan use `with TestClient(create_app(deps=fakes), base_url='http://127.0.0.1')`; TrustedHost requires a loopback base_url"

requirements-completed: []

duration: multi-session (first executor stopped by an API rate limit; continued in the same worktree)
completed: 2026-10-07
status: complete
plan_head_before: d725816d5e3527d6137378caff1d85e39a1c3eda
plan_head_after: 1240634f22619d89d4f83cf7b6ef257be749b3e2
actuals:
  tokens: 20000
  tasks: 3
  commits: 5
---

# Phase 2 Plan 03: Job runner and API boundary Summary

**A lesson created over HTTP now runs queued -> ready in an in-process runner (parallel downloads, one FIFO model worker), with retry, restart recovery, Whisper release and a locked-down write API (CORS, TrustedHost, Origin guard, ApiError 422).**

## Performance

- **Tasks:** 3 of 3 (Task 1 tracer, Task 2 and 3 TDD with RED then GREEN commits)
- **Tests:** `uv run --project services/audio --frozen pytest services/audio/tests -q` -> 388 passed
- **Interruption:** the first executor was killed by an API rate limit during Task 2 with only RED stubs and a finished test file uncommitted. The continuation verified the stubs were the only production change, committed the tests as RED (17 failing), then implemented GREEN.

## Accomplishments

- Tracer (Task 1, b4c009d): POST /lessons -> JobRunner -> ready observed through GET /lessons/{id}, invalid URL 400 and duplicate 409 with ApiError bodies.
- Queue guarantees proven by thread tests without models: B's download starts while A is in its model step, never two model steps at once, model order equals submission order (even when job 1 downloads last), worker survives a failing stage and a failing `mark_failed`.
- `retry_lesson`: failed only, same lessonId, `error`/`audioQuality` keys absent (verified with `json.loads`), `segments == []`, `seg/` removed, resubmitted; not-failed -> `InvalidState` -> HTTP 409 `invalid_state`; unknown or malformed id -> 404 `not_found`.
- `recover_interrupted`: runs in the lifespan before `runner.start()`, marks unfinished lessons `failed` with `{step: <status>, message: "bị gián đoạn"}`, idempotent, restarts nothing.
- `release_whisper`: clears mlx-whisper `ModelHolder.model`/`model_path`, `gc.collect()`, `mx.clear_cache()` when importable; no import of mlx-whisper if never loaded. `default_deps().free_memory` calls it before `free_accelerator_memory`.
- API boundary: CORS GET/POST/PUT/PATCH for http://localhost:3000 only; TrustedHost 127.0.0.1/localhost (others 400); foreign Origin on non-GET/HEAD/OPTIONS -> 403 `forbidden_origin`; `RequestValidationError` -> 422 `invalid_request` with fixed text and no echo; seven router shells mounted.

## Function signatures other plans import

```python
# lesson/pipeline.py
class StepError(Exception): message: str
def default_range(duration_sec: float) -> tuple[float, float]
def resolve_range(duration_sec: float, start: float | None, end: float | None, *, use_default: bool) -> tuple[float, float]
def create_lesson(url: str, *, start: float | None = None, end: float | None = None,
                  deps: PipelineDeps, timer: StepTimer | None = None,
                  info: download.VideoInfo | None = None) -> Lesson
def stage_download(lesson_id: str, *, deps: PipelineDeps, timer: StepTimer | None = None,
                   on_status: Callable[[Lesson], None] | None = None) -> Lesson
def stage_model(lesson_id: str, *, deps: PipelineDeps, timer: StepTimer | None = None,
                on_status: Callable[[Lesson], None] | None = None) -> Lesson
def mark_failed(lesson_id: str, exc: BaseException, *, on_status=None) -> None
def run_lesson(url, *, start=None, end=None, deps=None, timer=None, on_status=None)  # wrapper kept

# lesson/store.py
def lesson_lock(lesson_id: str) -> threading.Lock            # not reentrant
def load_lesson(lesson_id: str) -> Lesson                     # InvalidIdError / FileNotFoundError / ValidationError
def save_lesson(lesson: Lesson) -> None                       # atomic
def update_lesson(lesson_id: str, fn: Callable[[Lesson], Lesson]) -> Lesson
def iter_lessons() -> Iterator[Lesson]                        # skips invalid files, never raises

# lesson/jobs.py
class JobRunner: start(); submit(lesson_id); stop(); model_gate: threading.Lock
class InvalidState(Exception)
def recover_interrupted() -> list[str]
def retry_lesson(lesson_id: str, runner: Submitter) -> Lesson

# lesson/transcribe.py
def release_whisper() -> None

# errors.py
class ApiErrorException(status_code, code, message, *, lesson_id=None)
def error_response(status_code, code, message, *, lesson_id=None) -> JSONResponse
def install_error_handlers(app) -> None

# main.py
def create_app(*, deps: PipelineDeps | None = None) -> FastAPI   # app.state.runner, app.state.deps
```

Note: `create_lesson` in the router passes `info` it already fetched (the router needs the duration for the default range), a small addition to the plan's signature.

## Task Commits

1. Task 1 (tracer): b4c009d - POST /lessons -> JobRunner -> ready
2. Task 2 RED: 507a7e9 - 17 failing tests against stubs
3. Task 2 GREEN: 8672c90 - retry, recovery, Whisper release
4. Task 3 RED: 08b3225 - boundary tests failing
5. Task 3 GREEN: 1240634 - CORS, TrustedHost, Origin guard, 422 handler, router shells

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tests/test_api.py` client fixture switched to a loopback base_url**
- **Found during:** Task 3 (RED)
- **Issue:** TestClient's default Host `testserver` is rejected by the new TrustedHost middleware.
- **Fix:** fixture uses `TestClient(create_app(), base_url="http://127.0.0.1")`, as the plan itself prescribes in Task 3 action 4.
- **Commit:** 08b3225

**2. [Plan interpretation] Router shells use `tags=[name]` and no prefix** per the plan; the `scoring` shell (prefix `/scoring`) was left as is.

**3. [Process] Task 2 interrupted by an API rate limit.** No code or scope change resulted; RED evidence was captured from the surviving test file before any GREEN code was written (17 failed, 5 passed).

### Scope notes

- `mypy`/`pyright` are not installed in the project venv, so only `ruff format`/`ruff check` were run for static checks.
- REQUIREMENTS.md intentionally unmodified (see key-decisions); STATE.md and ROADMAP.md untouched per the orchestrator.

## TDD Gate Compliance

Task 2 and Task 3: `test(02-03)` RED commits (507a7e9, 08b3225) precede the `feat(02-03)` GREEN commits (8672c90, 1240634). RED evidence for Task 2: 17 failed against NotImplementedError stubs and a missing `release_whisper`; for Task 3: 18 failed before middleware/handlers/routers existed.

## Known Stubs

None. The seven router shells are intentionally empty and documented in each module docstring with the plan that fills them (02-06, 02-07, 02-10, 02-11, 02-15, 02-16).

## Threat Flags

None beyond the plan's register. T-02-05 (Origin guard, TrustedHost, CORS), T-02-07 (fixed messages, no input echo on 422), T-02-09 (per-lesson lock, atomic writes, retry only from failed) are implemented and tested.

## Next Phase Readiness

Wave-2 plans can add endpoints to the shell routers without touching `main.py`, and can use `store.update_lesson`, `runner.model_gate` and `app.state.deps`. 02-11 still has to add its lifespan warm-up.

## Self-Check: PASSED

All created files exist; commits b4c009d, 507a7e9, 8672c90, 08b3225, 1240634 are ancestors of HEAD; full audio test suite 388 passed.
