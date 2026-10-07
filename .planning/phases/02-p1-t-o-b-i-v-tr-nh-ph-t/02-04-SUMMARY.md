---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 04
subsystem: ui
tags: [nextjs, tanstack-query, zod, tailwind3, shadcn, radix-ui, design-tokens, fonts]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-01 approved contract shapes + endpoint list; 02-02 approved, frozen-installed web dependencies"
provides:
  - "apps/web/lib/api.ts: one Zod-validated typed client for the whole P1 API surface + ApiRequestError"
  - "apps/web/lib/queries.ts: query keys + hooks (useLessons polling, useLesson, useLessonProgress, useSystemStatus, useSettings)"
  - "Design tokens (tokens.css synced from docs/design, drift-tested), Tailwind 3 var() map, Figtree/Noto Sans/JetBrains Mono"
  - "15 shadcn (radix) primitives rewritten to the locked design + AppHeader"
  - "S1 route listing lessons from GET /lessons through TanStack Query"
affects: [02-08, 02-09, 02-13, 02-14, 02-17, 02-18, all later web plans]

plan_head_before: d725816d5e3527d6137378caff1d85e39a1c3eda
plan_head_after: ea5f90f5f9689e27c8d7528a24623eb172d473b5
actuals:
  tokens: 60000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Single API client: every response Zod-parsed at the boundary, errors normalised to ApiRequestError {status, error}"
    - "Colours as plain var(--x) (hex tokens), no hsl() wrapper, no opacity-modifier on var() colours, no dark mode"
    - "Button/Alert/Badge via cva with design variants; no box-shadow utilities (Kbd inset line is the single design exception)"

key-files:
  created:
    - apps/web/lib/api.ts
    - apps/web/lib/api.test.ts
    - apps/web/lib/queries.ts
    - apps/web/lib/tokens.test.ts
    - apps/web/lib/utils.ts
    - apps/web/components.json
    - apps/web/app/tokens.css
    - apps/web/postcss.config.js
    - apps/web/components/AppHeader.tsx
    - apps/web/components/ui/ (alert, badge, button, card, dialog, input, kbd, label, progress, select, skeleton, slider, sonner, tabs, tooltip)
  modified:
    - apps/web/tsconfig.json
    - apps/web/tailwind.config.ts
    - apps/web/app/providers.tsx
    - apps/web/app/layout.tsx
    - apps/web/app/globals.css
    - apps/web/app/page.tsx

key-decisions:
  - "Progress indeterminate uses a progress-slide keyframe added to tailwind.config.ts; reduced motion falls back to a static half bar"
  - "Sonner Toaster has no next-themes (no extra package); theme fixed to light, matching no-dark-mode design"
  - "Transition duration written as [transition-duration:120ms] because duration-[120ms] is ambiguous in Tailwind 3 and warns at build"

patterns-established:
  - "Later plans import from lib/api.ts and lib/queries.ts only; never edit components/ui/* (compose instead)"

requirements-completed: [LES-03, PLY-07]

duration: ~35min total across two executors (first killed by API rate limit)
completed: 2026-10-07
status: complete
---

# Phase 2 Plan 04: Web tracer and design foundation Summary

**One Zod-validated API client and TanStack Query hooks for all P1 endpoints, S1 listing lessons end to end, design tokens + three fonts, and 15 shadcn/radix primitives plus AppHeader rewritten to the locked design.**

## Task Commits

1. **Task 1 (tracer): api client, query hooks, S1 list** - `570b0a9` (feat)
2. **Task 2 (tdd): tokens, Tailwind 3 map, fonts** - `990c1d7` (test, RED), `8d1fab0` (feat, GREEN)
3. **Task 3: primitives and AppHeader** - `ea5f90f` (feat)

## Exports for later web plans

`lib/api.ts`: `API_BASE`, `ApiRequestError {status, error}`, `getSystemStatus()`, `getSettings()`, `putSettings(settings)`, `checkOpenAiKey(apiKey?)`, `previewVideo(url)`, `createLesson(input)`, `listLessons()`, `getLesson(id)`, `retryLesson(id)`, `getLessonProgress(id)`, `lessonVideoUrl(id)` (string builder), `reloadLessonVideo(id)` (204, void), `updateSegmentText(id, index, text)`, `extendSegmentEnd(id, index)`, `translateSegment(id, index)`, `uploadAttempt(lessonId, index, blob, {saveForEval, signal?})`, `saveEvalClip(lessonId, index, attempt, blob)`, `UploadAttemptOptions`.

`lib/queries.ts`: `POLL_INTERVAL_MS` (2000), `queryKeys`, `lessonsPollInterval`, `useLessons()` (polls 2 s while any lesson not ready/failed, `keepPreviousData`), `useLesson(id)`, `useLessonProgress(id)`, `useSystemStatus()` (polls while a model is loading), `useSettings()`.

`components/ui/button.tsx`: variants `solid | soft-original | soft-you | outline | ghost`; sizes `md` (h-11, 44 px), `lg` (h-12, 48 px), `icon` (44x44; type requires `aria-label` and `title`); optional `kbd` prop; `asChild`. Others: `Kbd`, `Badge` (`neutral | success | warning`), `Alert` (`warning | error | neutral`; AlertTitle/Description/Action), `Tabs`, `Dialog*` (720 px, no shadow), `Progress` (`value`, `indeterminate`), `Select*`, `Slider` (multi-thumb by value length), `Input`, `Label`, `Tooltip*`, `Toaster`, `Card*`, `Skeleton`. `AppHeader` (logo, Thư viện nav with `aria-current`, Settings icon link).

## Verification

- `pnpm --filter @shadowenglab/web test`: 2 files, 7 tests pass (api, tokens).
- `pnpm --filter @shadowenglab/web build`: succeeds, no warnings after the duration-class fix.
- `pnpm exec eslint apps/web`: clean. `tsc --noEmit` in apps/web: clean.
- `grep -rnE "shadow-(sm|md|lg|xl)|hsl\(var\("` over components, tailwind.config.ts, globals.css: no matches.
- `git diff pnpm-lock.yaml apps/web/package.json`: empty. The shadcn CLI added no package, so no unapproved package name entered the lockfile (T-02-12 / T-02-SC satisfied).
- `pnpm dlx shadcn@4.21.3 info` reports 15 installed components (alert, badge, button, card, dialog, input, kbd, label, progress, select, skeleton, slider, sonner, tabs, tooltip) and style `radix-nova`, with the tailwind config path pointing to `tailwind.config.ts`.

## Deviations from Plan

### Interruption and recovery

The first executor was killed by an API rate limit during Task 3, leaving the primitives and AppHeader written but uncommitted. This continuation executor reviewed every uncommitted file against the plan and docs/design, found all 15 primitives, AppHeader, providers and page changes complete and correct, and re-ran full verification before committing. No package was added or re-resolved.

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ambiguous Tailwind class `duration-[120ms]`**
- **Found during:** Task 3 verification (next build warning)
- **Issue:** Tailwind 3 matched the class to multiple utilities and warned on every build.
- **Fix:** replaced with `[transition-duration:120ms]` in all primitives and AppHeader.
- **Files modified:** components/ui/*.tsx, components/AppHeader.tsx
- **Commit:** `ea5f90f`

**Total deviations:** 1 auto-fixed. No scope change.

## Issues Encountered

- `make dev` visual check (human-check in Task 3: header, Figtree text, Vietnamese diacritics, no shadows) was not performed by the executor; it needs a human look at http://localhost:3000. Production build and static generation pass.
- `shadcn init` wrote `"style": "radix-nova"` in components.json. The primitives were rewritten by hand to the design, so the style name has no runtime effect.

## Known Stubs

None. The S1 list in `page.tsx` is intentionally unstyled; 02-08 builds the real cards (stated in the plan).

## Threat Flags

None.

## Self-Check: PASSED

- All listed files exist; commits `570b0a9`, `990c1d7`, `8d1fab0`, `ea5f90f` are ancestors of HEAD; `git rev-list --count d725816..HEAD` = 4 before this docs commit.
- STATE.md and ROADMAP.md intentionally not touched (orchestrator owns them in worktree mode).
