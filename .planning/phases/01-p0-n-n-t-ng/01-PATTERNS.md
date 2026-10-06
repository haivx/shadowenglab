# Phase 1: P0 Nền tảng - Pattern Map

**Mapped:** 2026-10-06
**Files analyzed:** ~45 (new/modified)
**Analogs found:** 4 doc-level / 45 (greenfield: no code analog exists)

Tracked non-GSD files are only docs, README stubs, `.gitignore`, `.env.example`. All code excerpts come from `01-RESEARCH.md` (executed on this machine), not from the repo. Analog paths below were verified with `git ls-files`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `pnpm-workspace.yaml`, root `package.json`, `tsconfig.base.json` | config | n/a | RESEARCH Pitfall 1 | no code analog |
| `eslint.config.mjs`, `.prettierrc`, `.prettierignore`, ruff config | config | n/a | RESEARCH Code Example 7 | no code analog |
| `apps/web/*`, `apps/eval/*` (Next 14 shells) | component/shell | request-response | `apps/web/README.md`, `apps/eval/README.md` (role only) | doc only |
| `packages/contracts/src/*.ts` (+ `*.test.ts`) | model | transform | `packages/contracts/README.md` (type list) + RESEARCH D-04..D-17 | doc only |
| `packages/contracts/src/generate.ts`, `cli-parse.ts` | utility | transform | RESEARCH Code Example 1 | none |
| `packages/contracts/fixtures/*.json`, `schema/contracts.schema.json` | test fixture / generated | transform | none | none |
| `services/audio/pyproject.toml`, `uv.lock`, `.python-version` | config | n/a | ADR 0001 (uv) | doc only |
| `services/audio/src/audio_service/contracts_gen.py` | model (generated) | transform | RESEARCH Code Example 2 | none |
| `.../main.py`, `routers/{health,lesson,scoring}.py` | controller | request-response | RESEARCH Pattern 6 + Example 6 | none |
| `.../config.py`, `paths.py` | config/utility | file-I/O | `.env.example` (DATA_DIR) + D-08 paths | partial |
| `.../lesson/{download,audio_io,separate,transcribe,segment,features,quality,pipeline,timing}.py` | service | batch / file-I/O | RESEARCH Pattern 2/3 + Example 4; dir layout from `services/audio/README.md` | doc only |
| `.../scoring/__init__.py`, `rules/__init__.py` | placeholder | n/a | `services/audio/README.md` | doc only |
| `.../setup_models.py` | utility | batch | RESEARCH Pattern 4 | none |
| `services/audio/tests/*` | test | request-response / transform | RESEARCH Example 3 | none |
| `Makefile` | config | n/a | RESEARCH Example 5 | none |
| `scripts/{smoke_lesson.py,check_deps.sh,contracts_check.sh}` | utility | batch | `scripts/README.md` (names/purpose) + RESEARCH Examples 2/4 | doc only |
| `docs/decisions/0003-<slug>.md` | doc (ADR) | n/a | `docs/decisions/0001-uv-va-xstate.md`, `0002-dung-gsd.md` | exact |
| `docs/product.md` (mục 3-4 update), `CLAUDE.md` Lệnh section | doc | n/a | existing sections | exact (edit in place) |
| `.env.example`, `.gitignore` (modify) | config | n/a | themselves | exact |

## Pattern Assignments

### `docs/decisions/0003-<slug>.md` (ADR)
**Analog:** `docs/decisions/0001-uv-va-xstate.md`, `0002-dung-gsd.md`. Vietnamese, same skeleton:
```markdown
# 0003 · <tiêu đề>

Ngày: 2026-10-NN · Trạng thái: Chấp nhận · Người quyết: Liam

## Bối cảnh
## Quyết định        (numbered list; 0002 also uses a "Phân chia nguồn sự thật" table)
## Lý do
## Hệ quả            (0002: "Hệ quả và rủi ro")
```
Content to record (per D-27 and RESEARCH Open Questions 5-9): contract/toolchain/model decisions, generated explicit `Field(alias=...)` instead of `alias_generator=to_camel`, single bundle schema, `Word.i` segment-local, Node >= 22.13, `trustPolicy: off`, `shifts=0` for Demucs.

### `.env.example` / `config.py` / `paths.py`
**Analog:** `.env.example` (`DATA_DIR=~/shadowenglab-data`, literal `~`). Use `Path(settings.data_dir).expanduser().resolve()` and read `.env` from the repo root (Pitfall 9). Path helpers follow D-08:
`DATA_DIR/videos/{videoId}/{video.mp4,audio.wav,vocals.wav,no_vocals.wav}`, `DATA_DIR/lessons/{lessonId}/lesson.json`, `.../seg/{index:04d}.npz`. No new env vars needed for P0.

### `.gitignore` (modify)
Already ignores `.env*` (except example), `node_modules/`, `.next/`, `.venv/`, `data/`, `models/`, `*.wav|mp3|mp4...`, `eval/clips/`, `eval/labels.jsonl`. Do not duplicate; only add if needed (e.g. `.ruff_cache/` is already present). Do NOT ignore `schema/*.json` or `contracts_gen.py` (they are committed).

### `packages/contracts/src/*.ts`
**No code analog.** Follow: `packages/contracts/README.md` (types: Segment, Lesson, ScoreResult, IssueCode, ClipManifest, Label), RESEARCH D-04..D-17 for shapes, Pattern 1 rules: every object/enum ends with `.meta({ id: "Name" })` (nested too), `z.discriminatedUnion('code', ...)` for issues, `createdAt: z.string()` (not `z.iso.datetime`), `.nullable()` for `scores.sound`, `.optional()` for absent fields, `gold: z.enum([...]).default("none")`. Package `"type": "module"`, `"main"/"types": "./src/index.ts"`.

### `packages/contracts/src/generate.ts`
**Source:** RESEARCH Code Example 1: `z.toJSONSchema(z.object(all), { io: "input" })`, write only `{ $schema, $defs }` to `schema/contracts.schema.json`; output dir via `process.argv[2]` so the drift gate can write to a temp dir.

### `services/audio/.../routers/*.py`, `main.py`
**Source:** RESEARCH Example 6 and Pattern 6: `APIRouter(prefix="/lessons")`, ULID regex 404, `response_model=Lesson, response_model_exclude_unset=True`, CORS only `http://localhost:3000`, uvicorn on `127.0.0.1:8000`; `scoring` router empty. `/health` returns a Python-only model.

### `services/audio/.../lesson/*.py`
**Source:** RESEARCH Pattern 2, 3 and Example 4 (StepTimer, Demucs `Separator(device="mps", shifts=0)`, mlx-whisper `language="en", condition_on_previous_text=False`, parselmouth `to_pitch_ac`, wav2vec2 `Wav2Vec2ForCTC` + FeatureExtractor). Rules from CLAUDE.md: DSP functions pure (array in, array out), IO only in `audio_io.py`/`pipeline.py`; atomic `lesson.json` writes (tmp + `os.replace`); `dump_contract()` = `model_dump(mode="json", by_alias=True, exclude_unset=True)`; NaN to None; cast numpy scalars to float. `segment.py` per the "Sentence splitting spec" with TDD on synthetic word lists.

### `services/audio/tests/test_contracts_roundtrip.py`
**Source:** RESEARCH Example 3 (Python-driven; shells to `pnpm --filter @shadowenglab/contracts exec tsx src/cli-parse.ts`; Draft202012Validator; pydantic dump with `exclude_unset=True`). Fixtures named `<TypeName>.<case>.json`.

### `Makefile`
**Source:** RESEARCH Example 5 (GNU Make 3.81 safe: `dev:` = `@$(MAKE) -j2 dev-api dev-web`; no `trap 'kill 0'`; `eval` is an echo stub exiting 0). Update the "Lệnh" section of `CLAUDE.md` if targets are added (`lint`, `smoke`, `contracts`, `contracts-check`).

### `scripts/check_deps.sh`, `setup_models.py`
**Source:** RESEARCH Pattern 4 and D-25: `command -v` for ffmpeg, espeak-ng, uv, pnpm, node >= 22.13; print `brew install ...` and `exit 1`; never install. Models via `huggingface_hub.snapshot_download` with the listed `allow_patterns`, Demucs via `demucs.pretrained.get_model("htdemucs")`.

### `scripts/smoke_lesson.py`
**Analog:** `scripts/README.md` ("`smoke_lesson.py <youtube_url>`: chạy pipeline tạo bài đầu–cuối, in thời gian từng bước"). Run via `uv run --project services/audio python scripts/smoke_lesson.py <url>`; prints timing table (Pattern 2).

### `apps/web`, `apps/eval` shells
**Analog (role only):** `apps/web/README.md`, `apps/eval/README.md`. Next 14.2.35, `next.config.mjs` = `{ transpilePackages: ["@shadowenglab/contracts"], eslint: { ignoreDuringBuilds: true } }`; ports 3000 / 3001; no UI/components in P0 (CLAUDE.md: UI follows `docs/design/` only). Package names `@shadowenglab/web`, `@shadowenglab/eval`, `@shadowenglab/contracts`.

## Shared Patterns

### Contract-first, one-way flow
Zod -> `schema/contracts.schema.json` (committed) -> `contracts_gen.py` (committed, header "GENERATED ... do not edit"). `make test` runs `contracts_check.sh` (regenerate to temp dir, `diff -u`, fail on drift). Never hand-edit generated files.

### Lint/format scope
Exclude generated files (`schema/`, `contracts_gen.py`), `.venv`, `.next`, `pnpm-lock.yaml`, `docs/design` from ruff, ESLint, Prettier (Pitfall 14).

### Language / doc convention
Docs, ADRs, and README stubs are in Vietnamese; code identifiers in English. TS strict, no `any` (ESLint `no-explicit-any: error`), Zod at I/O boundaries.

### Checkpoints required (from RESEARCH)
Lockfile review before first install; Liam picks the smoke video URL; Liam approves `nonVocalRatio` threshold, Node >= 22.13, `trustPolicy: off`; user runs `brew install ffmpeg espeak-ng`.

## No Analog Found

All code files (contracts, FastAPI, pipeline, Makefile, scripts, shells, lint config, tests). The repo has no source code yet. Planner should use RESEARCH.md Code Examples 1-7 and Patterns 1-6 as the reference implementation (executed in a scratch env on this machine).

## Metadata

**Analog search scope:** all `git ls-files` outside `.claude/`, `.planning/`; README stubs, ADRs, `.env.example`, `.gitignore`
**Files scanned:** ~50 tracked non-tooling files
**Pattern extraction date:** 2026-10-06
