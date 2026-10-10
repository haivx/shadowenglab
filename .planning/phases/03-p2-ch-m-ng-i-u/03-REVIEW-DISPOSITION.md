---
phase: 03-p2-ch-m-ng-i-u
review: 03-REVIEW.md
recorded: 2026-10-10T18:48:35Z
---

# Code review disposition — Phase 03

One row per finding in `03-REVIEW.md`. Default `open`; update to fixed / skipped / deferred as findings are triaged.

| ID | Finding | Disposition | Note |
|----|---------|-------------|------|
| WR-01 | Sidecar cache write uses a fixed `.part` name, so concurrent first scorings race and can fail the request | open | |
| WR-02 | `PUT .../eval-clip` does not bound `attempt`, so a huge value gives a 500 (`OverflowError`) | open | |
| WR-03 | `content-length` check uses `str.isdigit()`, so a non-ASCII digit header crashes the route with a 500 | open | |
| WR-04 | `STRESS_MISMATCH` can produce a nonsensical tip when the two words are textually identical | open | |
| WR-05 | Word row in `IntonationChart` is not aligned with the plot when the first word does not start at x = 0 | open | |
| WR-06 | Sidecar validation does not check the MFCC width or finiteness, so a bad file turns into a 500 later | open | |
| WR-07 | With `saveForEval=true` a failed clip write returns 500 after the attempt is already committed | open | |
| IN-01 | Retry after a lost or unparseable 201 duplicates the attempt | open | |
| IN-02 | `word_bounds` is not strictly increasing when there are more words than contour points | open | |
| IN-03 | Query-key prefix overlap causes unnecessary refetches | open | |
| IN-04 | Stale docstring in `thresholds.py` | open | |
| IN-05 | Cross-module private import and duplicated silence-mask logic | open | |
| IN-06 | Unmeasured word prominence is encoded as 0.0 in `stress` | open | |
