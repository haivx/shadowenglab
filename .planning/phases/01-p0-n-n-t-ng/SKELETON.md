# Walking Skeleton — ShadowEngLab

**Phase:** 1 (P0 · Nền tảng)
**Generated:** 2026-10-06

## Capability Proven End-to-End

> Liam chạy `make smoke` với một link YouTube và nhận `DATA_DIR/lessons/{ulid}/lesson.json` hợp lệ theo contract `Lesson` (Zod → JSON Schema → pydantic sinh tự động), sau đó `GET http://127.0.0.1:8000/lessons/{ulid}` trả lại đúng bài đó dạng camelCase; `make dev` chạy song song FastAPI và khung Next.js.

Đường đi của skeleton (mỗi tầng một lát mỏng nhưng thật, không prototype):

```
packages/contracts (Zod, .meta({id}))
  └─ scripts/contracts_gen.sh ─► schema/contracts.schema.json (commit) ─► services/audio/src/audio_service/contracts_gen.py (commit, sinh tự động)
       └─ lesson/pipeline.py (yt-dlp → ffmpeg → Demucs → mlx-whisper → split_sentences → F0/energy/PPG)
            └─ write_contract_json ─► DATA_DIR/lessons/{ulid}/lesson.json (+ seg/{index:04d}.npz)
                 └─ FastAPI GET /lessons/{id} (response_model=Lesson, exclude_unset) ─► camelCase JSON
apps/web (Next 14) ─ import @shadowenglab/contracts (transpilePackages) ─ next build
make dev = FastAPI 127.0.0.1:8000 + Next.js localhost:3000
```

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Contract (nguồn sự thật) | Zod v4 trong `packages/contracts/src/*.ts`; mọi object có `.meta({ id })`; `z.toJSONSchema(..., { io: "input" })` ra một bundle `schema/contracts.schema.json` (commit) | D-18/D-19; id ổn định giữ tên class pydantic ổn định; Liam review diff schema tại ranh giới |
| Kiểu Python | `datamodel-code-generator` (pin 0.83.0) sinh `audio_service/contracts_gen.py` (pydantic v2, alias camelCase, `populate_by_name`), commit; `make test` fail nếu lệch | D-20/D-21; không viết tay kiểu trùng lặp |
| Serialize contract | Một helper `dump_contract` = `model_dump(mode="json", by_alias=True, exclude_unset=True)`; FastAPI `response_model_exclude_unset=True`; không bao giờ truyền `None` cho field optional | Pitfall 5: giữ `null` của field nullable, bỏ field optional vắng mặt |
| Framework web | Next.js 14.2.35 App Router, TS strict (~5.9.3), package contracts dạng source-only qua `transpilePackages` | CLAUDE.md khoá Next 14; không có bước build cho contracts |
| Backend | FastAPI + uvicorn, chỉ bind `127.0.0.1:8000`, CORS chỉ `http://localhost:3000`; Python 3.11 quản lý bằng uv (`uv_build`, src layout `services/audio/src/audio_service`) | ADR 0001; app local một người dùng |
| Data layer | File system dưới `DATA_DIR` theo D-08: `videos/{videoId}/…` (cache dùng chung giữa các bài), `lessons/{lessonId}/lesson.json` (ghi atomic tmp + `os.replace`), `seg/{index:04d}.npz` (feature bản gốc, ngoài contract) | D-06/D-07/D-08; trạng thái job nằm trong `Lesson`, card S1 ở Phase 2 chỉ cần poll `lesson.json` |
| Auth | Không có (local, một người dùng); API chỉ nghe localhost | product.md §5; app eval (Supabase magic link) để Phase 6 |
| Deployment target | Local: `make setup`, `make dev`, `make smoke`; app eval lên Vercel để Phase 6 | Local-first, chi phí ~$0 |
| ML runtime | Demucs `htdemucs` (MPS, `shifts=0`), mlx-whisper `whisper-large-v3-turbo` (`language="en"`), wav2vec2 `facebook/wav2vec2-lv-60-espeak-cv-ft` (MPS, fallback CPU), parselmouth; model trong HF cache; nạp tuần tự và giải phóng giữa các bước (máy 8 GB) | D-22/D-23/D-24; đo được 133 s compute cho 300 s audio |
| Directory layout | Monorepo theo CLAUDE.md: `apps/web`, `apps/eval`, `packages/contracts`, `services/audio/{lesson,scoring,rules}`, `scripts/`, `eval/` | CLAUDE.md "Cấu trúc repo" |
| Toolchain | pnpm workspace + uv; ESLint 9 flat (typescript-eslint strict, không plugin Next), Prettier, ruff, vitest, pytest; Makefile tương thích GNU Make 3.81 | RESEARCH Pitfalls 1–3, 13, 14; phiên bản Node/pnpm theo quyết định 01-01 |

## Stack Touched in Phase 1

- [x] Project scaffold (framework, build, lint, test runner) — 01-01 (manifest + lockfile), 01-07 (khung Next), 01-08 (Makefile, lint, test)
- [x] Routing — `GET /health`, `GET /lessons/{id}` (01-02)
- [x] Data layer — ghi thật `lesson.json` + `.npz` (01-04 `write_contract_json`, 01-06 pipeline) và đọc thật qua FastAPI (01-02)
- [ ] UI — phần tử tương tác gắn API: **ngoài phạm vi P0 theo CONTEXT** ("Không có UI nào được dựng trong phase này, chỉ khung Next.js rỗng"); màn đầu tiên (S1/S2/S3) dựng ở Phase 2
- [x] Deployment — chạy local đầy đủ bằng lệnh có tài liệu: `make dev` (web + API), `make smoke` (pipeline), `make test`

## Out of Scope (Deferred to Later Slices)

- Mọi màn hình và component UI, Tailwind/shadcn/TanStack Query/Recharts/XState (Phase 2 trở đi, bám `docs/design/`)
- SQLite, job runner nền, tạo 2 bài song song, chọn đoạn > 6 phút bằng thanh kéo (Phase 2: LES-02, LES-03)
- Chấm điểm: Lớp B ngữ điệu + rule Lớp C (Phase 3), Lớp A PPG + DTW (Phase 5); công thức gộp `scores.*` (Deferred trong CONTEXT)
- Gợi ý LLM, TTS (Phase 7/8); app eval, Supabase, `export_clips.py` (Phase 6); `eval/analyze.py` thật (Phase 4, `make eval` chỉ là stub ở P0)
- Nguồn bản dịch `Segment.translation` (Discuss P1); ngưỡng `nonVocalRatio` chính thức (P1/P5)

## Subsequent Slice Plan

Mỗi phase sau thêm một lát dọc lên skeleton này mà không đổi các quyết định kiến trúc ở trên:

- Phase 2: Liam dán link ở S2, job nền ghi `lesson.json` theo trạng thái, S1 poll card; trình phát XState + ghi âm WAV 16 kHz
- Phase 3: `POST /scoring/...` trả `ScoreResult` (Lớp B + rule Lớp C template), UI kết quả ngữ điệu
- Phase 4: `make eval` thật (`eval/analyze.py` → `eval/report.md`), held-out 30%
- Phase 5: Lớp A (PPG + DTW, `ref_unclear`), `ScoredSentence`/`PhonemeDiff`
- Phase 6: `apps/eval` + Supabase + `export_clips.py` theo `ClipManifest`/`Label`
- Phase 7: hàng ôn, tổng kết buổi, dashboard, thư viện có nhãn
- Phase 8: logistic điểm %, gợi ý LLM, README portfolio
