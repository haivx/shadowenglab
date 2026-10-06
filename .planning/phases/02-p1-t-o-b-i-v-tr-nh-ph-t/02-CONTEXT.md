# Phase 2: P1 · Tạo bài và trình phát - Context

**Gathered:** 2026-10-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Liam dán link YouTube ở S2 → bài được tạo nền (tiến độ theo bước trên card S1) → mở S3 tập từng câu: video tự host, trình phát XState (đệm, lặp ×1/×2/×3, tốc độ, câu trước/sau), IPA nhận dạng từ audio mẫu, bản dịch câu, ghi âm lượt của mình và chuẩn hoá WAV 16 kHz mono, nghe so sánh bản gốc / bản mình. **Chưa chấm điểm** (Lớp B/C là Phase 3, Lớp A là Phase 5). Kèm banner trạng thái hệ thống ở S1 (model, key, micro) và Settings S8.

Requirements: SET-01..04, LES-01..07, PLY-01..07, REC-01..04. Flow F0, F1, F2 (tới bước ghi âm + nghe lại).

</domain>

<decisions>
## Implementation Decisions

> Kế thừa nguyên Phase 1 (`01-CONTEXT.md` D-01…D-27): contract `Lesson`/`Segment`/`Word`, trạng thái job nằm trong `Lesson.status`, feature bản gốc ở `DATA_DIR/lessons/{id}/seg/*.npz`, cache theo `videoId`, model đã khoá. Các quyết định dưới đây là **Liam đã chốt** trong Discuss Phase 2. Shape contract mới (`AttemptAck`, `AppSettings`) đã duyệt ở mức shape — được tinh chỉnh tên field khi Liam review PR contract, không tự thêm/bớt khái niệm.

### Job nền và lưu trữ
- **D-01:** **Tải song song, bước model xếp hàng.** Bước `downloading` (yt-dlp) của nhiều job chạy song song; các bước dùng model (`separating → transcribing → segmenting → analyzing`) chạy **tuần tự một job một lúc** qua một hàng đợi/khoá trong process FastAPI. Job đang chờ khoá model hiển thị `status: 'queued'` (giá trị đã có trong contract). UI và việc tập bài khác không bị chặn (P1 không cần model khi tập). Tạo bài trả về ngay `lessonId`; S1 poll `Lesson`.
- **D-02:** **SQLite cho tiến độ, `lesson.json` vẫn là nguồn sự thật của Lesson** (giữ D-08 Phase 1). SQLite file trong `DATA_DIR` (ví dụ `DATA_DIR/app.db`), P1 chỉ cần bảng lượt ghi, đề xuất: `attempts(lesson_id, segment_index, attempt, created_at, duration_ms, voiced, saved_for_eval)`. Phase 3 thêm cột điểm. Danh sách bài cho S1 = quét `DATA_DIR/lessons/*/lesson.json` (không index bài trong SQLite). — **Reversibility:** costly — Phase 3 (điểm tốt nhất), Phase 7 (ôn luyện, dashboard) xây trên bảng này; schema cụ thể Liam duyệt ở PR.
- **D-03:** **Restart giữa chừng → failed + Thử lại.** Khi FastAPI khởi động, mọi bài có `status` ∉ {`ready`, `failed`} chuyển sang `failed` với `error = { step: <bước dở>, message: 'bị gián đoạn' }`. Card hiện nút Thử lại (LES-07); thử lại chạy lại pipeline cho cùng `lessonId`, tận dụng cache theo `videoId` (bỏ qua tải và tách giọng nếu đã có). Không tự chạy lại.
- **D-04:** **Chỉnh heuristic tách câu ngay trong P1.** Video smoke có 39/62 câu < 3 s. Gộp mạnh hơn để phần lớn câu rơi vào 3–8 s, vẫn tôn trọng dấu câu và khoảng lặng dài, trong khuôn khổ product.md M1 (3–8 s, cắt > ~15 từ tại dấu phẩy/khoảng lặng, gộp < 1.5 s → nâng ngưỡng gộp là được phép). Báo **phân bố độ dài câu trên video smoke trước và sau** trong SUMMARY/PR. Không đổi model.

### Ghi âm khi chưa có chấm
- **D-05:** **Ghi xong → nghe so sánh, không điểm.** Flow: phát mẫu → "Lượt của bạn" (countdown = độ dài câu × `recordFactor`, thanh mức âm, `Space` hoặc im lặng 1 s dừng sớm) → upload → backend chuẩn hoá WAV 16 kHz mono + phát hiện không có tiếng (REC-03) → `reviewing` với các nút **Bản gốc (`O`) · Bạn (`M`) · Lần lượt (`B`) · Thử lại (`R`) · Câu sau (`→`)**. State `scoring` vẫn tồn tại trong machine XState (P1 = bước xử lý upload) để Phase 3 chỉ gắn chấm vào, không đổi cấu trúc machine (PLY-02). Không thu được tiếng → trạng thái riêng + ghi lại; lỗi backend → toast + nút thử lại, giữ blob vừa thu (REC-03).
- **D-06:** **Contract nhỏ riêng cho P1:** `POST /lessons/{lessonId}/segments/{index}/attempts` (multipart: `audio`, `saveForEval?: boolean`) trả
  ```ts
  AttemptAck { lessonId: string; segmentIndex: number; attempt: number /* int >= 1 */;
               durationMs: number /* int >= 0 */; voiced: boolean; savedForEval: boolean }
  ```
  Thêm vào `packages/contracts` (Zod → JSON Schema → pydantic, qua drift gate). Phase 3 cho endpoint trả `ScoreResult` (AttemptAck bỏ hoặc gộp vào); **không** nới `ScoreResult` cho trường hợp "chưa chấm". — **Reversibility:** costly — contract dùng chung web/Python; Phase 3 sẽ đổi response của endpoint.
- **D-07:** **Bản ghi phát lại ở client.** Blob ghi âm giữ trong bộ nhớ trình duyệt để nghe lại (`M`, `B`); backend xoá WAV tạm sau khi xử lý, trừ khi `saveForEval` (REC-04).
- **D-08:** **Chấm màu danh sách câu ở P1 = xám trung tính "đã tập"** (có ≥ 1 lượt `voiced`); câu chưa tập không có chấm (hoặc chấm rỗng theo design). Không dùng đỏ/vàng/xanh khi chưa có điểm. Phase 3 chuyển sang `scoreLevel()` theo điểm tốt nhất. S3 mở ở câu đầu tiên chưa có lượt `voiced` (PLY-04), suy từ bảng `attempts`.
- **D-09:** **"Lưu clip cho eval" làm luôn ở P1:** backend lưu WAV chuẩn hoá + metadata (lessonId, segmentIndex, attempt, text câu) vào `DATA_DIR/eval_clips/`; UI thêm **một nút ghost phụ "Lưu clip cho eval"** trong vùng reviewing, dùng style nút có sẵn trong `docs/design/components.md`. Đây là lệch nhẹ khỏi thiết kế S3 đã chốt — Liam đồng ý; ghi rõ trong UI-SPEC. Phase 4 dùng để thu ~100 clip lỗi cố ý.

### Settings và API key
- **D-10:** **Settings lưu ở backend, file JSON vị trí cố định** `~/.config/shadowenglab/settings.json` (không đặt trong DATA_DIR vì `dataDir` là một setting). `GET /settings`, `PUT /settings`, contract Zod:
  ```ts
  AppSettings { playbackRate: number /* 0.75, 1, ... */; repeat: 1|2|3;
                recordFactor: number /* mặc định 1.5 */; dataDir: string; accent: 'US' /* khoá */ }
  ```
  Thiếu file → giá trị mặc định (dataDir mặc định = giá trị hiện tại của config, `~/shadowenglab-data`). — **Reversibility:** costly — contract dùng chung; config.py hiện đọc DATA_DIR từ `.env` cần hợp nhất thứ tự ưu tiên (planner quyết, ghi rõ).
- **D-11:** **Key dán ở S8 ghi vào `.env` ở gốc repo + nạp nóng** (không cần restart). Không bao giờ trả key về client — chỉ `hasKey: boolean` và bản che (`sk-…abcd`). Nút "Kiểm tra" gọi OpenAI `GET /v1/models` từ backend → hợp lệ / không hợp lệ (SET-03). `.env` đã gitignore; ghi file giữ nguyên các biến khác.
- **D-12:** **Đổi thư mục dữ liệu áp dụng sau restart, không chuyển dữ liệu.** Lưu đường dẫn mới, kiểm tra tồn tại + ghi được; S8 hiện "Khởi động lại `make dev` để áp dụng; dữ liệu cũ vẫn ở <path cũ>". Không tự di chuyển file.
- **D-13:** **Banner model = kiểm tra cache + warm-up.** Backend kiểm tra 3 model (Demucs, mlx-whisper, wav2vec2) đã có trong cache; thiếu → banner đỏ "Chạy `make setup`" (app không tự tải, giữ D-25 Phase 1). Đủ → nạp model vào RAM ở nền lúc khởi động; banner "Model đang nạp…" cho tới khi sẵn sàng. Endpoint trạng thái hệ thống trả model (missing/loading/ready) + `hasKey`; trạng thái micro lấy phía client (Permissions API). Thiếu key → banner vàng không chặn + nút mở S8 (SET-02).

### IPA, bản dịch, video
- **D-14:** **`Word.ipa` = argmax PPG wav2vec2 trong ranh giới từ**, tính lúc tạo bài từ PPG đã có (bước `analyzing`): argmax từng frame trong `[word.start, word.end]`, gộp frame lặp, bỏ blank → chuỗi phone espeak. Không dùng G2P từ text (trái nguyên tắc so với bản gốc). Khi `endExtraMs` đổi và feature câu được tính lại, IPA câu đó tính lại theo.
- **D-15:** **Từ nhận dạng không chắc → ẩn IPA, hiện "—".** Claude đề xuất ngưỡng tạm (ví dụ trung bình xác suất argmax trong từ) trong plan, Liam duyệt. Ghi chú "nhận dạng tự động" luôn hiện cho cả câu; bật/tắt bằng nút IPA / phím `I` (PLY-06).
- **D-16:** **Bản dịch = OpenAI theo yêu cầu, cache vào bài.** Bấm Dịch (`T`) → backend dịch câu đó sang tiếng Việt (kèm vài câu xung quanh làm ngữ cảnh), ghi vào `segment.translation` trong `lesson.json`; lần sau đọc cache. Chỉ gửi text, không gửi audio. Không có key → nút Dịch disabled + tooltip "Cần OPENAI_API_KEY". **Tên model OpenAI Liam chốt ở PR.** Sửa text câu ("Sửa") → xoá `translation` cũ.
- **D-17:** **Bỏ YouTube IFrame dự phòng ở Step 1.** Bài chỉ mở được khi `ready`, lúc đó `video.mp4` đã có. S3 chỉ dùng `<video>` tự host (backend phục vụ file có hỗ trợ Range để seek). File thiếu/hỏng → trạng thái lỗi + nút "Tải lại video". PR phải thêm **ADR `docs/decisions/0004-<slug>.md`** và sửa `docs/product.md` M2 + REQUIREMENTS PLY-01 cho khớp. — **Reversibility:** reversible — thêm lại IFrame sau là việc cục bộ ở S3.

### Claude's Discretion
- Cơ chế hàng đợi/khoá model trong FastAPI (thread pool, asyncio + executor, …), chu kỳ poll của S1 (TanStack Query).
- Endpoint metadata cho preview S2 (LES-01) và thanh kéo chọn đoạn > 6 phút (LES-02) theo design S2.
- "Sửa câu": cách xử lý `words` khi text đổi (giữ timestamps, căn lại tối thiểu) — miễn không vỡ contract; "Mất chữ cuối?" tính lại feature câu đó đồng bộ hay nền (ngắn, một câu).
- Phát hiện "không có tiếng" (ngưỡng năng lượng/VAD) và im lặng 1 s phía client; chọn MIME `MediaRecorder` theo trình duyệt.
- Áp token `docs/design/tokens.md` vào Tailwind, font, component theo `docs/design/components.md` (UI audit Phase 1 = 8/24).
- Ngưỡng ẩn IPA (Liam duyệt), heuristic tách câu cụ thể (báo phân bố).
- Mở rộng CORS sang POST/PUT cho `http://localhost:3000`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Sản phẩm và luồng
- `docs/product.md` §2 M0–M3 — spec cài đặt, tạo bài, trình phát, ghi âm; §5 kiến trúc (SQLite + file system); §8 quyết định đã chốt
- `docs/flows.md` F0, F1, F2 — các bước, trạng thái cần thiết kế, tiêu chí "xong khi"
- `.planning/REQUIREMENTS.md` — SET-01..04, LES-01..07, PLY-01..07, REC-01..04
- `.planning/ROADMAP.md` Phase 2 — success criteria (5 phút, 2 bài không chặn, 30 câu chuột/phím, thiếu key, UI khớp design)

### Thiết kế UI
- `docs/design/README.md`, `docs/design/tokens.md`, `docs/design/tokens.css`, `docs/design/components.md`
- `docs/design/screens/S1-thu-vien.html` (+ `.png`) — thư viện, card tiến độ, banner
- `docs/design/screens/S2-tao-bai.html` — tạo bài, preview, chọn đoạn
- `docs/design/screens/S3-S4-phong-tap.html` — phòng tập (phần trái + thanh điều khiển, danh sách câu, IPA, Dịch, Sửa câu, Mất chữ cuối?)
- `docs/design/screens/S3-trang-thai-cau.html` — trạng thái vùng câu (P1 dùng: đang phát, đang ghi, không thu được tiếng, lỗi backend)
- `docs/design/screens/S8-settings.html` — Settings
- `.planning/phases/01-p0-n-n-t-ng/01-UI-REVIEW.md` — audit UI Phase 1, việc cần làm về token/font/component

### Contract và quyết định trước
- `.planning/phases/01-p0-n-n-t-ng/01-CONTEXT.md` — D-01…D-27 (contract Lesson/Segment/Word, quy ước đường dẫn, model, toolchain contract)
- `packages/contracts/src/lesson.ts`, `packages/contracts/src/common.ts` — contract hiện có; thêm `AttemptAck`, `AppSettings`
- `docs/decisions/0001-uv-va-xstate.md` — XState cho trình phát
- `docs/decisions/0003-contract-toolchain-va-moi-truong-p0.md` — toolchain Zod → JSON Schema → pydantic, drift gate
- `CLAUDE.md` — nguyên tắc (so với audio gốc, precision trước recall, chạy khi thiếu key, không tự đổi contract/schema DB/model)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `services/audio/src/audio_service/lesson/pipeline.py` — `run_lesson(url, start, end, deps, timer, on_status)` đã chạy đầu–cuối, có callback `on_status(Lesson)` để cập nhật tiến độ và `PipelineDeps` tiêm được cho test. Job runner P1 bọc hàm này; cần tách để hỗ trợ thử lại cùng `lessonId` và khoá model giữa bước tải và bước model.
- `lesson/download.py` (`fetch_info` — dùng cho preview S2, cache info theo videoId), `lesson/audio_io.py` (`to_mono_16k`, `read/write_audio` — dùng chuẩn hoá bản ghi), `lesson/features.py` (`compute_ppg`, `segment_window` — dùng cho IPA và tính lại khi `endExtraMs` đổi), `lesson/segment.py` (hằng `MIN_DUR_S=1.5`, `MAX_DUR_S=8.0`, `MAX_MERGED_S=9.0`, `HARD_GAP_S`, `SOFT_GAP_S` — chỗ chỉnh heuristic D-04), `lesson/quality.py` (nhãn clean/music), `lesson/timing.py` (`StepTimer`).
- `config.py` — `data_root()`, helper đường dẫn có chặn path traversal (`ULID_RE`, `VIDEO_ID_RE`, `_contained`); mở rộng cho `eval_clips/`, `app.db`, settings.
- `routers/lesson.py` — `GET /lessons/{id}` mẫu cho validate + lỗi không lộ đường dẫn.
- `scripts/smoke_lesson.py` + `make smoke` — đo thời gian tạo bài và phân bố câu (D-04).

### Established Patterns
- Contract-first: Zod trong `packages/contracts` → `make contracts` sinh JSON Schema + `contracts_gen.py`; `make test` fail khi lệch. pydantic alias camelCase.
- Hàm audio thuần (array in → array out), I/O ở rìa; deps tiêm được cho test.
- Thông báo lỗi tiếng Việt, không lộ đường dẫn ra API.

### Integration Points
- `main.py` — thêm router (lessons POST/list/retry, attempts, settings, system status, translate, video file), lifespan cho warm-up model + đánh dấu job gián đoạn (D-03, D-13); CORS hiện chỉ `GET`.
- `apps/web` — hiện chỉ có `app/layout.tsx`, `app/page.tsx`, dependency mới có `next` + `@shadowenglab/contracts`; cần thêm Tailwind, shadcn/ui, TanStack Query, XState theo stack đã khoá.

</code_context>

<specifics>
## Specific Ideas

- Thanh điều khiển và phím tắt theo PLY-07: nút có chữ cao 44–48 px, gợi ý phím (`Space`, `R`, `←/→`, `O`, `M`, `B`, `I`, `T`); tiêu chí "30 câu chỉ bằng chuột và chỉ bằng bàn phím" là kiểm tra thủ công ở UAT.
- Đo lại ngân sách tạo bài 5 phút với video smoke `https://www.youtube.com/watch?v=dUDi-F6eAvk` sau khi thêm bước IPA và hàng đợi.

</specifics>

<deferred>
## Deferred Ideas

- Chấm điểm và màu điểm theo `scoreLevel()` trong danh sách câu — Phase 3.
- Tinh chỉnh nhãn audio bằng tỉ lệ `ref_unclear` — Phase 5.
- Job queue bền vững, huỷ job, tự retry — Step 2 (product.md §6 Hardening).
- YouTube IFrame (nếu cần lại) — sau Step 1.

</deferred>

---

*Phase: 02-p1-t-o-b-i-v-tr-nh-ph-t*
*Context gathered: 2026-10-06*
