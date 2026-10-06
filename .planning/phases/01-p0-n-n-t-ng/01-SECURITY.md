---
phase: "01"
slug: "p0-n-n-t-ng"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-06"
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register merged from the `<threat_model>` blocks of 01-01..01-09; evidence checked at ASVS L1 (grep + test presence) after the wave-5 merge (HEAD 6c638f0).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| npm / PyPI registries → repo | third-party code enters via lockfile resolution and installs | package code (supply chain) |
| repo → public GitHub | anything committed becomes public | .env secrets, eval audio, rater labels |
| user input → audio service | YouTube URL and lesson/video ids reach file paths and subprocess argv | untrusted strings |
| YouTube / Hugging Face → local | yt-dlp downloads media; HF hub downloads model weights | media, pickled weights |
| browser → FastAPI (localhost) | Next.js on :3000 calls the API on :8000 | lesson JSON |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation (evidence) | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Tampering | npm/PyPI dependency set | high | mitigate | lockfiles resolved without install, approved by Liam 2026-10-06 (01-01-SUMMARY); Makefile installs use `--frozen-lockfile` / `--frozen` | closed |
| T-01-02 | Tampering | pnpm 11 `trustPolicy: off` | medium | mitigate | applied after Liam approved item 1; `allowBuilds` = esbuild only (pnpm-workspace.yaml) | closed |
| T-01-03 | Information disclosure | `.env` / eval audio / rater labels | high | mitigate | `.gitignore` covers `.env`, audio, `eval/clips/`, `eval/labels.jsonl`; `git ls-files` has no `.env` or audio file | closed |
| T-01-04 | Tampering | config.py path helpers / GET /lessons/{id} | high | mitigate | id regex + `resolve().is_relative_to(data_root())` (config.py:56); tests for traversal ids and symlink escape (test_config.py) | closed |
| T-01-05 | Information disclosure | FastAPI CORS | medium | mitigate | allow_origins `http://localhost:3000` only (main.py); foreign-origin test in test_api.py | closed |
| T-01-06 | Information disclosure | error responses | low | mitigate | fixed detail "lesson not found" (routers/lesson.py) | closed |
| T-01-07 | Tampering | generated contracts_gen.py | medium | mitigate | GENERATED header; single entry `scripts/contracts_gen.sh`; drift gate in `make test` | closed |
| T-01-08 | Elevation of privilege | check_deps.sh / setup_models.py | medium | mitigate | `brew install` appears only inside echo hints; stub-installer test (d) in test_setup.py | closed |
| T-01-09 | Tampering | model download (wav2vec2 pickle) | high | mitigate | fixed repo ids in models.py, `allow_patterns`, no `trust_remote_code=True`; Demucs via `hf://htdemucs` (no AWS fallback) | closed |
| T-01-10 | Information disclosure (SSRF) | parse_youtube_url | high | mitigate | host allow-list, userinfo/port/control-char rejection, yt-dlp only gets `canonical_watch_url`; look-alike + `@` cases in test_urls.py | closed |
| T-01-11 | Tampering (injection) | video id → paths / argv | high | mitigate | id fullmatch `[A-Za-z0-9_-]{11}` in urls.py and config.py; option-like/traversal tests | closed |
| T-01-12 | Tampering / DoS | lesson.json rewrite | medium | mitigate | temp file + fsync + `os.replace` (contract_io.py); failure test | closed |
| T-01-13 | Tampering | TS ↔ Python contract drift | high | mitigate | test_contracts_roundtrip.py over every fixture; `contracts-check` in `make test` | closed |
| T-01-14 | Information disclosure | ClipManifest.gold / systemScore | low | accept | see Accepted Risks (AR-01) | closed |
| T-01-15 | Tampering (injection) | audio_io / download | high | mitigate | no `shell=True` in audio_service; ffmpeg argv list; download.py uses `canonical_watch_url` | closed |
| T-01-16 | Information disclosure | pipeline egress | medium | mitigate | no requests/httpx/urllib client in `lesson/`; only yt-dlp + local HF cache | closed |
| T-01-17 | Denial of service | 8 GB RAM, three models | medium | mitigate | sequential stages + `free_accelerator_memory`; 5-min video measured 115.8–125.3 s (01-08) | closed |
| T-01-18 | Tampering | from_pretrained loading | high | mitigate | ids only from models.py (PPG_REPO), no remote code | closed |
| T-01-19 | Tampering | npm build-time scripts | low | accept | see Accepted Risks (AR-02) | closed |
| T-01-20 | Information disclosure | uvicorn in `make dev-api` | high | mitigate | `--host 127.0.0.1` in Makefile | closed |
| T-01-21 | Denial of service | dev_smoke.sh shutdown | low | mitigate | `kill -TERM -- "-$JOB_PID"` (own process group), no `kill 0`; ports verified closed | closed |
| T-01-22 | Tampering | lint auto-fixes on earlier files | low | mitigate | 01-08 changed no earlier-plan files; generated files excluded from linters | closed |
| T-01-23 | Tampering | `make test` drift gate | medium | mitigate | `test_detects_drift` in test_contracts_drift.py | closed |
| T-01-24 | Information disclosure | .env.example / docs | medium | mitigate | no filled KEY/SECRET/TOKEN value in .env.example | closed |
| T-01-25 | Repudiation | decision trail | low | mitigate | ADR 0003 records decisions with "Người quyết: Liam" | closed |
| T-01-SC | Tampering | npm/pip installs | high | mitigate | package-legitimacy gate passed (Liam `approved` 2026-10-06); every install in Makefile is frozen | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-01-14 | P0 ships no rater client; RAT-06 (Phase 6) must enforce that `gold` and `systemScore` never reach the client | plan 01-05 threat model (accept) | 2026-10-06 |
| AR-02 | T-01-19 | only esbuild may run install scripts (allowBuilds approved in 01-01); shells hold no user input, API routes or secrets. Note: fsevents@2.3.3 declares node-gyp rebuild in registry metadata and is not in allowBuilds (Liam informed at the 01-01 gate) | plan 01-07 threat model (accept) | 2026-10-06 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-06 | 26 | 26 | 0 | secure-phase (orchestrator, ASVS L1 grep + test evidence) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
