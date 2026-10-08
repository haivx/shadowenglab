---
phase: "02"
slug: "p1-t-o-b-i-v-tr-nh-ph-t"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-08"
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Browser → FastAPI (127.0.0.1:8000) | Web app (localhost:3000) calls the local API; write methods guarded by Origin check, CORS allow-list and TrustedHost | lesson ids, sentence text, settings, recorded audio (multipart), OpenAI key (once, on check/save) |
| FastAPI → yt-dlp / ffmpeg / ffprobe | Pasted YouTube links and uploaded recordings reach external binaries | canonical watch URL only; sniffed/whitelisted audio via argv lists with timeouts |
| FastAPI → OpenAI (Responses API over httpx) | Optional translation and key check | sentence text only (no audio); key in Authorization header |
| FastAPI → DATA_DIR / settings / .env | Lessons, SQLite `attempts`, stems, eval clips, settings.json, `.env` key file | validated ids, contained paths, atomic writes, key file 0600 |
| Package registries → lockfiles | npm / PyPI packages added in 02-02 | reviewed lockfiles, frozen installs only |

---

## Threat Register

Built from the `<threat_model>` blocks of 02-01..02-19 (70 rows, 52 unique; T-02-SC repeats in every plan). Per-threat evidence (file:line and asserting tests) is in the auditor verdict recorded in the audit trail below.

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-SC | Tampering | npm/pip installs | high | mitigate | this plan installs nothing; codegen runs with `UV_NO_SYNC=1 … --frozen` so no package enters before the 02-02 lockfile review | closed |
| T-02-01 | Tampering | contracts_gen.py / schema bundle | medium | mitigate | generated only via `scripts/contracts_gen.sh`; drift gate (`contracts_check.sh`) in `make test`; header "GENERATED … không sửa tay" | closed |
| T-02-02 | Information disclosure | ApiError.message | medium | mitigate | contract documents message as fixed Vietnamese user text; implementing routers (02-03..02-16) test that responses never contain DATA_DIR paths or exception text | closed |
| T-02-03 | Tampering | new JS/Python dependency set | high | mitigate | resolve with `--lockfile-only` / `uv lock`, Liam reviews new names in Task 2 before Task 3 installs with `--frozen-lockfile` / `--frozen` | closed |
| T-02-04 | Elevation of privilege | package install scripts | medium | mitigate | `allowBuilds` stays limited to esbuild; any other build script stops Task 1 | closed |
| T-02-05 | Spoofing | write endpoints (CSRF / DNS rebinding) | high | mitigate | TrustedHostMiddleware 127.0.0.1/localhost; Origin guard 403 for foreign Origin on non-GET; CORS only http://localhost:3000; tests in test_api.py | closed |
| T-02-06 | Tampering | POST /lessons url → yt-dlp | high | mitigate | `parse_youtube_url` allow-list; yt-dlp only receives `canonical_watch_url(videoId)` (unchanged) | closed |
| T-02-07 | Information disclosure | lesson.json error.message, ApiError bodies | medium | mitigate | StepError fixed Vietnamese messages; unexpected errors logged server-side, generic text stored; validation errors return fixed text | closed |
| T-02-08 | Denial of service | POST /lessons flood | low | accept | single local user; model steps serialized by one worker, downloads capped at 2 slots | closed |
| T-02-09 | Tampering | concurrent lesson.json writes | medium | mitigate | atomic writes (`write_json_atomic`), per-lesson lock in store.update_lesson, retry only from failed | closed |
| T-02-10 | Tampering (XSS) | rendering API strings | medium | mitigate | every response Zod-parsed; text rendered as React children only (no raw HTML injection APIs) | closed |
| T-02-11 | Spoofing | API base URL | low | accept | `NEXT_PUBLIC_API_URL` defaults to 127.0.0.1:8000; local single-user app | closed |
| T-02-12 | Tampering | shadcn CLI generated code / deps | medium | mitigate | pinned `shadcn@4.21.3` (reviewed in 02-02); lockfile diff check — any unapproved package name stops the task | closed |
| T-02-13 | Tampering | shortcut handling | low | mitigate | `shouldHandleShortcut` ignores input/textarea/select/combobox/listbox/contenteditable/dialog and modifier keys; tested | closed |
| T-02-14 | Tampering | db.py queries | high | mitigate | only `?` parameters; lesson ids validated with ULID_RE before any query | closed |
| T-02-15 | Tampering | app.db / eval_clips / tmp / stems paths | high | mitigate | helpers go through `_check_id` + `_contained`; tests for traversal, bad ids, inverted ranges | closed |
| T-02-16 | Denial of service | corrupt lesson.json in the scan | low | mitigate | iter_lessons skips invalid files with a log line; list never 500s (test) | closed |
| T-02-17 | Tampering / Info disclosure | GET …/video | high | mitigate | videoId read only from lesson.json; `video_asset_path` regex + `_contained`; only ready lessons; tests for bad ids | closed |
| T-02-18 | Spoofing (SSRF) | GET /videos/preview | high | mitigate | `parse_youtube_url` allow-list + `is_channel_url` before yt-dlp; yt-dlp receives only `canonical_watch_url(videoId)` | closed |
| T-02-19 | Denial of service | reload / transcode | low | mitigate | per-video lock; ffprobe/ffmpeg timeouts; argv lists, no shell | closed |
| T-02-20 | Information disclosure | preview / reload errors | medium | mitigate | fixed Vietnamese messages; yt-dlp exception text never returned (test) | closed |
| T-02-21 | Tampering (XSS / mixed content) | LessonCard thumbnail + title | low | mitigate | title rendered as text; `<img>` only for `https://` thumbnail URLs, else placeholder | closed |
| T-02-22 | Information disclosure | error banners | low | mitigate | only ApiError messages (fixed Vietnamese text from the backend) are displayed | closed |
| T-02-23 | Tampering (XSS) | TranscriptList / sentence text | low | mitigate | text rendered as React children only; responses Zod-parsed in lib/api.ts | closed |
| T-02-24 | Spoofing | video source | low | mitigate | `<video src>` built only by `lessonVideoUrl(id)` against API_BASE; id from the route, encoded | closed |
| T-02-25 | Information disclosure (SSRF/LFI) | ffmpeg on uploads | high | mitigate | magic-byte sniff + explicit `-f` demuxer whitelist, argv list, no shell; m3u8 test proves ffmpeg never runs | closed |
| T-02-26 | Denial of service | upload size / length | medium | mitigate | content-length + streaming cap 10 MB, `-t 61` + 60 s check, ffmpeg timeout 30 s | closed |
| T-02-27 | Information disclosure (privacy) | recordings on disk | high | mitigate | private mkdtemp under DATA_DIR/tmp, rmtree in finally on every path; eval clips only on explicit flag (REC-04) | closed |
| T-02-28 | Tampering | eval clip path | medium | mitigate | filename from validated ULID/int values only; `eval_clips_dir()` contained in DATA_DIR | closed |
| T-02-29 | Spoofing (CSRF) | multipart POST is a CORS simple request | high | mitigate | Origin guard + TrustedHost from 02-03 apply to these routes | closed |
| T-02-30 | Tampering | .env write | high | mitigate | KEY_RE rejects newline / `=` / whitespace before any write; `dotenv.set_key` (temp file + replace), chmod 600; written only after OpenAI returns 200 | closed |
| T-02-31 | Information disclosure | API key | high | mitigate | never returned (hasKey + maskedKey only), never logged or put in exception text; tests assert absence in responses and logs | closed |
| T-02-32 | Tampering | dataDir setting | low | mitigate | absolute + existing + directory + writable; no file moves (D-12); local single user | closed |
| T-02-33 | Tampering | settings.json content | low | mitigate | parsed through the AppSettings contract; invalid file → defaults | closed |
| T-02-34 | Denial of service | warm-up memory on 8 GB | medium | mitigate | one model at a time under model_gate, released after one inference (D-18) | closed |
| T-02-35 | Tampering | stems cache path | medium | mitigate | `stems_dir` validates videoId and integer ms bounds and checks containment (02-06) | closed |
| T-02-36 | Tampering | rmtree of seg/ | medium | mitigate | path from `lesson_dir(lesson_id)` (validated ULID) + "seg"; never from input strings | closed |
| T-02-37 | Tampering | URL input | low | mitigate | sent URL-encoded via URLSearchParams; server allow-list (02-07) is the trust boundary; no client-side fetch of the URL itself | closed |
| T-02-38 | Denial of service | preview requests while typing | low | mitigate | 400 ms debounce; TanStack Query dedupes identical URLs | closed |
| T-02-39 | Information disclosure (privacy) | recordings in the browser | medium | mitigate | blobs only in machine context for the session; object URLs revoked; no browser storage (grep check) | closed |
| T-02-40 | Information disclosure | open microphone after leaving S3 | medium | mitigate | actor cleanup stops tracks and closes AudioContext on every exit, StrictMode-safe | closed |
| T-02-41 | Tampering | localStorage mic device id | low | accept | only selects an input device among those the browser exposes | closed |
| T-02-42 | Tampering | segment text | low | mitigate | NFC + trim + 500 code-point limit; stored as JSON string; rendered as text in the UI; treated as data in the translate prompt (02-16) | closed |
| T-02-43 | Denial of service | repeated extend-end | low | mitigate | 3000 ms cap; single model gate with 150 s timeout → 503 | closed |
| T-02-44 | Tampering (prompt injection) | translation prompt | medium | mitigate | text inside delimiters declared as data; structured output {translation} only; no tools; length-capped, validated with pydantic; rendered as plain text in the UI | closed |
| T-02-45 | Information disclosure | API key / upstream errors | high | mitigate | key only in the Authorization header; never logged; fixed Vietnamese error messages; tests check responses and logs | closed |
| T-02-46 | Denial of service (cost) | repeated translate calls | low | mitigate | per-sentence cache in lesson.json; one sentence per call; 30 s timeout | closed |
| T-02-47 | Information disclosure | key in the S8 field | medium | mitigate | password input, component state only, cleared after success; never stored client-side or logged; backend returns only maskedKey | closed |
| T-02-48 | Information disclosure | open microphone after Thử micro | low | mitigate | mic closed after 3 s or on unmount | closed |
| T-02-49 | Tampering (XSS) | translation and edited text rendering | medium | mitigate | rendered as React text only; responses Zod-parsed (Segment) in lib/api.ts | closed |
| T-02-50 | Denial of service (cost) | repeated translate clicks | low | mitigate | one mutation per sentence while pending; backend caches results (02-16) | closed |
| T-02-51 | Tampering | smoke_jobs writing into Liam's real data/config | medium | mitigate | DATA_DIR, SHADOWENGLAB_CONFIG_DIR and SHADOWENGLAB_ENV_FILE point to temp paths set before importing the service; temp dir removed at exit; server bound to 127.0.0.1 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-02-08 | single local user; model steps serialized by one worker, downloads capped at 2 slots (rationale in the owning PLAN threat_model) | plan-phase (Liam-approved plan set) | 2026-10-06 |
| AR-02 | T-02-11 | `NEXT_PUBLIC_API_URL` defaults to 127.0.0.1:8000; local single-user app (rationale in the owning PLAN threat_model) | plan-phase (Liam-approved plan set) | 2026-10-06 |
| AR-03 | T-02-41 | only selects an input device among those the browser exposes (rationale in the owning PLAN threat_model) | plan-phase (Liam-approved plan set) | 2026-10-06 |

*Accepted risks do not resurface in future audit runs.*

---

## Non-blocking Observations (auditor, 2026-10-08)

1. `lesson/audio_io.py` `extract_audio` runs ffmpeg without a timeout (Phase 1 code, T-01-15 scope).
2. `GET /lessons`: a schema-valid but tampered `lesson.json` with a non-ULID `id` would raise `InvalidIdError` and 500 the list (`iter_lessons` skips only schema-invalid files). Needs local write access to DATA_DIR — robustness gap next to T-02-16.
3. T-02-22 residual: a few toasts show a generic `Error.message`, which after `lib/api.ts` normalisation can only be a ZodError on contract drift (schema field names, no secrets/paths).
4. No test asserts the exact argument yt-dlp receives (T-02-06/18) or the smoke-script isolation (T-02-51); the mitigations are present in code.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-08 | 52 | 52 | 0 | gsd-security-auditor (ASVS L1, block_on high; pytest 489 + vitest 172 security-relevant runs green) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-08
