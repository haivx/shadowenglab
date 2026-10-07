---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 06
subsystem: api
tags: [fastapi, sqlite, attempts, library, progress, tdd, path-safety]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-01 approved shapes (LessonListItem, LessonProgress, attempts DDL B, numbering C); 02-03 store.iter_lessons/load_lesson, router shells, ApiErrorException"
provides:
  - "GET /lessons: LessonListItem[] from lesson.json scan + practiced counts from SQLite, newest first"
  - "GET /lessons/{id}/progress: LessonProgress (per-segment attempts/voicedAttempts, firstUnpracticedIndex)"
  - "db.py: DATA_DIR/app.db with the single approved `attempts` table (WAL, user_version 1) and DAO"
  - "config.py path helpers app_db_path, eval_clips_dir, tmp_dir, stems_dir"
affects: [02-08, 02-09, 02-10, 02-12, 02-13]

tech-stack:
  added: []
  patterns:
    - "one sqlite3 connection per call (autocommit, isolation_level=None), manual BEGIN IMMEDIATE for read-then-write; schema ensured lazily once per process per db path"
    - "every lesson id validated with ULID_RE before any SQL; only `?` parameters (the IN list builds only `?` markers)"
    - "LessonSummary built from the dumped lesson minus `segments` so absent optionals stay absent"

key-files:
  created:
    - services/audio/src/audio_service/db.py
    - services/audio/tests/test_db.py
    - services/audio/tests/test_library_api.py
  modified:
    - services/audio/src/audio_service/config.py
    - services/audio/src/audio_service/routers/library.py
    - services/audio/tests/test_config.py
    - services/audio/tests/test_api.py

key-decisions:
  - "No contract, DDL, column, index or table was added: db.py creates exactly the `attempts` table approved in 02-01 item B (a test asserts sqlite_master holds only that table and the 7 approved columns)"
  - "An unreadable or schema-invalid lesson.json yields 404 not_found on /progress (and is skipped in /lessons) rather than 500"
  - "Attempts whose segment_index >= segmentCount are ignored when computing practicedCount/firstUnpracticedIndex in the list"

patterns-established:
  - "Missing-feature RED without stubs: new tests call `module.func` via attribute access so each target test fails on its own (AttributeError / 404 != 200) without breaking collection of the existing tests"

requirements-completed: [LES-03, LES-06, PLY-04]

duration: ~35 min
completed: 2026-10-07
status: complete
plan_head_before: 57cd5d456e98a0b3a8ee370782f8e5fd2d4f211b
plan_head_after: e0d0c2883125087680d93402386dec2be9783524
actuals:
  tokens: 14000
  tasks: 2
  commits: 3

coverage:
  - id: D1
    description: "GET /lessons returns light LessonListItem[] (no segments, no nulls except firstUnpracticedIndex), newest first, with practicedCount/firstUnpracticedIndex from voiced attempts; error and audioQuality pass through; corrupt lesson.json skipped"
    requirement: "LES-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_library_api.py#test_list_orders_newest_first_with_practice_counts"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_library_api.py#test_corrupt_lesson_json_is_skipped_not_500"
        status: pass
    human_judgment: false
  - id: D2
    description: "attempts table matches the approved DDL only; numbering per (lesson, segment) is atomic under concurrent writers"
    requirement: "PLY-04"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_db.py#test_concurrent_inserts_get_distinct_numbers"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_library_api.py#test_attempts_db_has_only_the_approved_schema"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /lessons/{id}/progress with empty / all-practiced / not-ready / unknown-id edges"
    requirement: "PLY-04"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_library_api.py#test_progress_lists_only_attempted_segments"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_library_api.py#test_progress_unknown_or_malformed_id_is_404_api_error"
        status: pass
    human_judgment: false
  - id: D4
    description: "eval_clips_dir, tmp_dir and stems_dir resolve inside DATA_DIR and reject bad ids, negative or inverted ranges and symlink escapes"
    requirement: "LES-06"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_config.py#test_stems_dir_rejects_negative_or_inverted_range"
        status: pass
    human_judgment: false
---

# Phase 2 Plan 06: Library and practice progress Summary

**GET /lessons and GET /lessons/{id}/progress built on a lesson.json scan plus the approved SQLite `attempts` table (WAL, user_version 1, BEGIN IMMEDIATE numbering), with contained app.db / eval_clips / tmp / stems path helpers for 02-10 and 02-12.**

## Performance

- **Duration:** about 35 min
- **Tasks:** 2 (Task 1 tracer, Task 2 TDD)
- **Files:** 3 created, 4 modified
- **Tests:** `uv run --project services/audio --frozen pytest services/audio/tests -q` -> 437 passed; `ruff check` and `ruff format` clean

## Accomplishments

- Tracer (Task 1, `c6e8f9c`): GET /lessons end to end: `store.iter_lessons()` scan, practiced indexes from SQLite, `LessonListItem` per lesson, newest first (createdAt desc, id as tie-break). Tracer verify re-ran green before expansion (`46 passed` for test_library_api + test_api).
- `db.py` creates only the approved `attempts` table; `ensure_schema` is idempotent and runs once per process per db path under a lock; `connection()` is one autocommit connection per call with WAL and foreign_keys.
- Edge cases resolved explicitly: no attempts -> firstUnpracticedIndex 0; all practiced -> null; not-ready lesson (segments []) -> counts 0 and null; unreadable lesson.json skipped in the list and 404 on /progress.
- Path helpers: `eval_clips_dir()` and `tmp_dir()` create on demand, `stems_dir(video_id, start_ms, end_ms)` validates the id with VIDEO_ID_RE and `0 <= start_ms < end_ms`; all go through `_contained`.

## DAO and helper signatures (for 02-10 and 02-12)

```python
# audio_service/db.py
@dataclass(frozen=True) class AttemptRow: lesson_id, segment_index, attempt, created_at, duration_ms, voiced: bool, saved_for_eval: bool
@dataclass(frozen=True) class SegmentProgressRow: segment_index, attempts, voiced_attempts
def connection() -> ContextManager[sqlite3.Connection]          # one per call, autocommit, Row factory
def ensure_schema(conn: sqlite3.Connection) -> None
def insert_attempt(lesson_id: str, segment_index: int, *, duration_ms: int, voiced: bool,
                   saved_for_eval: bool = False) -> int         # returns 1, 2, 3... per (lesson, segment)
def mark_saved_for_eval(lesson_id: str, segment_index: int, attempt: int) -> bool
def get_attempt(lesson_id: str, segment_index: int, attempt: int) -> AttemptRow | None
def segment_progress(lesson_id: str) -> list[SegmentProgressRow]  # only segments with >= 1 attempt
def practiced_indexes(lesson_ids: Sequence[str]) -> dict[str, set[int]]
def first_unpracticed_index(segment_count: int, practiced: set[int]) -> int | None

# audio_service/config.py
def app_db_path() -> Path
def eval_clips_dir() -> Path          # DATA_DIR/eval_clips, mkdir
def tmp_dir() -> Path                 # DATA_DIR/tmp, mkdir
def stems_dir(video_id: str, start_ms: int, end_ms: int) -> Path   # videos/{id}/stems/{start}-{end}, not created
```

Bad lesson ids, negative indexes or bad ranges raise `InvalidIdError` (a ValueError). `stems_dir` does not create the directory (02-12 owns writing).

## Task Commits

1. **Task 1 (tracer): GET /lessons** - `c6e8f9c` (feat)
2. **Task 2 RED: failing tests** - `f634c1d` (test)
3. **Task 2 GREEN: progress endpoint, DAO, path helpers** - `e0d0c28` (feat)

No REFACTOR commit.

## TDD Gate Compliance

- **RED (`f634c1d`):** `pytest test_db.py test_config.py test_library_api.py` -> 28 failed, 39 passed. Failures: `AttributeError` for the absent `db.get_attempt`, `db.mark_saved_for_eval`, `db.segment_progress`, `config.eval_clips_dir`, `config.tmp_dir`, `config.stems_dir`, and `{'detail': 'Not Found'} != <LessonProgress / ApiError body>` for the absent progress route. Semantic assessment: each target test executed and failed on the planned absence of the feature (no syntax, import, fixture or collection errors; pre-existing tests still passed). The `insert_attempt` numbering/concurrency tests and `app_db_path` test passed at RED because those were already implemented in Task 1 (the tracer needed them), so they are not RED evidence. pytest output is not one of the formats `gsd_run check tdd-red-evidence` parses, so no classifier verdict was produced; the assessment is manual.
- **GREEN (`e0d0c28`):** full audio suite 437 passed.
- **REFACTOR:** none.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tests/test_api.py` shell test no longer lists the `library` router**
- **Found during:** Task 1 verify
- **Issue:** `test_p1_router_shells_exist_and_are_mounted_empty[library]` asserts the router has no routes; filling `routers/library.py` (the plan's purpose) necessarily breaks it, and the plan's own verify command runs test_api.py.
- **Fix:** removed `"library"` from that test's parametrize list (one-line change). The file is outside `files_modified`; the change is the minimum needed.
- **Merge note for the orchestrator:** sibling plans that fill `media`, `attempts`, `settings`, `system`, `segments` or `translate` shells must make the same edit on the same list line, so expect a trivial textual conflict there.
- **Files modified:** `services/audio/tests/test_api.py`
- **Commit:** `c6e8f9c`

### Notes

- `/lessons/..%2Fetc/progress` style ids can be decoded into extra path segments by the client and then never reach the handler (default FastAPI 404, not the ApiError body); the test asserts only 404 and no file leak for those two ids and the ApiError body for ids that reach the handler.
- The plan calls `segment_progress(L)` -> `[{segmentIndex...}]`; the DAO returns `SegmentProgressRow` dataclasses and the router converts them to the camelCase contract shape.

**Total deviations:** 1 auto-fixed (Rule 3). **Impact:** none on scope or contract.

## Known Stubs

None.

## Threat Flags

None. Mitigations T-02-14 (ULID_RE before SQL, `?` parameters only), T-02-15 (all new paths through `_check_id` and `_contained`, traversal/bad-range/symlink tests) and T-02-16 (corrupt lesson.json skipped, list never 500s) are implemented and tested. The only prohibition (no schema beyond the approved `attempts`) is enforced by a test on `sqlite_master` and `PRAGMA table_info`.

## Issues Encountered

None.

## Next Phase Readiness

02-10 can call `insert_attempt`, `mark_saved_for_eval`, `get_attempt`, `eval_clips_dir`, `tmp_dir`; 02-12 can call `stems_dir`; 02-08/02-13 can consume `GET /lessons` and `GET /lessons/{id}/progress`. REQUIREMENTS.md untouched here (LES-03/LES-06/PLY-04 UI halves land in 02-08/02-09/02-13).

## Self-Check: PASSED

- FOUND: services/audio/src/audio_service/db.py, services/audio/tests/test_db.py, services/audio/tests/test_library_api.py
- FOUND commits (ancestors of HEAD): c6e8f9c, f634c1d, e0d0c28
- All acceptance criteria re-checked by grep; full audio suite 437 passed
