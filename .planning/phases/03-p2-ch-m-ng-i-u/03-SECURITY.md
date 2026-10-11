---
phase: "03"
slug: "p2-ch-m-ng-i-u"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-11"
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| web (Zod) ↔ FastAPI (pydantic) | New error codes and response shapes (ScoreResult, AttemptSummary, LessonProgress) | contract-validated JSON |
| npm registry → repo | recharts and its transitive set enter via the lockfile | third-party code, reviewed lockfile, frozen install |
| Browser upload → FastAPI scoring | Untrusted learner audio and path params enter the numeric pipeline | audio bytes (≤ 10 MB / 60 s), lesson id, segment index |
| SQLite `result_json` / sidecar `.prosody.npz` → API / scorer | Stored data re-enters the API and the scorer | scores in [0, 1], cached numeric arrays |
| Whisper / "Sửa câu" word text → tip text → DOM | Untrusted strings inserted into templates and rendered in the result panel | word strings |
| smoke script → real DATA_DIR; repo ← phase artifacts | Dev tool reads real lesson data; risk of committing personal audio | numbers only |

---

## Threat Register

Built from the `<threat_model>` blocks of 03-01..03-12 (28 unique; T-03-SC repeats in every plan). L1 evidence was checked by grep on 2026-10-11.

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-SC | Tampering | npm/pip installs | high | mitigate | Only 03-02 adds packages, behind a blocking human lockfile review and a frozen install; `react-is` pinned 18.3.1, `recharts` 3.10.1 (`apps/web/package.json`); every other plan adds nothing | closed |
| T-03-01 | Tampering | contracts_gen.py / schema bundle | medium | mitigate | Generated only via `scripts/contracts_gen.sh`; drift gate `contracts_check.sh` in `make test` | closed |
| T-03-02 | Information disclosure | ApiError.message (no_speech / invalid_state / internal_error) | low | mitigate | Fixed Vietnamese messages; 03-05 tests assert no DATA_DIR path in error bodies | closed |
| T-03-03 | Tampering | recharts transitive dependencies | high | mitigate | `--lockfile-only` resolution, Liam reviewed new keys, `--frozen-lockfile` install (03-02 SUMMARY) | closed |
| T-03-04 | Elevation of privilege | package install scripts | medium | mitigate | `pnpm-workspace.yaml` `allowBuilds` limited to `esbuild` | closed |
| T-03-05 | Denial of service | `align` DTW cost matrix | high | mitigate | `ALIGN_RATIO_MIN/MAX` gate before any matrix, `linear_path` fallback, BLAS distance (`scoring/align.py:20,50,66`); test proves matrix funcs not called | closed |
| T-03-06 | Tampering | NaN/inf in ScoreResult | medium | mitigate | `np.isfinite` guards (`scoring/metrics.py:78,99,115`), clip in `scorer._unit`, `ScoreResult.model_validate` | closed |
| T-03-07 | Tampering | `uploadAttempt` response | medium | mitigate | `request(..., ScoreResult)` Zod-parses 2xx; test `rejects when a 201 body fails ScoreResult validation` (`lib/api.test.ts:168`) | closed |
| T-03-08 | Spoofing | `isNoSpeechError` duck typing | low | accept | See accepted risks AR-03-01 | closed |
| T-03-09 | Tampering | SQL writes of scores / result_json | medium | mitigate | `?` params only, `ULID_RE` id check (`config.py:22,130`), `_SCORE_CHECK` bounds [0, 1] (`db.py:38`) | closed |
| T-03-10 | Tampering | corrupted `result_json` | medium | mitigate | `ScoreResult.model_validate_json` on read (`routers/attempts.py:306`), fixed 500 message, test asserts no echo | closed |
| T-03-11 | Tampering | sidecar `.prosody.npz` | medium | mitigate | `np.load(allow_pickle=False)` (`scoring/ref_cache.py:30,44`), feat_version + window check, `.part` + `os.replace` | closed |
| T-03-12 | Denial of service | scoring request (CPU, temp files) | medium | mitigate | 10 MB / 60 s caps; ratio gate (T-03-05); `mkdtemp` + `shutil.rmtree` in `finally` (`routers/attempts.py:216,270`); slice read with `start`/`stop` (`lesson/pipeline.py:445`) | closed |
| T-03-13 | Information disclosure | error bodies | low | mitigate | Fixed messages; tests assert no path or exception text | closed |
| T-03-14 | Tampering | word text inside `Tip.text` | medium | mitigate | `_clean` strips `*`, rejects blanks (`rules/tips.py:74`); client renders text only | closed |
| T-03-15 | Repudiation | false-positive tips | medium | mitigate | D-12 certainty gates, D-02 restriction, zero-issue self-compare test; Phase 4 measures precision | closed |
| T-03-16 | Denial of service | long contour arrays in chart | low | accept | See accepted risks AR-03-02 | closed |
| T-03-17 | Tampering | word labels in chart | low | mitigate | React text nodes / `title` attribute; no `dangerouslySetInnerHTML` in `apps/web/{components,lib,app}` | closed |
| T-03-18 | Tampering | TipList rendering (XSS) | high | mitigate | `splitTipMarkup` (`lib/tipMarkup.ts`) → React text children in `components/TipList.tsx`; grep for raw HTML injection in source is empty | closed |
| T-03-19 | Tampering | LessonProgress.bestOverall | low | mitigate | `getLessonProgress` parses with `LessonProgress` Zod schema (`lib/api.ts:160`) | closed |
| T-03-20 | Tampering | `getAttemptResult` / `listAttempts` bodies | medium | mitigate | Zod parse (`ScoreResult`, `AttemptSummary`) before render; tests `lib/api.test.ts:183,209` | closed |
| T-03-21 | Denial of service | unbounded attempt history | low | mitigate | `MAX_ATTEMPT_CHIPS = 6` (`lib/attemptChips.ts:18`); `staleTime: Infinity` (`lib/queries.ts:80`) | closed |
| T-03-22 | Tampering | smoke_score.py on real DATA_DIR | medium | mitigate | `write_cache=False` (`scripts/smoke_score.py:277`), no DB access, temp dir removed; test compares DATA_DIR listing | closed |
| T-03-23 | Information disclosure | committing real audio / data | medium | mitigate | Smoke prints numbers only; `.gitignore` excludes eval clips/labels/`.env` | closed |
| T-03-24 | Tampering | untrusted words in tip variants | medium | mitigate | `_clean` before `str.format`, no re-parse; pytest renders every variant with `a*b`, `**x**`, `{pct}`, `<b>x</b>` (`tests/test_scoring_tips.py`) | closed |
| T-03-25 | Denial of service | non-finite numbers in `issue.data` | low | mitigate | `_number` returns None for NaN/±inf/bool (`rules/tips.py:87`); tip skipped | closed |
| T-03-26 | Repudiation | `issueRef` pointing to wrong issue/word | medium | mitigate | Index into unfiltered `issues`; tests assert code and word agree (`tests/test_scoring_tips.py`, `test_scoring_rules.py`) | closed |
| T-03-27 | Tampering | history rewritten on re-render | low | mitigate | Tips stored in `result_json` at scoring time; API test compares `GET …/attempts/1` with first POST (`tests/test_scoring_api.py`) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-08 | Only errors thrown by the local api client reach the actor; worst case a mislabelled failure shows the "no voice" panel, which still offers Ghi lại | Liam (plan 03-04) | 2026-10-11 |
| AR-03-02 | T-03-16 | Contour downsampled to 20 ms server-side, recordings capped at 60 s (≤ ~3000 points), chart animation disabled | Liam (plan 03-07) | 2026-10-11 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-11 | 28 | 28 | 0 | /gsd-secure-phase (orchestrator, L1 grep; auditor skipped per short-circuit: plan-time register, ASVS 1, threats_open 0) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-11
