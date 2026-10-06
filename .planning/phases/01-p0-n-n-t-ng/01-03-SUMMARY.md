---
phase: 01-p0-n-n-t-ng
plan: 03
subsystem: infra
tags: [check-deps, setup-models, huggingface-hub, demucs, mlx-whisper, wav2vec2, parselmouth, posix-sh]

requires:
  - phase: 01-p0-n-n-t-ng
    provides: "services/audio/uv.lock đã duyệt, NODE_MIN 22.13 và pnpm 11.9.0 (01-01 mục 1)"
provides:
  - "scripts/check_deps.sh: cổng system dependency kiểu check-and-guide (D-25), không cài gì"
  - "audio_service.models: nguồn duy nhất của ba model id đã khoá (D-22, D-23, D-24)"
  - "python -m audio_service.setup_models: tải/tìm cache 3 model có progress, kiểm tra parselmouth/ffmpeg/MPS, in bảng trạng thái"
affects: [01-06, 01-08, 01-09]

actuals:
  tokens: 14000
  tasks: 2
  commits: 1
plan_head_before: df5a1a61d987445f78dfb1f15efdd2413c6fc929
plan_head_after: 09b8f7dae2988cdca6fcbef56384b3f94c7c640f

tech-stack:
  added: []
  patterns:
    - "Check-and-guide: script chỉ in lệnh cài, không bao giờ chạy brew/npm/curl"
    - "Model id chỉ định nghĩa ở models.py, không flag hay env var nào ghi đè"
    - "Hàm kiểm tra trả CheckResult(name, ok, detail, required); main trả 0 khi mọi mục required ok"

key-files:
  created:
    - scripts/check_deps.sh
    - services/audio/src/audio_service/models.py
    - services/audio/src/audio_service/setup_models.py
    - services/audio/tests/test_setup.py
  modified: []

key-decisions:
  - "ensure_demucs(download=True) gọi get_model('hf://htdemucs') để không bao giờ rơi về repo AWS cũ"
  - "download=False kiểm tra cache bằng snapshot_download(..., local_files_only=True) trên adefossez/HTDemucs"

requirements-completed: [FND-04]

coverage:
  - id: D1
    description: "check_deps.sh thoát 1 và in đúng lệnh cài khi thiếu tool, thoát 0 khi đủ; không chạy installer nào"
    requirement: FND-04
    verification:
      - kind: unit
        ref: "services/audio/tests/test_setup.py (stub-PATH tests a-d)"
        status: pass
      - kind: other
        ref: "env PATH=/usr/bin:/bin sh scripts/check_deps.sh -> exit 1 và có 'brew install ffmpeg espeak-ng'"
        status: pass
    human_judgment: false
  - id: D2
    description: "setup_models tải/tìm cache ba model đã khoá, kiểm tra parselmouth, ffmpeg, MPS và in bảng trạng thái"
    requirement: FND-04
    verification:
      - kind: unit
        ref: "services/audio/tests/test_setup.py (e-g, parametrization bổ sung)"
        status: pass
      - kind: other
        ref: "uv run --project services/audio --frozen python -m audio_service.setup_models -> exit 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "ffmpeg và espeak-ng có mặt trên máy này sau khi Liam cài"
    requirement: FND-04
    verification:
      - kind: other
        ref: "ffmpeg -version; espeak-ng --version; sh scripts/check_deps.sh -> exit 0"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-06
status: complete
---

# Phase 1 Plan 03: check_deps + setup_models Summary

**Cổng system dependency kiểu check-and-guide (POSIX sh, không tự cài) cùng `setup_models` tải/xác minh ba model đã khoá (whisper-large-v3-turbo, wav2vec2-lv-60-espeak-cv-ft, htdemucs) và in bảng trạng thái; sau khi Liam cài ffmpeg + espeak-ng, cả hai kiểm tra thoát 0 trên máy thật.**

## Performance

- **Duration:** ~25 min (không tính thời gian chờ Liam cài ffmpeg/espeak-ng)
- **Tasks:** 2 (Task 1 tracer auto, Task 2 checkpoint human-action)
- **Files modified:** 4 (tất cả là file mới)

## Accomplishments

- `scripts/check_deps.sh` kiểm tra Darwin/arm64, ffmpeg, espeak-ng, uv, pnpm, node (so major.minor với NODE_MIN 22.13), in một dòng OK/THIẾU mỗi tool và chỉ in lệnh cài cho phần thiếu rồi thoát 1.
- `models.py` giữ ba model id và `PPG_ALLOW_PATTERNS`; test (g) khoá chúng đúng nguyên văn.
- `setup_models.py` có `CheckResult`, `ensure_hf_snapshot`, `ensure_demucs`, `check_parselmouth`, `check_ffmpeg`, `check_mps`, `format_status_table`, `main` với cờ `--no-download`.
- 23 test trong `test_setup.py` (257 dòng) đều pass; chạy với stub PATH nên không động vào hệ thống.
- Task 2: Liam trả lời "done"; orchestrator xác nhận ffmpeg 9.0.2 và espeak-ng 1.52.0 trên PATH; cả hai lệnh xác minh thoát 0 (bảng bên dưới).

## Bảng trạng thái (Task 2 verification)

### 1. `sh scripts/check_deps.sh` — exit 0

```
Kiểm tra system dependency (ShadowEngLab):
  platform   OK     Darwin arm64
  ffmpeg     OK     ffmpeg version 9.0.2 Copyright (c) 2000-2026 the FFmpeg developers
  espeak-ng  OK     eSpeak NG text-to-speech: 1.52.0  Data at: /opt/homebrew/Cellar/espeak-ng/1.52.0/share/espeak-ng-data
  uv         OK     uv 0.12.10 (3c979abda 2026-09-04 aarch64-apple-darwin)
  node       OK     v24.16.0 (cần >= 22.13)
  pnpm       OK     11.9.0
Tất cả system dependency đã đủ.
```

### 2. `uv run --project services/audio --frozen python -m audio_service.setup_models` — exit 0

```
check                                 status  detail
------------------------------------  ------  ------
mlx-community/whisper-large-v3-turbo  OK      đã tải/có trong cache: /Users/xuanhai/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb
facebook/wav2vec2-lv-60-espeak-cv-ft  OK      đã tải/có trong cache: /Users/xuanhai/.cache/huggingface/hub/models--facebook--wav2vec2-lv-60-espeak-cv-ft/snapshots/ae45363bf3413b374fecd9dc8bc1df0e24c3b7f4
demucs htdemucs                       OK      đã tải/có trong cache HF (adefossez/HTDemucs)
parselmouth                           OK      praat-parselmouth 0.4.7 chạy được
ffmpeg                                OK      ffmpeg version 9.0.2 Copyright (c) 2000-2026 the FFmpeg developers
mps                                   OK      torch MPS khả dụng
```

`ffmpeg -version` và `espeak-ng --version` đều thoát 0.

## Ghi chú về cách Demucs lấy trọng số

Với demucs 4.1.0, `get_hf_model` tải qua `huggingface_hub.hf_hub_download` từ repo `adefossez/HTDemucs` (file `htdemucs.yaml` và `<sig>.safetensors`) vào HF cache. `get_model("htdemucs")` âm thầm rơi về repo AWS cũ khi HF lỗi, nên không dùng trực tiếp (xem Deviation 1).

## Task Commits

1. **Task 1: Tracer check_deps.sh → setup_models** — `09b8f7d` (feat)
2. **Task 2: Liam cài ffmpeg và espeak-ng** — checkpoint:human-action, không có commit (Liam "done"; xác minh ở trên)

**Plan metadata:** commit `docs(01-03): complete plan summary`. Các merge commit của plan 01-02 và 01-04 vào nhánh này không tính là commit của plan.

## Files Created/Modified

- `scripts/check_deps.sh` — gate system dependency, chỉ in lệnh cài
- `services/audio/src/audio_service/models.py` — hằng số model id (nguồn duy nhất)
- `services/audio/src/audio_service/setup_models.py` — tải/xác minh model, kiểm tra runtime, bảng trạng thái
- `services/audio/tests/test_setup.py` — test stub-PATH cho script và test mock cho setup_models

## Decisions Made

- Tải Demucs qua `hf://htdemucs` để không bao giờ chạm repo AWS legacy; chế độ `--no-download` chỉ kiểm tra cache cục bộ.
- Ba model đã có sẵn trong HF cache trên máy này nên lần chạy này không tải gì (xác minh "máy sạch" thật vẫn do 01-08 Task 3 đảm nhiệm, theo assumption đã flag trong plan).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `ensure_demucs` không dùng `get_model("htdemucs")` trần**
- **Found during:** Task 1 (đối chiếu demucs 4.1.0 `hf.py`)
- **Issue:** `get_model("htdemucs")` rơi về repo AWS cũ khi HF lỗi, tức có thể tải trọng số ngoài nguồn đã khoá (vi phạm prohibition governance về model id, T-01-09).
- **Fix:** `download=True` gọi `get_model("hf://htdemucs")` (không fallback); `download=False` dùng `snapshot_download(..., local_files_only=True)` trên `adefossez/HTDemucs`.
- **Files modified:** `services/audio/src/audio_service/setup_models.py`
- **Verification:** test_setup.py pass; bảng trạng thái hiện `adefossez/HTDemucs`
- **Committed in:** 09b8f7d

**2. [Bổ sung test] Test thêm ngoài (a)–(g)**
- Parametrization ranh giới phiên bản Node, gợi ý khi chỉ thiếu một trong hai tool, `main` từ chối `--whisper-repo`, xử lý `local_files_only`, và quét xác nhận không module nào khác hard-code model id. Tổng 23 test.
- **Committed in:** 09b8f7d

---

**Total deviations:** 1 auto-fixed (Rule 2) + 1 bổ sung test
**Impact on plan:** Chặt hơn prohibition về model id; không scope creep.

## Issues Encountered

None. Cả ba model đã nằm sẵn trong HF cache nên không có tải xuống thật nào trong plan này.

## User Setup Required

Đã hoàn tất: Liam chạy `brew install ffmpeg espeak-ng` (D-25). Không còn bước thủ công nào.

## Threat Surface

Mitigation theo threat_model:

- T-01-08: test (d) với stub `brew`/`npm` ghi marker, xác nhận không installer nào chạy, cộng quét script.
- T-01-09: model id cố định trong models.py (test g), `allow_patterns` giới hạn file wav2vec2, không bật remote-code, cache nằm ngoài repo.
- T-01-SC: `uv sync --frozen` từ lockfile đã duyệt ở 01-01.

## Threat Flags

None.

## Known Stubs

None.

## Next Phase Readiness

- 01-06 import `WHISPER_REPO`, `PPG_REPO`, `PPG_ALLOW_PATTERNS`, `DEMUCS_MODEL` từ `audio_service.models`.
- 01-08 nối `@sh scripts/check_deps.sh` làm dòng đầu của `make setup`, rồi `python -m audio_service.setup_models`.
- Không có blocker.

## Self-Check: PASSED

- Task 1: `pytest services/audio/tests/test_setup.py -q` -> 23 passed; `env PATH=/usr/bin:/bin sh scripts/check_deps.sh` -> exit 1 và in `brew install ffmpeg espeak-ng`; models.py chứa cả ba id; setup_models.py chứa `snapshot_download`, `--no-download`, `def main(`, `from audio_service.models import`; check_deps.sh chứa `exit 1` và `brew install`; test_setup.py 257 dòng (>= 60).
- Task 2: check_deps.sh exit 0, setup_models exit 0, ffmpeg và espeak-ng `--version` exit 0 (bảng ở trên).
- Commit `09b8f7d` là tổ tiên của HEAD; `git log df5a1a6..HEAD --grep='(01-03)'` = 1 commit (khớp `commits: 1`).

---
*Phase: 01-p0-n-n-t-ng*
*Completed: 2026-10-06*
