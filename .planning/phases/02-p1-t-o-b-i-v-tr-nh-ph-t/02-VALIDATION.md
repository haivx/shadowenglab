---
phase: "02"
slug: "p1-t-o-b-i-v-tr-nh-ph-t"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-06"
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + fastapi TestClient (`services/audio`); vitest ^4.1 node env (`packages/contracts`, `apps/web` — web test script added in 02-02) |
| **Config file** | `services/audio/pyproject.toml [tool.pytest.ini_options]` (exists); `services/audio/tests/conftest.py` (02-11, autouse isolation of settings dir / env file); no vitest config file (node defaults, relative imports) |
| **Quick run command** | `uv run --project services/audio --frozen pytest services/audio/tests/<file>.py -q` · `pnpm --filter @shadowenglab/web test -- <name>` · `pnpm --filter @shadowenglab/contracts test` |
| **Full suite command** | `make test` (drift gate → `pnpm -r --if-present test` → pytest) + `make lint` + `pnpm --filter @shadowenglab/web build` |
| **Estimated runtime** | ~60 seconds for `make test` (excluding `make smoke` ≈ 2 min and `make smoke-jobs` ≈ 4–5 min, which need models + network) |

---

## Sampling Rate

- **After every task commit:** the task's `<automated>` command (single test file / vitest filter / web build)
- **After every plan wave:** `make test` and `make lint`
- **Before `/gsd-verify-work`:** `make test` + `make lint` green, `make smoke END=300 BUDGET=300` → BUDGET OK, `make smoke-jobs` → JOBS OK, then the consolidated UAT (02-19 human-check)
- **Max feedback latency:** 60 seconds for per-task checks (model/network smoke runs are phase-gate only: 02-12 Task 3, 02-19 Task 1)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | SET-01/03/04, LES-01/03, PLY-04, REC-03/04 | — | Liam approves contract shapes + SQLite DDL (checkpoint) | checkpoint | — | n/a | ⬜ pending |
| 02-01-02 | 01 | 1 | same | T-02-01, T-02-02 | generated files only via codegen; drift gate | unit + round-trip | `UV_NO_SYNC=1 sh scripts/contracts_gen.sh && pnpm --filter @shadowenglab/contracts test` · `UV_NO_SYNC=1 uv run --project services/audio --frozen pytest services/audio/tests/test_contracts_roundtrip.py services/audio/tests/test_contracts_drift.py -q` | ✅ (extended) | ⬜ pending |
| 02-02-01 | 02 | 1 | REC-02, SET-03, PLY-02 | T-02-03 | lockfiles resolved without install | lockfile | `uv lock --project services/audio --check && grep -q 'name = "python-multipart"' services/audio/uv.lock && grep -q "xstate@5.33.2" pnpm-lock.yaml` | n/a | ⬜ pending |
| 02-02-02 | 02 | 1 | same | T-02-SC | package-legitimacy review before install | checkpoint (blocking-human) | — | n/a | ⬜ pending |
| 02-02-03 | 02 | 1 | same | T-02-SC | frozen install, lockfiles unchanged | smoke | `uv run --project services/audio --frozen python -c "import multipart, dotenv, httpx; print('ok')"` | n/a | ⬜ pending |
| 02-03-01 | 03 | 2 | LES-03, LES-02 | T-02-06, T-02-07 | URL allow-list; fixed error texts | API (TestClient + fake deps) | `uv run --project services/audio --frozen pytest services/audio/tests/test_lessons_api.py services/audio/tests/test_pipeline.py services/audio/tests/test_api.py -q` | ❌ W0 `test_lessons_api.py` | ⬜ pending |
| 02-03-02 | 03 | 2 | LES-03, LES-07 | T-02-09 | atomic writes, retry without null keys | unit (threads + Event) | `uv run --project services/audio --frozen pytest services/audio/tests/test_jobs.py services/audio/tests/test_lessons_api.py -q` | ❌ W0 `test_jobs.py` | ⬜ pending |
| 02-03-03 | 03 | 2 | LES-03 | T-02-05 | TrustedHost + Origin guard + CORS | API | `uv run --project services/audio --frozen pytest services/audio/tests/test_api.py services/audio/tests/test_lessons_api.py services/audio/tests/test_config.py -q` | ✅ (extended) | ⬜ pending |
| 02-04-01 | 04 | 2 | LES-03 | T-02-10 | Zod parse of every response | unit (stub fetch) + build | `pnpm --filter @shadowenglab/web test -- api && pnpm --filter @shadowenglab/web build` | ❌ W0 `lib/api.test.ts` | ⬜ pending |
| 02-04-02 | 04 | 2 | PLY-07 | — | n/a | unit (token drift) | `pnpm --filter @shadowenglab/web test -- tokens && pnpm --filter @shadowenglab/web build` | ❌ W0 `lib/tokens.test.ts` | ⬜ pending |
| 02-04-03 | 04 | 2 | PLY-07 | T-02-12 | lockfile diff check after shadcn CLI | build + lint + grep | `pnpm --filter @shadowenglab/web test && pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web` | n/a | ⬜ pending |
| 02-05-01 | 05 | 2 | PLY-02 | — | n/a | unit (XState, node) | `pnpm --filter @shadowenglab/web test -- playerMachine` | ❌ W0 `playerMachine.test.ts` | ⬜ pending |
| 02-05-02 | 05 | 2 | PLY-07, REC-01 | T-02-13 | shortcuts ignored in inputs/dialogs | unit | `pnpm --filter @shadowenglab/web test -- shortcuts level` | ❌ W0 `shortcuts.test.ts`, `level.test.ts` | ⬜ pending |
| 02-06-01 | 06 | 3 | LES-03, LES-06 | T-02-14, T-02-16 | parameterized SQL; corrupt file skipped | API | `uv run --project services/audio --frozen pytest services/audio/tests/test_library_api.py services/audio/tests/test_api.py -q` | ❌ W0 `test_library_api.py` | ⬜ pending |
| 02-06-02 | 06 | 3 | PLY-04 | T-02-15 | contained path helpers | unit + API | `uv run --project services/audio --frozen pytest services/audio/tests/test_db.py services/audio/tests/test_config.py services/audio/tests/test_library_api.py -q` | ❌ W0 `test_db.py` | ⬜ pending |
| 02-07-01 | 07 | 3 | PLY-01 | T-02-17 | videoId only from lesson.json | API (Range 206/416) | `uv run --project services/audio --frozen pytest services/audio/tests/test_media_api.py -q` | ❌ W0 `test_media_api.py` | ⬜ pending |
| 02-07-02 | 07 | 3 | LES-01 | T-02-18, T-02-20 | allow-list before yt-dlp; fixed messages | unit + API | `uv run --project services/audio --frozen pytest services/audio/tests/test_urls.py services/audio/tests/test_media_api.py -q` | ✅ (extended) | ⬜ pending |
| 02-07-03 | 07 | 3 | PLY-01, LES-04 | T-02-19 | per-video lock, argv ffmpeg/ffprobe | unit + API + doc grep | `uv run --project services/audio --frozen pytest services/audio/tests/test_download.py services/audio/tests/test_media_api.py services/audio/tests/test_pipeline.py -q` | ❌ W0 `test_download.py` | ⬜ pending |
| 02-08-01 | 08 | 3 | LES-03, LES-06, LES-07 | T-02-21 | https-only thumbnails | unit + build | `pnpm --filter @shadowenglab/web test -- lessonView && pnpm --filter @shadowenglab/web build` | ❌ W0 `lessonView.test.ts` | ⬜ pending |
| 02-08-02 | 08 | 3 | SET-01, SET-02 | T-02-22 | only ApiError messages shown | build + lint | `pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web` | n/a | ⬜ pending |
| 02-08-03 | 08 | 3 | LES-03 | — | no score colours (D-08) | unit + grep + human-check | `pnpm --filter @shadowenglab/web test -- lessonView && pnpm --filter @shadowenglab/web build` | ✅ | ⬜ pending |
| 02-09-01 | 09 | 3 | PLY-01, PLY-03 | T-02-24 | video src from API_BASE only | unit (fake video/raf) + build | `pnpm --filter @shadowenglab/web test -- playRange && pnpm --filter @shadowenglab/web build` | ❌ W0 `playRange.test.ts` | ⬜ pending |
| 02-09-02 | 09 | 3 | PLY-04, PLY-07 | T-02-23 | text rendered as text | build + lint | `pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web` | n/a | ⬜ pending |
| 02-09-03 | 09 | 3 | PLY-07, PLY-01 | — | n/a | unit + build + human-check | `pnpm --filter @shadowenglab/web test && pnpm --filter @shadowenglab/web build` | ✅ | ⬜ pending |
| 02-10-01 | 10 | 4 | REC-02, REC-03 | T-02-27 | temp dir removed in finally | API (real ffmpeg, synthetic audio) | `uv run --project services/audio --frozen pytest services/audio/tests/test_attempts_api.py -q` | ❌ W0 `test_attempts_api.py` | ⬜ pending |
| 02-10-02 | 10 | 4 | REC-02 | T-02-25, T-02-26 | demuxer whitelist, size/length caps | unit + API | `uv run --project services/audio --frozen pytest services/audio/tests/test_normalize.py services/audio/tests/test_vad.py services/audio/tests/test_attempts_api.py -q` | ❌ W0 `test_normalize.py`, `test_vad.py` | ⬜ pending |
| 02-10-03 | 10 | 4 | REC-04 | T-02-28 | eval filename from validated values | API | `uv run --project services/audio --frozen pytest services/audio/tests/test_attempts_api.py -q` | ✅ | ⬜ pending |
| 02-11-01 | 11 | 4 | SET-01, SET-02 | T-02-31 | no key in responses | API | `uv run --project services/audio --frozen pytest services/audio/tests/test_system_status.py -q` | ❌ W0 `test_system_status.py` | ⬜ pending |
| 02-11-02 | 11 | 4 | SET-04 | T-02-32, T-02-33 | dataDir validated; tests isolated | API | `uv run --project services/audio --frozen pytest services/audio/tests/test_settings_api.py services/audio/tests/test_config.py services/audio/tests/test_api.py -q` | ❌ W0 `test_settings_api.py`, `conftest.py` | ⬜ pending |
| 02-11-03 | 11 | 4 | SET-03, SET-01 | T-02-30, T-02-31, T-02-34 | KEY_RE before write; 0600; warm-up under gate | unit (MockTransport, fake loaders) | `uv run --project services/audio --frozen pytest services/audio/tests/test_openai_key.py services/audio/tests/test_system_status.py services/audio/tests/test_lessons_api.py -q` | ❌ W0 `test_openai_key.py` | ⬜ pending |
| 02-12-01 | 12 | 4 | PLY-06, LES-04 | — | IPA only from PPG (no G2P import) | unit | `uv run --project services/audio --frozen pytest services/audio/tests/test_ipa.py services/audio/tests/test_pipeline.py -q` | ❌ W0 `test_ipa.py` | ⬜ pending |
| 02-12-02 | 12 | 4 | LES-04 | — | n/a | unit + grep | `uv run --project services/audio --frozen pytest services/audio/tests/test_segment.py services/audio/tests/test_pipeline.py -q` | ✅ (updated) | ⬜ pending |
| 02-12-03 | 12 | 4 | LES-02, LES-05 | T-02-35, T-02-36 | contained stems path; rmtree only lesson seg/ | unit + real smoke | `uv run --project services/audio --frozen pytest services/audio/tests/test_pipeline.py services/audio/tests/test_ipa.py services/audio/tests/test_segment.py -q` · `make smoke END=300 BUDGET=300` | ✅ | ⬜ pending |
| 02-13-01 | 13 | 4 | LES-01, LES-03 | T-02-37 | URL encoded; server allow-list | unit + build | `pnpm --filter @shadowenglab/web test -- time && pnpm --filter @shadowenglab/web build` | ❌ W0 `time.test.ts` | ⬜ pending |
| 02-13-02 | 13 | 4 | LES-02 | T-02-38 | debounce | unit + build + human-check | `pnpm --filter @shadowenglab/web test -- time && pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web` | ✅ | ⬜ pending |
| 02-14-01 | 14 | 4 | REC-01 | T-02-40 | mic released on every exit | unit + build | `pnpm --filter @shadowenglab/web test -- mime playerMachine && pnpm --filter @shadowenglab/web build` | ❌ W0 `mime.test.ts` | ⬜ pending |
| 02-14-02 | 14 | 4 | PLY-07, REC-04 | T-02-39 | object URLs revoked | build + lint | `pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web` | n/a | ⬜ pending |
| 02-14-03 | 14 | 4 | REC-03 | T-02-39 | no browser persistence of recordings | unit + build + grep + human-check | `pnpm --filter @shadowenglab/web test && pnpm --filter @shadowenglab/web build` | ✅ | ⬜ pending |
| 02-15-01 | 15 | 5 | PLY-04 | T-02-42 | NFC + 500 code points | API | `uv run --project services/audio --frozen pytest services/audio/tests/test_segment_edit.py -q` | ❌ W0 `test_segment_edit.py` | ⬜ pending |
| 02-15-02 | 15 | 5 | PLY-05 | T-02-43 | cap 3000 ms; gate timeout → 503 | unit + API | `uv run --project services/audio --frozen pytest services/audio/tests/test_extend_end.py services/audio/tests/test_segment_edit.py -q` | ❌ W0 `test_extend_end.py` | ⬜ pending |
| 02-16-01 | 16 | 5 | PLY-04 | — | Liam chooses TRANSLATE_MODEL (D-23) | checkpoint | — | n/a | ⬜ pending |
| 02-16-02 | 16 | 5 | PLY-04, SET-02 | T-02-44, T-02-45, T-02-46 | text only; key never echoed; cache | unit (MockTransport) | `uv run --project services/audio --frozen pytest services/audio/tests/test_translate.py -q` | ❌ W0 `test_translate.py` | ⬜ pending |
| 02-17-01 | 17 | 5 | SET-03 | T-02-47 | password field, state only | build + lint | `pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web` | n/a | ⬜ pending |
| 02-17-02 | 17 | 5 | SET-04, SET-01 | — | auto-save revert | unit + build | `pnpm --filter @shadowenglab/web test -- settingsForm && pnpm --filter @shadowenglab/web build` | ❌ W0 `settingsForm.test.ts` | ⬜ pending |
| 02-17-03 | 17 | 5 | SET-01 | T-02-48 | mic closed after test | build + human-check | `pnpm --filter @shadowenglab/web test && pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web` | ✅ | ⬜ pending |
| 02-18-01 | 18 | 5 | PLY-06 | — | UI shows only Word.ipa | unit + build + grep | `pnpm --filter @shadowenglab/web test -- ipaLine && pnpm --filter @shadowenglab/web build` | ❌ W0 `ipaLine.test.ts` | ⬜ pending |
| 02-18-02 | 18 | 5 | PLY-04 | T-02-49 | translation rendered as text | build + lint | `pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web` | n/a | ⬜ pending |
| 02-18-03 | 18 | 5 | PLY-04, PLY-05 | T-02-50 | n/a | build + human-check | `pnpm --filter @shadowenglab/web test && pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web` | ✅ | ⬜ pending |
| 02-19-01 | 19 | 6 | LES-03, LES-05, SET-02 | T-02-51 | temp DATA_DIR/config/env for the harness | real end-to-end smoke | `make smoke-jobs` (JOBS OK) · `make smoke END=300 BUDGET=300` (BUDGET OK) | ❌ W0 `scripts/smoke_jobs.py` | ⬜ pending |
| 02-19-02 | 19 | 6 | PLY-07 | — | n/a | full suite + doc grep + UAT | `make test` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Test files created by the task that first needs them (each plan writes its tests before or with the implementation):

- [ ] `packages/contracts/fixtures/*.json` (11 new) + `contracts.test.ts` update — 02-01
- [ ] `apps/web` `test` script + vitest install (frozen) — 02-02
- [ ] `services/audio/tests/test_lessons_api.py`, `test_jobs.py` — 02-03
- [ ] `apps/web/lib/api.test.ts`, `lib/tokens.test.ts` — 02-04
- [ ] `apps/web/lib/player/playerMachine.test.ts`, `shortcuts.test.ts`, `lib/audio/level.test.ts` — 02-05
- [ ] `services/audio/tests/test_library_api.py`, `test_db.py` — 02-06
- [ ] `services/audio/tests/test_media_api.py`, `test_download.py` — 02-07
- [ ] `services/audio/tests/test_attempts_api.py`, `test_normalize.py`, `test_vad.py` — 02-10
- [ ] `services/audio/tests/conftest.py` (autouse isolation), `test_system_status.py`, `test_settings_api.py`, `test_openai_key.py` — 02-11
- [ ] `services/audio/tests/test_ipa.py` — 02-12
- [ ] `services/audio/tests/test_segment_edit.py`, `test_extend_end.py` — 02-15
- [ ] `services/audio/tests/test_translate.py` — 02-16
- [ ] `apps/web/lib/lessonView.test.ts`, `time.test.ts`, `mime.test.ts`, `playRange.test.ts`, `settingsForm.test.ts`, `ipaLine.test.ts` — 02-08/02-13/02-14/02-09/02-17/02-18
- [ ] `scripts/smoke_jobs.py` — 02-19

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 30 sentences mouse-only and keyboard-only (success criterion 3) | PLY-07, PLY-03, REC-01 | needs Chrome, a microphone and human judgement | 02-19 Task 2 human-check (and 02-14 Task 3) |
| UI matches `docs/design/` (success criterion 5) | all UI reqs | visual fidelity | compare S1/S2/S3/S8 with `docs/design/screens/*.html` (02-08, 02-13, 02-14, 02-17, 02-18 human-checks) |
| VAD thresholds feel right on Liam's mic (RESEARCH A1) | REC-01, REC-03 | hardware-dependent | quiet speech counts as voiced; silence shows the no-voice panel |
| IPA hide rate and glyph rendering (A6, D-20) | PLY-06 | perception / font coverage | 02-18 Task 3 human-check |
| Missing-key experience end to end in the browser (success criterion 4) | SET-02 | browser banner + flows | 02-19 Task 2 human-check (backend side automated by `make smoke-jobs`) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 02s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** {pending / approved YYYY-MM-DD}
