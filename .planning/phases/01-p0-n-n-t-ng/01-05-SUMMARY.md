---
phase: 01-p0-n-n-t-ng
plan: 05
subsystem: contracts
tags: [zod, json-schema, pydantic, round-trip, scoring, eval, vitest, pytest]

requires:
  - phase: 01-02
    provides: "Lesson contract, scripts/contracts_gen.sh, generate.ts, contracts_gen.py"
provides:
  - "ScoreResult (D-10..D-15), 7-variant Issue union, IssueCode (score.ts)"
  - "Label, WordFlags, ClipManifest, ClipWord (eval.ts)"
  - "Schemas = Segment, Lesson, ScoreResult, IssueCode, ClipManifest, Label (đủ sáu kiểu FND-02)"
  - "cli-parse.ts: cổng Zod cho test Python"
  - "Round-trip D-21 TS <-> JSON Schema <-> pydantic cho mọi fixture + test biên, cả ba bên cho cùng kết luận"
affects: [01-06, 01-08, P2, P3, P4, P5, P6, P7]

tech-stack:
  added: []
  patterns:
    - "Mọi object contract có .meta({ id }) kể cả lồng nhau (XxxData, XxxIssue) nên $defs ổn định"
    - "Fixture là mảng {name, data}; pytest parametrize trên mọi file trong packages/contracts/fixtures"
    - "Round-trip: Zod (subprocess tsx cli-parse) -> Draft202012Validator -> TypeAdapter -> dump(by_alias, exclude_unset) -> Zod, so bằng =="

key-files:
  created:
    - packages/contracts/src/score.ts
    - packages/contracts/src/eval.ts
    - packages/contracts/src/cli-parse.ts
    - packages/contracts/src/contracts.test.ts
    - packages/contracts/fixtures/ScoreResult.json
    - packages/contracts/fixtures/Lesson.json
    - packages/contracts/fixtures/Label.json
    - packages/contracts/fixtures/ClipManifest.json
    - services/audio/tests/test_contracts_roundtrip.py
  modified:
    - packages/contracts/src/index.ts
    - packages/contracts/schema/contracts.schema.json
    - services/audio/src/audio_service/contracts_gen.py

key-decisions:
  - "Giữ nguyên D-04..D-17; không thêm/bớt field, enum hay IssueCode. Chỉ chọn tên/ràng buộc ở chỗ plan để mở (xem 'Cần Liam duyệt trong PR contract')"
  - "Label.overall là z.union của literal 1..5; codegen ra Literal[1, 2, 3, 4, 5], không cần đổi cờ trong contracts_gen.sh"
  - "IssueCode và Issue được generator sinh thành RootModel (importable được, TypeAdapter chạy tốt); không đổi cờ codegen"

requirements-completed: [FND-02, FND-03]

actuals:
  tokens: 7000
  tasks: 2
  commits: 3
plan_head_before: 9a59e51123d14e6580bb785b01b0a88e63049bf1
plan_head_after: fd4eacb4edbbbdcb61b7722b9b8121860e65cb86

coverage:
  - id: D1
    description: "ScoreResult (7 loại issue, sound nullable, contour có null, chữ không ASCII) round-trip Zod -> JSON Schema -> pydantic -> Zod bằng nhau (tiêu chí hoàn thành #2)"
    requirement: FND-03
    verification:
      - kind: test
        ref: "services/audio/tests/test_contracts_roundtrip.py::test_roundtrip[ScoreResult:full], [ScoreResult:intonation-only]"
        status: pass
    human_judgment: false
  - id: D2
    description: "Lesson, Label, ClipManifest và đủ 7 giá trị IssueCode round-trip; ClipManifest không gold -> 'none'; Lesson queued segments [] và Label wordFlags [] hợp lệ ở cả ba bên"
    requirement: FND-02
    verification:
      - kind: test
        ref: "test_contracts_roundtrip.py::test_roundtrip + test_issue_code_roundtrip; packages/contracts/src/contracts.test.ts"
        status: pass
    human_judgment: false
  - id: D3
    description: "Biên: score 0/1 nhận, -0.0001/1.0001 từ chối; Label.overall 1,5 nhận, 0,6 từ chối; ms -1 và 1.5 từ chối; 2^53-1 nhận, 2^53 từ chối; attempt 0 từ chối; Zod, JSON Schema và pydantic cho cùng kết luận"
    requirement: FND-03
    verification:
      - kind: test
        ref: "test_contracts_roundtrip.py::test_python_boundaries (13 case) + contracts.test.ts 'negative and boundary edges'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Độ chính xác số (0.1, 1e-9, 12.345678901234567, 2^53-1) và Unicode (ən, Nhấn mạnh) giữ nguyên qua vòng; optional gửi null (Word.ipa: null) bị Zod từ chối"
    requirement: FND-03
    verification:
      - kind: test
        ref: "test_precision_roundtrip, test_non_ascii_survives_roundtrip, contracts.test.ts 'rejects an optional field sent as null'"
        status: pass
    human_judgment: false
  - id: D5
    description: "Schema bundle có $defs ổn định cho mọi kiểu, không có __schemaN hay DataN, mọi cận số nguyên trong ±2^53-1"
    requirement: FND-02
    verification:
      - kind: test
        ref: "packages/contracts/src/contracts.test.ts 'committed schema naming'"
        status: pass
    human_judgment: false
---

# Phase 1 Plan 05: Contract chấm điểm + eval và round-trip TS/JSON Schema/pydantic Summary

**ScoreResult (7 loại issue discriminated union theo `code`, `sound` nullable, contour có frame null), Label và ClipManifest được định nghĩa bằng Zod 4 và chứng minh bằng nhau qua Zod -> JSON Schema 2020-12 -> pydantic v2 -> Zod trên mọi fixture, kèm test biên khớp ở cả ba bên.**

## Performance

- **Tasks:** 2 (Task 1 tracer, Task 2 TDD)
- **Commits:** 3 (tracer, RED test, GREEN feat)
- **Tests:** vitest 20 pass; pytest `test_contracts_roundtrip.py` 33 pass; toàn bộ `services/audio/tests` 250 pass (không hỏng test cũ sau khi sinh lại `contracts_gen.py`)

## Accomplishments

- `score.ts`: `IssueCode`, bảy cặp `*Data` / `*Issue`, `Issue = discriminatedUnion("code", …)`, `WordScore`, `Contour`, `StressEntry`, `PauseEntry`, `Prosody`, `Scores`, `Tip`, `Versions`, `ScoreResult`, tất cả có `.meta({ id })`.
- `eval.ts`: `WordFlags`, `Label`, `ClipWord`, `ClipManifest` (`gold` mặc định `"none"`, `systemScore?` trong [0,1]).
- `cli-parse.ts`: đọc stdin, parse bằng `Schemas[name]`, in JSON ra stdout; thoát 2 cho kiểu lạ, 1 cho lỗi Zod.
- Fixture `{name, data}` cho `ScoreResult` (full, intonation-only), `Lesson` (ready, failed, queued-defaults), `Label` (flags, unsure-note), `ClipManifest` (default-gold, wrong-gold).
- `test_contracts_roundtrip.py` tự gom mọi fixture; `test_python_boundaries` kiểm cùng một phán quyết ở Zod (subprocess), JSON Schema và pydantic.
- Tracer feedback gate (verify tự động): chạy lại `sh scripts/contracts_gen.sh` + pytest trước khi mở rộng sang Task 2, đều pass.

## Tên được generator sinh (01-06 và các phase sau cần)

`audio_service.contracts_gen` giờ có: `Word, TimeRange, LessonError, AudioQuality, Segment, Lesson` (không đổi), cộng `Versions, Scores, WordScore, Contour, StressEntry, PauseEntry, Prosody, Tip, StressMismatchData, ExtraPauseData, FinalContourData, FlatPitchData, PitchDeviationData, PhoneData, WordMissingData, StressMismatchIssue … WordMissingIssue, ScoreResult, WordFlags, Label, ClipWord, ClipManifest`.

- `IssueCode` và `Issue` là `RootModel` (dùng `.root`; `TypeAdapter(IssueCode)` hoạt động). `Issue.root` là union bảy `*Issue`.
- Primitive không có id bị generator đặt tên theo tên field: `Scores.sound` kiểu `Sound(RootModel[float])`, `Contour.wordBounds` là `list[WordBound]` (`RootModel[int]`), `ScoreResult.timingMs` là `dict[str, TimingMsAdditionalProperty]` (TypeAliasType). Tên ổn định theo field, không phải kiểu `Data1`. Khi Python tự tạo `Scores`, truyền float thẳng cho `sound` được (pydantic validate), còn khi đọc dùng `.root`.
- Optional: bỏ hẳn kwarg thay vì truyền `None`; dump hợp đồng bằng `model_dump(mode="json", by_alias=True, exclude_unset=True)` (Pitfall 5, như 01-02).

## Cần Liam duyệt trong PR contract

Không thêm field, enum hay mã nào so với D-10..D-17. Các điểm plan để mở, Claude chọn như sau; sửa tại PR review nếu muốn:

- `StressMismatchData.refWord/userWord` là text của từ (string), không phải index.
- `attempt` là số nguyên >= 1 (01-01 mục 9); `segmentIndex`, `issueRef`, `wordIndex`, `afterWord`, `wordBounds[]` là số nguyên >= 0.
- `ClipManifest.systemScore` nằm trong [0,1] (Score01).
- `timingMs` là `Record<string, number >= 0>` (không ép số nguyên).
- `Label.overall` là union literal 1..5, `ExtraPauseData/PauseEntry.refMs, userMs` là ms nguyên >= 0.
- `Contour.ref/user` là `(number | null)[]` không ràng buộc độ dài giữa hai mảng và không ràng buộc `wordBounds` tăng dần.
- `WordMissingData` là object rỗng (`{}`), generator sinh class không có field.

## Task Commits

1. **Task 1 (tracer): ScoreResult round-trip** - `1131aec` (feat)
2. **Task 2 RED: fixtures + vitest + pytest biên** - `6a0ee83` (test, 8 pytest + 7 vitest fail đúng lý do: chưa có Label/ClipManifest)
3. **Task 2 GREEN: eval.ts + Schemas đủ sáu kiểu + sinh lại** - `fd4eacb` (feat)

## Deviations from Plan

None - plan executed exactly as written. Ghi nhận, không phải lệch:

- Không cần đổi cờ codegen trong `scripts/contracts_gen.sh` (bước 4 Task 1): generator 0.83.0 sinh `IssueCode` và `Issue` dưới dạng RootModel importable.
- `test_python_boundaries` được mở rộng thêm 3 case (`attempt` 0, `refMs` 1.5, `segmentIndex` 2^53) ngoài danh sách tối thiểu; và kiểm cả Zod qua subprocess để khẳng định "cùng kết luận".

**Total deviations:** 0.

## Issues Encountered

None. `make test` chưa tồn tại (01-08); drift gate (T-01-13) chạy qua `scripts/contracts_gen.sh <tmp_schema_dir> <tmp_py_file>` ở 01-08.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None - không có bề mặt mạng/auth/file mới. T-01-13 được giảm thiểu bằng round-trip trên mọi fixture và test biên cùng phán quyết ở ba bên; T-01-SC chỉ dùng `pnpm install --frozen-lockfile` và `uv sync --frozen`. T-01-14 (ClipManifest.gold/systemScore) chấp nhận, RAT-06 ở Phase 6.

## Next Phase Readiness

- 01-06 dùng `Lesson` không đổi (shape không thay đổi trong plan này). 01-08 nối drift gate và `pytest` vào `make test`; `test_contracts_roundtrip.py` cần `pnpm` và `tsx` đã cài (`pnpm install --frozen-lockfile`), mất khoảng 20 giây cho 33 case do mỗi lần gọi Zod là một tiến trình.
- Không có blocker.

## Self-Check: PASSED

- Files: score.ts, eval.ts, cli-parse.ts, contracts.test.ts, bốn fixture, test_contracts_roundtrip.py, contracts.schema.json, contracts_gen.py đều tồn tại
- Commits `1131aec`, `6a0ee83`, `fd4eacb` là tổ tiên của HEAD; `git rev-list --count 9a59e51..HEAD` = 3 (trước commit SUMMARY)
- Verify chạy lại: `pnpm --filter @shadowenglab/contracts test` 20 pass; `sh scripts/contracts_gen.sh` sạch (git status không lệch sau khi sinh); pytest round-trip 33 pass; `services/audio/tests` 250 pass; ruff và prettier sạch

---
*Phase: 01-p0-n-n-t-ng*
*Completed: 2026-10-06*
