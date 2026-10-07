---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 08
subsystem: ui
tags: [nextjs, react, tanstack-query, tailwind3, library, banners, job-steps]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-04 api client (retryLesson), query hooks (useLessons polling, useSystemStatus), design tokens and shadcn primitives"
provides:
  - "lib/lessonView.ts: pure STEP_LABELS, stepRows, failureText, librarySummary, filterByTab, cardCta, formatClock, safeThumbnailUrl (+ 32 tests)"
  - "LessonCard (ready / processing / music-warning / failed) and JobSteps"
  - "Banner (warning/error/neutral) and SystemBanners (models, key, mic, backend)"
  - "useMicPermission hook (Permissions API, unknown on any failure)"
  - "S1 library page: header, banners, title row, filter tabs, auto-fill grid, skeleton / empty / filtered-empty states"
affects: [02-13, 02-14, 02-17, 02-18]

plan_head_before: 57cd5d456e98a0b3a8ee370782f8e5fd2d4f211b
plan_head_after: e0c64eec2535581c12ca493fe2228d4d658d3b59
actuals:
  tokens: 8400
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "View logic (step rows, failure copy, tab filters, CTA) lives in pure lessonView.ts; components only render"
    - "Banner wraps the Alert primitive; role comes from the Alert variant (error = alert)"
    - "Only https:// thumbnail URLs become <img>; every other case is the dark video-bg placeholder (T-02-21)"

key-files:
  created:
    - apps/web/lib/lessonView.ts
    - apps/web/lib/lessonView.test.ts
    - apps/web/lib/audio/micPermission.ts
    - apps/web/components/JobSteps.tsx
    - apps/web/components/LessonCard.tsx
    - apps/web/components/Banner.tsx
    - apps/web/components/SystemBanners.tsx
  modified:
    - apps/web/app/page.tsx

key-decisions:
  - "The Tạo bài từ YouTube action is a Link to /?create=1; 02-13 mounts the dialog on that query"
  - "Failed first fetch shows only the backend banner, never the empty-library state"
  - "Interrupted copy lowercases the step label (Bị gián đoạn ở bước tách giọng.)"

requirements-completed: [LES-03, LES-06, LES-07, SET-01, SET-02]

coverage:
  - id: D1
    description: "Pure lessonView helpers: step rows, failure and interrupted copy, summary line, tab filters, card CTA, m:ss clock"
    requirement: "LES-03"
    verification:
      - kind: unit
        ref: "apps/web/lib/lessonView.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "S1 lesson cards in ready, processing, music-warning and failed states with retry and no delete"
    requirement: "LES-07"
    verification:
      - kind: other
        ref: "pnpm --filter @shadowenglab/web build (types + static render)"
        status: pass
    human_judgment: true
    rationale: "Visual fidelity to docs/design/screens/S1-thu-vien.html and live 2 s polling need a browser; the plan's human-check was not run by the executor"
  - id: D3
    description: "System banners for models, key, mic and backend, none blocking, SET-02 key banner keeps create/practice enabled"
    requirement: "SET-02"
    verification:
      - kind: other
        ref: "pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web"
        status: pass
    human_judgment: true
    rationale: "Banner order and the Permissions API denied state depend on real backend and browser state"
  - id: D4
    description: "Filter tabs plus empty, loading and filtered-empty states of the grid"
    requirement: "LES-06"
    verification:
      - kind: unit
        ref: "apps/web/lib/lessonView.test.ts#filterByTab"
        status: pass
    human_judgment: true
    rationale: "Skeleton, empty-state and tab visuals need a browser check"

duration: 14min
completed: 2026-10-07
status: complete
---

# Phase 2 Plan 08: S1 Thư viện Summary

**S1 library with four lesson-card states and live per-step job progress, retry, quality labels, practice progress, filter tabs, skeleton/empty/error states, and a non-blocking banner stack for models, OpenAI key, mic and backend.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-10-07T14:51:00Z
- **Completed:** 2026-10-07T15:05:22Z
- **Tasks:** 3
- **Files modified:** 8 (7 created, 1 modified)

## Accomplishments

- `lessonView.ts` holds all view decisions as pure functions with 32 passing tests, including the no-speech `segmenting` failure text, the interrupted copy, and tab edge cases (no ready lessons, all practiced, failed lessons only under Tất cả).
- `LessonCard` renders ready (quality badge, `{n} câu`, music warning line, `Đã tập k/n`, CTA link to `/lessons/{id}`), processing (`JobSteps`), and failed (failure text, full-width `Thử lại` calling `retryLesson` then invalidating the lessons query, sonner toast on error). No delete button; only ready cards link out.
- `SystemBanners` shows nothing before the first status response, then stacks models-missing, models-loading, no-key (with `Thêm key` to `/settings`), mic-denied and backend-unreachable (`Tải lại` refetches both queries). Nothing on S1 is disabled by `hasKey`.
- `page.tsx` is the full S1: banners, title row with summary line, `Tạo bài từ YouTube` link to `/?create=1`, tabs, grid keyed by `lesson.id`.

## Task Commits

1. **Task 1 (tracer): cards, JobSteps, retry, lessonView** - `42826e2` (feat)
2. **Task 2: system banners** - `5844ce7` (feat)
3. **Task 3: tabs, empty / loading / filtered-empty states** - `e0c64ee` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Verification

- `pnpm --filter @shadowenglab/web test`: 6 files, 90 tests pass (lessonView.test.ts has 32).
- `pnpm --filter @shadowenglab/web build`: compiled, types valid (after each task).
- `pnpm exec eslint apps/web`: clean. Prettier applied to every new file.
- Tracer gate: the tracer `<verify>` is automated-only; it was re-run end to end after the task and passed before expansion.
- Acceptance greps: every required literal present (`Thử lại`, `Audio sạch`, `Có nhạc nền`, `line-clamp-2`, `retryLesson`, `aria-label="Tiến độ xử lý"`, `Đang xếp hàng`, `Thêm key`, `Model đang nạp`, `make setup`, `Không kết nối được backend`, tab and empty-state copy); `page.tsx` keys cards by `lesson.id`.
- No score colours, `scoreLevel`, or percentages in any file this plan created or modified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan's `! grep -rn "score-" apps/web/components apps/web/app` cannot pass as written**
- **Found during:** Task 3 verification
- **Issue:** The grep matches pre-existing 02-04 content outside this plan's `files_modified`: the `--score-*` variable definitions in `app/tokens.css` (verbatim copy of `docs/design/tokens.css`, drift-tested) and a comment in `components/ui/badge.tsx`. It would fail regardless of this plan's code.
- **Fix:** Verified the intent (no score colour in P1 UI) with a grep over only the files this plan created or modified plus a class-pattern check; both found nothing. Did not edit tokens.css or badge.tsx.
- **Files modified:** none
- **Commit:** n/a

**2. [Rule 1 - Bug] eslint-disable for an unregistered rule**
- **Found during:** Task 1 verification
- **Issue:** `// eslint-disable-next-line @next/next/no-img-element` errored because the repo's flat ESLint config does not define that rule.
- **Fix:** Replaced with a plain explanatory comment (the plain `<img>` is required by UI-SPEC).
- **Files modified:** apps/web/components/LessonCard.tsx
- **Commit:** `42826e2`

**3. [Plan reordering] Tab edge-case tests written in Task 1**
- Task 3 asked to extend `lessonView.test.ts` with tab filtering edge cases. They were written together with the rest of the file in Task 1, so Task 3 changed only `page.tsx`.

**Total deviations:** 2 auto-fixed (1 blocking verify command, 1 bug), 1 reordering. **Impact:** none on behaviour or scope.

## Issues Encountered

- The human-check in Task 3 (empty DATA_DIR, ready/processing/failed lessons, API stopped, no key, 120-char title, long error message) was not performed; it needs a browser and the running backend. The two `backstop` truths (title clamp, long error wrap) rely on `line-clamp-2` / `break-words` and are unverified visually.
- On backend failure the mic-denied banner is suppressed until a status response exists (all status-derived banners wait for the first response, per the plan's "nothing renders before its first response").

## Known Stubs

None. The `/?create=1` link intentionally has no dialog until 02-13 mounts it, and `/lessons/{id}` has no route until the practice-room plans; both are stated in the plan.

## Threat Flags

None. Mitigations applied: T-02-21 (title as text, `<img>` only for `https://` thumbnails via `safeThumbnailUrl`), T-02-22 (only `ApiRequestError.message` shown in toasts; banner copy fixed), T-02-SC (only `pnpm install --frozen-lockfile`; no package added).

## Self-Check: PASSED

- All 8 listed files exist; commits `42826e2`, `5844ce7`, `e0c64ee` are ancestors of HEAD; `git rev-list --count 57cd5d4..HEAD` = 3 before this docs commit.
- STATE.md and ROADMAP.md intentionally not touched (orchestrator owns them in worktree mode).
