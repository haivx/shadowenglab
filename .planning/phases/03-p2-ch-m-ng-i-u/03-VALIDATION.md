---
phase: "3"
slug: "p2-ch-m-ng-i-u"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-08"
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Nguồn: `03-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + fastapi `TestClient` (`services/audio`); vitest ^4.1 (node env) cho `apps/web`, `packages/contracts` |
| **Config file** | `services/audio/pyproject.toml [tool.pytest.ini_options]`, `services/audio/tests/conftest.py`; web: không có file config vitest (mặc định node) |
| **Quick run command** | `uv run --project services/audio --frozen pytest services/audio/tests/<file>.py -q` · `pnpm --filter @shadowenglab/web test -- <tên>` |
| **Full suite command** | `make test && make lint && pnpm --filter @shadowenglab/web build` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run test file của task (quick run command, ≤ 30 s)
- **After every plan wave:** Run `make test && make lint`
- **Before `/gsd-verify-work`:** Full suite must be green; smoke tự so trên bài thật báo `overall ≈ 1.00` và `timingMs.total`
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (planner điền) | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `services/audio/tests/synth.py` — helper sinh câu giả giọng tổng hợp, seed cố định
- [ ] `services/audio/tests/test_scoring_{features,metrics,rules,tips,pipeline}.py` — PRO-01..03, RUL-01..02
- [ ] `services/audio/tests/test_scoring_api.py` — D-09 (POST trả `ScoreResult`, `no_speech`, eval-clip), PRO-04 timing
- [ ] `apps/web/lib/{scoreLevel,chartData,tipMarkup}.test.ts` — FBK-01..03
- [ ] Cập nhật `playerMachine.test.ts`, `api.test.ts`, `test_attempts_api.py`, `test_db.py`, contract round-trip — FBK-05, FBK-06, contract
- [ ] Cài Recharts (cổng legitimacy) + `pnpm --filter @shadowenglab/web build`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Câu đọc sai hẳn bằng giọng thật cho điểm thấp; ngưỡng `ALIGN_COST_MAX` hợp với micro thật | PRO-03, RUL-01 | Cần giọng người học thật, không commit audio | Liam ghi 3–5 câu đúng và 3–5 câu sai hẳn, ghi lại điểm/issue vào UAT |
| UI khớp `docs/design/` (6 trạng thái vùng câu, hover tip highlight từ, `R` giữ lượt tốt nhất) | FBK-01..06 | So khớp thị giác | Mở S3, đối chiếu `S3-S4-phong-tap.png`, `S3-trang-thai-cau.png` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
