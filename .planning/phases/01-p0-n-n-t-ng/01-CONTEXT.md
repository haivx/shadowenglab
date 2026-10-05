# Phase 1: P0 · Nền tảng - Context

**Gathered:** 2026-10-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Dựng monorepo (pnpm workspace `apps/web`, `apps/eval`, `packages/contracts` + `services/audio` bằng uv), chốt và hiện thực `packages/contracts` (Zod → JSON Schema → pydantic), Makefile (`setup`, `dev`, `test`, `eval` stub), FastAPI skeleton (`/health`, router `lesson`, `scoring` rỗng, response validate theo contracts), `make setup` tải model + kiểm tra system deps, và `scripts/smoke_lesson.py <youtube_url>` chạy pipeline tạo bài đầu–cuối (yt-dlp → Demucs → mlx-whisper → tách câu → F0 + PPG → `Lesson` JSON) có in thời gian từng bước.

Thiết kế UI của P0 **đã xong** (`docs/design/`), không thuộc phạm vi còn lại. Không có UI nào được dựng trong phase này (chỉ khung Next.js rỗng cho `make dev`).

Requirements: FND-01..FND-07.

</domain>

<decisions>
## Implementation Decisions

> Các contract dưới đây là **Liam đã chốt** trong Discuss. Planner/executor hiện thực đúng shape; đổi shape phải dừng lại và hỏi Liam. Tên field cụ thể trong `data` của từng `IssueCode` là đề xuất đã được duyệt ở mức shape — được phép tinh chỉnh tên khi Liam review PR contract, không được tự thêm/bớt mã lỗi.

### Quy ước chung của contract
- **D-01:** Mốc thời gian (`start`, `end`) là **giây float**, tính từ đầu video gốc (khớp `video.currentTime` và Whisper). Độ dài khoảng lặng/khoảng đệm là **ms nguyên** (`refMs`, `userMs`, `padMs`, `endExtraMs`). — **Reversibility:** costly — mọi consumer (web, FastAPI, eval) phụ thuộc đơn vị.
- **D-02:** JSON qua ranh giới dùng **camelCase**. Phía Python đặt tên snake_case và map bằng pydantic `alias_generator=to_camel` (+ `populate_by_name=True`). `ref_ms`/`user_ms` trong bản nháp product.md đổi thành `refMs`/`userMs`. Bảng SQL Supabase (`clips`, `labels`) vẫn snake_case; map ở tầng app eval/export. — **Reversibility:** costly — đổi convention phải sửa toàn bộ contract và serializer.
- **D-03:** Điểm số trong contract là **float 0..1**. Web `scoreLevel()` nhân 100 rồi áp ngưỡng đỏ < 60, vàng 60–79, xanh ≥ 80. Sau P7, điểm qua logistic vẫn ở 0..1.

### Contract Lesson / Segment / Word
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

### Contract ScoreResult
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

### Contract eval: Label, ClipManifest
- **D-16:** `Label`:
  ```ts
  Label { clipId: string; raterId: string; overall: 1|2|3|4|5;
          wordFlags: { wordIndex: number; flags: ('sound'|'stress'|'pitch'|'pause'|'speed')[] }[];
          finalContourMatch: boolean; unsure: boolean; note?: string;
          durationMs: number; createdAt: string }
  ```
  Chỉ lưu từ có cờ; `wordIndex` khớp `ClipManifest.words[].i`. Map sang cột SQL `word_flags jsonb` (snake_case ở DB).
- **D-17:** `ClipManifest` giữ nguyên bản nháp product.md mục 4 (`clipId, videoId, sentenceText, words[{i,text}], refAudio, userAudio, gold: 'none'|'identical'|'wrong' (default 'none'), systemScore?`).

### Toolchain contract (Zod → JSON Schema → pydantic)
- **D-18:** Dùng **Zod v4**, sinh JSON Schema bằng `z.toJSONSchema()` có sẵn (draft 2020-12, discriminated union → `oneOf`). Đăng ký `id` cho từng kiểu để xuất `$defs` dùng chung. Không thêm `zod-to-json-schema`.
- **D-19:** JSON Schema sinh ra được **commit** ở `packages/contracts/schema/*.json` — Liam review diff schema ngay tại ranh giới; Python không cần Node để đọc.
- **D-20:** Pydantic **sinh tự động** bằng `datamodel-code-generator` từ JSON Schema ra file generated (ví dụ `services/audio/.../contracts_gen.py`, có header "generated — không sửa tay"), commit file đó. `make test` sinh lại cả JSON Schema lẫn pydantic và **fail nếu lệch** bản đã commit. Cấu hình generator phải ra pydantic v2 với alias camelCase (D-02).
- **D-21:** Test round-trip bắt buộc (tiêu chí hoàn thành #2): fixture `ScoreResult` (và các kiểu khác) parse bằng Zod → JSON → validate bằng JSON Schema → parse bằng pydantic → dump JSON (by_alias) → parse lại bằng Zod, bằng nhau.

### Model, setup và ngân sách thời gian
- **D-22:** Transcribe bằng **`mlx-community/whisper-large-v3-turbo`** (mlx-whisper, `word_timestamps=True`). — **Reversibility:** reversible — nhưng đổi model cần Liam duyệt (CLAUDE.md).
- **D-23:** Tách giọng bằng **Demucs `htdemucs --two-stems=vocals`** chạy MPS. Stem `no_vocals` dùng luôn để tính `nonVocalRatio` (D-09).
- **D-24:** PPG bằng `facebook/wav2vec2-lv-60-espeak-cv-ft` (đã khoá ở product.md).
- **D-25:** `make setup` **chỉ kiểm tra và hướng dẫn** system deps (ffmpeg, espeak-ng, uv, pnpm, Node 20+): thiếu thì in lệnh `brew install …` và dừng với mã lỗi rõ ràng; không tự cài vào hệ thống. Tải model Python (Demucs, mlx-whisper, wav2vec2) có hiển thị tiến độ; kiểm tra parselmouth import được.
- **D-26:** Nếu smoke video 5 phút > 5 phút: Claude được tự tối ưu phần **không phải model** (thiết bị MPS/CPU, chia đoạn, chạy song song bước độc lập, batch PPG, cache). Vẫn vượt → dừng, báo bảng thời gian từng bước và đề xuất phương án; đổi model cần Liam duyệt.

### Quy trình cho PR của phase này
- **D-27:** Contract chốt ở đây lệch so với bản nháp trong `docs/product.md` mục 3–4 (thêm `scores`, đổi `status` từ, `refMs`, union `issues`, `source` tip, metadata). Theo CLAUDE.md, PR contract phải **cập nhật `docs/product.md` mục 3–4** cho khớp và thêm **ADR `docs/decisions/0003-<slug>.md`** ghi các quyết định contract/toolchain/model ở trên.

### Claude's Discretion
- Thiết bị cho wav2vec2 (MPS với fallback CPU), batch size, cách chunk audio dài.
- Cấu trúc thư mục bên trong `services/audio` (`lesson/`, `scoring/`, `rules/` theo CLAUDE.md), tổ chức router FastAPI, tên file generated.
- Chi tiết heuristic tách câu trong khuôn khổ product.md (3–8 s, cắt > ~15 từ tại dấu phẩy/khoảng lặng, gộp < 1.5 s).
- Thư viện ulid, cấu hình ESLint/Prettier/ruff, phiên bản pnpm/Node cụ thể, cách `make dev` chạy song song hai server.
- Đề xuất ngưỡng `nonVocalRatio` cho nhãn `clean|music` (Liam duyệt).
- Nội dung `.env.example` (B4): kiểm lại, chỉ thêm biến thật sự cần cho P0.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Sản phẩm và hệ thống chấm
- `docs/product.md` §3 — Hệ thống chấm 3 lớp, bản nháp `ScoreResult`, bảng mã lỗi Lớp C (nguồn cho D-10..D-15)
- `docs/product.md` §4 — App eval: data model `clips`/`labels`, `ClipManifest` (nguồn cho D-16, D-17)
- `docs/product.md` §2 M1 — Pipeline tạo bài, quy tắc tách câu
- `docs/product.md` §5 — Kiến trúc, tech stack, cấu trúc repo

### Kế hoạch và quy tắc
- `docs/gsd/roadmap-seed.md` §P0 — Phạm vi B1–B4, C1–C3 và tiêu chí hoàn thành
- `CLAUDE.md` — Quy tắc: không tự đổi contract/model/ngưỡng; code style TS/Python; lệnh make
- `docs/decisions/0001-uv-va-xstate.md` — uv cho Python, XState cho trình phát
- `docs/decisions/0002-dung-gsd.md` — Phân chia nguồn sự thật

### UI (tham chiếu tên component/trạng thái mà contract phải phục vụ)
- `docs/design/components.md` — `ScoreHero`, `IntonationChart`, `TipList`, `ScoredSentence`, `LessonCard`, `JobSteps`
- `docs/flows.md` — F1 (các bước job), F2 (trạng thái chấm)

### Môi trường
- `.env.example` — `OPENAI_API_KEY`, `AZURE_SPEECH_*`, `DATA_DIR`
- `.gitignore` — đã loại trừ audio, model, `eval/clips/`, `eval/labels.jsonl`, `.env`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Chưa có code. Các thư mục `apps/web`, `apps/eval`, `packages/contracts`, `services/audio`, `eval/`, `scripts/` chỉ có README mô tả vai trò — giữ và cập nhật README khi dựng.
- `docs/design/tokens.css` có sẵn giá trị token (dùng ở P1 khi dựng UI, không cần trong P0).

### Established Patterns
- Chưa có pattern code. Convention lấy từ CLAUDE.md: TS strict không `any`, Zod ở mọi ranh giới I/O; Python type hints, ruff, pytest, hàm audio thuần (array in → array out, không đọc file bên trong).

### Integration Points
- `packages/contracts` → `apps/web`, `apps/eval` (import TS) và `services/audio` (qua JSON Schema → pydantic generated).
- `DATA_DIR` (từ `.env`) là gốc lưu trữ cho video, lesson và feature (D-08).

</code_context>

<specifics>
## Specific Ideas

- Smoke script phải in bảng thời gian từng bước (tải, Demucs, Whisper, tách câu, F0, PPG, tổng) để đối chiếu tiêu chí "video 5 phút ≤ 5 phút".
- Video thử: một video phỏng vấn giọng Mỹ audio sạch bất kỳ (bộ 3–4 video eval chưa chọn).

</specifics>

<deferred>
## Deferred Ideas

- Nguồn bản dịch câu (`Segment.translation`) — Discuss P1.
- Công thức gộp `scores.overall`/`intonation`/`rhythm` — P2; `scores.sound` — P4.
- Ngưỡng `nonVocalRatio` chính thức và tinh chỉnh nhãn audio bằng tỉ lệ `ref_unclear` — P1/P5.

</deferred>

---

*Phase: 01-p0-nen-tang*
*Context gathered: 2026-10-05*
