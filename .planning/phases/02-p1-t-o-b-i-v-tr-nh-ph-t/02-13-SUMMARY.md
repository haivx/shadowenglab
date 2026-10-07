---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 13
subsystem: ui
tags: [nextjs, react, tanstack-query, radix-slider, tailwind3, create-lesson, range-picker]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-04 api client (previewVideo, createLesson, ApiRequestError), queryKeys, shadcn primitives; 02-07 GET /videos/preview and its error codes; 02-08 S1 page with the /?create=1 link"
provides:
  - "lib/time.ts: parseClock, formatClockMs, defaultRange, estimateSentences, estimateMinutes, validateRange, clampThumb (+ 25 tests)"
  - "CreateLessonDialog: S2 dialog with debounced preview, skeleton, inline link errors, duplicate notice, create with toast retry"
  - "RangePicker: two-thumb slider + mm:ss inputs, estimates, 5-minute hint, per-field errors"
  - "S1 page mounts the dialog on the create=1 search param"
affects: [02-14, 02-17, 02-18]

plan_head_before: dd556e3d20e358aa260d8144b8a281d9c52762d5
plan_head_after: be5f360b811d4a9560de943b6b483d29c0f341bd
actuals:
  tokens: 7800
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Pure time helpers (parse, format, validate, estimate) live in lib/time.ts; components only render and wire state"
    - "Per-field validation is derived at render from the two input texts; errors show only after the field was blurred, but Tạo bài is disabled immediately"
    - "RangePicker reports the valid range (or null) to its parent through one effect; the parent keeps a stable callback"
    - "Preview existingLessonId is honoured only while the chosen range equals the default; other collisions come back as 409 duplicate_lesson"

key-files:
  created:
    - apps/web/components/CreateLessonDialog.tsx
    - apps/web/components/RangePicker.tsx
    - apps/web/lib/time.ts
    - apps/web/lib/time.test.ts
  modified:
    - apps/web/app/page.tsx

key-decisions:
  - "RangePicker composes radix-ui Slider primitives directly instead of the 02-04 ui/slider wrapper, because the wrapper cannot give each thumb its own aria-label (Điểm bắt đầu / Điểm kết thúc); styling is identical and ui/slider.tsx stays untouched"
  - "Keyboard (arrow 1 s, Shift+arrow 10 s) is Radix's native behaviour with step=1; clampThumb is the specified pure helper and is unit-tested but not wired into an extra key handler"
  - "clampThumb takes a fourth argument (durationSec) because the planned (value, step, shift) signature cannot clamp to the video length"
  - "Dialog is mounted through a Suspense-wrapped host component in page.tsx, since useSearchParams would otherwise fail the static build"

requirements-completed: [LES-01, LES-02, LES-03]

coverage:
  - id: D1
    description: "Pure S2 time helpers: parseClock, formatClockMs, defaultRange, estimates, validateRange (per-field errors, order error on Kết thúc), clampThumb"
    requirement: "LES-02"
    verification:
      - kind: unit
        ref: "apps/web/lib/time.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "S2 dialog: paste link, debounced preview with skeleton, inline channel/invalid/blocked/duplicate errors, create and close with the new card queued in S1"
    requirement: "LES-01"
    verification:
      - kind: other
        ref: "pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web"
        status: pass
    human_judgment: true
    rationale: "Debounced network preview, dialog focus handling and the new queued card appearing in S1 need a browser against a running backend; the plan's human-check was not run by the executor"
  - id: D3
    description: "RangePicker for videos over 6 minutes: default 00:00-05:00, keyboard-operable thumbs with aria-labels, estimates, 5-minute hint, mm:ss validation, short videos send no range"
    requirement: "LES-02"
    verification:
      - kind: unit
        ref: "apps/web/lib/time.test.ts#validateRange"
        status: pass
      - kind: other
        ref: "react-dom/server render of RangePicker (throwaway check, not committed): aria-labels, 00:00/05:00 values, 38-60 cau"
        status: pass
    human_judgment: true
    rationale: "Slider feel (mouse and keyboard), thumb/input sync and partial-invalid behaviour are interactive and were not exercised in a browser"
  - id: D4
    description: "Create failure keeps the dialog open with a toast and Thử lại; 409 duplicate_lesson shows the duplicate notice with Mở bài đã có"
    requirement: "LES-03"
    verification: []
    human_judgment: true
    rationale: "Needs a backend returning a failure and a 409; no component-test harness (no jsdom) exists in apps/web"

duration: 12 min
completed: 2026-10-07
status: complete
---

# Phase 2 Plan 13: S2 Tạo bài (create dialog and range picker) Summary

**S2 create dialog on `/?create=1` with debounced link preview, precise inline link errors, duplicate detection, a keyboard-operable two-thumb RangePicker (default 00:00-05:00, mm:ss validation, sentence/time estimates) for videos over 6 minutes, and background lesson creation.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-10-07T15:11:00Z
- **Completed:** 2026-10-07T15:23:37Z
- **Tasks:** 2 of 2
- **Files modified:** 5 (4 new, 1 modified)
- **Tests:** `pnpm --filter @shadowenglab/web test` -> 133 passed (25 in `time.test.ts`); `pnpm --filter @shadowenglab/web build` and `pnpm exec eslint apps/web` clean

## Accomplishments

- Tracer (Task 1): `CreateLessonDialog` opens from the S1 link `/?create=1`; after a 400 ms debounce it calls `previewVideo` (TanStack Query, `retry: false`, deduped per URL), shows a skeleton with `Đang lấy thông tin video…`, then the preview block (160 px 16:9 thumbnail on `--video-bg` or dark placeholder, title clamped to 2 lines, `{m:ss} · {channel}`, hint). Errors render under the field with `role="alert"` and a 2 px destructive border: channel link, invalid link, blocked/live video (UI-SPEC copy keyed on the API error code), duplicate (`Video đã được tạo bài trước đó.` + `Mở bài đã có` -> `/lessons/{id}`). `Tạo bài` is disabled until a preview succeeded; submit calls `createLesson`, invalidates the lessons query and closes (removes the `create` param). 409 `duplicate_lesson` shows the same duplicate notice with the returned id; other failures keep the dialog open with a toast `Không tạo được bài: {message}. Thử lại.` and a `Thử lại` action. Tracer verified end-to-end (tests + build) before expansion.
- Task 2: `RangePicker` for `durationSec > 360`: `Chọn đoạn để tập`, default 00:00-05:00, thumbs 24 px, aria-labels `Điểm bắt đầu {mm:ss}` / `Điểm kết thúc {mm:ss}`, arrow = 1 s and Shift+arrow = 10 s, two mono 44x120 inputs kept in sync, `≈ {a}–{b} câu` / `Xử lý ≈ {m} phút, chạy nền`, non-blocking `Đoạn dài hơn 5 phút: xử lý sẽ lâu hơn.`. An invalid field shows its own error (format error, or `Kết thúc phải sau Bắt đầu.` on Kết thúc) while the thumbs keep the last valid range, and the dialog disables `Tạo bài`. Videos up to 6 minutes show `Video ngắn hơn 6 phút nên dùng toàn bộ.` with whole-video estimates and send no range.
- `lib/time.ts` pure helpers with 25 tests, including `"05:60"` and `"abc"` -> null.

## Task Commits

1. **Task 1 (tracer): S2 dialog, time helpers, page mount** - `5fdd196` (feat)
2. **Task 2 RED: failing tests for validateRange and clampThumb** - `b2b4e95` (test)
3. **Task 2 GREEN (helpers): validateRange and clampThumb** - `a342615` (feat)
4. **Task 2 GREEN (UI): RangePicker and dialog integration** - `be5f360` (feat)

No REFACTOR commit was needed. Plan metadata: the SUMMARY docs commit follows this file.

## TDD Gate Compliance

- **RED:** `b2b4e95`. With the helpers stubbed to throw `not implemented`, `vitest run lib/time.test.ts` -> 11 failed, 14 passed. The failing tests are exactly the new `validateRange` (8) and `clampThumb` (3) cases, failing on the missing behavior (the stub throwing), not on syntax, import or fixture faults. `gsd_run check tdd-red-evidence` was not applied (plan type is `execute` with a `tdd` task; vitest default reporter output was captured, not a TAP/JUnit record). Semantic assessment: target tests executed and failed for the intended reason.
- **GREEN:** `a342615` -> 25 passed; full web suite 133 passed after `be5f360`.
- **REFACTOR:** none.

## Decisions Made

See `key-decisions` above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Per-thumb aria-labels required bypassing the ui/slider wrapper**
- **Found during:** Task 2 (RangePicker)
- **Issue:** The 02-04 `Slider` wrapper renders thumbs without any per-thumb props, so `Điểm bắt đầu {mm:ss}` / `Điểm kết thúc {mm:ss}` could not be set; editing `ui/slider.tsx` is outside this plan's `files_modified` (parallel siblings).
- **Fix:** `RangePicker` uses `Slider` primitives from `radix-ui` directly with the same track/range/thumb classes as the wrapper.
- **Files modified:** `apps/web/components/RangePicker.tsx`
- **Verification:** throwaway react-dom/server render confirmed both aria-labels and default values.
- **Committed in:** `be5f360`

**2. [Plan interpretation] `clampThumb` gets a fourth `durationSec` argument**
- The behavior line says `clampThumb(value, step, shift)` "within [0, duration]"; a pure function cannot clamp to the duration without it. Signature is `clampThumb(value, step, shift, durationSec)`; `step` is signed (-1 / +1). Radix handles the actual key presses, so the helper is specified and tested but not called from an extra key handler.

---

**Total deviations:** 1 auto-fixed (1 blocking), 1 plan interpretation
**Impact on plan:** No scope creep; all plan truths are met by the delivered components.

## Issues Encountered

- `pnpm ... test -- time` ignores the filter and runs the whole web suite (all green); targeted runs used `vitest run lib/time.test.ts`.
- The per-plan commit ledger file under the shared git directory could not be written from the worktree sandbox, so `plan_head_before` is the orchestrator-supplied base `dd556e3...` (verified equal to HEAD at start), and `commits: 4` was measured with `git rev-list --count dd556e3..HEAD` before the SUMMARY commit.

## Known Stubs

None. (`createLesson` and `previewVideo` are real calls; no hardcoded empty data reaches the UI.)

## Threat Flags

None. The only new surface is the URL input already covered by T-02-37/38 (URL sent via `URLSearchParams`, 400 ms debounce, query dedupe, no client-side fetch of the pasted URL). Thumbnails go through `safeThumbnailUrl` (https only).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- S2 is complete; 02-14 and later plans can rely on lessons created from S1 appearing as `queued` cards.
- The plan's human-check (channel link, invalid link, private video, 3-minute and 20-minute videos, thumb mouse/keyboard, `99:99`, duplicate create) still needs a browser run with `make dev`.

## Self-Check: PASSED

All four created files exist on disk; commits `5fdd196`, `b2b4e95`, `a342615`, `be5f360` are in the branch history; the working tree is clean.

---
*Phase: 02-p1-t-o-b-i-v-tr-nh-ph-t*
*Completed: 2026-10-07*
