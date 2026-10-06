---
phase: "01"
slug: "p0-n-n-t-ng"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-06"
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `01-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (Python, `services/audio`), vitest ^4.1 (TS, `packages/contracts`) |
| **Config file** | none — Wave 0 creates `services/audio/pyproject.toml [tool.pytest.ini_options]` and (optional) `packages/contracts/vitest.config.ts` |
| **Quick run command** | `cd services/audio && uv run pytest -x -q <touched test file>` / `pnpm --filter @shadowenglab/contracts test` |
| **Full suite command** | `make test` (= `contracts-check` + `pnpm -r --if-present test` + `cd services/audio && uv run pytest`) |
| **Estimated runtime** | ~30 seconds (excluding model-loading smoke runs) |

---

## Sampling Rate

- **After every task commit:** Run the quick command matching the touched area
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** `make test` green + one real `make smoke URL=...` with total ≤ 300 s
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Filled by the planner/executor per task. Requirement → test map from research:

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| FND-01 | workspace installs; lint/format/ruff pass | smoke | `pnpm install --frozen-lockfile && make lint` | ❌ W0 | ⬜ pending |
| FND-02 | Zod types parse fixtures; every object type has an `id`; schema bundle generated | unit | `pnpm --filter @shadowenglab/contracts test` | ❌ W0 | ⬜ pending |
| FND-03 | committed schema/pydantic == regenerated; round-trip TS ↔ JSON Schema ↔ pydantic | integration | `sh scripts/contracts_check.sh && cd services/audio && uv run pytest tests/test_contracts_roundtrip.py` | ❌ W0 | ⬜ pending |
| FND-04 | `check_deps.sh` reports missing tools with `brew install` hint + non-zero exit; parselmouth works | unit/smoke | `sh scripts/check_deps.sh; cd services/audio && uv run pytest tests/test_setup.py` | ❌ W0 | ⬜ pending |
| FND-05 | `make test` runs both suites; `make eval` exits 0; `make dev` starts both ports | smoke (dev manual) | `make test && make eval` | ❌ W0 | ⬜ pending |
| FND-06 | `/health` 200; lesson route returns contract-valid camelCase JSON; bad id 404 | unit | `cd services/audio && uv run pytest tests/test_api.py` | ❌ W0 | ⬜ pending |
| FND-07 | `split_sentences` rules; smoke-built `Lesson` validates; timing table printed | unit + manual | `cd services/audio && uv run pytest tests/test_segment.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/contracts/src/*.test.ts` + `fixtures/*.json` — FND-02/03
- [ ] `services/audio/tests/{test_contracts_roundtrip,test_segment,test_api,test_setup}.py` + `conftest.py` (tmp `DATA_DIR`)
- [ ] Framework install: `uv add --dev pytest httpx jsonschema`, `pnpm add -D vitest tsx`
- [ ] `scripts/check_deps.sh`, `scripts/contracts_check.sh`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `make dev` starts Next.js (3000) + FastAPI (8000) | FND-05 | long-running processes | `make dev`, then `curl -s localhost:8000/health && curl -sI localhost:3000` |
| 5-min real video processed in ≤ 5 min | FND-07 | needs a real YouTube video + network; timing on hardware | `make smoke URL=<clean US interview video>`; check printed total ≤ 300 s |
| `make setup` on a clean machine | FND-04 | needs empty model cache + brew tools | `HF_HOME=$(mktemp -d) make setup` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
