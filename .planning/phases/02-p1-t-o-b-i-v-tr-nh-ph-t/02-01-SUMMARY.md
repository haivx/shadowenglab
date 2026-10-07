---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 01
subsystem: contracts
tags: [zod, json-schema, pydantic, datamodel-codegen, vitest, contract-first]

requires:
  - phase: 01-foundation
    provides: packages/contracts Zod pipeline, scripts/contracts_gen.sh, drift gate, fixture round-trip test
provides:
  - "Zod contracts AttemptAck, AppSettings, VideoPreview, CreateLessonRequest, LessonSummary, LessonListItem, SegmentProgress, LessonProgress, ModelStatuses, SystemStatus, OpenAiKeyCheckRequest, OpenAiKeyCheckResult, UpdateSegmentTextRequest, ApiError (+ ApiErrorCode, ModelState enums)"
  - "regenerated contracts.schema.json and contracts_gen.py with pydantic classes for all of them"
  - "11 round-trip fixtures; 15 fixture files in total"
  - "Decision record 'Quyết định đã chốt' (A1..A10, B..H) that plans 02-02..02-19 read"
affects: [02-03, 02-04, 02-05, 02-06, 02-07, 02-08, 02-09, 02-10, 02-11, 02-12, 02-13, 02-14, 02-15, 02-16, 02-17, 02-18, 02-19]

actuals:
  tokens: 9900
  tasks: 2
  commits: 2

plan_head_before: 57700e789361079580374601d4983b788a8ae59a
plan_head_after: 3c5b6f4648df470874ac35ba044e3efad9c4e961

tech-stack:
  added: []
  patterns:
    - "Every new object carries .meta({ id }); enums used inline (ApiErrorCode, ModelState) carry no id and become Literal in pydantic"
    - "Optional = absent (never null); nullable only where intentional (OpenAiKeyCheckResult.valid, firstUnpracticedIndex)"
    - "LessonSummary = Lesson.omit({ segments: true }).meta({ id }) keeps the pydantic class name stable"

key-files:
  created:
    - packages/contracts/src/api.ts
    - packages/contracts/src/settings.ts
    - packages/contracts/src/attempt.ts
    - packages/contracts/fixtures/AttemptAck.json
    - packages/contracts/fixtures/AppSettings.json
    - packages/contracts/fixtures/VideoPreview.json
    - packages/contracts/fixtures/CreateLessonRequest.json
    - packages/contracts/fixtures/LessonListItem.json
    - packages/contracts/fixtures/LessonProgress.json
    - packages/contracts/fixtures/SystemStatus.json
    - packages/contracts/fixtures/OpenAiKeyCheckRequest.json
    - packages/contracts/fixtures/OpenAiKeyCheckResult.json
    - packages/contracts/fixtures/UpdateSegmentTextRequest.json
    - packages/contracts/fixtures/ApiError.json
  modified:
    - packages/contracts/src/index.ts
    - packages/contracts/src/contracts.test.ts
    - packages/contracts/schema/contracts.schema.json
    - services/audio/src/audio_service/contracts_gen.py

key-decisions:
  - "Liam answered `approved` on 2026-10-07: every item A1..A10 and B..H accepted exactly as proposed, no overrides"
  - "Implemented only the approved shapes: no extra field, ApiError code or type was added"

patterns-established:
  - "Contract gate first: shapes and DB schema approved by Liam in one stop, then implemented TDD (fixtures + edge tests RED, schemas GREEN)"

requirements-completed: [SET-01, SET-03, SET-04, LES-01, LES-03, PLY-04, REC-03, REC-04]

coverage:
  - id: D1
    description: "Approved Phase 2 shapes exist in Zod and export from packages/contracts"
    requirement: "LES-03"
    verification:
      - kind: unit
        ref: "packages/contracts/src/contracts.test.ts#phase 2 contract edges"
        status: pass
    human_judgment: false
  - id: D2
    description: "JSON Schema and pydantic regenerated with a $defs entry per new object and no anonymous defs; drift gate green"
    requirement: "LES-03"
    verification:
      - kind: integration
        ref: "UV_NO_SYNC=1 uv run --project services/audio --frozen pytest services/audio/tests/test_contracts_drift.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every new fixture round-trips Zod -> JSON Schema -> pydantic -> Zod"
    requirement: "SET-01"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_contracts_roundtrip.py#test_roundtrip"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-10-07
status: complete
---

# Phase 2 Plan 01: Contract gate Summary

**Phase 2 wire contracts (attempt ack, settings, system status, key check, lesson list/progress, preview, API error envelope) approved by Liam in one stop and implemented in Zod, regenerated to JSON Schema and pydantic, with 11 round-tripping fixtures and edge tests.**

## Performance

- **Duration:** about 40 min (continuation agent; Task 1 decision was taken by the previous run)
- **Completed:** 2026-10-07
- **Tasks:** 2 (Task 1 decision only, Task 2 TDD)
- **Files modified:** 18 (11 fixtures, 3 new source files, index.ts, contracts.test.ts, 2 generated files)

## Quyết định đã chốt

Liam answered `approved` on 2026-10-07. Every item below is the value proposed in 02-01-PLAN.md Task 1; source is "recommended" for all rows (no overrides). Field names are camelCase on the wire; `?` = optional (absent, never null); `| null` = intentionally nullable.

| Item | Final value | Source |
| ---- | ----------- | ------ |
| A1 | `AttemptAck` {lessonId: string, segmentIndex: int >= 0, attempt: int >= 1, durationMs: int ms >= 0, voiced: boolean, savedForEval: boolean} (D-06 as locked) | recommended |
| A2 | `AppSettings` {playbackRate: number in [0.5, 1] (UI offers 0.75 and 1), repeat: 1 \| 2 \| 3, recordFactor: number in [1, 2] (UI offers 1.25 / 1.5 / 2.0), dataDir: string (absolute path), accent: literal "US"}. No defaults inside the contract; the server fills defaults (1, 1, 1.5, current data dir, "US") | recommended |
| A3 | `VideoPreview` {videoId, title, durationSec: seconds, channel?: string, thumbnailUrl?: string, existingLessonId?: string} | recommended |
| A4 | `CreateLessonRequest` {url: string, start?: seconds, end?: seconds} | recommended |
| A5 | `LessonSummary` = Lesson without `segments` (own id so pydantic names stay stable); `LessonListItem` {lesson: LessonSummary, segmentCount: int >= 0, practicedCount: int >= 0, firstUnpracticedIndex: int >= 0 \| null (null = every sentence practiced)}. GET /lessons returns an array of LessonListItem (light payload, RESEARCH Pitfall 14) | recommended |
| A6 | `SegmentProgress` {segmentIndex: int >= 0, attempts: int >= 0 (every upload), voicedAttempts: int >= 0}; `LessonProgress` {lessonId, segments: SegmentProgress[] (only segments with >= 1 attempt), firstUnpracticedIndex: int >= 0 \| null}. "Practiced" = voicedAttempts >= 1 (D-08) | recommended |
| A7 | `ModelState` = "missing" \| "loading" \| "ready"; `ModelStatuses` {demucs, whisper, wav2vec2: ModelState}; `SystemStatus` {models: ModelStatuses, hasKey: boolean, maskedKey?: string, activeDataDir: string} (D-13; mic state stays client-side) | recommended |
| A8 | `OpenAiKeyCheckRequest` {apiKey?: string (absent = test the saved key)}; `OpenAiKeyCheckResult` {valid: boolean \| null (null = could not check), saved: boolean, maskedKey?: string, reason?: "invalid" \| "network" \| "no_key"} (D-11, SET-03) | recommended |
| A9 | `UpdateSegmentTextRequest` {text: string, 1-500 chars after trim}; PATCH / extend-end / translate respond with the existing `Segment` | recommended |
| A10 | `ApiErrorCode` enum (inline literal, no id): invalid_request, invalid_url, channel_url, video_unavailable, live_video, invalid_range, duplicate_lesson, not_found, invalid_state, invalid_segment, unsupported_media, payload_too_large, recording_too_long, busy, no_openai_key, upstream_error, network_error, invalid_settings, forbidden_origin, internal_error. `ApiError` {code: ApiErrorCode, message: string (Vietnamese, user-facing, never a path or stack), lessonId?: string (only with duplicate_lesson)} | recommended |
| B | SQLite schema (D-02), file `DATA_DIR/app.db`, stdlib sqlite3, WAL, `PRAGMA user_version = 1`, one table: `attempts(lesson_id TEXT NOT NULL, segment_index INTEGER NOT NULL CHECK >= 0, attempt INTEGER NOT NULL CHECK >= 1, created_at TEXT NOT NULL (ISO-8601 UTC "...Z"), duration_ms INTEGER NOT NULL CHECK >= 0, voiced INTEGER NOT NULL CHECK IN (0,1), saved_for_eval INTEGER NOT NULL DEFAULT 0 CHECK IN (0,1), PRIMARY KEY (lesson_id, segment_index, attempt))`. Phase 3 adds score columns | recommended |
| C | Attempt numbering (Open Q7a): every upload, voiced or not, inserts a row and increments `attempt` per (lesson, segment); the UI "Lượt k" counts voiced attempts only | recommended |
| D | "Lưu clip cho eval" after the fact (Open Q7b, D-09, REC-04): `PUT /lessons/{id}/segments/{i}/attempts/{n}/eval-clip` re-sends the blob kept in the browser; the server re-normalizes, writes `DATA_DIR/eval_clips/{lessonId}_{index:04d}_{attempt:02d}.wav` + `.json` sidecar (lessonId, segmentIndex, attempt, text), sets `saved_for_eval = 1`, creates no new attempt | recommended |
| E | "Mất chữ cuối?" while the model gate is busy (Open Q9, PLY-05): `endExtraMs += 300` is saved immediately (playback uses it at once); feature + IPA recompute waits for the model gate up to 150 s, then answers 503 `busy` (the saved extension stays) | recommended |
| F | Duplicate lesson (Open Q10): duplicate = same videoId AND same resolved range AND status != failed. Preview returns `existingLessonId` for the default range (whole video if <= 6 min, else 00:00-05:00); POST /lessons answers 409 `duplicate_lesson` with `lessonId` for any exact duplicate | recommended |
| G | dataDir precedence (D-10, D-12): `settings.json` dataDir (if the file has the key) > `DATA_DIR` from env/.env > `~/shadowenglab-data`, resolved once at process start; changes apply after restart. Test override of the settings folder via env `SHADOWENGLAB_CONFIG_DIR` | recommended |
| H | ADRs (Open Q8): `docs/decisions/0004-bo-iframe-video-tu-host.md` (D-17, in 02-07) and one `docs/decisions/0005-job-runner-attempts-settings-p1.md` (job runner + model gate + D-18 warm-up reading, `attempts` schema, dataDir precedence, `Segment.text` may differ from the joined `words` after "Sửa câu", D-19/D-20/D-21, items C-F) in 02-19 | recommended |

Endpoint surface these shapes serve (built in 02-03..02-16): GET /system/status; GET+PUT /settings; POST /settings/openai-key/check; GET /videos/preview?url=; POST /lessons; GET /lessons; POST /lessons/{id}/retry; GET /lessons/{id}/progress; GET /lessons/{id}/video (Range); POST /lessons/{id}/video/reload; PATCH /lessons/{id}/segments/{i}; POST .../segments/{i}/extend-end; POST .../segments/{i}/translate; POST .../segments/{i}/attempts (multipart audio + saveForEval); PUT .../segments/{i}/attempts/{n}/eval-clip.

Items B..H are decisions only; they have no code in this plan (the `attempts` DDL, eval-clip route, busy-gate behavior, duplicate rule, dataDir precedence and ADRs are built in later plans).

## Generated pydantic class names

Later plans import these from `audio_service.contracts_gen`:

- New I/O classes: `AttemptAck`, `AppSettings`, `VideoPreview`, `CreateLessonRequest`, `LessonListItem`, `LessonProgress`, `SystemStatus`, `OpenAiKeyCheckRequest`, `OpenAiKeyCheckResult`, `UpdateSegmentTextRequest`, `ApiError`.
- Nested classes: `LessonSummary`, `SegmentProgress`, `ModelStatuses`.
- `ApiErrorCode`, `ModelState` and `AppSettings.repeat`/`accent` are inlined as `Literal[...]` (no class), as with `LessonStatus` in Phase 1.
- `FirstUnpracticedIndex` (a `RootModel[int]`) is emitted by datamodel-codegen because the same `integer >= 0 | null` shape is reused by `LessonListItem` and `LessonProgress`. Same pattern as the Phase 1 `Sound` and `WordBound` root models. It validates from a plain int or None, but the generated annotation is `FirstUnpracticedIndex | None`, so server code should pass a plain `int | None` into model validation rather than constructing the root model by hand.
- Python field names are snake_case with camelCase aliases (`populate_by_name=True`); dump with `by_alias=True, exclude_unset=True` as the round-trip test does.

## Accomplishments

- Implemented the 14 approved object shapes plus the two inline enums exactly as approved; Schemas map grew from 6 to 17 keys.
- Regenerated `contracts.schema.json` and `contracts_gen.py` through `scripts/contracts_gen.sh` only (no hand edits); no anonymous `__schema` defs; header still says GENERATED.
- 11 new fixture files (>= 2 valid cases each, LessonListItem covers `error`, `audioQuality` and `firstUnpracticedIndex: null`), all round-trip through Zod, JSON Schema and pydantic.
- Edge tests: optional-as-null rejected (VideoPreview.channel), AttemptAck.attempt 0 rejected, AppSettings.repeat 4 / accent "UK" / out-of-range rate and factor rejected, UpdateSegmentTextRequest "", whitespace and 501 chars rejected, LessonListItem requires `firstUnpracticedIndex` (null accepted), ApiError rejects unknown code and accepts all 20.

## Task Commits

1. **Task 1: Liam approves contract shapes, SQLite schema and defaults** - none (checkpoint:decision; answer `approved`, recorded above)
2. **Task 2 RED: failing tests and fixtures** - `cc147e4` (test)
3. **Task 2 GREEN: Zod contracts, regenerated schema and pydantic** - `3c5b6f4` (feat)

No REFACTOR commit was needed.

**Plan metadata:** the SUMMARY docs commit follows this file (hash recorded by the orchestrator).

## TDD Gate Compliance

- **RED:** `cc147e4`. Command: `pnpm --silent --filter @shadowenglab/contracts exec vitest run --reporter=tap-flat`, exit 1, 39 of 58 tests failing, 19 passing. Classifier verdict `RED_EVIDENCE_OK` (reason `target_test_failed`) with target `src/contracts.test.ts > phase 2 contract edges > AttemptAck.attempt starts at 1: 0 rejected, 1 accepted`. Semantic assessment: the target executed and failed with `TypeError: Cannot read properties of undefined (reading 'safeParse')` because `AttemptAck` was not exported yet, and the schema-key test failed on `expected [...] to include 'ApiError'`. These are the planned absence-of-feature failures, not syntax, import or fixture faults; the existing 19 tests still passed.
- **GREEN:** `3c5b6f4`. Vitest 58/58 pass; round-trip + drift pytest 61 passed.
- **REFACTOR:** none.

## Decisions Made

- Followed the approved list verbatim; no override was applied.
- `repeat` is `z.union` of three literals (generates `Literal[1, 2, 3]`), `accent` is `z.literal("US")`, as the plan specified.
- `UpdateSegmentTextRequest.text` uses `z.string().trim().min(1).max(500)` as specified; generated pydantic keeps `min_length=1, max_length=500` (the trim happens on the Zod side; servers must strip before validating).

## Deviations from Plan

None - plan executed exactly as written.

Environment setup note (not a deviation): the worktree had no `node_modules` or venv, so `pnpm install --frozen-lockfile` and `uv sync --project services/audio --frozen` were run from the existing lockfiles. No package was added, upgraded or resolved; `git status` stayed clean after install. Plan 02-02's dependency changes and its package-legitimacy gate were not touched.

## Issues Encountered

None.

## Known Stubs

None. Only contract definitions, fixtures and generated code were added.

## Threat Flags

None. The new shapes sit on the existing web <-> FastAPI boundary already covered by T-02-01 / T-02-02. `ApiError.message` is documented as fixed Vietnamese text; the routers that emit it (02-03..02-16) carry the test that responses never leak paths or exception text.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 02-02..02-19 can build against the approved shapes; the contract is public (one-way) after merge.
- Server work that depends on this gate: `attempts` DDL (item B), eval-clip route (D), busy gate (E), duplicate rule (F), dataDir precedence (G), ADRs 0004 / 0005 (H).
- Caveat for implementers: `FirstUnpracticedIndex` root model (see above) and snake_case/alias handling in `contracts_gen.py`.

## Self-Check: PASSED

- FOUND: packages/contracts/src/api.ts, settings.ts, attempt.ts, index.ts, contracts.test.ts
- FOUND: 15 fixture files in packages/contracts/fixtures
- FOUND: packages/contracts/schema/contracts.schema.json (ApiError def), services/audio/src/audio_service/contracts_gen.py (AttemptAck, LessonListItem, SystemStatus classes)
- FOUND commits: cc147e4, 3c5b6f4

---
*Phase: 02-p1-t-o-b-i-v-tr-nh-ph-t*
*Completed: 2026-10-07*
