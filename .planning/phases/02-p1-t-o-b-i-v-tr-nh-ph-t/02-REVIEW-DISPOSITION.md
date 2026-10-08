---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "First-use mic permission prompt eats the recording window and yields a near-empty clip"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Several backend error paths do not use the `ApiError` envelope, so the web shows \"Backend trả lỗi không đọc được\""
  - id: WR-03
    severity: warning
    disposition: open
    title: "A stale `dataDir` in settings.json makes every Practice-defaults save fail with 422"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`POST /lessons` accepts live, upcoming and unavailable videos and gives the wrong error"
  - id: WR-05
    severity: warning
    disposition: open
    title: "No server-side cap on lesson range length (OOM risk on the 8 GB target)"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`_real_separate` / `_warm_demucs` can raise `UnboundLocalError` that hides the real failure"
  - id: WR-07
    severity: warning
    disposition: open
    title: "`DownloadError` is always reported as \"limited by region, private or downloads disabled\""
  - id: WR-08
    severity: warning
    disposition: fixed
    title: "Retrying a failed lesson bypasses the duplicate-lesson rule"
  - id: IN-01
    severity: info
    disposition: open
    title: "Stale `lastError` can show the wrong error panel"
  - id: IN-02
    severity: info
    disposition: open
    title: "`_store_eval_clip` failure leaves an already-counted attempt row"
  - id: IN-03
    severity: info
    disposition: open
    title: "`dotenv_values` can raise on a non-UTF-8 `.env`, breaking `/system/status`"
  - id: IN-04
    severity: info
    disposition: open
    title: "`load_ppg_model` uses `from_pretrained` without `local_files_only`, unlike `load_inv_vocab`"
  - id: IN-05
    severity: info
    disposition: open
    title: "`safeThumbnailUrl` accepts any https host"
  - id: IN-06
    severity: info
    disposition: open
    title: "Duplicated helpers across web components"
  - id: IN-07
    severity: info
    disposition: open
    title: "Dead exports and an unused UI component"
  - id: IN-08
    severity: info
    disposition: open
    title: "Attempt label can show the previous count until progress refetches"
  - id: IN-09
    severity: info
    disposition: open
    title: "Timing-based assertions in tests"
open: 16
total: 17
recorded: 2026-10-08T15:18:48.849Z
---

# Phase 02: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | fixed | 02-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |
| IN-09 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
