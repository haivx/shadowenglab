---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Empty or relative `DATA_DIR` resolves against the current working directory"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Saved F0, energy and PPG tracks have different frame counts and no time origin"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`_real_separate` can mask the real error with `UnboundLocalError`"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`smoke_lesson.py` reports pipeline `ValueError`s as \"bad URL or range\" (exit 2)"
  - id: WR-05
    severity: warning
    disposition: open
    title: "Download fallback format can yield a non-mp4 file and then fail after a full download"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`cli-parse.ts` returns the same exit code for invalid JSON as for a Zod rejection"
  - id: IN-01
    severity: info
    disposition: open
    title: "`_merge_short` never tries the other neighbour, and can exceed `MAX_WORDS`"
  - id: IN-02
    severity: info
    disposition: open
    title: "`make lint` type-checks only the contracts package, not the apps"
  - id: IN-03
    severity: info
    disposition: open
    title: "Feature `.npz` files are written non-atomically"
  - id: IN-04
    severity: info
    disposition: open
    title: "`smoke_lesson._self_check` uses `assert` for runtime validation"
  - id: IN-05
    severity: info
    disposition: open
    title: "Global `data/` and `*.wav`/`*.mp4` ignores will swallow test fixtures"
open: 11
total: 11
recorded: 2026-10-06T15:17:53.915Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
