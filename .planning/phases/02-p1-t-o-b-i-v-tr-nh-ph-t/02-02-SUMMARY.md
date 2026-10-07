---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 02
subsystem: infra
tags: [pnpm, uv, tailwind3, shadcn, radix-ui, xstate, tanstack-query, vitest, python-multipart, package-legitimacy]

requires:
  - phase: 01-p0-n-n-t-ng
    provides: pnpm workspace, uv project for services/audio, frozen-lockfile install discipline
provides:
  - Phase 2 JS dependency set declared in apps/web/package.json and locked in pnpm-lock.yaml
  - Python runtime deps python-multipart, python-dotenv, httpx locked in services/audio/uv.lock
  - apps/web `test` script (vitest run) so `make test` runs web unit tests
  - Both environments installed from the Liam-approved frozen lockfiles
affects: [02-04, 02-05, 02-10, 02-11, all later Phase 2 plans (install with --frozen only)]

plan_head_before: 57700e789361079580374601d4983b788a8ae59a
plan_head_after: d0c6c829e8c3ca077502abf1595e41ec696e41ba
actuals:
  tokens: 35000
  tasks: 3
  commits: 1

tech-stack:
  added: [xstate, "@xstate/react", "@tanstack/react-query", radix-ui, class-variance-authority, clsx, tailwind-merge, lucide-react, sonner, tailwindcss-animate, tailwindcss 3, postcss, autoprefixer, vitest (web), python-multipart]
  patterns: ["package-legitimacy gate: resolve with --lockfile-only / uv lock, human review, then install with --frozen"]

key-files:
  created: []
  modified: [apps/web/package.json, services/audio/pyproject.toml, pnpm-lock.yaml, services/audio/uv.lock]

key-decisions:
  - "radix-ui declared as ^1.7.0 (resolved 1.7.0): the only pin chosen by the executor, since the plan gave none ('latest 1.x')"
  - "httpx moved from the dev group to runtime dependencies (OpenAI REST calls at runtime, D-23, no openai SDK)"
  - "shadcn CLI 4.21.3 runs via pnpm dlx in 02-04 only; it is a tool, not a dependency"

requirements-completed: [REC-02, SET-03, PLY-02]

duration: 15min
completed: 2026-10-07
status: complete
---

# Phase 2 Plan 02: Dependency gate Summary

**Phase 2 packages (Tailwind 3 + shadcn/radix-ui, XState 5, TanStack Query 5, vitest 4, python-multipart) were declared, resolved lockfile-only, reviewed and approved by Liam, then installed from the frozen lockfiles with no lockfile drift.**

## Performance

- **Duration:** ~15 min (continuation agent: Task 3 + summary)
- **Completed:** 2026-10-07
- **Tasks:** 3 (1 auto, 1 blocking-human checkpoint, 1 auto)
- **Code commits:** 1 (`09c904a`, Task 1); Task 2 is verification only; Task 3 installs only (gitignored output)

## Accomplishments

- Manifests declare every Phase 2 package; `pnpm-lock.yaml` and `services/audio/uv.lock` resolved without installing (Task 1).
- Package-legitimacy gate (T-02-SC / T-02-03) passed: Liam replied `approved` on 2026-10-07 to the resolved set of commit `09c904a` (Task 2).
- `pnpm install --frozen-lockfile` and `uv sync --project services/audio --frozen` succeeded; python-multipart, python-dotenv, httpx import; vitest 4.1.11 resolves in apps/web; lockfiles unchanged by the install (Task 3).

## Task Commits

1. **Task 1: Declare dependencies and resolve lockfiles** - `09c904a` (chore(02-02))
2. **Task 2: Liam reviews new packages** - no commit (checkpoint:human-verify, blocking-human; approval recorded here)
3. **Task 3: Install from approved lockfiles and verify imports** - no commit (installs only; node_modules and .venv are gitignored)

**Plan metadata:** this SUMMARY (docs commit).

## Approval record (Task 2)

- **Approver / date:** Liam, 2026-10-07, reply `approved`, verbatim.
- **Approved JS direct dependencies:** xstate 5.33.2, @xstate/react 6.1.0, @tanstack/react-query 5.104.1, radix-ui ^1.7.0 (resolved 1.7.0), class-variance-authority 0.7.1, clsx 2.1.1, tailwind-merge 3.7.0, lucide-react 1.52.0, sonner 2.0.8, tailwindcss-animate 1.0.7.
- **Approved JS devDependencies:** tailwindcss 3.4.19, postcss 8.5.29, autoprefixer 10.6.1, vitest 4.1.11.
- **pnpm-lock.yaml:** 145 new package keys (65 `@radix-ui/*` transitive; the rest Tailwind 3 / PostCSS / Floating UI / Radix helpers); none removed.
- **Python (uv.lock):** one new locked package, python-multipart 0.0.32; httpx and python-dotenv moved to runtime deps (already locked).
- **Tool:** shadcn@4.21.3 via `pnpm dlx`, executed in 02-04 only.
- **RESEARCH [SUS] flags** (too-new / no-repository heuristics, including tailwindcss-animate and python-multipart) were shown to Liam and accepted.
- **Install scripts:** only esbuild (allowBuilds unchanged).

## Installed versions (Task 3)

- JS (apps/web): @tanstack/react-query 5.104.1, @xstate/react 6.1.0, class-variance-authority 0.7.1, clsx 2.1.1, lucide-react 1.52.0, next 14.2.35, radix-ui 1.7.0, react 18.3.1, sonner 2.0.8, tailwind-merge 3.7.0, tailwindcss-animate 1.0.7, xstate 5.33.2; dev: autoprefixer 10.6.1, postcss 8.5.29, tailwindcss 3.4.19, vitest 4.1.11.
- Python (services/audio venv): python-multipart 0.0.32, python-dotenv 1.2.4, httpx 0.28.1.
- pnpm 11.9.0, Node v24.16.0.

## Verification

- `uv run --project services/audio --frozen python -c "import multipart, dotenv, httpx"` printed ok.
- `pnpm --filter @shadowenglab/web exec vitest --version` printed `vitest/4.1.11`.
- `git diff --quiet -- pnpm-lock.yaml services/audio/uv.lock` exit 0 (lockfiles unchanged after install).

## Deviations from Plan

None - plan executed exactly as written. The only executor-chosen pin was `radix-ui ^1.7.0` (plan said "latest 1.x"), disclosed to and approved by Liam.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- Commit `09c904a` is an ancestor of HEAD; manifests and lockfiles present; install verification commands above all passed.
- STATE.md and ROADMAP.md intentionally not touched (orchestrator owns them in worktree mode).
