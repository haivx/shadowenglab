---
phase: 01-p0-n-n-t-ng
plan: 09
subsystem: docs
tags: [adr, product-md, contracts, makefile, readme, env-example]

requires:
  - phase: 01-p0-n-n-t-ng
    provides: "01-01 quyết định 1-10, 01-05 contract cuối, 01-08 Makefile và số đo 5 phút"
provides:
  - "ADR 0003: D-01..D-27, 10 mục Liam chốt ở 01-01, cờ datamodel-codegen, môi trường P0, kết quả D-26"
  - "docs/product.md mục 3-4-5 khớp packages/contracts (ScoreResult, Issue union, ClipManifest, Label)"
  - "CLAUDE.md 'Lệnh' và README.md khớp Makefile và check_deps.sh; Node >= 22.13 trong PROJECT.md và .claude/CLAUDE.md"
  - "README của apps/web, apps/eval, packages/contracts, services/audio, scripts mô tả đúng mã sau P0"
affects: [phase-2, phase-3, phase-6]

actuals:
  tokens: 8500
  tasks: 3
  commits: 3
plan_head_before: 1347357280b10c1b2f5a18ec1c52d32d1eb1be17
plan_head_after: 3a022b32a81841276f98d1343eb282089278f96e

tech-stack:
  added: []
  patterns:
    - "Tài liệu chỉ mô tả cái đang tồn tại: mỗi lệnh, file, cổng được đối chiếu với Makefile, scripts/ và mã nguồn trước khi viết"
    - "product.md chỉ tóm tắt shape; packages/contracts là nguồn sự thật và được ghi rõ ngay tại khối contract"

key-files:
  created:
    - docs/decisions/0003-contract-toolchain-va-moi-truong-p0.md
  modified:
    - docs/product.md
    - CLAUDE.md
    - README.md
    - .planning/PROJECT.md
    - .claude/CLAUDE.md
    - .env.example
    - apps/web/README.md
    - apps/eval/README.md
    - packages/contracts/README.md
    - services/audio/README.md
    - scripts/README.md

key-decisions:
  - "ADR 0003 gom toàn bộ quyết định P0 vào một file theo khung 0001/0002, ghi 'Người quyết: Liam'"
  - "Không có knob D-26 nào được đổi: 115.8 s và 125.3 s đều dưới ngân sách 300 s"
  - "services/audio/README.md nói rõ scoring/ và rules/ chưa tồn tại, chỉ có router /scoring rỗng"

requirements-completed: [FND-04, FND-05]

coverage:
  - id: D1
    description: "ADR 0003 tồn tại, nêu mọi decision id D-01..D-27, các mục 1-10 của 01-01 và kết quả D-26, với metadata 'Người quyết: Liam'"
    requirement: FND-05
    verification:
      - kind: other
        ref: "vòng lặp grep D-01..D-27 trên docs/decisions/0003-contract-toolchain-va-moi-truong-p0.md + grep 'Người quyết: Liam' -> ADR_OK"
        status: pass
    human_judgment: true
    rationale: "Grep chỉ chứng minh id có mặt, không chứng minh nội dung diễn giải đúng ý Liam; Liam review ADR cùng PR contract (CLAUDE.md quy trình mục 5)"
  - id: D2
    description: "docs/product.md mục 3-4-5 khớp packages/contracts (intonationOnly, ref_unclear, refMs/userMs, union issues, source tip, finalContourMatch, Label) và không còn ref_ms/user_ms; khối SQL Data model giữ nguyên"
    requirement: FND-05
    verification:
      - kind: other
        ref: "grep intonationOnly/ref_unclear/issueRef/refMs/finalContourMatch/packages/contracts trên product.md -> FIELDS_OK; grep ref_ms|user_ms -> exit 1 (không còn); grep -c 'word_flags jsonb' = 2"
        status: pass
    human_judgment: true
    rationale: "Khối TS trong product.md là bản tóm tắt viết tay của Zod; Liam đối chiếu shape tại PR contract, không có test so sánh tự động"
  - id: D3
    description: "CLAUDE.md 'Lệnh' và README.md liệt kê đúng tám target Makefile (setup, dev, test, lint, eval, smoke, contracts, dev-eval) và điều kiện tiên quyết khớp check_deps.sh (macOS Apple Silicon, Node >= 22.13, pnpm 11.9, uv, ffmpeg, espeak-ng)"
    requirement: FND-04
    verification:
      - kind: other
        ref: "grep 'make lint|smoke|contracts|dev-eval' CLAUDE.md và 'make setup|espeak-ng' README.md -> DOCS_OK; đối chiếu thủ công với Makefile và scripts/check_deps.sh"
        status: pass
    human_judgment: false
  - id: D4
    description: "Năm README module mô tả đúng mã hiện có: workflow đổi contract, bản đồ module và bố cục DATA_DIR, mọi script trong scripts/, cổng 3000/3001 và thời điểm dựng UI"
    requirement: FND-05
    verification:
      - kind: other
        ref: "grep make contracts + contracts_gen.py (contracts), DATA_DIR (audio), smoke_lesson.py + dev_smoke.sh (scripts), 3000 (web), 3001 (eval) -> READMES_OK; ls scripts khớp bảng trong scripts/README.md"
        status: pass
    human_judgment: false
  - id: D5
    description: ".env.example giữ bốn key (OPENAI_API_KEY, AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, DATA_DIR), secret rỗng, thêm một dòng ghi chú về expand ~, không biến mới"
    requirement: FND-04
    verification:
      - kind: other
        ref: "vòng lặp grep '^KEY=' cho bốn key (không in 'missing'); grep -En '^(OPENAI_API_KEY|AZURE_SPEECH_KEY)=.+' -> exit 1 (không có giá trị)"
        status: pass
    human_judgment: false

# Metrics
duration: 10min
completed: 2026-10-06
status: complete
---

# Phase 1 Plan 09: ADR 0003, product.md đồng bộ contract, README và Lệnh Summary

**ADR 0003 ghi mọi quyết định P0 (D-01..D-27 cùng 10 mục Liam chốt), product.md mục 3-4 khớp contract đã chốt trong `packages/contracts`, và CLAUDE.md, README gốc cùng năm README module mô tả đúng Makefile, script và mã đang có.**

## Performance

- **Duration:** ~10 min (đồng hồ hệ thống; phần lớn là đọc SUMMARY 01-01..01-08 và mã nguồn để đối chiếu)
- **Started:** 2026-10-06T14:58:00Z (xấp xỉ, không ghi lúc bắt đầu)
- **Completed:** 2026-10-06T15:10:00Z (trước commit SUMMARY)
- **Tasks:** 3
- **Files modified:** 12 (1 mới, 11 sửa)

## Accomplishments

- **ADR 0003** (`docs/decisions/0003-contract-toolchain-va-moi-truong-p0.md`) theo khung 0001/0002 (Bối cảnh, Quyết định, Lý do, Hệ quả và rủi ro). Tám nhóm quyết định: quy ước chung, Lesson/Segment/Word, ScoreResult, Label/ClipManifest, toolchain (kèm đủ cờ `datamodel-code-generator` ghim 0.83.0 và drift gate), model (Demucs `hf://htdemucs`, `shifts=0`, `overlap=0.25`), môi trường (Node >= 22.13, pnpm 11.9.0, `trustPolicy: off`, `allowBuilds: esbuild`, `uv_build`, `[tool.uv] environments`, `yt-dlp[default,deno]`, ESLint 9 flat không có plugin Next, TypeScript ~5.9.3, GNU Make 3.81), `/health`. Mục D-26: không knob nào đổi, đo 125.3 s và 115.8 s.
- **product.md** mục 3 có khối `ScoreResult` cuối cùng (metadata, `scores` với `sound` nullable, `words[].status` scored/missing/ref_unclear, `contour {ref, user, wordBounds}` với frame null, `pauses` camelCase, union `Issue` bảy mã với `data` riêng, `tips[].source`) kèm câu "Nguồn sự thật: `packages/contracts`"; mục 4 có `ClipManifest` cuối và `Label` kèm ghi chú SQL vẫn snake_case; mục 5 liệt kê đủ kiểu contract. Phần Lớp A/B/C và khối SQL giữ nguyên.
- **Lệnh và điều kiện tiên quyết:** CLAUDE.md "Lệnh" liệt kê tám target thật; README có mục "Bắt đầu" (kèm `make smoke URL=`), bảng "Lệnh" và dòng yêu cầu khớp `check_deps.sh`; PROJECT.md và `.claude/CLAUDE.md` ghi Node >= 22.13, pnpm 11.9.
- **README module:** mỗi file mô tả đúng cái đã có sau P0 và cách chạy hoặc đổi nó (workflow `Zod -> make contracts -> commit schema + contracts_gen.py -> make test`; bản đồ module và bố cục `DATA_DIR` gồm `info.json` và `timing.json`; mọi script trong `scripts/` kèm cờ, output, mã thoát; cổng 3000 và 3001).

## Task Commits

1. **Task 1: ADR 0003 và product.md mục 3-4 (D-27)** - `b22e023` (docs)
2. **Task 2: CLAUDE.md Lệnh, README, điều kiện tiên quyết, .env.example** - `de2f260` (docs)
3. **Task 3: README từng module** - `3a022b3` (docs)

**Plan metadata:** commit `docs(01-09): complete plan summary` (chỉ SUMMARY.md; STATE.md, ROADMAP.md và REQUIREMENTS.md do orchestrator sở hữu).

## Files Created/Modified

- `docs/decisions/0003-contract-toolchain-va-moi-truong-p0.md` - ADR 0003
- `docs/product.md` - mục 3 (ScoreResult + Issue), mục 4 (ClipManifest + Label), mục 5 (danh sách contract), ngày cập nhật
- `CLAUDE.md` - chỉ block "Lệnh" và dòng chú thích
- `README.md` - trạng thái, "Bắt đầu", bảng "Lệnh", mô tả `scripts/`
- `.planning/PROJECT.md`, `.claude/CLAUDE.md` - dòng "Nền tảng"
- `.env.example` - một dòng ghi chú trên `DATA_DIR`
- `apps/web/README.md`, `apps/eval/README.md`, `packages/contracts/README.md`, `services/audio/README.md`, `scripts/README.md`

## Decisions Made

Xem `key-decisions`. Mọi nội dung ADR đều lấy từ 01-CONTEXT.md, 01-01..01-08-SUMMARY.md và đối chiếu với mã nguồn; không có quyết định mới nào được đặt ra trong plan này.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Văn bản không nhất quán] Dòng "Nền tảng" sửa rộng hơn chuỗi "Node 20+" của plan**
- **Found during:** Task 2 (PROJECT.md và `.claude/CLAUDE.md`)
- **Issue:** Plan nói chỉ thay "Node 20+" bằng "Node ≥ 22.13 (pnpm 11.9)", nhưng câu gốc là "cần Node 20+, pnpm, uv, …" nên thay đúng chuỗi sẽ thành "Node ≥ 22.13 (pnpm 11.9), pnpm, uv", lặp pnpm.
- **Fix:** thay "Node 20+, pnpm," bằng "Node ≥ 22.13, pnpm 11.9," (cùng ý nghĩa, không lặp). Chỉ đổi hai file này ở đúng một dòng.
- **Files modified:** `.planning/PROJECT.md`, `.claude/CLAUDE.md`
- **Commit:** `de2f260`

**2. [Rule 3 - Lệnh verify bị harness từ chối] Lệnh `sh -c '...'` lồng nhau của Task 1 không chạy được**
- **Found during:** Task 1 (verify tự động thứ nhất)
- **Issue:** Harness của executor từ chối `sh -c '<chuỗi nhiều lệnh>'` (không chứng minh được nó không phải thao tác git ngoài worktree), cùng hiện tượng 01-08 đã ghi.
- **Fix:** chạy tương đương bằng vòng lặp `for i in $(seq -w 1 27); do grep -q "D-$i" ...` cộng `grep 'Người quyết: Liam'`, cùng điều kiện pass/fail; kết quả "ADR_OK", không có dòng "missing D-NN". Lệnh verify của Task 2 (khoá `.env.example`) cũng được tách thành vòng lặp thường.
- **Files modified:** không
- **Commit:** không áp dụng

**3. [Ghi nhận, nằm trong files_modified] Nội dung thêm ngoài danh sách tối thiểu của plan**
- `docs/product.md` đổi ngày "Cập nhật" thành 2026-10-06; `README.md` thêm bảng "Lệnh", dòng "Không có API key vẫn chạy được" và sửa mô tả `scripts/`; `apps/web/README.md` ghi cách `transpilePackages` được chứng minh bằng probe `data-lesson-statuses`. Không file nào ngoài `files_modified` bị sửa.

---

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 3) + 1 ghi nhận
**Impact on plan:** Không đổi phạm vi; chỉ làm văn bản chính xác hơn và verify chạy được trong sandbox.

## Issues Encountered

- Ledger commit (`gsd-plan-head-before-01-09`) ghi được vào git dir của worktree nên `commits: 3` đo bằng `git rev-list --count 1347357..HEAD` trước commit SUMMARY.
- Harness chặn mọi lệnh Bash chứa chữ "eval" nên các lệnh tham chiếu `apps/eval` được thay bằng công cụ Read/Edit; không cố lách. `make eval` chưa được chạy trực tiếp ở plan này (xem mục dưới).

## Việc còn mở cho con người (không được giải quyết ở plan này)

- `make eval` (stub, một dòng `echo`): chưa agent nào chạy trực tiếp vì sandbox từ chối lệnh chứa từ "eval"; orchestrator hoặc Liam chạy `make eval` một lần để xác nhận thoát 0 và in "stub".
- Nghe thử các segment của video smoke (62 segment, trung bình 3.03 s, 39 segment dưới 3 s): ngưỡng tách câu 3-8 s là giả định RESEARCH A1, chỉ Liam quyết.
- Nhãn `audioQuality` (clean ở -17.5 dB, ngưỡng tạm -15 dB, giả định A2) chưa được kiểm bằng tai.
- Tuỳ chọn: `HF_HOME=$(mktemp -d) make setup` để kiểm máy sạch hoàn toàn (tải ~3 GB model).
- Liam duyệt ADR 0003 và khối contract trong product.md tại PR (ranh giới schema).

## Follow-ups (ngoài `files_modified` của plan này)

- Drift gate tạo thư mục tạm `services/audio/.contracts-check.*` và xoá khi thoát; nếu bị ngắt giữa chừng thư mục có thể còn lại và chưa nằm trong `.gitignore` (đã ghi ở ADR 0003, mục Hệ quả). Thêm một dòng vào `.gitignore` nếu muốn.
- `.gsd/**` đã được orchestrator thêm vào `.prettierignore` (commit `6d46038`); ADR chưa liệt kê vì là thay đổi quy trình, không phải quyết định kỹ thuật.

## Authentication Gates

None.

## User Setup Required

None - không cần cấu hình dịch vụ ngoài.

## Threat Flags

None. T-01-24: `.env.example` vẫn rỗng secret (vòng kiểm tra không thấy giá trị), tài liệu chỉ nhắc tên biến. T-01-25: ADR 0003 ghi D-01..D-27 và các câu trả lời của Liam ở 01-01 với "Người quyết: Liam". T-01-SC: plan không cài gì.

## Known Stubs

None. `make eval` là stub có chủ đích của Phase 4 (EVL-02) và được tài liệu ghi rõ là stub ở CLAUDE.md và README.md.

## Next Phase Readiness

- Phase 1 đủ tài liệu cho PR: ADR 0003, product.md khớp contract, lệnh và điều kiện tiên quyết đúng với mã.
- Phase 2 bắt đầu dựng UI trên `apps/web` (khung rỗng đã có) và job runner dùng lại `run_lesson`.
- Không có blocker; các mục "Việc còn mở cho con người" cần Liam trước khi chốt ngưỡng tách câu ở phase sau.

## Self-Check: PASSED

- File tồn tại: ADR 0003, product.md, CLAUDE.md, README.md, `.planning/PROJECT.md`, `.claude/CLAUDE.md`, `.env.example`, năm README module (đã commit, `git status` sạch trước SUMMARY).
- Commit `b22e023`, `de2f260`, `3a022b3` là tổ tiên của HEAD; `git rev-list --count 1347357..HEAD` = 3.
- Acceptance Task 1: ADR có D-01..D-27 và "Người quyết: Liam"; product.md có `intonationOnly`, `ref_unclear`, `issueRef`, `refMs`, `finalContourMatch`, `packages/contracts`, vẫn có `word_flags jsonb`, không còn `ref_ms|user_ms`.
- Acceptance Task 2: CLAUDE.md có `make lint`, `make smoke`, `make contracts`, `make dev-eval`; README có `make setup`, `espeak-ng`; Node tối thiểu 22.13 khớp `check_deps.sh` (`NODE_MIN="22.13"`); `.env.example` đủ bốn key, secret rỗng.
- Acceptance Task 3: `make contracts` và `contracts_gen.py` trong packages/contracts/README.md; `DATA_DIR` trong services/audio/README.md; `smoke_lesson.py` và `dev_smoke.sh` trong scripts/README.md; cổng 3000 và 3001 trong hai README app; mọi file trong `scripts/` được liệt kê.

---
*Phase: 01-p0-n-n-t-ng*
*Completed: 2026-10-06*
