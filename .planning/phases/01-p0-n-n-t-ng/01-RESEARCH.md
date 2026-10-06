# Phase 1: P0 · Nền tảng - Research

**Researched:** 2026-10-06
**Domain:** pnpm + uv monorepo; Zod v4 -> JSON Schema -> pydantic contract toolchain; Apple-Silicon audio pipeline (yt-dlp, Demucs, mlx-whisper, wav2vec2 PPG, parselmouth)
**Confidence:** HIGH for the toolchain and pipeline mechanics (every load-bearing claim below was executed on this machine, an M1 / 8 GB / macOS 26.6); MEDIUM for sentence-splitting thresholds and `nonVocalRatio` threshold (synthetic audio only, need real video).

Provenance tags used: `[VERIFIED: local run]` = I executed it in a scratch env this session (scratchpad, not the repo); `[CITED: url]` = official docs; `[ASSUMED]` = training knowledge / not verified. Package legitimacy: see the Package Legitimacy Audit (the seam returned SUS for everything because of its heuristics, not because of real signals).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

> Các contract dưới đây là **Liam đã chốt** trong Discuss. Planner/executor hiện thực đúng shape; đổi shape phải dừng lại và hỏi Liam. Tên field cụ thể trong `data` của từng `IssueCode` là đề xuất đã được duyệt ở mức shape — được phép tinh chỉnh tên khi Liam review PR contract, không được tự thêm/bớt mã lỗi.

#### Quy ước chung của contract
- **D-01:** Mốc thời gian (`start`, `end`) là **giây float**, tính từ đầu video gốc (khớp `video.currentTime` và Whisper). Độ dài khoảng lặng/khoảng đệm là **ms nguyên** (`refMs`, `userMs`, `padMs`, `endExtraMs`). — **Reversibility:** costly — mọi consumer (web, FastAPI, eval) phụ thuộc đơn vị.
- **D-02:** JSON qua ranh giới dùng **camelCase**. Phía Python đặt tên snake_case và map bằng pydantic `alias_generator=to_camel` (+ `populate_by_name=True`). `ref_ms`/`user_ms` trong bản nháp product.md đổi thành `refMs`/`userMs`. Bảng SQL Supabase (`clips`, `labels`) vẫn snake_case; map ở tầng app eval/export. — **Reversibility:** costly — đổi convention phải sửa toàn bộ contract và serializer.
- **D-03:** Điểm số trong contract là **float 0..1**. Web `scoreLevel()` nhân 100 rồi áp ngưỡng đỏ < 60, vàng 60–79, xanh ≥ 80. Sau P7, điểm qua logistic vẫn ở 0..1.

#### Contract Lesson / Segment / Word
- **D-04:** `Word` có đủ field ngay từ P0, phần chưa có dữ liệu để optional:
  ```ts
  Word { i: number; text: string; start: number; end: number; asrProb: number;
         ipa?: string;            // IPA nhận dạng từ audio mẫu (P1 điền)
         refConfidence?: number;  // confidence bản gốc từ PPG (P4 điền)
         prominence?: number }    // P0/P2 điền
  ```
- **D-05:** `Segment` giữ mốc gốc chưa đệm; đệm và "Mất chữ cuối?" lưu riêng:
  ```ts
  Segment { index: number; text: string; start: number; end: number;
            endExtraMs: number /* mặc định 0, +300 mỗi lần bấm "Mất chữ cuối?" */;
            words: Word[]; translation?: string }
  ```
  Trình phát và pipeline chấm tự tính đoạn thực tế = `[start − padMs, end + padMs + endExtraMs]`. Khi `endExtraMs` đổi, feature bản gốc của câu đó phải tính lại (việc của P1, P0 chỉ cần shape). Nguồn bản dịch quyết ở Discuss P1.
- **D-06:** Trạng thái job nằm **trong `Lesson`** (không có contract Job riêng). Card S1 chỉ cần poll `Lesson`:
  ```ts
  Lesson { id: string /* ulid */; videoId: string; title: string; durationSec: number;
           thumbnailUrl?: string; range: { start: number; end: number };
           padMs: number /* mặc định 150 */;
           status: 'queued'|'downloading'|'separating'|'transcribing'|'segmenting'|'analyzing'|'ready'|'failed';
           error?: { step: string; message: string };
           audioQuality?: { label: 'clean'|'music'; nonVocalRatio: number };
           segments: Segment[]; createdAt: string }
  ```
- **D-07:** **Nhiều bài trên một video:** `lessonId` là ulid riêng, kèm `videoId` + `range`. File tải về và output Demucs cache theo `videoId`, dùng chung giữa các bài.
- **D-08:** **Feature bản gốc (PPG, F0, energy) nằm ngoài contract**, lưu file theo quy ước đường dẫn, nội bộ Python:
  ```
  DATA_DIR/videos/{videoId}/video.mp4, audio.wav, vocals.wav, no_vocals.wav
  DATA_DIR/lessons/{lessonId}/lesson.json        # Lesson (contract)
  DATA_DIR/lessons/{lessonId}/seg/{index:04d}.npz # ppg, f0, energy, ...
  ```
  Contour bản gốc để vẽ biểu đồ được trả trong `ScoreResult`, không nằm trong `Lesson`. — **Reversibility:** reversible — chỉ là quy ước nội bộ `services/audio`.
- **D-09:** Nhãn chất lượng audio (`audioQuality`) tính lúc tạo bài từ tỉ lệ năng lượng `no_vocals` / `vocals` của Demucs (đã chốt ở roadmap, LES-06). Ngưỡng `clean|music` để Claude đề xuất trong P0/P1, Liam duyệt; Phase 5 bổ sung tỉ lệ `ref_unclear`.

#### Contract ScoreResult
- **D-10:** Thêm khối điểm tổng (bản nháp chưa có):
  ```ts
  scores: { overall: number;          // ScoreHero
            sound: number | null;     // Lớp A; null ở P2–P3 hoặc khi cả câu ref_unclear
            intonation: number;       // Lớp B
            rhythm: number }          // tốc độ + ngắt nghỉ
  ```
  Công thức gộp do P2 (intonation, rhythm, overall tạm) và P4 (sound, overall) quyết.
- **D-11:** `words[].status ∈ 'scored' | 'missing' | 'ref_unclear'` (bỏ `ok`/`unclear`/`diff` của bản nháp). Màu chip luôn suy từ `similarity` qua `scoreLevel()` — một nguồn sự thật cho ngưỡng màu. Giữ `similarity`, `start`, `end` (giây, trên audio người học), `refPhones?`, `userPhones?`, `text`.
- **D-12:** `issues` là **`z.discriminatedUnion('code', …)`**, `data` có schema riêng cho từng mã (7 mã của product.md mục 3 Lớp C):
  ```ts
  { code:'STRESS_MISMATCH', wordIndex, data:{ refWord, userWord } }
  { code:'EXTRA_PAUSE',     wordIndex, data:{ refMs, userMs } }
  { code:'FINAL_CONTOUR',              data:{ refSlope, userSlope } }
  { code:'FLAT_PITCH',                 data:{ pitchRange } }
  { code:'PITCH_DEVIATION', wordIndex, data:{ meanDiffSt } }
  { code:'PHONE',           wordIndex, data:{ refPhones, userPhones, similarity } }
  { code:'WORD_MISSING',    wordIndex, data:{} }
  ```
  `IssueCode` là enum export riêng. Thêm rule mới = sửa contract (đúng tinh thần contract-first). — **Reversibility:** costly — LLM prompt (P7), template (P2), analyze.py đều đọc shape này.
- **D-13:** `prosody.contour` cho cả câu trên một trục thời gian chuẩn hoá chung, frame không hữu thanh là `null`:
  ```ts
  contour: { ref: (number|null)[]; user: (number|null)[]; wordBounds: number[] /* index bắt đầu từ i */ }
  ```
  Phần còn lại của `prosody` giữ như bản nháp (`speed`, `pitchRange`, `melodyMatch` 0..1; `stress: {word, ref, user}[]`; `pauses: {afterWord, refMs, userMs}[]`).
- **D-14:** `tips: { text: string; issueRef: number /* index trong issues */; source: 'template'|'llm' }[]`. UI chỉ hiện nhãn "AI" khi `source==='llm'`.
- **D-15:** Metadata lượt chấm trong `ScoreResult`:
  ```ts
  lessonId: string; segmentIndex: number; attempt: number;
  mode: 'full' | 'intonationOnly';
  versions: { scorer: string; thresholds: string };
  timingMs: Record<string, number>   // thời gian từng bước, dùng kiểm ngân sách ≤ 3 s
  ```

#### Contract eval: Label, ClipManifest
- **D-16:** `Label`:
  ```ts
  Label { clipId: string; raterId: string; overall: 1|2|3|4|5;
          wordFlags: { wordIndex: number; flags: ('sound'|'stress'|'pitch'|'pause'|'speed')[] }[];
          finalContourMatch: boolean; unsure: boolean; note?: string;
          durationMs: number; createdAt: string }
  ```
  Chỉ lưu từ có cờ; `wordIndex` khớp `ClipManifest.words[].i`. Map sang cột SQL `word_flags jsonb` (snake_case ở DB).
- **D-17:** `ClipManifest` giữ nguyên bản nháp product.md mục 4 (`clipId, videoId, sentenceText, words[{i,text}], refAudio, userAudio, gold: 'none'|'identical'|'wrong' (default 'none'), systemScore?`).

#### Toolchain contract (Zod → JSON Schema → pydantic)
- **D-18:** Dùng **Zod v4**, sinh JSON Schema bằng `z.toJSONSchema()` có sẵn (draft 2020-12, discriminated union → `oneOf`). Đăng ký `id` cho từng kiểu để xuất `$defs` dùng chung. Không thêm `zod-to-json-schema`.
- **D-19:** JSON Schema sinh ra được **commit** ở `packages/contracts/schema/*.json` — Liam review diff schema ngay tại ranh giới; Python không cần Node để đọc.
- **D-20:** Pydantic **sinh tự động** bằng `datamodel-code-generator` từ JSON Schema ra file generated (ví dụ `services/audio/.../contracts_gen.py`, có header "generated — không sửa tay"), commit file đó. `make test` sinh lại cả JSON Schema lẫn pydantic và **fail nếu lệch** bản đã commit. Cấu hình generator phải ra pydantic v2 với alias camelCase (D-02).
- **D-21:** Test round-trip bắt buộc (tiêu chí hoàn thành #2): fixture `ScoreResult` (và các kiểu khác) parse bằng Zod → JSON → validate bằng JSON Schema → parse bằng pydantic → dump JSON (by_alias) → parse lại bằng Zod, bằng nhau.

#### Model, setup và ngân sách thời gian
- **D-22:** Transcribe bằng **`mlx-community/whisper-large-v3-turbo`** (mlx-whisper, `word_timestamps=True`). — **Reversibility:** reversible — nhưng đổi model cần Liam duyệt (CLAUDE.md).
- **D-23:** Tách giọng bằng **Demucs `htdemucs --two-stems=vocals`** chạy MPS. Stem `no_vocals` dùng luôn để tính `nonVocalRatio` (D-09).
- **D-24:** PPG bằng `facebook/wav2vec2-lv-60-espeak-cv-ft` (đã khoá ở product.md).
- **D-25:** `make setup` **chỉ kiểm tra và hướng dẫn** system deps (ffmpeg, espeak-ng, uv, pnpm, Node 20+): thiếu thì in lệnh `brew install …` và dừng với mã lỗi rõ ràng; không tự cài vào hệ thống. Tải model Python (Demucs, mlx-whisper, wav2vec2) có hiển thị tiến độ; kiểm tra parselmouth import được.
- **D-26:** Nếu smoke video 5 phút > 5 phút: Claude được tự tối ưu phần **không phải model** (thiết bị MPS/CPU, chia đoạn, chạy song song bước độc lập, batch PPG, cache). Vẫn vượt → dừng, báo bảng thời gian từng bước và đề xuất phương án; đổi model cần Liam duyệt.

#### Quy trình cho PR của phase này
- **D-27:** Contract chốt ở đây lệch so với bản nháp trong `docs/product.md` mục 3–4 (thêm `scores`, đổi `status` từ, `refMs`, union `issues`, `source` tip, metadata). Theo CLAUDE.md, PR contract phải **cập nhật `docs/product.md` mục 3–4** cho khớp và thêm **ADR `docs/decisions/0003-<slug>.md`** ghi các quyết định contract/toolchain/model ở trên.

### Claude's Discretion
- Thiết bị cho wav2vec2 (MPS với fallback CPU), batch size, cách chunk audio dài.
- Cấu trúc thư mục bên trong `services/audio` (`lesson/`, `scoring/`, `rules/` theo CLAUDE.md), tổ chức router FastAPI, tên file generated.
- Chi tiết heuristic tách câu trong khuôn khổ product.md (3–8 s, cắt > ~15 từ tại dấu phẩy/khoảng lặng, gộp < 1.5 s).
- Thư viện ulid, cấu hình ESLint/Prettier/ruff, phiên bản pnpm/Node cụ thể, cách `make dev` chạy song song hai server.
- Đề xuất ngưỡng `nonVocalRatio` cho nhãn `clean|music` (Liam duyệt).
- Nội dung `.env.example` (B4): kiểm lại, chỉ thêm biến thật sự cần cho P0.

### Deferred Ideas (OUT OF SCOPE)
- Nguồn bản dịch câu (`Segment.translation`) — Discuss P1.
- Công thức gộp `scores.overall`/`intonation`/`rhythm` — P2; `scores.sound` — P4.
- Ngưỡng `nonVocalRatio` chính thức và tinh chỉnh nhãn audio bằng tỉ lệ `ref_unclear` — P1/P5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FND-01 | pnpm workspace (`apps/web`, `apps/eval`, `packages/contracts`) + `services/audio` (uv), ESLint, Prettier, ruff, `.gitignore` | Standard Stack; Pitfalls 1-3 (pnpm 11 `trustPolicy`/`allowBuilds`, ESLint 9 vs Next plugin, TypeScript pin); Project Structure |
| FND-02 | Zod for `Segment`, `Lesson`, `ScoreResult`, `IssueCode`, `ClipManifest`, `Label` + JSON Schema | Pattern 1 (contract pipeline), Code Example "generate.ts"; Pitfalls 5-8 |
| FND-03 | pydantic matches JSON Schema; round-trip test for `ScoreResult` | Pattern 1, exact `datamodel-codegen` flags, Code Example round-trip test, Pitfall 5 (`exclude_unset`) |
| FND-04 | `make setup`: deps, model download with progress, check parselmouth/espeak-ng/ffmpeg | Pattern 4 (setup), Environment Availability, model sizes |
| FND-05 | `make dev` (Next.js + FastAPI), `make test` (pytest + vitest), `make eval` stub | Pattern 5 (Makefile), Pitfall 14 |
| FND-06 | FastAPI `/health`, routers `lesson`, `scoring`, response validated by contracts | Pattern 6 (FastAPI skeleton), verified alias/`exclude_unset` behaviour |
| FND-07 | `scripts/smoke_lesson.py`: yt-dlp -> Demucs -> mlx-whisper -> split -> F0+PPG -> `Lesson` JSON, per-step timing, 5 min video <= 5 min | Pattern 2/3, measured timing table, yt-dlp JS-runtime finding, segmenter spec |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

From `./CLAUDE.md` and `./.claude/CLAUDE.md` (treated as locked):
- Không tự đổi contract (`packages/contracts`), schema DB, ngưỡng chấm hay model. Cần đổi thì dừng và đề xuất.
- Mỗi phase đủ Discuss -> Plan -> Execute -> Verify -> Ship; PR nhỏ, review tại ranh giới (schema, state machine, output pipeline).
- Quyết định kỹ thuật mới hoặc lệch `docs/product.md` -> thêm ADR `docs/decisions/NNNN-<slug>.md` trong cùng PR; đổi spec sản phẩm: sửa `product.md` trước.
- TypeScript strict, không `any`; Zod ở mọi ranh giới I/O. Python: uv (`uv sync`, `uv run`), type hints, ruff, pytest; hàm xử lý audio thuần (input array -> output), không đọc file bên trong.
- Python 3.11 (`services/audio`); Python types must match `packages/contracts` (JSON Schema from Zod, validated with pydantic).
- Lệnh (verbatim from CLAUDE.md): `make setup`, `make dev`, `make test`, `make eval  # python eval/analyze.py → eval/report.md`. CLAUDE.md says "(Các lệnh được tạo trong P0; cập nhật mục này khi thay đổi.)" so the P0 PR must update the Lệnh section if commands change (e.g. add `make lint`, `make smoke`).
- Không commit audio eval, nhãn thô của người chấm, hay file `.env`; app phải chạy được khi thiếu API key.
- UI: no screens/components in P0 (only an empty Next.js shell for `make dev`).
- GSD workflow: all file edits go through a GSD command (the executor runs under `/gsd-execute-phase`).
- **Conflict to surface to Liam:** CLAUDE.md/D-25 say "Node 20+", but pnpm 11.9.0 declares `engines.node >=22.13` `[VERIFIED: npm view pnpm@11.9.0 engines]` and yt-dlp's JS-runtime path needs Node >= 22 `[CITED: github.com/yt-dlp/yt-dlp/wiki/EJS]`. Recommendation: document Node >= 22.13 (machine has v24.16.0). Version choice is in Claude's Discretion ("phiên bản pnpm/Node cụ thể") but the prerequisite text in CLAUDE.md/README/product.md must be updated in the same PR.

## Summary

Phase 1 is a walking skeleton with two independent risk axes: (a) the contract toolchain (Zod -> JSON Schema -> pydantic with camelCase aliases and a drift check), and (b) the audio pipeline performance on an M1 with only **8 GB RAM**. I built both in a scratch env (`uv` Python 3.11, `pnpm` workspace, Next 14.2.35) and ran them. Result: the whole pipeline fits the budget with a wide margin. Measured on 300 s of clean synthetic speech (macOS `say`): Demucs htdemucs on MPS with `shifts=0` 40 s, mlx-whisper large-v3-turbo with word timestamps 76 s (incl. model load), F0 0.5 s, wav2vec2 PPG on MPS 15 s (12 s extra cold load). Sum approx. 133 s of compute, peak RSS 2.3 GB (models run sequentially) `[VERIFIED: local run]`. Real video adds download + ffmpeg (est. 10-30 s) so the <= 5 min target (LES-05/FND-07) has roughly 2 min of headroom; it must be re-measured on a real interview video because synthetic TTS is easy for Whisper.

The contract toolchain works exactly as locked in D-18..D-21, with several non-obvious requirements discovered by running it: (1) give every object-shaped type its own `.meta({id})`, otherwise `datamodel-code-generator` invents unstable names (`Data`, `Data1`); (2) emit JSON Schema with `io: "input"` and strip the wrapper so `$defs` is the bundle; (3) pydantic round-trip must dump with `exclude_unset=True` (not `exclude_none`, not default) or `null` vs absent breaks Zod parsing; (4) keep `createdAt` a plain string (a `date-time` format makes pydantic reformat the timestamp and breaks equality); (5) `--strict-nullable --enum-field-as-literal all --skip-root-model --allow-population-by-field-name --snake-case-field` are the flags that produce clean pydantic v2 with `populate_by_name` and camelCase aliases.

Four environment traps will otherwise stall the executor: pnpm 11 fails the install on its default trust policy (postcss) and on unreviewed build scripts (esbuild) - fix with `trustPolicy: off` + `allowBuilds` in `pnpm-workspace.yaml`; ESLint 9 crashes with `@next/eslint-plugin-next@14` (`context.getAncestors is not a function`) - use typescript-eslint + react-hooks flat config without the Next plugin; TypeScript 7 exists but typescript-eslint peers `<6.1.0` - pin `~5.9.3`; yt-dlp needs a JS runtime for YouTube - install `yt-dlp[default,deno]` (works on Node-less machines; also verified with the `node` runtime). `ffmpeg` and `espeak-ng` are not installed on this machine (D-25: print `brew install` guidance only). Note espeak-ng is **not** needed at inference by wav2vec2 PPG (ran without it), only by `make setup`'s check per D-25.

**Primary recommendation:** Build tracer-first: Slice 0 = `uv` project + `smoke_lesson.py` running the real chain on a 60 s clip with plain dicts (the benchmark script in Code Examples is already proof it works); Slice 1 = contracts + generated pydantic + round-trip test; Slice 2 = bind smoke output to generated `Lesson`, FastAPI skeleton, Makefile, final 5-min measurement. Treat the human checkpoints (pick the real test video; Liam approves the `nonVocalRatio` threshold and the Node >= 22.13 prerequisite) as explicit tasks.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Contract definition (Zod) | `packages/contracts` (shared TS) | - | Single source of truth, D-18; consumed by web/eval as TS source |
| JSON Schema generation | `packages/contracts` (Node, tsx script) | - | Needs Zod runtime; output committed so Python needs no Node (D-19) |
| pydantic models | `services/audio` (Python, generated file) | - | Generated by datamodel-codegen from committed schema (D-20); never hand-edited |
| Drift check + round-trip test | Repo root `make test` (Python test shells to Node) | `packages/contracts` vitest | Only a cross-language test can prove TS <-> Python equality (D-21) |
| yt-dlp download, ffmpeg extract | `services/audio` `lesson/` (IO shell) | - | Impure IO kept at pipeline edge; core functions stay array in -> array out (CLAUDE.md) |
| Demucs / Whisper / wav2vec2 / parselmouth | `services/audio` `lesson/` (pure functions + model loader) | - | Local ML on Apple Silicon (MPS / MLX) |
| Sentence splitting | `services/audio` `lesson/segment.py` (pure, no models) | - | Pure function over word list; unit-testable without audio |
| Model download + system-dep check | `make setup` (bash check) + Python `setup_models` | - | D-25: check-and-guide only, no system installs |
| Job status / lesson persistence | `services/audio` filesystem (`lesson.json`) | FastAPI `lesson` router (read) | D-06/D-08: status lives in `Lesson`, files under `DATA_DIR` |
| HTTP API skeleton | FastAPI | - | `/health`, empty `lesson`/`scoring` routers, `response_model` = generated models |
| Web/Eval shells | Next.js 14 (`apps/web`, `apps/eval`) | - | Empty shells; web imports contracts to prove workspace wiring |

## Standard Stack

### Core
| Library | Version (verified 2026-10-06) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Node | >= 22.13 (machine: v24.16.0) | JS runtime | pnpm 11 engines `>=22.13` `[VERIFIED: npm view pnpm@11.9.0 engines]` |
| pnpm | 11.9.0 (`packageManager` field) | workspace manager | already on machine; see pnpm 11 pitfalls |
| uv | 0.12.10 (machine) | Python env | ADR 0001 |
| Python | 3.11 (`requires-python = ">=3.11,<3.12"`, `.python-version`) | audio service | CLAUDE.md; 3.11.16 already installed via uv |
| zod | 4.6.5 (pin exact) | contracts | D-18; `z.toJSONSchema` `[CITED: zod.dev via Context7 /colinhacks/zod]` |
| typescript | ~5.9.3 | TS | typescript-eslint peer `>=4.8.4 <6.1.0`; latest is 7.0.2 (incompatible) `[VERIFIED: npm view]` |
| next / react / react-dom | next 14.2.35, react ^18.3.1 | web + eval shells | CLAUDE.md locks Next 14; 14.2.35 is the last 14.x `[VERIFIED: npm view next@14]`; build verified on Node 24 |
| vitest | ^4.1.11 | TS tests | engines `^20 \|\| ^22 \|\| >=24`; vitest 5.0.3 is also out, 4.x chosen for conservative peers (not tested) |
| tsx | ^4.23 | run TS scripts (schema generation, zod parse CLI) | |
| eslint | ^9.39.5 (NOT 10, NOT 8) | lint | see Pitfall 2 |
| typescript-eslint | ^8.71 | lint | peers eslint ^8.57\|\|^9\|\|^10 |
| eslint-plugin-react-hooks, eslint-config-prettier, prettier | ^7 / ^10 / ^3.9 | lint/format | |
| fastapi + uvicorn | 0.142.2 / 0.54.0 | HTTP API | |
| pydantic (+ pydantic-settings) | 2.13.5 / 2.15.0 | models, `.env` settings | |
| yt-dlp[default,deno] | 2026.8.19 (+ yt-dlp-ejs 0.8.0, deno 2.9.7 from PyPI) | download | EJS needs a JS runtime; extras verified |
| demucs | 4.1.0 (2026-07-11) | vocal separation | has `demucs.api.Separator.separate_tensor`; uses `sphn` for decode (no torchaudio dep); weights from HF `adefossez/HTDemucs` (84 MB) |
| mlx-whisper | 0.4.3 | ASR + word timestamps | D-22; model `mlx-community/whisper-large-v3-turbo` (1.6 GB) |
| torch / transformers | 2.14.1 / 5.18.0 | wav2vec2 PPG | `Wav2Vec2ForCTC` + `Wav2Vec2FeatureExtractor` (no phonemizer needed) |
| praat-parselmouth | 0.4.7 | F0 | wheels import fine on py3.11 arm64 |
| numpy / scipy / soundfile | 2.4.6 / 1.17.1 / 0.14.0 (resolved by uv for py3.11; numpy 2.5 requires >=3.12) | arrays, resample, wav IO | |
| python-ulid | 4.0.1 | lesson ids | `from ulid import ULID; str(ULID())` `[VERIFIED: local run]` |
| datamodel-code-generator | 0.83.0 (dev dep) | pydantic generation | D-20 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ruff | ^0.16 (dev; also the formatter datamodel-codegen shells out to) | lint/format Python | must be in the same venv or codegen warns "Ruff executable was not found" |
| pytest, httpx | 9.1.1 / 0.28.1 (dev) | tests, FastAPI TestClient | |
| jsonschema | 4.26.0 (dev) | validate fixtures vs committed schema (Draft 2020-12) | round-trip test |
| ajv + ajv-formats | 8.20 / 3.0 (dev, contracts) | optional TS-side schema validation | vitest check that Zod parse == JSON Schema valid |
| huggingface-hub | 1.33 (transitive) | model download with tqdm progress | `snapshot_download` / `hf_hub_download` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `yt-dlp[deno]` (PyPI deno) | system Node >= 22 via `js_runtimes: {"node": {}}` | Verified both work; deno extra avoids a Node-version prerequisite. |
| ESLint 9 flat w/o Next plugin | ESLint 8.57 + `eslint-config-next@14` legacy | 8.57 is "no longer supported"; only Next-specific rules lost, irrelevant for empty shells; revisit when Next is upgraded |
| pnpm 11 | pnpm 10.34.6 | pnpm 10 avoids the two new defaults but is not what is on the machine; keep 11 with explicit settings |
| `Demucs` CLI `--two-stems=vocals` | `demucs.api.Separator` in-process + `no_vocals = sum(other stems)` | In-process keeps array-in/array-out and avoids a second ffmpeg encode; the CLI's two-stems is just the same 4-source inference with stems summed |

**Installation (illustrative; lockfiles are the source of truth):**
```bash
# repo root
pnpm add -D -w typescript@~5.9.3 eslint@^9.39.5 typescript-eslint prettier eslint-config-prettier eslint-plugin-react-hooks
pnpm add --filter @shadowenglab/contracts zod@4.6.5
pnpm add -D --filter @shadowenglab/contracts vitest@^4.1.11 tsx ajv ajv-formats
# services/audio
uv add "yt-dlp[default,deno]" demucs mlx-whisper transformers torch praat-parselmouth \
       numpy scipy soundfile python-ulid fastapi uvicorn pydantic pydantic-settings
uv add --dev pytest httpx jsonschema ruff datamodel-code-generator
```
**Version verification:** versions above were read from the PyPI JSON API and `npm view` on 2026-10-06 and then resolved/installed by uv and pnpm in a scratch workspace (`uv sync` resolved 111 packages; imports verified). `[VERIFIED: local run]`

## Package Legitimacy Audit

The seam (`gsd_run query package-legitimacy check`) returned **SUS for almost every package**, with reasons only `unknown-downloads` (PyPI download counts are not available to the seam), `too-new` (the seam looks at the latest release date, not package age), and `no-repository` (PyPI metadata for yt-dlp/numpy/scipy/deno omits a repo URL field). None returned SLOP. These are heuristic artifacts: every package below is a long-established, widely used library or an official component of one (e.g. `deno` and `yt-dlp-ejs` are yt-dlp's own declared extras `[VERIFIED: PyPI requires_dist of yt-dlp: 'yt-dlp-ejs==0.8.0; extra == "default"', 'deno>=2.6.6; extra == "deno"']`). All were installed and imported/executed successfully in this session. Because the seam rule says SUS requires a checkpoint, **add ONE consolidated `checkpoint:human-verify` task ("review the resolved lockfile diff: `uv.lock`, `pnpm-lock.yaml`, no unexpected names") before the first install**, rather than one per package.

| Package | Registry | Latest release | Source Repo | Seam verdict | Disposition |
|---------|----------|----------------|-------------|--------------|-------------|
| fastapi, uvicorn, pydantic, pydantic-settings, httpx, pytest, jsonschema, numpy, scipy, soundfile, huggingface-hub, transformers, torch, ruff | PyPI | 2024-12 to 2026-10 | mainstream | SUS (too-new / unknown-downloads) | Approved after lockfile checkpoint |
| yt-dlp, yt-dlp-ejs, deno | PyPI | 2026-08 / 2026-03 / 2026-09 | yt-dlp org extras | SUS (no-repository / too-new) | Approved: extras declared by yt-dlp itself |
| demucs | PyPI | 2026-07-11 | github.com/adefossez/demucs (PyPI Homepage) | SUS (unknown-downloads) | Approved; note maintainer fork of the original facebookresearch project |
| mlx-whisper | PyPI | 2025-08-29 | github.com/ml-explore/mlx-examples | SUS (unknown-downloads) | Approved |
| praat-parselmouth | PyPI | 2025-11-27 | github.com/YannickJadoul/Parselmouth | SUS (unknown-downloads) | Approved |
| python-ulid | PyPI | 2026-07-20 | - | SUS (unknown-downloads) | Approved (Claude's discretion; alternative: write 20 lines, but don't) |
| datamodel-code-generator | PyPI | 2026-09-24 | github.com/datamodel-code-generator/... | SUS (too-new) | Approved; dev-only; pin exact in `uv.lock` |
| zod, vitest, tsx, eslint, typescript-eslint, prettier, next, react, react-dom, @types/node, @types/react | npm | 2026-09/10 | official | SUS (too-new only; downloads 76M-548M/wk) | Approved |
| typescript, eslint-plugin-react-hooks, eslint-config-prettier, ajv, ajv-formats | npm | - | official | OK | Approved |

**Packages removed due to SLOP verdict:** none
**Packages flagged SUS:** all of the SUS rows above (single consolidated checkpoint recommended; see paragraph above)
**Postinstall:** only `esbuild@0.28.2` has a postinstall (`node install.js`, standard binary installer, pnpm 11 forces explicit `allowBuilds`). `[VERIFIED: local run, pnpm output]`

## Architecture Patterns

### System Architecture Diagram

```
 CONTRACT FLOW (build-time, enforced by `make test`)
 ───────────────────────────────────────────────────
 packages/contracts/src/*.ts  (Zod v4, every object has .meta({id}))
        │  tsx src/generate.ts  →  z.toJSONSchema(z.object({...all}), {io:"input"})  → strip wrapper
        ▼
 packages/contracts/schema/contracts.schema.json   (COMMITTED, Liam reviews diff)
        │  uv run datamodel-codegen (pinned flags, ruff-format)
        ▼
 services/audio/src/audio_service/contracts_gen.py  (COMMITTED, "do not edit")
        │
        ├─► FastAPI response_model=Lesson/ScoreResult (by alias, exclude_unset)
        └─► pipeline builds Lesson via generated models
 make test: regenerate to temp dir ─► diff -r vs committed ─► FAIL on drift
            pytest round-trip: fixture ─► Zod(parse) ─► JSON ─► jsonschema ─► pydantic ─► dump(by_alias, exclude_unset) ─► Zod(parse) ─► equal

 LESSON PIPELINE (runtime; smoke_lesson.py today, P2 job runner later)
 ─────────────────────────────────────────────────────────────────────
 YouTube URL
   │ validate (youtube.com/youtu.be only) → videoId  ^[A-Za-z0-9_-]{11}$
   ▼
 [downloading] yt-dlp (Python API, js_runtimes=deno) ─► DATA_DIR/videos/{videoId}/video.mp4  (cache hit → skip)
   ▼ ffmpeg (argv list) ─► audio.wav  (44.1 kHz stereo, for Demucs)
 [separating]  Demucs htdemucs, MPS, shifts=0 ─► vocals.wav, no_vocals.wav ; nonVocalRatio = E(no_vocals)/E(vocals) → audioQuality
   ▼ resample vocals → 16 kHz mono float32 (scipy resample_poly 160/441)
 [transcribing] mlx-whisper turbo, word_timestamps, language="en" ─► words[{text,start,end,probability}]
   ▼
 [segmenting]  split_sentences(words)  (PURE: 3–8 s, >15 words cut at comma/gap, merge <1.5 s) ─► Segment[]
   ▼
 [analyzing]   per segment, slice [start−pad, end+pad+endExtra]: F0 (parselmouth, 10 ms) + energy + PPG (wav2vec2, MPS→CPU)
               ─► DATA_DIR/lessons/{lessonId}/seg/{index:04d}.npz
   ▼
 [ready]  lesson.json (validated by generated Lesson)  + printed timing table
 (lesson.json is rewritten atomically at EVERY status transition → P2's S1 card polls it for free;
  any exception → status "failed" + error{step,message})
```

### Recommended Project Structure
```
shadowenglab/
├── pnpm-workspace.yaml        # packages + trustPolicy: off + allowBuilds (see Pitfall 1)
├── package.json               # private, packageManager pnpm@11.9.0, engines node >=22.13, scripts
├── eslint.config.mjs          # ESLint 9 flat (typescript-eslint strict + react-hooks + prettier)
├── .prettierrc / .prettierignore   # ignore pnpm-lock.yaml, .next, .venv, schema/, contracts_gen.py, docs/design
├── tsconfig.base.json
├── Makefile
├── apps/web/  apps/eval/      # Next 14.2.35 shells; transpilePackages: ["@shadowenglab/contracts"]; ports 3000 / 3001
├── packages/contracts/
│   ├── package.json           # "main"/"types": ./src/index.ts (source-only, no build step); scripts: test, gen
│   ├── src/{index.ts, common.ts, lesson.ts, score.ts, eval.ts, generate.ts, cli-parse.ts, *.test.ts}
│   ├── fixtures/*.json        # hand-written valid fixtures (ScoreResult, Lesson, Label, ClipManifest...)
│   └── schema/contracts.schema.json   # generated, committed
├── services/audio/
│   ├── pyproject.toml  uv.lock  .python-version (3.11)
│   ├── src/audio_service/
│   │   ├── main.py            # create_app(): FastAPI, CORS localhost:3000, routers
│   │   ├── config.py paths.py # pydantic-settings; D-08 path helpers; DATA_DIR.expanduser()
│   │   ├── contracts_gen.py   # GENERATED
│   │   ├── routers/{health,lesson,scoring}.py
│   │   ├── lesson/{download,audio_io,separate,transcribe,segment,features,quality,pipeline,timing}.py
│   │   ├── scoring/__init__.py  rules/__init__.py     # empty placeholders (CLAUDE.md layout)
│   │   └── setup_models.py    # python -m audio_service.setup_models
│   └── tests/                 # test_segment.py, test_contracts_roundtrip.py, test_health.py, test_paths.py ...
├── scripts/{smoke_lesson.py, check_deps.sh, contracts_check.sh}
└── eval/                      # untouched in P0 (make eval = stub)
```
Run the smoke script as `uv run --project services/audio python scripts/smoke_lesson.py <url>` (the script lives outside the uv project; add `make smoke URL=...`).

### Pattern 1: One-way contract pipeline with a drift gate
**What:** Zod is edited; two generators produce committed artifacts; a gate regenerates into a temp dir and `diff -r`s.
**When:** every contract change. Planner tasks: (a) Zod types, (b) `generate.ts`, (c) codegen script + flags, (d) `contracts_check`, (e) fixtures + round-trip.
**Rules proven by running it:**
- `z.toJSONSchema(z.object({Segment, Lesson, ...}), {io: "input"})` then keep only `{ $schema, $defs }`; every type with `.meta({ id })` becomes a `$defs` entry with `$ref` links. Do **not** pass `reused: "ref"` (creates `__schemaN` defs, ugly pydantic class names `FieldSchemaN`). `[VERIFIED: local run]`
- Give nested objects ids too (`StressMismatchData`, `TimeRange`, `AudioQuality`, `Contour`, ...) or the generator names them `Data`, `Data1`, `Err` (position-dependent, noisy diffs). `[VERIFIED: local run]`
- `z.discriminatedUnion` -> `oneOf` (docs: "discriminatedUnion ... emit oneOf") `[CITED: github.com/colinhacks/zod json-schema-processors.ts via Context7]`; pydantic gets `Issue = RootModel[A | B | C]` (smart union; fine because `code` literals differ).
- `z.union([z.literal(1),...5])` -> JSON Schema `anyOf` of consts -> pydantic `Literal[1, 2, 3, 4, 5]` OK. `z.record(z.string(), z.number())` -> `dict[str, float]`. `.int()` adds `±9007199254740991` bounds to every int (noise but harmless). `[VERIFIED: local run]`
- With `io: "input"`, `.default("none")` fields become optional with `default` in schema -> pydantic `gold: Literal[...] = "none"` (needs `--strict-nullable` else it becomes `| None`). `[VERIFIED: local run]`
- Codegen emits explicit `Field(alias="refMs")` per field + `populate_by_name=True` instead of `alias_generator=to_camel`. Behaviour is identical to D-02 (camelCase on the wire, snake_case attributes, accept both). Mention in PR/ADR so Liam can approve the literal deviation.

### Pattern 2: Step-timed pipeline with durable status
**What:** a `StepTimer` context manager records wall time per step; `pipeline.run(url)` writes `lesson.json` atomically (tmp file + `os.replace`) at each status change (`queued → downloading → separating → transcribing → segmenting → analyzing → ready`), and on exception writes `status="failed", error={step,message}`.
**Why:** FND-07 requires the timing table; D-06 puts job state in `Lesson`; P2 gets polling for free. Timing is printed (and may go to a sidecar `timing.json`); do NOT add a timing field to `Lesson` (contract is locked).
**Table to print:** download, extract_audio, demucs, whisper, segment, f0, ppg, write, total (+ audio duration, realtime factor, nonVocalRatio, #segments).

### Pattern 3: Pure audio functions + explicit model objects
`separate(wav2xN: np.ndarray, sr, separator) -> (vocals, no_vocals)`, `transcribe(audio16k, model_repo) -> list[Word]`, `extract_f0(audio16k, sr) -> np.ndarray`, `compute_ppg(audio16k, model, fe, device) -> np.ndarray (T, 392)`, `split_sentences(words) -> list[Segment]`. No function opens a file; `audio_io.py`/`pipeline.py` own all IO (CLAUDE.md rule). Models are loaded once by a small `Models` holder and freed (`del`, `gc.collect()`, `torch.mps.empty_cache()`) between stages because the machine has 8 GB.

### Pattern 4: `make setup` = check-and-guide, then idempotent download
1. `scripts/check_deps.sh`: for each of `ffmpeg`, `espeak-ng`, `uv`, `pnpm`, `node (>= 22.13)`: `command -v`; collect missing; print the exact `brew install ffmpeg espeak-ng` (and `brew install node` / pnpm / uv hints); `exit 1` with a distinct message. Never installs (D-25).
2. `pnpm install` (workspace) and `uv sync --project services/audio`.
3. `uv run --project services/audio python -m audio_service.setup_models`: `huggingface_hub.snapshot_download` for `mlx-community/whisper-large-v3-turbo` (1.6 GB), `facebook/wav2vec2-lv-60-espeak-cv-ft` with `allow_patterns` limited to `config.json, preprocessor_config.json, vocab.json, tokenizer_config.json, special_tokens_map.json, pytorch_model.bin` (1.26 GB), and Demucs via `demucs.pretrained.get_model("htdemucs")` (downloads `htdemucs.yaml` + `955717e8.safetensors` 84 MB from HF `adefossez/HTDemucs`). tqdm bars appear by default; re-running is a no-op. Then verify: `parselmouth.Sound(np.zeros(1600), 16000).to_pitch()` works, `ffmpeg -version` runs, `torch.backends.mps.is_available()` (warn only), print a status table. Models land in the HF cache (`~/.cache/huggingface`, outside the repo; `.gitignore` already excludes `models/`).
4. The setup is "clean machine" only if system deps exist; verify the criterion on this machine after `brew install ffmpeg espeak-ng` (both currently missing).

### Pattern 5: Makefile
`setup`, `dev`, `test`, `eval`, plus `lint`, `smoke`, `contracts` (regen), `contracts-check`. `dev` is `@$(MAKE) -j2 dev-api dev-web` (works on macOS's GNU Make 3.81, see Pitfall 13 and Code Examples). `eval` is `@echo "make eval: stub (implemented in Phase 4 / EVL-02)"` and exits 0; do not create `eval/analyze.py` yet.

### Pattern 6: FastAPI skeleton bound to generated models
`create_app()` with CORS for `http://localhost:3000` only; `GET /health -> {"status":"ok", ...}` (a tiny `Health` model in Python is fine, it is not a contract type; or add it to contracts if Liam prefers). `lesson` router: `GET /lessons/{lesson_id}` with `response_model=Lesson, response_model_exclude_unset=True` reading `DATA_DIR/lessons/{id}/lesson.json` (validate `lesson_id` as a ULID; 404 otherwise); `scoring` router: empty `APIRouter(prefix="/scoring")`. FastAPI serialises by alias (camelCase) by default and `exclude_unset` omits unset optionals `[VERIFIED: local run: {'i': 0, 'text': 'a', 'start': 0.0, 'end': 1.0, 'asrProb': 0.5}]`. Bind uvicorn to `127.0.0.1` only.

### Sentence splitting spec (pure function, TDD with synthetic word lists, no audio)
Input: whisper words `[{text,start,end,probability}]` (text carries punctuation, leading space; cast `np.float64` to `float`). Algorithm (initial thresholds are `[ASSUMED]`, tune on the real video; product.md fixes only 3–8 s, ~15 words, 1.5 s):
1. Cut after a word ending in `.?!` or when the gap to the next word >= 0.7 s.
2. For any chunk with duration > 8.0 s or > 15 words: choose the cut among (comma-ending words, gaps >= 0.25 s) that minimises `|left_dur − dur/2|` with both sides >= 1.5 s; if none, the largest gap; recurse.
3. Merge any chunk shorter than 1.5 s into the neighbour with the smaller gap if the merged duration stays <= ~9 s.
4. Emit `Segment(index, text, start=first.start, end=last.end, endExtraMs=0, words=[Word(i=<global index>, asrProb=probability)])`. `Word.i` = index within the segment or the lesson? D-04 does not say; `wordBounds` (D-13) says "index bắt đầu từ i", and `ClipManifest.words[].i` is per clip -> use **index within the segment, starting at 0** (flag in Open Questions for Liam).
Unit tests: punctuation split, long chunk split at comma, tiny fragment merge, no 0-length segments, monotonic times, all words preserved exactly once.

### Anti-Patterns to Avoid
- **Hand-editing `contracts_gen.py` or `schema/*.json`:** the drift gate will fail; change Zod.
- **`model_dump(exclude_none=True)` or plain `model_dump()` for contract output:** see Pitfall 5.
- **Calling `yt-dlp` via `subprocess` with a shell string:** use the Python API (`yt_dlp.YoutubeDL`) or argv lists.
- **Loading all three models at once on 8 GB:** sequence them and free memory between stages.
- **Reading files inside DSP functions** (CLAUDE.md rule) and **making F0/PPG part of `Lesson`** (D-08: files, not contract).
- **Using `reused: "ref"` or leaving objects without `id`** in Zod -> unstable pydantic names.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Zod -> JSON Schema | custom walker | `z.toJSONSchema` with `.meta({id})` (D-18) | handles unions, nullables, defaults, `$defs` |
| JSON Schema -> pydantic | hand-written mirror classes | `datamodel-code-generator` flags above (D-20) | drift-free, reviewable |
| Camel/snake mapping | custom serializer | generated `Field(alias=...)` + `populate_by_name` | verified round-trip |
| YouTube download / cipher solving | scraping or `pytube` | `yt-dlp[default,deno]` | EJS + JS runtime handled by yt-dlp |
| Demucs windowing/overlap-add | own chunking | `demucs.api.Separator` (`split=True`, `overlap=0.25`) | handles segments + MPS |
| Model download progress/caching | `requests` + progress bar | `huggingface_hub.snapshot_download` | resumable, tqdm, cache dedup |
| Pitch tracking | own autocorrelation | `parselmouth` `to_pitch_ac(time_step=0.01, ...)` | Praat algorithm; octave filtering is Phase 3 (PRO-01) |
| ULID | own generator | `python-ulid` | |
| Atomic JSON writes | direct `open(...,"w")` | write tmp + `os.replace` | S1 polls `lesson.json` while it is being rewritten |
| `.env` parsing | manual | `pydantic-settings` (+ `Path.expanduser()`) | see Pitfall 9 |
| Process supervision for `make dev` | bespoke runner | `$(MAKE) -j2 dev-api dev-web` (Make 3.81 has no `-O`) | no new dependency; verified |

**Key insight:** in this phase everything "clever" has an off-the-shelf piece; the real work is wiring, pinning flags, and the drift/round-trip gates.

## Common Pitfalls

### Pitfall 1: pnpm 11 install fails on defaults (trust policy + build scripts)
**What goes wrong:** `pnpm add vitest` fails with `ERR_PNPM_NO_MATCHING_VERSION ... postcss@^8.5.28 ... The latest release of postcss is "8.5.22"` (a newer postcss is filtered out by the default trust policy), then with that cleared fails with `ERR_PNPM_IGNORED_BUILDS Ignored build scripts: esbuild@0.28.2`. `[VERIFIED: local run]` (clearing `--config.trustPolicy=off` fixed the first; `strictDepBuilds` default is `true` in v11 `[CITED: pnpm.io/settings/build]`).
**How to avoid:** commit this `pnpm-workspace.yaml` (verified: install + vitest pass):
```yaml
packages:
  - apps/*
  - packages/*
trustPolicy: off
allowBuilds:
  esbuild: true
```
**Warning signs:** a clean-machine `make setup` that dies at `pnpm install`. Mention in the ADR (supply-chain default relaxed knowingly; lockfile committed).

### Pitfall 2: ESLint 9 + `@next/eslint-plugin-next@14` crash
`TypeError: context.getAncestors is not a function` from rule `@next/next/no-duplicate-head` `[VERIFIED: local run]`. Use ESLint 9 flat config with `typescript-eslint` strict + `eslint-plugin-react-hooks` + `eslint-config-prettier` only (verified clean on the Next shell), and set `eslint: { ignoreDuringBuilds: true }` in `next.config.mjs` (lint is run by `make lint`). Re-add the Next plugin when Next is upgraded. Alternative if Liam insists on Next rules: ESLint 8.57.1 + legacy config (unsupported release).

### Pitfall 3: TypeScript 7 / ESLint 10 are "latest"
`npm view typescript version` = 7.0.2, but typescript-eslint peers `typescript >=4.8.4 <6.1.0`. Pin `typescript@~5.9.3` and `eslint@^9.39.5` explicitly; `tsc -p apps/web --noEmit` and `next build` passed on 5.9.3 `[VERIFIED: local run]`.

### Pitfall 4: yt-dlp cannot fully extract YouTube without a JS runtime
yt-dlp's default runtime is Deno; Node is opt-in and needs >= 22 `[CITED: github.com/yt-dlp/yt-dlp/wiki/EJS]`. Install `yt-dlp[default,deno]` (puts `deno` 2.9.7 in the venv `bin`, so run the pipeline through `uv run` so PATH includes it). Verified `extract_info` on `jNQXAC9IVRw` with both `js_runtimes={'deno': {}}` and `{'node': {}}` `[VERIFIED: local run]`. `ffmpeg` is also required for merging/extraction (not installed here). YouTube changes break yt-dlp periodically (product.md risk): pin in `uv.lock`, document `uv lock --upgrade-package yt-dlp`.

### Pitfall 5: round-trip equality depends on how pydantic dumps
Verified on a `ScoreResult` fixture: `model_dump(mode="json", by_alias=True, exclude_unset=True)` equals the input; `exclude_none=True` drops `scores.sound: null` (Zod `.nullable()` is required -> parse fails); default dump emits `ipa: null` for absent optionals (Zod `.optional()` rejects `null`). `[VERIFIED: local run]` -> a single helper `dump_contract(model)` (`mode="json", by_alias=True, exclude_unset=True`) used by FastAPI (`response_model_exclude_unset=True`), pipeline writes and tests. When Python **constructs** models, never pass `None` for an optional field (omit it), else it counts as "set" and serialises `null`.

### Pitfall 6: NaN/inf in JSON
D-13 contour uses `null` for unvoiced frames; numpy `NaN` serialises to invalid JSON (`Out of range float values are not JSON compliant`). Convert `np.nan -> None` at the boundary (`[None if np.isnan(x) else float(x) for x in arr]`) and cast numpy scalars (`np.float64` from Whisper words) to Python floats before building models.

### Pitfall 7: timestamps as `date-time`
`z.iso.datetime()` -> pydantic `AwareDatetime` + a 600-char regex; pydantic re-serialises `…00.000Z` as `…00Z`, breaking equality. D-06/D-16 say `createdAt: string`: keep `z.string()` and produce `datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")` in Python (same shape as JS `toISOString()`).

### Pitfall 8: Zod 4 `io` mode and defaults
`io: "output"` marks defaulted fields required (and adds `additionalProperties: false`), so a Python reader would reject a manifest lacking `gold`. Use `io: "input"` for wire schemas (verified `gold` defaulting works).

### Pitfall 9: `DATA_DIR=~/shadowenglab-data`
`.env.example` has a literal `~`; dotenv/pydantic do not expand it (a directory named `~` would be created inside `services/audio`). Always `Path(settings.data_dir).expanduser().resolve()`; resolve `.env` from the repo root (pydantic-settings `env_file=<repo_root>/.env`, not CWD, since uv runs inside `services/audio`). `.env.example` needs no new vars for P0 (`OPENAI_API_KEY`, `AZURE_SPEECH_*`, `DATA_DIR` already exist; optionally add `API_PORT`/`WEB_PORT` only if used).

### Pitfall 10: 8 GB RAM and the Demucs/Whisper/wav2vec2 stack
Measured peak RSS 2.3 GB when sequential `[VERIFIED: local run: maximum resident set size 2337767424]`. Do not keep Demucs + Whisper (1.6 GB) + wav2vec2 (1.26 GB) resident together plus a running Next dev server without checking; free between stages. Demucs `Separator` defaults to `shifts=1` in the CLI (2x cost) — use `shifts=0` (not a model change; D-26 allows knob tuning but record it in the ADR). MPS works for Demucs and wav2vec2; PPG: MPS 14.8 s vs CPU 44.5 s for 300 s audio, so MPS with CPU fallback.

### Pitfall 11: wav2vec2 "needs espeak/phonemizer" (it does not, for PPG)
`Wav2Vec2FeatureExtractor.from_pretrained` + `Wav2Vec2ForCTC` produce logits (392 classes, 50 fps) with no phonemizer or espeak-ng installed `[VERIFIED: local run; espeak-ng absent on this machine]`. Do not instantiate `Wav2Vec2Processor`/phoneme tokenizer in P0. espeak-ng stays in `make setup` checks per D-25 (later phases may need it). Use per-segment inference with padding `[start−pad, end+pad+endExtra]` and `torch.inference_mode()`; softmax to get the PPG.

### Pitfall 12: Whisper settings
Pass `language="en"` (skip detection) and `condition_on_previous_text=False` (reduces repetition/hallucination loops); words carry `probability` -> `asrProb`. Timing (76 s/300 s) was measured on synthetic speech; real interviews with overlap/noise may be slower; keep margin check in the smoke test. `[VERIFIED: local run]` for call signature; real-video behaviour is `[ASSUMED]`.

### Pitfall 13: `make dev` on macOS GNU Make 3.81
`/usr/bin/make` is GNU Make **3.81** `[VERIFIED: make --version]`: no `-O` (output sync), no `.ONESHELL`, no `$(file)`. Verified working pattern: `dev:` runs `@$(MAKE) -j2 dev-api dev-web`; sending SIGTERM to the process group stopped both children (0 left) `[VERIFIED: local run]`. Do NOT use `trap 'kill 0' ...` inside a recipe: `kill 0` signals the whole process group, which killed my invoking shell in testing (exit 144). macOS also has no GNU `timeout`; keep recipes POSIX-sh. Ports: web 3000, API 8000 (CORS allow `http://localhost:3000`), eval shell 3001 (not part of `make dev`; optional `make dev-eval`).

### Pitfall 14: lint/format scope
Generated files must be excluded from ruff (`extend-exclude`), eslint (`ignores`) and prettier (`.prettierignore`); also `.venv`, `.next`, `pnpm-lock.yaml`, `docs/design`. Otherwise `prettier --check .` flagged 69 files in the scratch run. `[VERIFIED: local run]`

## Code Examples

All snippets below were executed (or are minimal variants of executed code) in the scratch env on 2026-10-06 unless marked otherwise.

### 1. `packages/contracts/src/generate.ts` (schema bundle; run with tsx)
```typescript
// Source: Zod docs (z.toJSONSchema, .meta({id}) -> $defs) via Context7 /colinhacks/zod; behaviour verified locally
import * as z from "zod";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import * as C from "./index";

const outDir = process.argv[2] ?? "schema";
const all = { Segment: C.Segment, Lesson: C.Lesson, ScoreResult: C.ScoreResult,
              IssueCode: C.IssueCode, ClipManifest: C.ClipManifest, Label: C.Label };
const wrapper = z.toJSONSchema(z.object(all), { io: "input" }) as
  { $schema: string; $defs: Record<string, unknown> };
mkdirSync(outDir, { recursive: true });
writeFileSync(join(outDir, "contracts.schema.json"),
  JSON.stringify({ $schema: wrapper.$schema, $defs: wrapper.$defs }, null, 2) + "\n");
```
Every exported Zod object/enum must end with `.meta({ id: "Name" })` (nested ones too: e.g. `TimeRange`, `AudioQuality`, `LessonError`, `Contour`, `Scores`, `StressMismatchData`, ...). Verified `$defs` keys for a sample: `Issue, StressIssue, StressMismatchData, PauseIssue, ExtraPauseData, MissIssue, WordMissingData, Word, ClipManifest, ScoreResult, Contour, Scores`.

### 2. Codegen command (flags verified) and drift gate
```bash
# services/audio  (ruff must be in the same venv)
uv run datamodel-codegen \
  --input ../../packages/contracts/schema/contracts.schema.json --input-file-type jsonschema \
  --output-model-type pydantic_v2.BaseModel --snake-case-field --use-annotated \
  --use-union-operator --use-standard-collections --allow-population-by-field-name \
  --strict-nullable --enum-field-as-literal all --skip-root-model --disable-timestamp \
  --custom-file-header "# GENERATED from packages/contracts/schema/contracts.schema.json - do not edit by hand (make contracts)" \
  --formatters ruff-format --output "$OUT"
```
```bash
# scripts/contracts_check.sh  (called by make test; POSIX sh; fails on drift)
set -eu
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pnpm --filter @shadowenglab/contracts exec tsx src/generate.ts "$T/schema"
( cd services/audio && uv run datamodel-codegen --input "$T/schema/contracts.schema.json" ... --output "$T/contracts_gen.py" )
diff -u packages/contracts/schema/contracts.schema.json "$T/schema/contracts.schema.json"
diff -u services/audio/src/audio_service/contracts_gen.py "$T/contracts_gen.py"
```
Output sample (verified): `class StressIssue(BaseModel): ... code: Literal["STRESS_MISMATCH"]; word_index: Annotated[int, Field(alias="wordIndex", ...)]`, `class ClipManifest: gold: Literal["none","identical","wrong"] = "none"`, `Issue = RootModel[StressIssue | PauseIssue | MissIssue]`, `model_config = ConfigDict(populate_by_name=True)`.

### 3. Round-trip test (D-21), Python-driven because it needs both worlds
```python
# services/audio/tests/test_contracts_roundtrip.py
import json, subprocess
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from audio_service import contracts_gen as C

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "packages/contracts/schema/contracts.schema.json").read_text())
FIXTURES = sorted((ROOT / "packages/contracts/fixtures").glob("*.json"))  # name = "<TypeName>.<case>.json"

def zod_parse(type_name: str, payload: object) -> object:
    r = subprocess.run(["pnpm", "--filter", "@shadowenglab/contracts", "exec", "tsx", "src/cli-parse.ts", type_name],
                       input=json.dumps(payload), text=True, capture_output=True, cwd=ROOT, check=True)
    return json.loads(r.stdout)            # cli-parse: JSON.stringify(Schemas[name].parse(JSON.parse(stdin)))

@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_roundtrip(path: Path) -> None:
    type_name = path.name.split(".")[0]
    fixture = json.loads(path.read_text())
    a = zod_parse(type_name, fixture)                                              # Zod parse
    Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{type_name}"}).validate(a)   # JSON Schema
    model = getattr(C, type_name).model_validate(a)                                # pydantic
    b = model.model_dump(mode="json", by_alias=True, exclude_unset=True)           # NOT exclude_none (Pitfall 5)
    assert zod_parse(type_name, b) == a                                            # back through Zod
```
Fixtures must include: `scores.sound: null`, absent optionals (`ipa`, `translation`), every one of the 7 issue codes, `contour` with `null` frames, and a Lesson at `status: "failed"` with `error`. (Python `1.0 == 1` after `json.loads`, so float formatting is not an issue.) `[VERIFIED: local run]` for the dump-mode equality; `IssueCode` enum is an exported bare enum, round-trip it with a fixture of a string (use `RootModel`-free `Literal` check instead of the Zod parse CLI if the generated type is a `Literal` alias).

### 4. Pipeline core with measured timings (this is the Slice-0 spike; executed on 300 s audio)
```python
# Source: executed in scratchpad (bench.py); demucs 4.1.0 API read from installed package
import time, gc, numpy as np, torch
from scipy.signal import resample_poly

class StepTimer:
    def __init__(self): self.t: dict[str, float] = {}
    def step(self, name):
        timer = self
        class _C:
            def __enter__(s): s.t0 = time.perf_counter()
            def __exit__(s, *a): timer.t[name] = round(time.perf_counter() - s.t0, 2)
        return _C()

from demucs.api import Separator
sep = Separator(model="htdemucs", device="mps", shifts=0, overlap=0.25, split=True)
_, stems = sep.separate_tensor(torch.from_numpy(stereo_f32_44k), 44100)      # (2, N) float32
vocals = stems["vocals"]; no_vocals = sum(v for k, v in stems.items() if k != "vocals")
non_vocal_ratio = float((no_vocals**2).mean() / ((vocals**2).mean() + 1e-9))  # D-09 (power ratio)
voc16 = resample_poly(vocals.mean(0).numpy(), 160, 441).astype("float32")     # 44.1k -> 16k
del sep, stems; gc.collect(); torch.mps.empty_cache()

import mlx_whisper
res = mlx_whisper.transcribe(voc16, path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
        word_timestamps=True, language="en", condition_on_previous_text=False)
words = [w for s in res["segments"] for w in s["words"]]   # {'word','start','end','probability'}; cast np.float64 -> float

import parselmouth
f0 = parselmouth.Sound(voc16.astype("float64"), 16000).to_pitch_ac(time_step=0.01, pitch_floor=75, pitch_ceiling=500)\
        .selected_array["frequency"]                         # 0.0 = unvoiced; 10 ms hop (P3 does octave filtering / speaker range)

from transformers import Wav2Vec2ForCTC, Wav2Vec2FeatureExtractor
name = "facebook/wav2vec2-lv-60-espeak-cv-ft"
fe = Wav2Vec2FeatureExtractor.from_pretrained(name)
model = Wav2Vec2ForCTC.from_pretrained(name).to("mps").eval()
with torch.inference_mode():                                 # per-segment in the real pipeline
    x = fe(seg16, sampling_rate=16000, return_tensors="pt").input_values.to("mps")
    ppg = torch.softmax(model(x).logits, -1).cpu().numpy()[0]  # (T, 392), 50 frames/s
```
**Measured (M1 8 GB, 300 s clean TTS):** demucs 40.25 s (+1.8 s load), whisper 76.07 s, F0 0.49 s, PPG 14.83 s on MPS (12.09 s first load) vs 44.52 s CPU, peak RSS 2.34 GB. Sum approx. 133 s + ~15 s loads. `nonVocalRatio` on clean TTS = 5.7e-5.

### 5. Makefile skeleton (GNU Make 3.81 safe)
```make
.PHONY: setup dev dev-api dev-web test lint eval smoke contracts contracts-check
setup:
	@sh scripts/check_deps.sh
	pnpm install
	cd services/audio && uv sync
	cd services/audio && uv run python -m audio_service.setup_models
dev:
	@$(MAKE) -j2 dev-api dev-web
dev-api:
	cd services/audio && uv run uvicorn audio_service.main:app --reload --host 127.0.0.1 --port 8000
dev-web:
	pnpm --filter @shadowenglab/web dev
test: contracts-check
	pnpm -r --if-present test
	cd services/audio && uv run pytest
eval:
	@echo "make eval: stub (Phase 4 / EVL-02 implements eval/analyze.py -> eval/report.md)"
smoke:
	uv run --project services/audio python scripts/smoke_lesson.py "$(URL)"
```
`.env` is read by the Python service itself (pydantic-settings), so Make does not need `include .env`.

### 6. FastAPI router bound to generated models
```python
# services/audio/src/audio_service/routers/lesson.py
import re
from fastapi import APIRouter, HTTPException
from audio_service.contracts_gen import Lesson
from audio_service.paths import lesson_json_path
router = APIRouter(prefix="/lessons", tags=["lesson"])
ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

@router.get("/{lesson_id}", response_model=Lesson, response_model_exclude_unset=True)
def get_lesson(lesson_id: str) -> Lesson:
    if not ULID_RE.fullmatch(lesson_id):
        raise HTTPException(404)
    p = lesson_json_path(lesson_id)
    if not p.is_file():
        raise HTTPException(404)
    return Lesson.model_validate_json(p.read_text())
```

### 7. Verified lint config (root `eslint.config.mjs`)
```js
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import prettier from "eslint-config-prettier";
export default tseslint.config(
  { ignores: ["**/.next/**", "**/node_modules/**", "**/dist/**", "**/schema/**"] },
  ...tseslint.configs.strict,
  { files: ["apps/**/*.{ts,tsx}"], plugins: { "react-hooks": reactHooks },
    rules: { "react-hooks/rules-of-hooks": "error", "react-hooks/exhaustive-deps": "warn" } },
  { rules: { "@typescript-eslint/no-explicit-any": "error" } },
  prettier,
);
```
Next shell: `next.config.mjs` = `{ transpilePackages: ["@shadowenglab/contracts"], eslint: { ignoreDuringBuilds: true } }`; contracts `package.json` `"main"/"types": "./src/index.ts"`, `"type": "module"`. `next build` passed on this layout (14.2.35, Node 24, ~11 s) `[VERIFIED: local run]`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Demucs CLI + torchaudio I/O | `demucs` 4.1.0 uses `sphn`, `demucs.api.Separator`, HF-hosted safetensors weights | 4.1.0 (2026-07) | No torchaudio pin problems; in-process arrays |
| `zod-to-json-schema` | `z.toJSONSchema` built into Zod 4 | Zod 4 | D-18 |
| yt-dlp worked without JS runtime | yt-dlp needs an EJS JS runtime (deno default, node >= 22 opt-in) | 2025-11 | `yt-dlp[default,deno]` |
| pnpm 10 permissive defaults | pnpm 11 `strictDepBuilds: true`, supply-chain defaults | pnpm 11 | explicit `allowBuilds`, `trustPolicy: off` |
| numpy 2.x on any Python | numpy 2.5 requires Python >= 3.12 (uv resolves 2.4.6 on 3.11) | 2026-09 | none, but do not hard-pin numpy 2.5 |

**Deprecated/outdated:** ESLint 8.57 is "no longer supported"; `facebookresearch/demucs` moved to `adefossez/demucs` (PyPI Homepage); `Wav2Vec2Processor` (needs phonemizer) is unnecessary for PPG.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Sentence-splitting thresholds (gap 0.7 s, comma-gap >= 0.25 s, merged <= 9 s) are good starting values | Sentence splitting spec | Poor segments; tune on real video; unit tests protect behaviour not quality |
| A2 | Proposed `nonVocalRatio` label rule: `music` if `10*log10(ratio) > -15 dB`; only synthetic data measured (5.7e-5 = -42 dB) | Open Questions | Mislabelled videos; Liam approves (D-09); smoke prints the ratio for 2-3 real videos |
| A3 | Real 5-min interview takes ~2.5-3.5 min end to end (download 10-30 s estimated, ffmpeg ~5 s) | Summary | If > 5 min, D-26 optimisation list applies; first-run model load adds ~15 s |
| A4 | Whisper on real noisy speech is not much slower than on TTS | Pitfall 12 | Time budget; measure in smoke |
| A5 | `Word.i` is the index within the segment (starting 0) | Sentence splitting spec | Contract semantics (costly if consumers assume lesson-global); ask Liam |
| A6 | `torch`/`transformers` load the wav2vec2 `pytorch_model.bin` (pickle) safely from the official facebook repo | Security | Supply-chain risk is the HF repo itself; loaded fine in this session |
| A7 | vitest 4.x is the safer pick over 5.0.3 (only 4.x tested here) | Standard Stack | Trivial |
| A8 | `trustPolicy: off` is acceptable to Liam (relaxes pnpm 11 supply-chain default; the lockfile is committed) | Pitfall 1 | Security posture decision |
| A9 | Node >= 22.13 may replace "Node 20+" in docs | Constraints | Prerequisite text change |
| A10 | `yt-dlp` stays functional against YouTube for the test video day-of | Pitfall 4 | Smoke blocked; update yt-dlp |

## Open Questions

1. **Real test video for the smoke and the 5-minute criterion**
   - Known: STATE.md says use a US-accent, clean interview temporarily; synthetic TTS timing is already measured.
   - Unclear: which URL; this must be chosen by Liam (or accepted from the executor's proposal).
   - Recommendation: plan a `checkpoint:human-verify` ("run `make smoke URL=<chosen>` and confirm total <= 300 s and segments look sane"), and ask Liam for the URL at that checkpoint.
2. **`Word.i` scope** (segment-local vs lesson-global) - see A5. Recommend segment-local; confirm in the contract PR.
3. **`prominence` in P0**: D-04 says "P0/P2 điền". Recommend leaving unset in P0 (optional), computing it in P2/Phase 3 with the formula in product.md; smoke still produces F0/energy files.
4. **`nonVocalRatio` threshold** (D-09): Claude proposes, Liam approves; smoke prints the ratio and the label with a clearly marked provisional threshold.
5. **Schema layout**: one bundle `contracts.schema.json` (recommended) vs per-type files (D-19 says `schema/*.json`); bundle gives one codegen input and a single diff. Confirm in PR.
6. **D-02 literal wording** (`alias_generator=to_camel`) vs generated explicit aliases (same behaviour) - note in ADR 0003.
7. **Prerequisite changes**: Node >= 22.13, `trustPolicy: off` (A8/A9) - document in ADR 0003 and README/CLAUDE.md.
8. **"Clean machine" validation**: this machine already has the three models in the HF cache and lacks ffmpeg/espeak-ng, so success criterion 1 can only be exercised partially; to simulate a clean download set `HF_HOME` to an empty temp dir for one `make setup` run (adds ~3 GB download).
9. **`/health` payload shape**: Python-only model vs adding a `Health` type to contracts (Liam's call; default: Python-only, not a contract type).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | pnpm 11, Next, vitest, tsx | yes | v24.16.0 | - |
| pnpm | workspace | yes | 11.9.0 | pnpm 10.34.6 |
| uv | Python env | yes | 0.12.10 | - |
| Python 3.11 | audio service | yes (uv-managed) | 3.11.16 | `uv python install 3.11` |
| GNU Make | Makefile | yes | 3.81 (no `-O`, no `.ONESHELL`) | `brew install make` (gmake) not needed |
| Homebrew | system deps guidance | yes | 6.0.22 | - |
| ffmpeg | yt-dlp merge, audio extraction, (RAT-08 later) | **no** | - | none: `brew install ffmpeg` (D-25 guides, does not install) |
| espeak-ng | D-25 check (not needed by PPG inference) | **no** | - | `brew install espeak-ng`; PPG verified to work without it |
| YouTube network access | yt-dlp | yes (extract_info verified) | - | - |
| Apple GPU (MPS) | Demucs, wav2vec2 | yes (`torch.backends.mps.is_available()` True; MLX device gpu) | M1, 8 GB RAM | CPU fallback (PPG 3x slower) |
| HF models in cache | setup | yes (whisper-large-v3-turbo, wav2vec2-lv-60-espeak-cv-ft, adefossez/HTDemucs already cached) | ~3 GB | download on `make setup` |

**Missing dependencies with no fallback:** `ffmpeg` (blocks the real smoke run and `make setup` check; user must `brew install ffmpeg espeak-ng`, so add a human step).
**Missing with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (Python), vitest ^4.1 (TS) |
| Config file | none yet: Wave 0 creates `services/audio/pyproject.toml [tool.pytest.ini_options]`, `packages/contracts/vitest.config.ts` (optional) |
| Quick run command | `cd services/audio && uv run pytest -x -q tests/test_segment.py` and `pnpm --filter @shadowenglab/contracts test` |
| Full suite command | `make test` (= `contracts-check` + `pnpm -r --if-present test` + `cd services/audio && uv run pytest`) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FND-01 | workspace installs; lint/format pass; ruff passes | smoke | `pnpm install --frozen-lockfile && make lint` | Wave 0 |
| FND-02 | Zod types parse fixtures; every type has an `id`; schema bundle generated | unit | `pnpm --filter @shadowenglab/contracts test` | Wave 0 |
| FND-03 | committed schema/pydantic == regenerated; round-trip TS<->JSON Schema<->pydantic | integration | `sh scripts/contracts_check.sh && cd services/audio && uv run pytest tests/test_contracts_roundtrip.py` | Wave 0 |
| FND-04 | `check_deps.sh` reports missing tools with `brew install` and non-zero exit; parselmouth import/pitch works | unit/smoke | `sh scripts/check_deps.sh; cd services/audio && uv run pytest tests/test_setup.py` | Wave 0 |
| FND-05 | `make test` runs both suites; `make eval` exits 0; `make dev` starts both ports | smoke (manual for dev) | `make test && make eval`; `make dev` then `curl -s localhost:8000/health && curl -sI localhost:3000` | Wave 0 |
| FND-06 | `/health` 200; `GET /lessons/{id}` returns contract-valid camelCase JSON; bad id 404 | unit | `cd services/audio && uv run pytest tests/test_api.py` | Wave 0 |
| FND-07 | `split_sentences` rules; `Lesson` built by smoke validates; timing table printed; 5 min video <= 5 min | unit + manual | `uv run pytest tests/test_segment.py` ; `make smoke URL=<url>` (human checkpoint for the 5 min criterion) | Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command matching the touched area
- **Per wave merge:** `make test`
- **Phase gate:** `make test` green + one real `make smoke URL=...` with total <= 300 s, before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `packages/contracts/src/*.test.ts` + `fixtures/*.json` (covers FND-02/03)
- [ ] `services/audio/tests/{test_contracts_roundtrip,test_segment,test_api,test_setup}.py`, `conftest.py` (tmp `DATA_DIR`)
- [ ] Framework install via `uv add --dev pytest httpx jsonschema` and `pnpm add -D vitest tsx`
- [ ] `scripts/{check_deps.sh,contracts_check.sh}`

## Security Domain

`security_enforcement` is enabled (ASVS level 1, block on high). The app is local-only; the relevant surface is the local API, subprocess/file handling and the supply chain.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (single-user local app) | bind to `127.0.0.1`, no remote exposure |
| V3 Session Management | no | - |
| V4 Access Control | no (CORS only) | CORS allow-list `http://localhost:3000` |
| V5 Input Validation | yes | pydantic/Zod at every boundary; URL host allow-list (`youtube.com`, `youtu.be`); `videoId` `^[A-Za-z0-9_-]{11}$`; `lessonId` ULID regex before any path join; resolve and assert paths stay under `DATA_DIR` |
| V6 Cryptography | no | no secrets handled in P0; never hand-roll |
| V10/V14 Config & supply chain | yes | lockfiles committed (`uv.lock`, `pnpm-lock.yaml`); pinned versions; `.env` ignored (`.gitignore` already has `.env`, `.env.*`, `!.env.example`) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Command injection via URL into yt-dlp/ffmpeg | Tampering | yt-dlp Python API; ffmpeg via argv list (`subprocess.run([...])`, never `shell=True`) |
| Path traversal via `videoId`/`lessonId` | Tampering | strict regex + `Path.resolve().is_relative_to(DATA_DIR)` |
| SSRF via arbitrary URL passed to yt-dlp | Information disclosure | only YouTube hosts accepted before calling yt-dlp |
| Malicious model weights (pickle `.bin`) | Tampering / EoP | load only the fixed official repo ids from CONTEXT; no `trust_remote_code`; pin repo ids in code (A6) |
| API exposed on LAN | Information disclosure | `--host 127.0.0.1` |
| Secrets in repo / logs | Information disclosure | `.env` ignored; never log env values; `OPENAI_API_KEY` optional |
| Dependency compromise (npm/PyPI) | Tampering | committed lockfiles + one human lockfile review checkpoint; pnpm `allowBuilds` limited to `esbuild` |

## Sources

### Primary (HIGH confidence)
- Context7 `/colinhacks/zod` (v4.3.6 docs): `z.toJSONSchema` params (`target`, `io`, `metadata`, `reused`, `cycles`), registry ids -> `$defs`, `discriminatedUnion` -> `oneOf`
- Local execution (scratch env, 2026-10-06): uv/pnpm installs, `z.toJSONSchema` + `datamodel-codegen 0.83.0`, pydantic round-trip, FastAPI alias output, yt-dlp (`deno` and `node` runtimes), Demucs 4.1.0 / mlx-whisper 0.4.3 / wav2vec2 / parselmouth benchmark, Next 14.2.35 build, ESLint 9 runs, GNU Make 3.81 `-j2` pattern
- PyPI JSON API and `npm view` (versions, engines, peerDependencies, `requires_dist`) read 2026-10-06
- Installed `demucs` 4.1.0 source (`api.py`, `hf.py`) in the scratch venv

### Secondary (MEDIUM confidence)
- [yt-dlp EJS wiki](https://github.com/yt-dlp/yt-dlp/wiki/EJS) - runtimes, Node >= 22, `--js-runtimes node`, `yt-dlp[default]`
- [pnpm settings: build](https://pnpm.io/settings/build) (`strictDepBuilds` default true in v11, `allowBuilds`) and [dependency resolution](https://pnpm.io/settings/dependency-resolution) (`trustPolicy` documented default `off`; observed behaviour on 11.9.0 differs, hence the explicit `trustPolicy: off`)
- [pnpm 11 release notes](https://pnpm.io/blog/releases/11.0) and web summaries of the supply-chain defaults (`minimumReleaseAge` 1 day)

### Tertiary (LOW confidence)
- Sentence-splitting thresholds, `nonVocalRatio` threshold, real-video timing margin (all `[ASSUMED]`, see Assumptions Log)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - every package resolved, installed and executed this session; seam SUS flags are heuristic artifacts (see audit)
- Architecture / contract toolchain: HIGH - end-to-end executed, including the equality semantics of the round-trip
- Pipeline timing: MEDIUM - measured, but on synthetic speech and without network download
- Pitfalls: HIGH for 1-11 (reproduced), MEDIUM for 12
- Segmentation / quality thresholds: LOW-MEDIUM - starting values only

**Research date:** 2026-10-06
**Valid until:** 2026-10-20 for the toolchain (pnpm 11, Zod, yt-dlp move fast; re-run `npm view`/PyPI before the first install); contract-flag findings stay valid until `datamodel-code-generator` or Zod majors change.



