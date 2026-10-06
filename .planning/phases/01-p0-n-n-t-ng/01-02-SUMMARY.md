---
phase: 01-p0-n-n-t-ng
plan: 02
subsystem: contracts-api
tags: [zod, json-schema, datamodel-code-generator, pydantic, fastapi, cors, path-safety]

requires:
  - phase: 01-01
    provides: "quyết định 1-10 đã chốt, lockfile đã duyệt (pnpm + uv)"
provides:
  - "Contract Lesson (Zod) -> contracts.schema.json -> contracts_gen.py (pydantic v2) -> GET /lessons/{id}, một lệnh sinh lại"
  - "FastAPI create_app(): /health, /lessons/{id}, /scoring (rỗng), CORS chỉ http://localhost:3000"
  - "config.py: Settings (DATA_DIR từ .env gốc repo, expand ~) + helper đường dẫn D-08 có kiểm tra id và containment"
affects: [01-03, 01-04, 01-05, 01-06, 01-07, 01-08]

tech-stack:
  added: []
  patterns:
    - "Contract một chiều: Zod -> JSON Schema bundle (io: input, $defs có id) -> pydantic sinh tự động; sửa Zod rồi chạy sh scripts/contracts_gen.sh"
    - "Response bằng model sinh ra + response_model_exclude_unset=True (optional vắng mặt vẫn vắng mặt, alias camelCase)"
    - "Mọi id đi vào đường dẫn đều fullmatch regex rồi resolve().is_relative_to(data_root())"

key-files:
  created:
    - packages/contracts/src/common.ts
    - packages/contracts/src/lesson.ts
    - packages/contracts/src/index.ts
    - packages/contracts/src/generate.ts
    - packages/contracts/schema/contracts.schema.json
    - scripts/contracts_gen.sh
    - services/audio/src/audio_service/contracts_gen.py
    - services/audio/src/audio_service/config.py
    - services/audio/src/audio_service/main.py
    - services/audio/src/audio_service/routers/__init__.py
    - services/audio/src/audio_service/routers/lesson.py
    - services/audio/src/audio_service/routers/scoring.py
    - services/audio/tests/test_api.py
    - services/audio/tests/test_config.py
  modified: []

key-decisions:
  - "Giữ đúng quyết định 01-01 mục 2/4/6/9: Field(alias) tường minh, Word.i trong segment từ 0, Health là model riêng của Python, cận contract"
  - "TimeRange/AudioQuality/LessonError/Word/Segment/Lesson đều có .meta({ id }); LessonStatus và các primitive không có id nên inline"
  - "datamodel-codegen thêm --target-python-version 3.11 (theo plan); file sinh dùng from __future__ import annotations"

requirements-completed: [FND-02, FND-03, FND-06]

actuals:
  tokens: 21000
  tasks: 2
  commits: 3
plan_head_before: df5a1a61d987445f78dfb1f15efdd2413c6fc929
plan_head_after: 058dde00a291914cd2a6bbba0f1fc856e138ebb9

coverage:
  - id: D1
    description: "Lesson (Zod) -> contracts.schema.json -> contracts_gen.py sinh bằng một lệnh, $defs đủ 6 id, không def ẩn danh"
    requirement: FND-02
    verification:
      - kind: other
        ref: "sh scripts/contracts_gen.sh && node check $defs (Lesson, Segment, Word, TimeRange, AudioQuality, LessonError; không __schema*)"
        status: pass
    human_judgment: false
  - id: D2
    description: "contracts_gen.py là pydantic v2 với alias camelCase và populate_by_name"
    requirement: FND-03
    verification:
      - kind: other
        ref: "grep GENERATED / class Lesson(BaseModel) / alias=\"asrProb\" / populate_by_name=True trên contracts_gen.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /lessons/{id} trả lesson.json camelCase, optional vắng mặt vẫn vắng mặt; id xấu hoặc không tồn tại -> 404; file hỏng -> 500 không lộ đường dẫn"
    requirement: FND-06
    verification:
      - kind: test
        ref: "services/audio/tests/test_api.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "/health, router scoring rỗng, CORS chỉ localhost:3000; helper D-08 chặn traversal, id sai, symlink thoát DATA_DIR; ~ được expand"
    requirement: FND-06
    verification:
      - kind: test
        ref: "services/audio/tests/test_api.py + services/audio/tests/test_config.py (27 passed)"
        status: pass
    human_judgment: false
---

# Phase 1 Plan 02: Tracer Lesson contract -> pydantic -> FastAPI Summary

**Lesson được viết một lần bằng Zod 4, đi qua JSON Schema bundle đã commit và datamodel-codegen thành pydantic v2 (alias camelCase), rồi FastAPI phục vụ lesson.json qua GET /lessons/{id} với /health, router /scoring rỗng và CORS chỉ cho localhost:3000.**

## Performance

- **Tasks:** 2 (Task 1 tracer, Task 2 TDD)
- **Files created:** 14, modified: 0
- **Commits:** 3 (tracer, RED test, GREEN feat)

## Accomplishments

- Contract `Word`, `Segment`, `TimeRange`, `AudioQuality`, `LessonError`, `LessonStatus`, `Lesson` đúng D-04..D-06 cộng cận 01-01 mục 9; không thêm field nào.
- `scripts/contracts_gen.sh [schema_dir] [pydantic_file]` là cửa sinh duy nhất (đã dùng được cho drift gate ở 01-08 vì nhận đường dẫn đầu ra).
- Tracer end-to-end chạy thật: 27 test pass (7 test lesson/health/CORS/scoring + test_config).
- Tracer feedback gate (HUMAN_VERIFY_MODE end-of-phase, verify chỉ có automated): chạy lại verify cuối-đến-cuối trước khi mở rộng, đều pass.

## Tên class/field do datamodel-codegen sinh (01-06 và 01-05 cần)

Các class trong `audio_service.contracts_gen`: `Word`, `TimeRange`, `LessonError`, `AudioQuality`, `Segment`, `Lesson` (thứ tự trong file). Tất cả có `model_config = ConfigDict(populate_by_name=True)`; khởi tạo bằng tên snake_case hoặc alias camelCase đều được.

| Wire (camelCase) | Python attribute | Ghi chú |
|---|---|---|
| `Lesson.id, title, status, segments` | `id, title, status, segments` | `status` là `Literal[8 giá trị]` inline |
| `videoId` | `video_id` | |
| `durationSec` | `duration_sec` | `float`, `ge=0` |
| `thumbnailUrl` | `thumbnail_url` | `str \| None = None` |
| `range` | `range` | kiểu `TimeRange` (`start`, `end`); tên trùng builtin nhưng chỉ là attribute của class |
| `padMs` | `pad_ms` | `int = 150`, `ge=0` |
| `error` | `error` | `LessonError \| None = None` (`step`, `message`) |
| `audioQuality` | `audio_quality` | `AudioQuality \| None = None`; `label` Literal clean/music, `nonVocalRatio` -> `non_vocal_ratio` |
| `createdAt` | `created_at` | `str` |
| `Segment.endExtraMs` | `end_extra_ms` | `int = 0` |
| `Segment.index, text, start, end, words, translation` | cùng tên | `translation: str \| None = None` |
| `Word.asrProb` | `asr_prob` | |
| `Word.refConfidence` | `ref_confidence` | `float \| None = None` |
| `Word.i, text, start, end, ipa, prominence` | cùng tên | `ipa`, `prominence` là `... \| None = None` |

Khi Python TỰ TẠO model (pipeline 01-06): với field optional, bỏ hẳn kwarg thay vì truyền `None` (nếu không nó bị tính là "set" và serialize thành `null`, Pitfall 5). Dump hợp đồng: `model.model_dump(mode="json", by_alias=True, exclude_unset=True)`.

## Task Commits

1. **Task 1: Tracer Lesson Zod -> schema -> pydantic -> GET /lessons/{id}** - `1b7b1bd` (feat)
2. **Task 2 RED: test /health, CORS, scoring, helper D-08** - `fa15ddf` (test, 3 test fail đúng lý do)
3. **Task 2 GREEN: /health, scoring rỗng, CORS** - `058dde0` (feat)

## Deviations from Plan

None - plan executed exactly as written. Ghi nhận không phải lệch:

- Task 1 đã hiện thực đủ helper D-08 trong `config.py` (theo bước 7 của plan) nên các test đường dẫn của Task 2 pass ngay ở bước RED; chỉ 3 test /health, CORS, scoring fail (đúng như mong đợi) rồi được GREEN.
- `.meta({ id })` và định dạng file TS do prettier chuẩn hoá (xuống dòng), nội dung không đổi.

**Total deviations:** 0.

## Issues Encountered

None. Cảnh báo `StarletteDeprecationWarning` (dùng httpx với TestClient) trong pytest là của thư viện, không thuộc phạm vi plan (pyproject/lockfile bị khoá bởi cổng 01-01; không thêm package).

## Authentication Gates

None.

## Known Stubs

None. Router `/scoring` rỗng là chủ ý của plan (FND-06), Phase 3/5 thêm endpoint.

## Threat Flags

None - bề mặt mới (GET /lessons/{id}, CORS, đường dẫn từ id) đều nằm trong threat_model: T-01-04 (regex + containment + test traversal/lowercase/symlink), T-01-05 (CORS allow-list + test origin lạ), T-01-06 (detail cố định, test không lộ tmp_path), T-01-07 (header GENERATED + cửa sinh duy nhất; drift gate ở 01-08), T-01-SC (chỉ `--frozen`).

## Next Phase Readiness

- 01-05 mở rộng `Schemas` trong `packages/contracts/src/index.ts` rồi chạy `sh scripts/contracts_gen.sh`; 01-06 dùng bảng tên field ở trên; 01-08 dùng `scripts/contracts_gen.sh <tmp_schema_dir> <tmp_py_file>` cho drift gate và chạy uvicorn với `--host 127.0.0.1`.
- Không có blocker.

## Self-Check: PASSED

- Files: tất cả file trong key-files.created tồn tại (kiểm tra bằng git ls-files)
- Commits `1b7b1bd`, `fa15ddf`, `058dde0` là tổ tiên của HEAD; `git rev-list --count df5a1a6..HEAD` = 3
- Verify chạy lại: `sh scripts/contracts_gen.sh` thành công, `$defs` đủ 6 id không `__schema*`, grep contracts_gen.py pass, pytest `test_api.py test_config.py` 27 passed, ruff check/format sạch

---
*Phase: 01-p0-n-n-t-ng*
*Completed: 2026-10-06*
