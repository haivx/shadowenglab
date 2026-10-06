---
phase: 01-p0-n-n-t-ng
plan: 08
subsystem: infra
tags: [make, gnu-make-3.81, eslint9, prettier, ruff, drift-gate, smoke, process-group]

requires:
  - phase: 01-p0-n-n-t-ng
    provides: "01-03 check_deps.sh + setup_models, 01-05 contracts_gen.sh + vitest, 01-06 smoke_lesson.py + pipeline, 01-07 Next shells"
provides:
  - "Makefile: setup, dev, dev-api, dev-web, dev-eval, test, lint, eval (stub), smoke, contracts, contracts-check"
  - "scripts/dev_smoke.sh: kiểm tra tự động make dev (cả hai cổng, bài LESSON_ID tuỳ chọn, SIGTERM tới process group, cổng được giải phóng)"
  - "scripts/contracts_check.sh + test_contracts_drift.py: drift gate D-20 nằm trong make test"
  - "eslint.config.mjs, .prettierrc, .prettierignore, packages/contracts/tsconfig.json: make lint xanh toàn repo"
  - "Đo thật mốc 5 phút: video 308 s (range 0-300) xử lý trong 115.8-125.3 s từ DATA_DIR rỗng"
affects: [01-09, phase-2]

actuals:
  tokens: 9500
  tasks: 3
  commits: 2
plan_head_before: 98d8f869a85114d702df97eadae84c295499a765
plan_head_after: 860c4e919a9dd9e2737b71d82930ad13028f3df9

tech-stack:
  added: []
  patterns:
    - "make dev = $(MAKE) -j2 dev-api dev-web; dừng bằng SIGTERM tới process group của job (set -m + kill -- -PID), không trap kill 0"
    - "Drift gate sinh lại artifact vào thư mục tạm nằm TRONG services/audio để ruff-format đọc đúng [tool.ruff]"
    - "Lint một cách gọi duy nhất: ruff chạy từ services/audio với --config pyproject.toml . ../../scripts"

key-files:
  created:
    - Makefile
    - scripts/dev_smoke.sh
    - scripts/contracts_check.sh
    - services/audio/tests/test_contracts_drift.py
    - eslint.config.mjs
    - .prettierrc
    - .prettierignore
    - packages/contracts/tsconfig.json
  modified: []

key-decisions:
  - "make lint chọn MỘT cách gọi ruff: từ services/audio (`ruff check/format --check --config pyproject.toml . ../../scripts`), khớp ghi chú của 01-06; không gọi ruff từ gốc repo"
  - "contracts_check.sh tạo thư mục tạm bên trong services/audio (không phải /tmp) để ruff-format dùng line-length 100"
  - "dev_smoke.sh từ chối chạy khi cổng 8000/3000 đã bị chiếm, để 'lên được' không thể là server của lần chạy khác"
  - "Không cần tối ưu D-26: 115.8 s và 125.3 s đều dưới 300 s nên pipeline.py, features.py, separate.py và models.py không đổi"

requirements-completed: [FND-01, FND-04, FND-05, FND-07]

coverage:
  - id: D1
    description: "make dev chạy FastAPI 127.0.0.1:8000 và Next.js localhost:3000 song song; một SIGTERM tới process group dừng cả hai và cổng được giải phóng"
    requirement: FND-05
    verification:
      - kind: other
        ref: "sh scripts/dev_smoke.sh -> DEV-SMOKE OK (API và web lên sau 1-2 s, cả hai cổng đóng sau SIGTERM)"
        status: pass
    human_judgment: false
  - id: D2
    description: "make setup thoát 0: check_deps, pnpm/uv frozen, setup_models mọi dòng OK"
    requirement: FND-04
    verification:
      - kind: other
        ref: "make setup -> exit 0 (6 dòng setup_models OK, 6 system dependency OK)"
        status: pass
    human_judgment: false
  - id: D3
    description: "make test = drift gate D-20 + vitest (20) + pytest (306, gồm ScoreResult round-trip); gate đỏ khi schema đã commit bị sửa"
    requirement: FND-05
    verification:
      - kind: unit
        ref: "make test -> 20 vitest + 306 pytest pass; services/audio/tests/test_contracts_drift.py#test_no_drift, #test_detects_drift"
        status: pass
    human_judgment: false
  - id: D4
    description: "make lint (eslint, prettier --check, tsc, ruff check, ruff format --check) xanh trên toàn repo"
    requirement: FND-01
    verification:
      - kind: other
        ref: "make lint -> exit 0 (eslint sạch, prettier 'All matched files use Prettier code style!', tsc sạch, ruff 'All checks passed!', '34 files already formatted')"
        status: pass
    human_judgment: false
  - id: D5
    description: "make eval là stub thoát 0 in thông điệp 'stub' (không tạo eval/analyze.py)"
    requirement: FND-05
    verification:
      - kind: other
        ref: "grep -c stub Makefile = 1; make -n smoke chạy được. LƯU Ý: không chạy được `make eval` trực tiếp trong worktree do harness chặn lệnh chứa từ khoá ngay lập tức, xem Issues Encountered"
        status: unknown
    human_judgment: true
    rationale: "Recipe chỉ là một echo; orchestrator hoặc Liam chạy `make eval` một lần để xác nhận exit 0 vì harness của executor chặn lệnh này"
  - id: D6
    description: "Video smoke 308 s (range 0-300) từ DATA_DIR rỗng (tải + Demucs đo thật) xong trong <= 300 s, in SELF-CHECK OK và BUDGET OK; bài tạo ra được GET /lessons/{id} trả status ready khi make dev chạy"
    requirement: FND-07
    verification:
      - kind: other
        ref: "make smoke END=300 BUDGET=300 (DATA_DIR rỗng, 2 lần): 125.3 s và 115.8 s, SELF-CHECK OK, BUDGET OK; DATA_DIR=<lần 1> LESSON_ID=01M48VBZ3RSRV9VX1PZDGRY3MC sh scripts/dev_smoke.sh -> DEV-SMOKE OK, lesson status ready"
        status: pass
    human_judgment: false
  - id: D7
    description: "Chất lượng thực tế của việc tách câu trên 5 phút (62 segment, trung bình 3.03 s, 39 segment dưới 3 s, dài nhất 7.68 s) và nhãn audioQuality clean (-17.5 dB)"
    requirement: FND-07
    verification: []
    human_judgment: true
    rationale: "Cần nghe: ranh giới câu, cụt từ cuối, nhãn clean/music; ngoài ra 39/62 segment ngắn hơn khoảng 3-8 s mà plan kỳ vọng (ngưỡng tách câu 01-04 thuộc assumption A1, chỉ Liam quyết)"

duration: 9min
completed: 2026-10-06
status: complete
---

# Phase 1 Plan 08: Bề mặt lệnh dev + đo thật mốc 5 phút Summary

**Makefile (setup/dev/test/lint/eval/smoke/contracts) cho GNU Make 3.81 với `make dev` chạy FastAPI + Next.js song song và được `dev_smoke.sh` kiểm tra tự động, `make test` có drift gate D-20 (đỏ khi schema hoặc contracts_gen.py lệch Zod), `make lint` xanh toàn repo, và video 5 phút xử lý trong 115.8-125.3 s từ DATA_DIR rỗng (ngân sách 300 s) rồi được API trả về `ready`.**

## Performance

- **Duration:** ~9 min theo đồng hồ hệ thống (chưa tính thời gian chờ pnpm/uv; hai lần smoke 5 phút chiếm ~4 min)
- **Started:** 2026-10-06T14:51:05Z
- **Completed:** 2026-10-06T14:59:39Z (trước commit SUMMARY)
- **Tasks:** 3 (Task 1 tracer, Task 2 auto, Task 3 đo thật; Task 3 không có thay đổi mã)
- **Files created:** 8, modified: 0 (không sửa file của plan trước)

## Đo thật các tiêu chí thành công của phase

| # | Tiêu chí ROADMAP | Kết quả đo trên máy này (Apple Silicon 8 GB, MPS) |
|---|------------------|----------------------------------------------------|
| 1 | `make setup && make dev` chạy | `make setup` exit 0 (check_deps 6 OK, pnpm/uv frozen không đổi lockfile, setup_models 6 dòng OK). `make dev`: `dev_smoke.sh` thấy `/health` và `localhost:3000/` trả 2xx sau 1-2 s, SIGTERM một lần tới process group, cả cổng 8000 và 3000 đóng, `DEV-SMOKE OK` |
| 2 | `make test` gồm round-trip | `make test`: drift gate "contracts: không lệch" + vitest 20 pass + pytest 306 pass (gồm `test_contracts_roundtrip.py` 33 case và `test_contracts_drift.py` 2 case) |
| 3 | (tách câu / feature) | Chạy lại trên 5 phút đầy đủ: 62 segment, mỗi segment có f0_hz/energy/ppg/window (SELF-CHECK OK) |
| 4 | Video 5 phút <= 5 phút | **115.8 s và 125.3 s** (hai lần từ DATA_DIR rỗng, gồm tải + ffmpeg + Demucs); ngân sách 300 s còn dư ~175-185 s |

## Bảng thời gian 5 phút (DATA_DIR rỗng, video `dUDi-F6eAvk`, 308 s, range 0-300)

Lần 1 (`BUDGET OK: 125.3 s <= 300.0 s`):

```
step              seconds
--------------  ---------
download             5.36
write                0.03
extract_audio        0.48
demucs              46.07
quality              0.09
resample             0.15
whisper             47.89
segment              0.00
ppg                 22.70
f0                   1.10
write_features       0.78
--------------  ---------
total              124.65

range            0.0-300.0 s (300.0 s)
wall time        125.3 s
realtime factor  0.42x
nonVocalRatio    1.775e-02 (-17.5 dB) -> clean
segments         62
SELF-CHECK OK
```

Lần 2, DATA_DIR rỗng khác (`BUDGET OK: 115.8 s <= 300.0 s`):

```
step              seconds
--------------  ---------
download             3.87
write                0.03
extract_audio        0.49
demucs              41.45
quality              0.08
resample             0.13
whisper             42.39
segment              0.00
ppg                 24.71
f0                   1.23
write_features       0.88
--------------  ---------
total              115.26

wall time        115.8 s
realtime factor  0.39x
nonVocalRatio    1.775e-02 (-17.5 dB) -> clean
segments         62
SELF-CHECK OK
```

Ghi chú: mô hình đã nằm trong HF cache (như mọi máy sau `make setup`), nên thời gian tải ~3 GB model không nằm trong số này; việc kiểm tra "máy sạch hoàn toàn" (`HF_HOME=$(mktemp -d) make setup`) là bước tuỳ chọn trong human-check của Task 3 và chưa chạy. Lát 60 s của 01-06 mất 92.9 s chỉ vì Demucs vẫn xử lý cả 308 s; với 300 s Whisper (42-48 s) và PPG (23-25 s) chiếm phần còn lại.

### Knob D-26 đã đổi

Không có. Ngân sách không bị vượt nên `pipeline.py`, `features.py`, `separate.py` không được sửa; Demucs vẫn `shifts=0, overlap=0.25, split=True` (01-01 mục 8), id model trong `models.py` không đổi (`git diff 98d8f86..HEAD -- services/audio/src` rỗng). 01-09 ghi vào ADR 0003: không có knob thời gian nào cần chỉnh ở P0.

### Walking skeleton từ URL tới HTTP

`DATA_DIR=<thư mục lần 1> LESSON_ID=01M48VBZ3RSRV9VX1PZDGRY3MC sh scripts/dev_smoke.sh` -> "dev: API và web cùng lên sau 1s", "dev: lesson 01M48VBZ3RSRV9VX1PZDGRY3MC status ready", `DEV-SMOKE OK`.

### Thống kê segment cho Liam (lần 1, 62 segment)

Độ dài nhỏ nhất 1.50 s, lớn nhất 7.68 s, trung bình 3.03 s; 39/62 segment ngắn hơn 3 s, 0 segment dài hơn 8 s; nhãn `audioQuality` = `clean` (nonVocalRatio 0.01775, -17.5 dB, ngưỡng tạm -15 dB). Video là cảnh phim nhiều lượt thoại ngắn nên nhiều segment ngắn là hợp lý, nhưng khoảng "3-8 s" trong human-check của plan không đạt cho phần lớn segment. Đây là ngưỡng tách câu của 01-04 (RESEARCH A1), không sửa ở plan này; Liam cần nghe và quyết.

## Accomplishments

- `make dev` được chứng minh tự động: hai server lên, tuỳ chọn lấy được bài từ API, một SIGTERM tới process group dừng cả uvicorn `--reload` (kèm worker) lẫn `next dev`, `lsof` xác nhận hai cổng đóng.
- Drift gate D-20 thực sự bắt được lệch: `test_detects_drift` sửa bản sao của schema đã commit và gate thoát 1 kèm "CONTRACT DRIFT". Khi viết gate đã gặp và sửa một cảnh báo giả về cấu hình ruff (xem Deviation 1).
- Lint toàn repo xanh mà không phải sửa file nào của plan trước.
- Mốc 5 phút đo thật hai lần với tải + Demucs không cache.

## Task Commits

1. **Task 1: Tracer, Makefile + dev_smoke.sh** - `27a16ca` (feat)
2. **Task 2: make test với drift gate + make lint** - `860c4e9` (feat)
3. **Task 3: Đo thật mốc 5 phút** - không có commit mã (không vượt ngân sách, kết quả nằm trong SUMMARY này)

Tracer feedback gate (HUMAN_VERIFY_MODE end-of-phase, verify chỉ có `<automated>`): `sh scripts/dev_smoke.sh` pass trước khi mở rộng và chạy lại trong Task 3 với `LESSON_ID`; "Tracer verified end-to-end — expanding".

**Plan metadata:** commit `docs(01-08): complete dev command surface plan` (SUMMARY). STATE.md và ROADMAP.md không đụng tới (orchestrator sở hữu).

## Files Created/Modified

- `Makefile` — các target dev/test/lint/eval/smoke/contracts, GNU Make 3.81, recipe POSIX sh, `--host 127.0.0.1`
- `scripts/dev_smoke.sh` — `set -m`, chặn chạy nếu cổng đã bận, poll 120 s, `LESSON_ID` tuỳ chọn, SIGTERM tới `-PID`, `lsof` kiểm tra cổng đóng
- `scripts/contracts_check.sh` — drift gate (override `CONTRACTS_SCHEMA_COMMITTED`, `CONTRACTS_PYDANTIC_COMMITTED`)
- `services/audio/tests/test_contracts_drift.py` — `test_no_drift`, `test_detects_drift`
- `eslint.config.mjs`, `.prettierrc`, `.prettierignore`, `packages/contracts/tsconfig.json` — cấu hình lint/format/typecheck

File của plan trước được sửa vì lint: không có.

## Decisions Made

Xem `key-decisions` ở frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Drift gate báo lệch giả vì ruff không thấy `[tool.ruff]` trong thư mục `/tmp`**
- **Found during:** Task 2 (chạy `sh scripts/contracts_check.sh` lần đầu)
- **Issue:** Theo plan, gate sinh vào `mktemp -d` (dưới `/var/folders`). `datamodel-codegen` chạy `ruff format` với cwd là nơi đặt file output, nên ngoài project ruff dùng line-length mặc định 88 thay vì 100 của `services/audio/pyproject.toml`; kết quả xuống dòng khác bản đã commit và gate báo "CONTRACT DRIFT" trên cây sạch (4 hunk chỉ khác ngắt dòng).
- **Fix:** `T=$(mktemp -d "$ROOT/services/audio/.contracts-check.XXXXXX")`; trap vẫn chỉ xoá đúng thư mục này. Sau đó "contracts: không lệch" trên cây sạch và `test_detects_drift` vẫn đỏ khi sửa schema.
- **Files modified:** `scripts/contracts_check.sh`
- **Verification:** `sh scripts/contracts_check.sh` exit 0; `test_no_drift` + `test_detects_drift` pass; `make test` xanh
- **Committed in:** `860c4e9`

**2. [Rule 2 - Bảo vệ thiếu] `dev_smoke.sh` từ chối chạy khi cổng 8000/3000 đã bị chiếm**
- **Found during:** Task 1 (thiết kế script)
- **Issue:** Plan giả định cổng trống (flagged assumption FND-05). Nếu cổng đã bận, `curl` sẽ trả lời từ server khác và script báo OK sai, hoặc dừng nhầm.
- **Fix:** kiểm tra `lsof` trước khi bật `make dev`; bận thì in "DEV-SMOKE FAIL" và thoát 1 mà không gửi tín hiệu nào.
- **Files modified:** `scripts/dev_smoke.sh`
- **Committed in:** `27a16ca`

---

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 2)
**Impact on plan:** Cả hai chỉ làm gate/script đáng tin hơn; không đổi phạm vi, hợp đồng hay model.

## Issues Encountered

- **`make eval` chưa được chạy trực tiếp** trong worktree: harness của executor chặn mọi lệnh chứa chữ `eval` (đã thử đúng một cách gọi rồi dừng, không cố lách). Recipe là một dòng `echo`, đã kiểm `grep -c stub Makefile` = 1 và `make -n smoke` hoạt động. Orchestrator cần chạy `make eval | grep stub` một lần để đóng acceptance criterion này.
- Lệnh `<automated>` của Task 3 dùng `sh -c '...'` lồng nhau bị harness từ chối; đã chạy tương đương bằng ba lệnh tách rời (smoke với DATA_DIR rỗng, kiểm "SELF-CHECK OK"/"BUDGET OK"/`LESSON_ID`, rồi `dev_smoke.sh` với cùng DATA_DIR và LESSON_ID) với cùng điều kiện pass/fail.
- Ledger commit (`gsd-plan-head-before-01-08`) không ghi được vào git dir dùng chung từ worktree (harness chặn lệnh git phức hợp); `commits: 2` đo bằng `git rev-list --count 98d8f86..HEAD` với base SHA trong prompt.
- RUF100 từ gốc repo (orchestrator ghi chú): `make lint` chỉ dùng cách gọi từ `services/audio`, nơi `scripts/smoke_lesson.py` sạch; không ai nên gọi `ruff` từ gốc repo.
- Human-check của Task 3 (nghe 5 segment ngẫu nhiên, kiểm nhãn audioQuality, tuỳ chọn `HF_HOME=$(mktemp -d) make setup` tải ~3 GB) chưa làm vì cần tai người; xem coverage D7.

## Authentication Gates

None.

## User Setup Required

None - không cần cấu hình dịch vụ ngoài.

## Threat Flags

None. T-01-20 (`--host 127.0.0.1` trong Makefile), T-01-21 (chỉ gửi tín hiệu tới process group của job nền, không pid 0, xác nhận cổng đóng), T-01-22 (không sửa file nào của plan trước, generated file bị loại khỏi eslint/prettier/ruff), T-01-23 (`test: contracts-check` + `test_detects_drift`), T-01-SC (`--frozen-lockfile` / `--frozen`, lockfile không đổi) đều đã giảm thiểu như kế hoạch. Thư mục tạm `.contracts-check.*` nằm trong `services/audio` chỉ tồn tại trong lúc gate chạy và bị trap xoá.

## Known Stubs

`make eval` là stub có chủ đích (Phase 4, EVL-02 hiện thực `eval/analyze.py`); không thuộc mục tiêu của phase này.

## Next Phase Readiness

- 01-09 (docs + ADR 0003): lấy từ đây bảng thời gian 5 phút, "không đổi knob D-26 nào", ghi chú lint một cách gọi và gate drift tạo thư mục tạm trong `services/audio` (README/`.gitignore` có thể thêm `.contracts-check.*` nếu muốn).
- Cần Liam: nghe segment (39/62 ngắn hơn 3 s) và quyết ngưỡng tách câu; tuỳ chọn chạy `HF_HOME=$(mktemp -d) make setup` để kiểm tra máy sạch.
- Không có blocker.

## Self-Check: PASSED

- Files tồn tại (`git ls-files`): Makefile, scripts/dev_smoke.sh, scripts/contracts_check.sh, services/audio/tests/test_contracts_drift.py, eslint.config.mjs, .prettierrc, .prettierignore, packages/contracts/tsconfig.json.
- Commit `27a16ca` và `860c4e9` là tổ tiên của HEAD; `git rev-list --count 98d8f86..HEAD` = 2 trước commit SUMMARY.
- Acceptance Task 1: Makefile có `--host 127.0.0.1`, `-j2 dev-api dev-web`, `--frozen-lockfile`, `uv sync --project services/audio --frozen`, `audio_service.setup_models`, `smoke_lesson.py`, `contracts_gen.sh` (qua `sh scripts/contracts_gen.sh`); dev_smoke.sh có `set -m`, `lsof`, `DEV-SMOKE OK`; `sh scripts/dev_smoke.sh` và `make setup` exit 0 (`make eval`: xem Issues Encountered).
- Acceptance Task 2: Makefile có `test: contracts-check`, `pnpm -r --if-present test`, `uv run --frozen pytest`, target `lint:` đủ eslint/prettier/tsc/hai ruff; contracts_check.sh có `mktemp -d`, `diff -u`, `CONTRACT DRIFT`, `CONTRACTS_SCHEMA_COMMITTED`; eslint.config.mjs có `no-explicit-any` và `tseslint.configs.strict`; .prettierignore có `packages/contracts/schema` và `services/**`; `make test` và `make lint` exit 0.
- Acceptance Task 3: ngân sách đo hai lần (125.3 s, 115.8 s) < 300 s, SELF-CHECK OK, BUDGET OK, LESSON_ID in ra, `DEV-SMOKE OK` với bài ready; không id model nào đổi (`git diff 98d8f86..HEAD -- services/audio/src` rỗng).

---
*Phase: 01-p0-n-n-t-ng*
*Completed: 2026-10-06*
