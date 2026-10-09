---
gsd_state_version: "1.0"
current_phase: 03
current_phase_name: P2 · Chấm ngữ điệu
status: executing
stopped_at: Phase 3 UI-SPEC approved
last_updated: "2026-10-09T07:04:44.052Z"
last_activity: 2026-10-09
last_activity_desc: Phase 03 execution resumed (wave continue)
state_head: "0b260a770957bf00026117e41786a8badbdb4ad9"
progress:
  total_phases: 8
  completed_phases: 2
  total_plans: 39
  completed_plans: 30
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-08)

**Core value:** Sau mỗi lượt nói, Liam biết đáng tin mình lệch khỏi người nói gốc ở đâu — so audio với audio gốc, precision trước recall.
**Current focus:** Phase 03 — P2 · Chấm ngữ điệu

## Current Position

Phase: 03 (P2 · Chấm ngữ điệu) — EXECUTING
Plan: 1 of 11
Status: Executing Phase 03
Last activity: 2026-10-09 — Phase 03 execution resumed (wave continue)

Next step: `/gsd-discuss-phase 3` — Discuss trước; Liam chốt contract trong `packages/contracts` rồi mới Plan.

Progress: [███░░░░░░░] 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 28
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 9 | - | - |
| 02 | 19 | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 1 P01 | 17 min | 3 tasks | 9 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Cấu trúc 8 phase do Liam chốt trong `docs/gsd/roadmap-seed.md` (P0→Phase 1 … P7→Phase 8; GSD dành riêng Phase 0)
- [Roadmap]: Phase 5 (P4) và Phase 6 (P5) chạy song song được; cùng phụ thuộc Phase 4
- [Roadmap]: Từ Phase 4 trở đi mọi thay đổi model/ngưỡng/rule phải chạy `make eval` và dán bảng metric vào PR
- [Phase 2]: LES-06 tính nhãn "Audio sạch" / "Có nhạc nền" lúc tạo bài từ tỉ lệ năng lượng non-vocal/vocal của Demucs; Phase 5 bổ sung tỉ lệ câu `ref_unclear` để tinh chỉnh
- [Phase 1]: Phần thiết kế UI của P0 (design system + 13 màn, flows, product doc) đã xong trước GSD; phạm vi còn lại là B1–B4, C1–C3
- [Phase 1]: Toolchain: Node >= 22.13 + pnpm 11.9.0, trustPolicy off, allowBuilds esbuild
- [Phase 1]: pydantic alias: explicit Field(alias=camelCase) + populate_by_name=True
- [Phase 1]: Schema layout: one bundle contracts.schema.json with shared $defs
- [Phase 1]: Word.i = index inside segment from 0; Word.prominence unset in P0
- [Phase 1]: /health is a Python-only model, not a contract type
- [Phase 1]: nonVocalRatio provisional: music when > 10^(-15/10) (~0.0316), else clean
- [Phase 1]: Demucs: Separator(htdemucs, shifts=0, overlap=0.25, split=True), no_vocals = sum of non-vocal stems
- [Phase 1]: Contract bounds: seconds>=0, ms int>=0, ratios/probabilities in [0,1], indexes int>=0, attempt int>=1
- [Phase 1]: Smoke video URL: https://www.youtube.com/watch?v=dUDi-F6eAvk
- [Phase 1]: Wave 3 ui.safety-gate (blocking) overridden by Liam: 01-07 shells are bare frames; UI-SPEC deferred to the first phase with real screens (design in docs/design/)
- [Phase 2]: Contract P1 (02-01 mục A–H) Liam duyệt nguyên đề xuất; package mới duyệt qua cổng 02-02
- [Phase 2]: Tách câu D-21 (3 s / 8 s / 18 từ): câu < 3 s trên video smoke giảm 35/59 → 7/46
- [Phase 2]: Dịch câu dùng `gpt-6-luna` (effort none) qua httpx — ứng viên gpt-5 nano/mini đã deprecated
- [Phase 2]: Video tự host H.264/AAC, bỏ IFrame (ADR 0004); job runner/attempts/dataDir ghi ở ADR 0005

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: Bộ 3–4 video eval chưa chọn; smoke script dùng tạm một video giọng Mỹ có audio sạch
- [Phase 2]: Code review fix (2026-10-08): 8/8 warning đã sửa (`02-REVIEW-FIX.md`); 9 info còn `open`. `test_db.py::test_concurrent_inserts_get_distinct_numbers` chập chờn (`database is locked`, có từ trước)
- [Phase 2]: Chờ Liam chốt: `EXTEND_MAX_MS = 3000`. Đã chốt: WR-04 (`live_video`/`video_unavailable` ở POST /lessons), WR-05 (`MAX_RANGE_S = 360`; RangePicker chưa chặn > 6 phút ở UI)
- [Phase 2]: `extract_audio` (Phase 1) gọi ffmpeg không timeout; chất lượng dịch `gpt-6-luna` chưa eval
- [Phase 4]: Liam tự thu ~100 clip lỗi cố ý (mỗi clip 1 lỗi) cùng ~8 clip mốc đúng
- [Phase 6]: Cần 2 người chấm bản xứ Mỹ sẵn sàng (email allowlist) trước đợt chấm

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-10-08T16:18:51.521Z
Stopped at: Phase 3 UI-SPEC approved
Resume file: .planning/phases/03-p2-ch-m-ng-i-u/03-UI-SPEC.md
