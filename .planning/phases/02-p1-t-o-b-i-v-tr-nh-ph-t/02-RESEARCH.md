# Phase 2: P1 · Tạo bài và trình phát - Research

**Researched:** 2026-10-06
**Domain:** job nền tạo bài (FastAPI, thread + hàng đợi model), trình phát XState + `<video>` tự host, ghi âm `MediaRecorder` → ffmpeg → WAV 16 kHz, IPA từ PPG, Settings/`.env`, áp token shadcn + Tailwind 3 vào `apps/web`
**Confidence:** HIGH cho phần backend/pipeline và các số đo (đã chạy trên máy này: M1, 8 GB, macOS 26); MEDIUM cho hành vi trình duyệt (Safari/Firefox chưa chạy thật trong session này) và các ngưỡng VAD/IPA (cần chỉnh với micro thật).

Quy ước tag: `[VERIFIED: local run]` = tôi đã chạy/đọc trong session này; `[VERIFIED: path:dòng]` = đã đọc file nguồn, kèm trích nguyên văn; `[CITED: url]` = tài liệu chính thức/Context7; `[ASSUMED]` = kiến thức huấn luyện, chưa kiểm chứng (xem Assumptions Log). Prose tiếng Việt, định danh/code giữ tiếng Anh (khớp tài liệu Phase 1).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

> Kế thừa nguyên Phase 1 (`01-CONTEXT.md` D-01…D-27): contract `Lesson`/`Segment`/`Word`, trạng thái job nằm trong `Lesson.status`, feature bản gốc ở `DATA_DIR/lessons/{id}/seg/*.npz`, cache theo `videoId`, model đã khoá. Các quyết định dưới đây là **Liam đã chốt** trong Discuss Phase 2. Shape contract mới (`AttemptAck`, `AppSettings`) đã duyệt ở mức shape — được tinh chỉnh tên field khi Liam review PR contract, không tự thêm/bớt khái niệm.

#### Job nền và lưu trữ
- **D-01:** **Tải song song, bước model xếp hàng.** Bước `downloading` (yt-dlp) của nhiều job chạy song song; các bước dùng model (`separating → transcribing → segmenting → analyzing`) chạy **tuần tự một job một lúc** qua một hàng đợi/khoá trong process FastAPI. Job đang chờ khoá model hiển thị `status: 'queued'` (giá trị đã có trong contract). UI và việc tập bài khác không bị chặn (P1 không cần model khi tập). Tạo bài trả về ngay `lessonId`; S1 poll `Lesson`.
- **D-02:** **SQLite cho tiến độ, `lesson.json` vẫn là nguồn sự thật của Lesson** (giữ D-08 Phase 1). SQLite file trong `DATA_DIR` (ví dụ `DATA_DIR/app.db`), P1 chỉ cần bảng lượt ghi, đề xuất: `attempts(lesson_id, segment_index, attempt, created_at, duration_ms, voiced, saved_for_eval)`. Phase 3 thêm cột điểm. Danh sách bài cho S1 = quét `DATA_DIR/lessons/*/lesson.json` (không index bài trong SQLite). — **Reversibility:** costly — Phase 3 (điểm tốt nhất), Phase 7 (ôn luyện, dashboard) xây trên bảng này; schema cụ thể Liam duyệt ở PR.
- **D-03:** **Restart giữa chừng → failed + Thử lại.** Khi FastAPI khởi động, mọi bài có `status` ∉ {`ready`, `failed`} chuyển sang `failed` với `error = { step: <bước dở>, message: 'bị gián đoạn' }`. Card hiện nút Thử lại (LES-07); thử lại chạy lại pipeline cho cùng `lessonId`, tận dụng cache theo `videoId` (bỏ qua tải và tách giọng nếu đã có). Không tự chạy lại.
- **D-04:** **Chỉnh heuristic tách câu ngay trong P1.** Video smoke có 39/62 câu < 3 s. Gộp mạnh hơn để phần lớn câu rơi vào 3–8 s, vẫn tôn trọng dấu câu và khoảng lặng dài, trong khuôn khổ product.md M1 (3–8 s, cắt > ~15 từ tại dấu phẩy/khoảng lặng, gộp < 1.5 s → nâng ngưỡng gộp là được phép). Báo **phân bố độ dài câu trên video smoke trước và sau** trong SUMMARY/PR. Không đổi model.

#### Ghi âm khi chưa có chấm
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

#### Settings và API key
- **D-10:** **Settings lưu ở backend, file JSON vị trí cố định** `~/.config/shadowenglab/settings.json` (không đặt trong DATA_DIR vì `dataDir` là một setting). `GET /settings`, `PUT /settings`, contract Zod:
  ```ts
  AppSettings { playbackRate: number /* 0.75, 1, ... */; repeat: 1|2|3;
                recordFactor: number /* mặc định 1.5 */; dataDir: string; accent: 'US' /* khoá */ }
  ```
  Thiếu file → giá trị mặc định (dataDir mặc định = giá trị hiện tại của config, `~/shadowenglab-data`). — **Reversibility:** costly — contract dùng chung; config.py hiện đọc DATA_DIR từ `.env` cần hợp nhất thứ tự ưu tiên (planner quyết, ghi rõ).
- **D-11:** **Key dán ở S8 ghi vào `.env` ở gốc repo + nạp nóng** (không cần restart). Không bao giờ trả key về client — chỉ `hasKey: boolean` và bản che (`sk-…abcd`). Nút "Kiểm tra" gọi OpenAI `GET /v1/models` từ backend → hợp lệ / không hợp lệ (SET-03). `.env` đã gitignore; ghi file giữ nguyên các biến khác.
- **D-12:** **Đổi thư mục dữ liệu áp dụng sau restart, không chuyển dữ liệu.** Lưu đường dẫn mới, kiểm tra tồn tại + ghi được; S8 hiện "Khởi động lại `make dev` để áp dụng; dữ liệu cũ vẫn ở <path cũ>". Không tự di chuyển file.
- **D-13:** **Banner model = kiểm tra cache + warm-up.** Backend kiểm tra 3 model (Demucs, mlx-whisper, wav2vec2) đã có trong cache; thiếu → banner đỏ "Chạy `make setup`" (app không tự tải, giữ D-25 Phase 1). Đủ → nạp model vào RAM ở nền lúc khởi động; banner "Model đang nạp…" cho tới khi sẵn sàng. Endpoint trạng thái hệ thống trả model (missing/loading/ready) + `hasKey`; trạng thái micro lấy phía client (Permissions API). Thiếu key → banner vàng không chặn + nút mở S8 (SET-02).

#### IPA, bản dịch, video
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

### Deferred Ideas (OUT OF SCOPE)
- Chấm điểm và màu điểm theo `scoreLevel()` trong danh sách câu — Phase 3.
- Tinh chỉnh nhãn audio bằng tỉ lệ `ref_unclear` — Phase 5.
- Job queue bền vững, huỷ job, tự retry — Step 2 (product.md §6 Hardening).
- YouTube IFrame (nếu cần lại) — sau Step 1.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SET-01 | Banner trạng thái hệ thống (model, key, micro) | `GET /system/status` (model missing/loading/ready + `hasKey`), Permissions API phía client; **D-13 xung đột RAM 8 GB** (Pitfall 1, Open Q1) |
| SET-02 | Thiếu key → banner vàng không chặn, vẫn tạo bài/tập | `hasKey` đọc nóng từ `os.environ`/`.env`; không đường nào trong P1 bắt buộc key (Pattern 7) |
| SET-03 | S8 dán key, "Kiểm tra" → hợp lệ/không | Pattern 7: httpx `GET /v1/models`, ghi `.env` bằng `dotenv.set_key`, regex chặn newline injection |
| SET-04 | Mặc định tốc độ, lặp, thời gian ghi, thư mục dữ liệu, US khoá | `GET/PUT /settings`, file `~/.config/shadowenglab/settings.json`, thứ tự ưu tiên `dataDir` (Pattern 7) |
| LES-01 | Dán link → preview; link xấu/video chặn báo lỗi | `GET /videos/preview?url=` bọc `parse_youtube_url` + `fetch_info` (thêm `channel`, `live_status`, `availability`); mã lỗi (Pattern 1b) |
| LES-02 | Video > 6 phút chọn đoạn | `RangePicker` (slider 2 thumb) + **tách giọng chỉ trên range** (Pitfall 4, Open Q3) |
| LES-03 | Job nền, tiến độ theo bước, 2 bài không chặn nhau | Pattern 1: pool tải + một worker model FIFO; `lesson.json` ghi mỗi lần đổi trạng thái (đã có); S1 poll bằng `refetchInterval` hàm |
| LES-04 | Pipeline yt-dlp/Demucs/Whisper/tách câu/feature | Đã có ở Phase 1; P1 bọc lại + chỉnh heuristic D-04 + IPA + format H.264 (Pitfall 3) |
| LES-05 | Video 5 phút ≤ 5 phút | Baseline đo lại hôm nay: 110.9 s (bảng bước); ngân sách còn ~189 s cho IPA, hàng đợi |
| LES-06 | Nhãn "Audio sạch"/"Có nhạc nền" trên card | `Lesson.audioQuality` đã có từ Phase 1; chỉ cần hiển thị |
| LES-07 | Job lỗi hiện card + Thử lại | `POST /lessons/{id}/retry` + lifespan đánh dấu gián đoạn (D-03); Pitfall 5 (null vs absent khi rebuild) |
| PLY-01 | `<video>` tự host | `FileResponse` Range (starlette 1.7.0 đã hỗ trợ); **video hiện AV1+Opus → chuyển ưu tiên H.264/AAC** (Pitfall 3) |
| PLY-02 | State machine XState ở file riêng, có test | Pattern 3: `setup()` + actors tiêm bằng `machine.provide`, test bằng `createActor`/`waitFor` (vitest, node env) |
| PLY-03 | Đệm 100–200 ms, lặp, tốc độ, điều khiển câu | Pattern 4: rAF stop-at-end, `playbackRate`, `padMs` 150; seek đầu mỗi lần lặp |
| PLY-04 | Mở ở câu đầu chưa tập; danh sách highlight; Sửa câu | `GET /lessons/{id}/progress` từ SQLite; `PATCH segments/{i}` (Pattern 2b) |
| PLY-05 | "Mất chữ cuối?" nới 300 ms + lưu | `POST segments/{i}/extend-end`: `endExtraMs += 300`, tính lại feature + IPA dưới cổng model (Pattern 2c) |
| PLY-06 | IPA từ audio mẫu, ghi chú, bật/tắt | Pattern 6 (đã chạy thử trên video smoke): argmax trong từ ±2 frame, ngưỡng 0.7; **vocab không có dấu trọng âm** |
| PLY-07 | Nút có chữ 44–48 px, phím tắt phụ | UI-SPEC shortcut map + hook `useShortcuts` thuần (Pitfall 12, test) |
| REC-01 | Tự ghi sau mẫu, countdown, mức âm, Space/im lặng 1 s | `MediaRecorder` + `AnalyserNode` trong `fromCallback` actor (Pattern 5a) |
| REC-02 | Chuẩn hoá webm/mp4 → WAV 16 kHz mono | Pattern 5b: file tạm + `ffmpeg -f <demuxer>` (đã chạy thử webm/mp4/fragmented mp4) |
| REC-03 | Không tiếng → trạng thái riêng; lỗi backend → toast, giữ bản ghi | VAD năng lượng (`frame_energy` đã có), `AttemptAck.voiced`; blob giữ trong context machine |
| REC-04 | Không lưu bản ghi trừ khi đánh dấu eval | Xoá file tạm trong `finally`; `PUT …/attempts/{n}/eval-clip` gửi lại blob (Open Q7) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Từ `./CLAUDE.md` và `./.claude/CLAUDE.md` (coi như khoá, ngang CONTEXT.md):
- Không tự đổi contract (`packages/contracts`), schema DB, ngưỡng chấm hay model. Cần đổi → dừng và đề xuất. **Hệ quả trực tiếp cho phase này:** schema `attempts`, `AttemptAck`, `AppSettings`, các shape contract bổ sung (Open Q2), ngưỡng IPA, tên model OpenAI đều qua checkpoint của Liam.
- Chấm điểm luôn so với audio gốc; precision trước recall; **IPA chỉ lấy từ audio mẫu, không G2P**. LLM chỉ nhận text (bản dịch), không nhận audio; không dùng LLM đa phương thức để chấm.
- App phải chạy được khi thiếu API key (banner vàng, nút Dịch disabled, tạo bài/tập bình thường).
- Không commit audio eval, nhãn thô, `.env`. `DATA_DIR/eval_clips/` nằm ngoài repo (và `.gitignore` đã loại `*.wav`, `data/`).
- UI bám `docs/design/`; không thêm màn/component ngoài thiết kế (ngoại lệ đã duyệt: nút ghost `Lưu clip cho eval`, D-09). Nút là chính, phím tắt phụ.
- Code style: TS strict, không `any`, Zod ở mọi ranh giới I/O; Python type hints + ruff + pytest, hàm audio thuần (array in → array out), I/O ở rìa. Kiểu Python phải khớp `packages/contracts` (sinh pydantic, drift gate).
- Quy trình: PR nhỏ, review tại ranh giới (schema, state machine, output pipeline); quyết định mới/lệch product.md → ADR `docs/decisions/NNNN-<slug>.md` (ADR 0004 cho D-17; xem Open Q8 cho ADR còn lại); sửa `product.md` trước khi cập nhật roadmap.
- Lệnh: `make setup/dev/test/lint/eval/smoke/contracts`; cập nhật mục "Lệnh" nếu đổi Makefile.
- Mọi sửa file đi qua lệnh GSD (executor chạy dưới `/gsd-execute-phase`).

## Summary

Phase 2 là phase "lớn nhất về bề mặt" (22 requirement, 5 màn hình, ~15 endpoint mới) nhưng **ít rủi ro nghiên cứu mới** vì pipeline, contract toolchain và UI-SPEC đã chốt. Tôi đã chạy lại pipeline thật (`make smoke`, 111 s cho 5 phút, 62 câu) và dùng chính dữ liệu đó để đo bốn thứ mà plan phụ thuộc vào: phân bố độ dài câu theo heuristic mới, chất lượng IPA argmax từ PPG, codec của `video.mp4`, và footprint RAM thật của ba model. Bốn phép đo đều cho kết quả **làm lệch một quyết định đã chốt hoặc một giả định của UI-SPEC**, nên chúng được đặt lên đầu "Open Questions" để Liam duyệt trước khi Plan.

Các phát hiện quan trọng nhất (chi tiết ở Pitfalls và Open Questions):
1. **D-13 (nạp 3 model vào RAM lúc khởi động) không khả thi trên máy 8 GB**: footprint đo được wav2vec2 ≈ 2.5 GB, + whisper ≈ 4.6 GB, + Demucs ≈ 6.0 GB `[VERIFIED: local run, footprint]`. Cần diễn giải lại "warm-up" thành load-rồi-giải-phóng (làm nóng page cache + kiểm tra load được).
2. **`video.mp4` hiện tải về là AV1 + Opus** `[VERIFIED: ffprobe]` vì `_FORMAT` không ưu tiên codec; Chrome phát được, Safari trên M1 nhiều khả năng không (A5). Đổi selector sang H.264/AAC đã kiểm chứng chọn được format 135+140 `[VERIFIED: local run]`.
3. **Pipeline hiện tách giọng toàn bộ video** (cache theo `videoId`, D-07). Với video dài, đây là đường vỡ RAM/thời gian (LES-02 chính là để chọn đoạn); cần tách trên range.
4. **IPA từ PPG hoạt động nhưng thô**: vocab wav2vec2-espeak **không có dấu trọng âm** (`ˈ`) và không có ranh giới từ; ranh giới từ của Whisper lệch làm phone rò sang từ bên cạnh. Ngưỡng "trung bình xác suất phone phát ra ≥ 0.7" tách được từ tin cậy (giống từ điển 0.74) khỏi từ không tin cậy (0.40) nhưng ẩn ~32% từ trên video sitcom nhanh này.
5. **D-04 có số liệu rõ ràng**: `MIN_DUR_S` 1.5→3.0, `MAX_MERGED_S` 9→8 đưa 3–8 s từ 23/62 lên 34/39 câu; đồng thời phát hiện bước gộp hiện **không giới hạn số từ** (câu gộp tới 23 từ, vượt quy tắc ~15 từ của product.md).

Phần còn lại là kỹ thuật thông thường nhưng có nhiều bẫy cụ thể (đã kiểm chứng): `python-multipart` chưa cài (upload sẽ lỗi lúc chạy), `mlx_whisper.ModelHolder` giữ model 2.1 GB trong process dài, `model_copy(update={"error": None})` ghi `null` làm Zod `.optional()` từ chối, ffmpeg cần `-f` whitelist để không bị dụ mở playlist, CORS chỉ cho GET, và các bẫy Tailwind 3 / shadcn / Vietnamese font đã nêu trong UI-SPEC.

**Primary recommendation:** Thực hiện theo 3 làn song song sau một **Wave 0 "contract + nền"** (PR contract duyệt bởi Liam: `AttemptAck`, `AppSettings` + các shape bổ sung ở Open Q2; schema SQLite; scaffold web Tailwind/shadcn/token; `python-multipart`): (A) backend job runner = pool tải + **một worker model FIFO** dùng chung cổng với `extend-end`; (B) machine XState thuần + test trước UI; (C) màn S1/S2/S8 rồi S3. Dừng hỏi Liam 6 câu ở Open Questions (1–6) **trước Plan**, vì 1–3 đổi cấu trúc task.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tạo bài (validate URL, preview, tạo lesson `queued`) | API / Backend | — | `parse_youtube_url` + `fetch_info` là biên tin cậy; web chỉ hiển thị |
| Job nền (tải song song, model tuần tự, retry, đánh dấu gián đoạn) | API / Backend (in-process threads) | Database / Storage (`lesson.json`) | D-01/D-03; trạng thái nằm trong `Lesson.status`, atomic write |
| Danh sách bài + tiến độ (`practicedCount`, `firstUnpracticedIndex`) | API / Backend | Database (SQLite `attempts`) | D-02/D-08: quét `lesson.json` + join bảng `attempts` |
| Phục vụ `video.mp4` có Range | API / Backend (`FileResponse`) | — | D-17; trình duyệt cần 206 để seek |
| Trình phát theo câu (machine, rAF stop, lặp, tốc độ) | Browser / Client | — | `video.currentTime`/`playbackRate` chỉ có ở client; machine thuần, actor tiêm vào |
| Ghi âm, mức âm, im lặng 1 s, MIME | Browser / Client | — | `MediaRecorder`/`AnalyserNode`; blob giữ ở client (D-07) |
| Chuẩn hoá WAV 16 kHz mono + phát hiện không có tiếng | API / Backend | — | ffmpeg + `frame_energy`; hàm thuần, I/O ở rìa |
| IPA từng từ | API / Backend (lúc `analyzing`, từ PPG đã lưu) | — | D-14: argmax trên `seg/*.npz`, không cần model khi tính lại |
| Bản dịch | API / Backend (OpenAI, chỉ text) | Database (`segment.translation` trong `lesson.json`) | Key không bao giờ ra client (D-11/D-16) |
| Settings, API key | API / Backend (`~/.config/…`, `.env`) | Browser (chọn micro lưu `localStorage`) | D-10/D-11; micro device không thuộc `AppSettings` (UI-SPEC) |
| Trạng thái model/key/micro (banner) | API (model, key) + Browser (micro, Permissions API) | — | D-13: micro chỉ client biết |
| Token/typography/component | Frontend (`apps/web`) | — | UI-SPEC "Token Implementation Map" |

## Standard Stack

### Core (đã có từ Phase 1, không đổi)
| Library | Version | Purpose | Ghi chú |
|---------|---------|---------|---------|
| Next.js / React | 14.2.35 / ^18.3.1 | `apps/web` | `[VERIFIED: apps/web/package.json]` đã khoá |
| FastAPI / uvicorn / pydantic | 0.142.2 / 0.54.0 / 2.13.5 | API | `[VERIFIED: uv.lock, venv dist-info]`; starlette 1.7.0 `FileResponse` đã xử lý `Range` `[VERIFIED: starlette/responses.py:364-388]` |
| yt-dlp[default,deno] | ≥2026.8.19 | tải + metadata | đã dùng; thêm đọc `channel`, `live_status`, `availability` |
| Zod / contracts toolchain | zod 4.6.5 | contract | thêm shape mới qua `make contracts` |
| vitest | ^4.1.11 (contracts) | test web | giữ cùng major với contracts; vitest 5.0.3 đã ra nhưng chưa cần `[VERIFIED: npm view]` |

### Thêm mới cho `apps/web` (đã `npm view` ngày 2026-10-06)
| Library | Version | Purpose | Vì sao |
|---------|---------|---------|--------|
| tailwindcss | **^3.4.19** (không dùng 4.x, latest = 4.3.3) | style | UI-SPEC G1; `tokens.md` "Map sang Tailwind" là cấu hình v3 `[VERIFIED: npm view tailwindcss]` |
| postcss, autoprefixer | 8.5.29 / 10.6.1 | Tailwind 3 cần | |
| xstate | 5.33.2 | player machine | ADR 0001 |
| @xstate/react | 6.1.0 (peer react ^18/19, xstate ^5.28) | hook React | `[VERIFIED: npm view @xstate/react peerDependencies]` |
| @tanstack/react-query | 5.104.1 (peer react ^18‖^19) | poll lesson, settings, status | `refetchInterval` nhận hàm `[CITED: tanstack.com/query polling guide]` |
| shadcn (CLI) | 4.21.3, `-b radix`, Tailwind v3 hợp lệ | component primitives | `[CITED: shadcn-ui/ui preflight-init.ts, cli.mdx]`; init theo UI-SPEC (không `-d`) |
| radix-ui / @radix-ui/*, class-variance-authority 0.7.1, clsx 2.1.1, tailwind-merge 3.7.0, tailwindcss-animate 1.0.7, lucide-react 1.52.0, sonner 2.0.8 | | do CLI shadcn cài | kiểm tra diff lockfile sau init |
| jsdom + @testing-library/react | 30.1.2 / 16.3.3 | (tuỳ chọn) test hook DOM | chỉ nếu cần test `useShortcuts`/`useRecorder`; ưu tiên trích hàm thuần để test trong môi trường node |

### Thêm mới cho `services/audio`
| Library | Version | Purpose | Vì sao |
|---------|---------|---------|--------|
| **python-multipart** | 0.0.32 (2026-06-04) | FastAPI nhận `UploadFile`/`Form` | **Chưa có trong `uv.lock`** `[VERIFIED: grep uv.lock]`; thiếu thì `POST …/attempts` lỗi runtime `[CITED: fastapi.tiangolo.com request-forms-and-files]` |
| python-dotenv | 1.2.4 (đã có, transitive qua pydantic-settings) | ghi `.env` bằng `set_key` (giữ biến khác, ghi qua file tạm + `os.replace`) | Khai báo **trực tiếp** trong `pyproject.toml` `[VERIFIED: dotenv/main.py dùng NamedTemporaryFile + os.replace]` |
| httpx | 0.28.1 (hiện là dev dep) | gọi OpenAI REST (`GET /v1/models`, dịch) | Chuyển sang dependency chính; tránh thêm SDK (xem Alternatives) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx gọi OpenAI REST | `openai` SDK 3.24.0 (2026-10-02) | SDK có `responses.parse` + retry, nhưng v3 vừa ra, Context7 chỉ có tài liệu 2.x → rủi ro khác biệt API; Phase 7/8 (TTS, structured output) có thể đáng thêm SDK. P1 chỉ cần 2 lệnh REST. |
| Thread + `queue.Queue` FIFO cho bước model | `asyncio` + `run_in_executor`, hoặc `threading.Lock` | Lock không đảm bảo FIFO; asyncio không giúp vì công việc là CPU/GPU nặng. Một worker thread duy nhất cho FIFO tự nhiên (Pattern 1). |
| Energy VAD tự viết (30 dòng, dùng `frame_energy`) | webrtcvad / Silero VAD | Thêm dependency/model (CLAUDE: không đổi model). Energy đủ cho "có tiếng hay không" (không phải ranh giới từ). |
| `tailwindcss` 4 + `tw-animate-css` | giữ 3.4 | UI-SPEC G1 đã khoá 3.4; không đổi trong phase này. |

**Installation:**
```bash
# apps/web
pnpm --filter @shadowenglab/web add xstate@5.33.2 @xstate/react@6.1.0 @tanstack/react-query@5.104.1
pnpm --filter @shadowenglab/web add -D tailwindcss@^3.4.19 postcss autoprefixer vitest@^4.1.11
cd apps/web && npx shadcn@latest init -b radix --css-variables   # KHÔNG truyền -d (ép preset nova)
# services/audio
cd services/audio && uv add python-multipart httpx python-dotenv   # sau đó: uv lock, kiểm tra diff
```
**Version verification:** mọi version web ở trên lấy từ `npm view <pkg> version` ngày 2026-10-06; PyPI từ `https://pypi.org/pypi/<pkg>/json` cùng ngày. Training data có thể cũ hơn vài tháng.

## Package Legitimacy Audit

Seam `gsd_run query package-legitimacy check` đã chạy cho tất cả gói mới. Kết quả:

| Package | Registry | Age / Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----------------|-------------|---------|-------------|
| tailwindcss | npm | 163M/wk | tailwindlabs/tailwindcss | OK | Approved. (Lần chạy đầu với `tailwindcss@3.4.19` trả SLOP "does-not-exist" vì seam coi hậu tố `@3.4.19` là một phần tên; `npm view tailwindcss@3.4.19 version` = 3.4.19, tức **artifact của seam, không phải gói giả**.) |
| @xstate/react, sonner, class-variance-authority, clsx, @testing-library/react | npm | 3.7M–155M/wk | repo chính chủ | OK | Approved |
| xstate | npm | 6.0M/wk, release 2026-09-15 | statelyai/xstate | SUS (too-new) | Approved sau checkpoint lockfile |
| @tanstack/react-query | npm | 82.8M/wk, release 2026-10-02 | TanStack/query | SUS (too-new) | Approved sau checkpoint lockfile |
| lucide-react, tailwind-merge, radix-ui, postcss, autoprefixer, jsdom, shadcn | npm | 13M–360M/wk | repo chính chủ | SUS (too-new: bản mới phát hành gần đây) | Approved sau checkpoint lockfile |
| tailwindcss-animate | npm | 25.8M/wk, release 2023-08 | metadata npm không có repo (`repository.url` rỗng) | SUS (no-repository) | Approved: do CLI shadcn cho Tailwind 3 tự cài; kiểm tra khi review lockfile |
| python-multipart | PyPI | 0.0.32, first release 2013, repo Kludex/python-multipart | có | SUS (unknown-downloads) | Approved: là dependency chính thức mà FastAPI yêu cầu `[CITED: fastapi docs]` |
| python-dotenv, httpx | PyPI | đã có trong `uv.lock` | có | SUS/OK (heuristic) | Approved (đã dùng từ Phase 1) |
| openai | PyPI | 3.24.0, repo openai/openai-python | có | SUS (too-new) | **Không dùng trong P1** (xem Alternatives); nếu Liam muốn SDK thì thêm vào checkpoint |

**Packages removed due to SLOP verdict:** none (SLOP duy nhất là artifact `tailwindcss@3.4.19`, đã xác minh bằng `npm view`).
**Packages flagged as suspicious [SUS]:** như bảng trên; heuristic của seam chỉ nêu `too-new`/`unknown-downloads`/`no-repository`, không có tín hiệu thật. Giống Phase 1: **một checkpoint `human-verify` gộp** trước lần cài đầu tiên ("duyệt diff `pnpm-lock.yaml` và `uv.lock`, không có tên lạ"), không cần một checkpoint cho mỗi gói.
**Postinstall:** `npm view <pkg> scripts.postinstall` rỗng cho tailwindcss-animate, radix-ui, sonner, shadcn `[VERIFIED: local run]`.

## Architecture Patterns

### System Architecture Diagram

```
 TẠO BÀI (F1)                                                   (một process uvicorn, KHÔNG dùng --workers N)
 ────────────
 S2 dialog ──GET /videos/preview?url──► parse_youtube_url ─► fetch_info(videoId, cache info.json)
    │  (debounce)                          │ lỗi → {code,message}: invalid_url | channel_url | unavailable | live
    ▼
 POST /lessons {url,start?,end?} ─► tạo lesson.json status=queued ─► trả Lesson ngay (D-01)
                                          │
                                          ▼ submit
                         ┌── download_pool (ThreadPool, 2 slot) ──────────────────────────┐
                         │ downloading: yt-dlp (H.264 480p) + ffmpeg extract audio(range) │  chạy SONG SONG giữa các job
                         └────────────────────────────┬───────────────────────────────────┘
                                                      │ status=queued (chờ cổng model)
                                                      ▼
                         ┌── model_queue (queue.Queue FIFO) ── MỘT worker thread ─────────┐
                         │ separating → transcribing → segmenting → analyzing(+IPA)       │  TUẦN TỰ, giữ "cổng model"
                         │ → ready | failed{step,message}                                 │  mỗi lần đổi status: ghi lesson.json atomic
                         └────────────────────────────────────────────────────────────────┘
 S1 ◄── poll GET /lessons (2 s khi còn job chưa ready/failed) ◄── quét DATA_DIR/lessons/*/lesson.json + join SQLite attempts
 Khởi động: lifespan → job ∉ {ready,failed} → failed{step,'bị gián đoạn'} (D-03) → (warm-up model nền, D-13 diễn giải lại)

 TẬP MỘT CÂU (F2)  ── Browser ─────────────────────────────────────────────  ── Backend ──
 S3 mở: GET /lessons/{id} + /progress ─► chọn câu đầu chưa voiced (PLY-04)
 playerMachine (XState, file riêng, actor tiêm vào)
  idle ─Space/O/R─► playing ──(rAF: currentTime ≥ end+pad+extra, lặp ×N, seek lại)──► recording
        <video src=/lessons/{id}/video (Range 206)>        │ getUserMedia(no AGC/NS/EC) → MediaRecorder + AnalyserNode
                                                           │ Space | im lặng 1 s sau khi có tiếng | hết countdown
                                                           ▼
                                  scoring(=upload) ──POST …/attempts (multipart)──► sniff magic → temp file
                                                           │                         → ffmpeg -f demuxer → WAV 16k mono
                                                           │                         → VAD (frame_energy) → voiced?
                                                           │                         → INSERT attempts (BEGIN IMMEDIATE)
                                                           │                         → xoá temp (trừ eval) → AttemptAck
                                                           ▼
                           reviewing {O,M,B,R,→} | noVoice | error(toast+Thử lại, giữ blob)
 Dịch (T): POST …/translate ─► OpenAI (chỉ text) ─► ghi segment.translation   Mất chữ cuối?: POST …/extend-end ─► cổng model
```

### Recommended Project Structure
```
services/audio/src/audio_service/
├── config.py              # + app_db_path(), eval_clips_dir(), settings_file_path(); đọc settings.json (D-10)
├── db.py                  # sqlite3: connect(), ensure_schema() (PRAGMA user_version), attempts DAO
├── settings_store.py      # GET/PUT AppSettings (file ~/.config/shadowenglab/settings.json), active dataDir
├── secrets_env.py         # get_openai_key(), set_openai_key() (dotenv.set_key), mask_key()
├── system_status.py       # model cache check + warm-up state (D-13) + hasKey
├── lesson/
│   ├── pipeline.py        # TÁCH: create_lesson() + stage_download() + stage_model(); run_lesson() giữ nguyên chữ ký cho smoke/test
│   ├── jobs.py            # JobRunner (pool tải + worker model FIFO + cổng model), recover_interrupted()
│   ├── ipa.py             # thuần: ipa_for_segment(ppg, window_start, words, vocab, ...) -> dict[i, str]
│   ├── vad.py             # thuần: voiced_ms(audio16k) -> int
│   ├── normalize.py       # sniff_container(), normalize_to_wav16k(path)  (ffmpeg argv, -f whitelist)
│   ├── translate.py       # httpx -> OpenAI (chỉ text), cache vào segment.translation
│   └── segment.py         # chỉnh D-04 (MIN_DUR_S, MAX_MERGED_S, cap từ khi gộp)
├── routers/
│   ├── lesson.py          # mở rộng: POST /lessons, GET list, retry, video, progress, segments/{i}/(patch|extend-end|translate)
│   ├── attempts.py        # POST …/attempts, PUT …/attempts/{n}/eval-clip
│   ├── videos.py          # GET /videos/preview
│   ├── settings.py        # GET/PUT /settings, POST /settings/openai-key/check
│   └── system.py          # GET /system/status
apps/web/
├── app/{layout.tsx, globals.css, tokens.css, providers.tsx, page.tsx(S1), settings/page.tsx(S8), lessons/[id]/page.tsx(S3)}
├── components/ui/…        # shadcn (đã chỉnh theo design)
├── components/*.tsx       # AppHeader, Banner, LessonCard, JobSteps, RangePicker, PlayerControls, TranscriptList, SentenceStatePanel, ResultActionBar…
├── lib/api.ts             # fetch + parse Zod (mọi response), NEXT_PUBLIC_API_URL (mặc định http://127.0.0.1:8000)
├── lib/player/{playerMachine.ts, playerMachine.test.ts, actors.ts (DOM, không test machine), shortcuts.ts, shortcuts.test.ts}
└── lib/audio/{recorder.ts, level.ts, mime.ts}
```

### Pattern 1: Job runner = pool tải + MỘT worker model FIFO
**What:** hai giai đoạn nối bằng `queue.Queue`. Giai đoạn A (tải + ffmpeg) chạy trong `ThreadPoolExecutor(max_workers=2)` (song song, D-01). Xong A → `save(status="queued")` rồi đẩy `lesson_id` vào hàng đợi; **một thread duy nhất** lấy từng job làm giai đoạn B (`separating → … → analyzing`). FIFO tự nhiên, không cần khoá và không bao giờ có hai job cùng dùng model.
**Vì sao không `threading.Lock`:** không đảm bảo thứ tự (job 3 có thể vượt job 2) và khó mở rộng cho `extend-end`. Muốn dùng chung cổng cho `extend-end`, bọc một `threading.Lock` quanh *mỗi lần dùng model* (worker giữ nó suốt giai đoạn B của một job, `extend-end` lấy nó cho một câu).
**Quan trọng:** endpoint FastAPI dạng `def` chạy trong anyio threadpool (mặc định 40); **không** chạy pipeline trong đó. Dùng pool/thread riêng, `daemon=True` cho worker, tạo trong `lifespan` (không ở import time, để `TestClient` và `--reload` sạch).
```python
# services/audio/src/audio_service/lesson/jobs.py (phác thảo, không phải mã chạy được nguyên văn)
class JobRunner:
    def __init__(self, stage_download, stage_model, mark_failed, download_slots: int = 2) -> None:
        self._dl = ThreadPoolExecutor(max_workers=download_slots, thread_name_prefix="dl")
        self._q: queue.Queue[str | None] = queue.Queue()
        self.model_gate = threading.Lock()          # dùng chung với extend-end
        self._stage_download, self._stage_model, self._mark_failed = stage_download, stage_model, mark_failed
        self._worker = threading.Thread(target=self._loop, name="model-worker", daemon=True)

    def start(self) -> None: self._worker.start()
    def submit(self, lesson_id: str) -> None: self._dl.submit(self._run_download, lesson_id)

    def _run_download(self, lesson_id: str) -> None:
        try:
            self._stage_download(lesson_id)          # đặt status downloading, xong đặt queued
            self._q.put(lesson_id)
        except BaseException as exc:                 # bao gồm yt-dlp lỗi
            self._mark_failed(lesson_id, exc)

    def _loop(self) -> None:
        while (lesson_id := self._q.get()) is not None:
            with self.model_gate:
                try: self._stage_model(lesson_id)    # separating..analyzing -> ready
                except BaseException as exc: self._mark_failed(lesson_id, exc)
```
**Test (không cần model):** tiêm `stage_*` giả dùng `threading.Event`; khẳng định (a) job 2 vào `downloading` khi job 1 đang ở `separating` (không chặn), (b) hai job không bao giờ ở bước model cùng lúc, (c) thứ tự FIFO. Đây là bằng chứng tự động cho success criterion 2.

### Pattern 1b: Tách `pipeline.run_lesson` mà không vỡ test/smoke
`run_lesson(url, …)` hiện tạo `lesson_id`, gọi `fetch_info`, ghi `queued`, rồi chạy tất cả `[VERIFIED: pipeline.py]`. `tests/test_pipeline.py` (≈15 lời gọi) và `scripts/smoke_lesson.py` phụ thuộc chữ ký này. Giữ nguyên `run_lesson` như wrapper mỏng và tách:
- `create_lesson(url, start, end, deps) -> Lesson` (parse URL, `fetch_info`, ghi `queued`) — dùng cho `POST /lessons`.
- `stage_download(lesson_id, deps)` và `stage_model(lesson_id, deps, timer)` đọc `lesson.json` + `range`; `retry` gọi lại cặp này cho cùng `lesson_id`.
- **Rebuild khi retry (Pitfall 5):** dựng `Lesson` mới từ dict đã bỏ hẳn `error`/`audioQuality`/`segments`, không dùng `model_copy(update={"error": None})`.
- Khi vào `analyzing` thì `rmtree(seg/)` rồi ghi lại (nếu D-04 đổi số câu, `.npz` cũ sẽ mồ côi).
- Mã lỗi step: `LessonError.step = lesson.status` lúc lỗi (đã có); step có thể là `queued` (chờ cổng) → UI cần fallback prefix "Không xử lý được bài" cho step ngoài 5 bước.

### Pattern 2: `lesson.json` là nguồn sự thật, ghi tuần tự theo từng lesson
- **Khoá theo lesson:** `dict[str, threading.Lock]` (hoặc `functools.lru_cache`-ed factory) cho mọi read-modify-write ngoài pipeline (`PATCH` text, `extend-end`, `translate`) — hai request cùng lúc không được ghi đè nhau. Atomic `write_json_atomic` đã có `[VERIFIED: contract_io.py]`.
- **2b. "Sửa câu":** chỉ cho khi lesson `ready`. Quy tắc tối thiểu, không vỡ contract: tách `text` mới theo khoảng trắng; **nếu số token = `len(words)`** thì gán 1:1 vào `words[i].text`, giữ nguyên `start/end/asrProb/ipa`; **nếu khác** thì giữ `words` cũ và chỉ đổi `segment.text` (hiển thị), đồng thời bỏ `ipa` của các từ không còn ánh xạ tin cậy (Open Q: có cần realign không). Luôn xoá `translation` (D-16).
- **2c. `extend-end`:** `endExtraMs += 300` (PLY-05) ghi ngay (phát lại dùng `end + pad + extra` tức thì), rồi tính lại F0/energy/PPG của câu đó cho cửa sổ mới và ghi lại `seg/{i}.npz` + IPA, **dưới `model_gate`** (cần wav2vec2). Đồng bộ + nút ở trạng thái pending là đủ; nếu cổng đang bận bởi job tạo bài thì request chờ (tới ~2 phút) — chấp nhận hoặc trả "đang bận" (Open Q9). Tính "cũ" phát hiện được: `.npz` lưu `window` `[VERIFIED: pipeline.py:284]`, so với `segment_window(...)` hiện tại.

### Pattern 3: XState machine thuần, actor tiêm vào, test trước UI (PLY-02)
- File `apps/web/lib/player/playerMachine.ts` **không import DOM, React, fetch**. Mọi tác dụng phụ là *actor* khai báo trong `setup({ actors })` (stub mặc định) và được thay thế bằng `playerMachine.provide({ actors: {...} })` ở UI (thật) hoặc test (giả).
- Trạng thái: `idle`, `previewing` (phím `O`, phát một lần, không ghi), `playing` (invoke `playSample`, lặp ×N trong actor, `onDone → recording`), `recording` (invoke `record` là `fromCallback`: `sendBack` `LEVEL`/`SPEECH_STARTED`/`SILENCE`, trả blob qua `STOPPED`; `after: { recordDelay: 'stop' }` với `delays.recordDelay = sentenceMs × recordFactor`), `scoring` (invoke `uploadAttempt` `fromPromise`; P1 = upload), `reviewing` (con: `idle | original | yours | both`), `noVoice`, `error`. `GOTO(index)`/`NEXT`/`PREV` hợp lệ ở mọi trạng thái trừ `recording`/`scoring` (PLY-04: bấm hàng chọn câu "dừng phát").
- `context`: `segmentIndex`, `repeat`, `rate`, `recordFactor`, `recordings: Record<number, {blob, durationMs, attempt}>`, `lastError`. Hủy mềm: `fromPromise` nhận `signal` để huỷ khi rời state `[CITED: stately.ai promise-actors]`; timer `after` tự huỷ khi thoát state `[CITED: stately.ai delayed-transitions]`.
- **Test** (vitest, môi trường `node`, không DOM): `createActor(machine.provide({actors:{playSample: fromPromise(async()=>{}), record: fromCallback(...)…}}))`, `actor.send`, `waitFor(actor, s => s.matches('reviewing'))`; các transition tối thiểu cần phủ: idle→playing→recording→scoring→reviewing; Space dừng sớm ghi; `STOPPED` với blob không tiếng → `noVoice`; upload reject → `error` và **`recordings[i].blob` còn nguyên**; `R` từ reviewing/noVoice/error → `recording`; `NEXT` ở câu cuối bị chặn; `GOTO` trong `recording` bị bỏ qua.
```ts
// Source: stately.ai docs (setup + provide + waitFor) — hình dạng, không phải mã nguyên văn
export const playerMachine = setup({
  types: { context: {} as PlayerContext, events: {} as PlayerEvent, input: {} as PlayerInput },
  actors: { playSample: fromPromise<void, PlaySampleInput>(async () => {}), /* stub */
            record: fromCallback<PlayerEvent, RecordInput>(() => () => {}),
            uploadAttempt: fromPromise<AttemptAck, UploadInput>(async () => { throw new Error('not provided') }) },
  delays: { recordDelay: ({ context }) => context.sentenceMs * context.recordFactor },
}).createMachine({ /* idle → playing → recording → scoring → reviewing | noVoice | error */ });
// UI: const actor = useActorRef(playerMachine.provide({ actors: { playSample: realPlaySample(videoEl), … } }), { input })
```

### Pattern 4: Phát đoạn câu chính xác (PLY-03)
- Bắt đầu: `video.currentTime = start − padMs/1000` (kẹp ≥ 0), `playbackRate = rate`, `play()`. Dừng: vòng `requestAnimationFrame` so `video.currentTime ≥ end + padMs/1000 + endExtraMs/1000` (sai số ≤ ~16 ms). **Không dùng `timeupdate`** (tần suất 4–66 Hz, trễ tới ~250 ms, vượt cả biên đệm 100–200 ms) `[ASSUMED: HTML spec behaviour]`.
- Lặp ×N: sau mỗi lần dừng, `currentTime` về đầu và `play()` lại, nghỉ ngắn cố định (vd 300 ms) để người nghe tách lần; chip "lần i/n" lấy từ actor `sendBack`.
- Phát cần cử chỉ người dùng (autoplay policy): luôn bắt đầu từ click/phím; **bản machine tự chuyển `playing → recording` không cần phát gì thêm nên an toàn**.
- `preservesPitch` mặc định true trên trình duyệt hiện đại cho `playbackRate` 0.75; Safari cũ cần `webkitPreservesPitch` `[ASSUMED]`.
- Dọn dẹp: huỷ rAF, `pause()`, bỏ listener trong hàm cleanup của actor.

### Pattern 5: Ghi âm
**5a. Client.**
- `getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 } })`. Mặc định Chrome bật AEC/NS/AGC làm biến dạng năng lượng và đường nét ngữ điệu — thứ Phase 3 sẽ so với bản gốc `[CITED: blog.addpipe.com/getusermedia-audio-constraints]`; hỗ trợ constraint khác nhau theo trình duyệt (A4), nên **đặt cờ nhưng không dựa vào nó**.
- MIME: `['audio/webm;codecs=opus','audio/mp4','audio/webm']` đi qua `MediaRecorder.isTypeSupported`, bản đầu tiên được hỗ trợ; Safari ≤ 18.3 chỉ `audio/mp4` (AAC), Safari 18.4+ ghi được webm/opus `[CITED: testmuai.com mediarecorder-browser-support, buildwithmatija.com]`. Backend nhận cả hai (Pattern 5b).
- Mức âm + im lặng: `AudioContext` → `createMediaStreamSource(stream)` → `AnalyserNode.getFloatTimeDomainData` mỗi frame → RMS → dB. Ước lượng nền ồn trong 300 ms đầu; "đã có tiếng" khi RMS > nền + 10 dB; im lặng 1 s sau khi đã có tiếng → `SILENCE`. Hàm này là **hàm thuần** `(samples, state) → state` để test bằng vitest; chỉ vòng rAF/`getFloatTimeDomainData` nằm trong actor DOM.
- React 18 StrictMode (Next dev) chạy effect hai lần: cleanup phải `stream.getTracks().forEach(t => t.stop())`, `audioContext.close()`, `recorder.state !== 'inactive' && recorder.stop()`, thu hồi `URL.createObjectURL`. Quên → đèn micro không tắt.
- Blob đặt vào `context.recordings[segmentIndex]` (D-07), phát bằng `new Audio(URL.createObjectURL(blob))`; "Lần lượt" (B) = phát bản gốc xong rồi phát blob.

**5b. Backend `normalize.py` + `POST …/attempts`.**
- Giới hạn: `Content-Length` và đọc theo khúc, tối đa **10 MB** và thời lượng ≤ **60 s** (câu tối đa ~9 s × `recordFactor` ≤ 2.0 + dư) — Starlette không giới hạn kích thước file upload mặc định `[ASSUMED]`, phải tự chặn.
- Ghi vào file tạm trong `DATA_DIR/tmp/` (mkdtemp, xoá trong `finally`), **không** pipe stdin: `mp4` thường cần seek để đọc `moov` ở cuối. Đã chạy thử trên máy này: webm/opus, mp4/aac và fragmented mp4 đều ra WAV 16 kHz mono (`16000,1,2.000000`/`2.043375` s) `[VERIFIED: local run]`.
- **Chặn demuxer lạ:** sniff magic bytes (`1A 45 DF A3` → `-f matroska,webm`; `ftyp` ở offset 4 → `-f mov,mp4,m4a,3gp,3g2,mj2`; `OggS`/`RIFF....WAVE` nếu muốn) rồi truyền `-f <demuxer>` trước `-i`; ngoài hai định dạng này → 415. Đã chạy thử: playlist `.m3u8` trỏ `file:///etc/hosts` bị ffmpeg 9.0.2 từ chối khi tự dò, và với `-f matroska,webm` thì dừng ngay ở "EBML header parsing failed" `[VERIFIED: local run]` — kiểm soát này là phòng thủ nhiều lớp, không dựa vào hành vi mặc định của một phiên bản ffmpeg.
- Lệnh: `ffmpeg -nostdin -loglevel error -y -f <demux> -i <tmp> -vn -ac 1 -ar 16000 -c:a pcm_s16le -f wav <out.wav>`; **không** loudnorm/AGC (giữ nguyên động học cho Phase 3). argv list, không shell, như `audio_io.extract_audio`.
- VAD (REC-03) `vad.py`: đọc WAV → float32, `frame_energy` (đã có, 10 ms/25 ms) → dB; `noise = percentile 10`; voiced frame = `dB > max(-50, noise + 12)`; `voiced_ms = 10 × (số frame)`; `voiced = voiced_ms ≥ 150` **và** có ít nhất một đoạn liên tục ≥ 100 ms. **Ngưỡng là `[ASSUMED]`** (A1), cần chỉnh bằng micro thật ở UAT; đưa hằng số lên đầu file và test bằng tín hiệu tổng hợp (im lặng, nhiễu thấp, tone, đoạn giọng cắt từ `vocals.wav` của video smoke).
- `INSERT` lượt ghi trong `BEGIN IMMEDIATE`: `attempt = COALESCE(MAX(attempt),0)+1` theo `(lesson_id, segment_index)`; mỗi upload (kể cả không tiếng) tăng `attempt` (Open Q7). Xoá WAV tạm trong `finally`; nếu `saveForEval` thì ghi `DATA_DIR/eval_clips/{lessonId}_{index:04d}_{attempt:02d}.wav` + `.json` sidecar (lessonId, segmentIndex, attempt, text câu).

### Pattern 6: IPA từ PPG (D-14/D-15) — đã chạy trên video smoke
Dữ liệu: `seg/{index:04d}.npz` có `ppg (T,392)` softmax, `window=[w_start,w_end]` (giây tuyệt đối) và `ppg_fps=50.0` `[VERIFIED: pipeline.py:284-287]`; vocab `facebook/wav2vec2-lv-60-espeak-cv-ft/vocab.json` có 392 token, `<pad>`=0 là blank, `<s>/</s>/<unk>`=1..3 `[VERIFIED: local run]`. Token có thể nhiều ký tự (`aɪ`, `oʊ`, `iː`, `ɑː`); **không có `ˈ`/`ˌ` và không có token ranh giới từ** `[VERIFIED: local run: 'stress marks in vocab: []']`.
Thuật toán (đúng tinh thần D-14, thêm hai chi tiết đã đo):
1. Giải mã tham lam **cả câu một lần**: argmax từng frame, gộp frame lặp, bỏ `{0,1,2,3}` → danh sách `(frame, token, prob)`.
2. Gán mỗi phone cho từ có khoảng `[start,end)` (đổi sang frame: `(t − window_start) × 50`) **nới ±2 frame (40 ms)**; trùng thì chọn từ chứa frame. Nới ±2 giảm số từ rỗng 27 → 20/577; tăng thêm gần như không đổi `[VERIFIED: local run]`.
3. `ipa = "".join(tokens)`; độ tin cậy từ = **trung bình `prob` của các frame phát phone** (không phải trung bình max-prob trên mọi frame: CTC peaky, ~78% frame là blank nên số đó luôn ~0.94 và vô nghĩa `[VERIFIED: local run: blank_frac median 0.78, mean_all p50 0.94]`).
4. Ẩn (omit `ipa`, UI hiện "—") khi không có phone hoặc độ tin cậy < ngưỡng. **Đề xuất ngưỡng 0.7** (Liam duyệt, D-15). Chỉ số đo trên 577 từ của video smoke, dùng espeak-ng G2P *chỉ làm thước đo ngoại tuyến* (không phải nguồn của IPA, giữ nguyên tắc):

| Ngưỡng | Từ giữ | Giống từ điển (từ giữ) | Giống từ điển (từ ẩn) |
|--------|--------|------------------------|------------------------|
| 0.5 | 494 | 0.70 | 0.21 |
| 0.6 | 459 | 0.71 | 0.31 |
| **0.7** | **394 (68%)** | **0.74** | **0.40** |

Kết luận thật thà cho Liam: IPA từ PPG trên video thoại nhanh có nhiều sai lệch ranh giới (vd "Hot" → `/haɪ/`, "Hey," → `/ɹɑːsɛ/`), phần do Whisper timestamp lệch, phần do nói thật sự rút gọn. Ghi chú "nhận dạng tự động" là bắt buộc, không hứa hẹn độ đúng. **UI-SPEC có ví dụ `ˈɑnɪstli` (có dấu trọng âm) — mô hình này không thể sinh `ˈ`**; ví dụ chỉ mang tính minh hoạ (Open Q4).
Tính lại: đổi `text` (nếu realign) hoặc `endExtraMs` → chạy lại bước 1–4 từ `.npz` (không cần model, vài ms); riêng `endExtraMs` còn phải tính lại `.npz` (cần wav2vec2). Vocab nạp bằng `huggingface_hub.hf_hub_download(PPG_REPO, "vocab.json")` (đã có trong cache; không thêm tải mới ngoài `PPG_ALLOW_PATTERNS` đã chứa `vocab.json` `[VERIFIED: models.py]`).

### Pattern 7: Settings, API key, `.env`, trạng thái hệ thống
- **Thứ tự ưu tiên `dataDir` (đề xuất, ghi vào ADR):** `settings.json.dataDir` (nếu file có khoá) > `DATA_DIR` (env/.env) > mặc định `~/shadowenglab-data`. Giải quyết **một lần lúc khởi động** (`data_root()` đã `lru_cache` `[VERIFIED: config.py]`) ⇒ D-12 "áp dụng sau restart" xảy ra tự nhiên. `GET /settings` trả giá trị **đã lưu**, `GET /system/status` trả `activeDataDir` để S8 hiện chênh lệch ("dữ liệu cũ vẫn ở …"). Test cần ghi đè thư mục config bằng biến môi trường (`SHADOWENGLAB_CONFIG_DIR`) để không đụng `~/.config` thật; fixture `data_dir` hiện chỉ đặt `DATA_DIR` + `cache_clear()` `[VERIFIED: tests/test_api.py]`.
- **Key:** `set_openai_key(key)`: validate `^[A-Za-z0-9_\-]{20,256}$` (chặn newline/`=`/khoảng trắng → không thể chèn thêm biến vào `.env`), `dotenv.set_key(REPO_ROOT/".env", "OPENAI_API_KEY", key, quote_mode="never")`, `os.chmod(…, 0o600)`, rồi `os.environ["OPENAI_API_KEY"] = key` (nạp nóng). `get_openai_key()` đọc `os.environ` rồi `dotenv_values`. `mask_key("sk-proj-…abcd") → "sk-…abcd"`. Không log, không đưa vào exception message, không trả về.
- **Kiểm tra:** `httpx.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=10)` → 200 hợp lệ (mới ghi `.env`), 401 không hợp lệ (không ghi), lỗi mạng/5xx → `{valid: null, reason: "network"}` (UI-SPEC: "Không kiểm tra được (không có mạng). Key chưa được lưu."). Key rỗng + đã có key → kiểm tra key đã lưu.
- **Dịch (D-16):** cùng httpx; gửi *chỉ text* câu mục tiêu + tối đa 2 câu trước/sau làm ngữ cảnh; đầu ra JSON `{"translation": "..."}` (structured output), cắt độ dài, validate bằng pydantic; text câu là dữ liệu không tin cậy (do Whisper/người dùng) nên đặt trong khối phân tách rõ ràng và không cho model gọi công cụ. **Tên model do Liam chốt ở PR** (hằng số trong `models.py`, như `WHISPER_REPO`): ứng viên đang có trong danh mục giá tháng 10/2026 là `gpt-5-nano`, `gpt-5-mini`, `gpt-5.4-nano` `[CITED: developers.openai.com/api/docs/models/gpt-5-nano, benchlm.ai/openai/api-pricing]`; họ GPT-5 là reasoning model (không nhận `temperature` tuỳ ý) `[ASSUMED]` ⇒ đọc tài liệu tham số của model đã chọn lúc hiện thực, đừng copy payload từ ví dụ cũ.
- **`GET /system/status`:** `{ models: {demucs, whisper, wav2vec2: 'missing'|'loading'|'ready'}, hasKey, maskedKey?, activeDataDir }`. "missing" = không thấy snapshot trong HF cache (`huggingface_hub.try_to_load_from_cache`/`scan_cache_dir`, không gọi mạng). Xem Pitfall 1 về "loading/ready".

### Pattern 8: Phục vụ video có Range
`GET /lessons/{lesson_id}/video`: đọc `videoId` từ `lesson.json` (client không bao giờ gửi `videoId`/đường dẫn), `video_asset_path(videoId,"video.mp4")` đã chặn traversal `[VERIFIED: config.py]`, trả `FileResponse(path, media_type="video/mp4")`; Starlette 1.7.0 trả 206/`Content-Range`/416 và `Accept-Ranges: bytes` `[VERIFIED: starlette/responses.py:321,364-388]`. Chỉ phục vụ khi lesson `ready` (404 nếu không). CORS: `<video src>` cross-origin không cần CORS (không dùng canvas/WebAudio trên video) — giữ `allow_origins=["http://localhost:3000"]`.

### Pattern 9: Quy trình thêm contract
Một PR contract riêng (Wave 0, Liam duyệt diff `schema/contracts.schema.json` — đúng D-19): thêm Zod (mỗi object `.meta({id})`, `io:"input"` nên field có default là optional), `make contracts`, fixture + test round-trip cho từng kiểu mới, `Schemas` trong `index.ts`. Bổ sung `generate.ts` yêu cầu mọi key của `Schemas` có `$defs` `[VERIFIED: generate.ts]`. Web phải `Schema.parse()` mọi response (CLAUDE: Zod ở mọi ranh giới I/O).

### Anti-Patterns to Avoid
- **Chạy pipeline trong request handler/threadpool của anyio** (làm nghẽn mọi endpoint).
- **Giữ model trong RAM giữa các job** (Pitfall 1) hoặc quên giải phóng `mlx_whisper.ModelHolder`.
- **`model_copy(update={"error": None})`** hay bất kỳ `None` cho field optional (ghi `null`, Zod `.optional()` từ chối) — Pitfall 5.
- **`timeupdate` để dừng đoạn mẫu**; **pipe ffmpeg từ stdin** cho mp4; **ffmpeg tự dò định dạng** trên file người dùng tải lên.
- **Đặt logic UI/DOM trong file machine** (UI-SPEC: UI chỉ đọc `state.value/context`).
- **Class `bg-primary/90`** (token là `var(--hex)`, không có opacity modifier) và **dùng `--score-*`** trong P1 (grep kiểm).
- **Trả key/`.env` về client**, hoặc ghi key chưa qua kiểm tra.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Range/206 cho video | handler đọc file + parse `Range` | `starlette.responses.FileResponse` | Đã xử lý single/multi range, `If-Range`, 416 `[VERIFIED: starlette 1.7.0]` |
| Giải mã webm/mp4 → WAV | parser container / codec | `ffmpeg` argv (đã có pattern ở `audio_io.extract_audio`) | Safari mp4/AAC, Chrome webm/opus, fragmented mp4 |
| Ghi `.env` giữ biến khác | đọc/ghi chuỗi thủ công | `dotenv.set_key` | Ghi qua file tạm + `os.replace`, giữ comment/biến khác |
| State machine trình phát | `useReducer` + cờ boolean | XState v5 `setup().createMachine` (ADR 0001) | Test transition không cần DOM; Phase 3 gắn `scoring` không đổi cấu trúc |
| Polling trạng thái job | `setInterval` + state tay | TanStack Query `refetchInterval: (q) => … ? 2000 : false` | Tự dừng khi xong, dedupe, giữ dữ liệu cũ khi refetch |
| Slider 2 thumb | `<input type=range>` x2 chồng nhau | shadcn `slider` (Radix) | Bàn phím (mũi tên, Shift) + ARIA sẵn (UI-SPEC) |
| Toast + nút "Thử lại" | tự dựng | `sonner` | UI-SPEC |
| Truy cập HF cache/vocab | tự đọc `~/.cache/huggingface` | `huggingface_hub.hf_hub_download` / `try_to_load_from_cache` | Layout snapshot/blobs là chi tiết nội bộ |
| Atomic JSON write | `open(...,'w')` | `contract_io.write_json_atomic` (đã có) | S1 poll file đang ghi |
| ULID, URL parse, đường dẫn an toàn | — | `python-ulid`, `parse_youtube_url`, `config.*_path` (đã có) | Đã được review ở Phase 1 |

**Key insight:** phase này chủ yếu là *nối dây* các khối đã có. Phần duy nhất cần mã mới "thật" là: hàng đợi job, VAD năng lượng, IPA từ PPG, và machine — cả bốn đều là hàm/lớp thuần nhỏ, test được không cần model.

## Common Pitfalls

### Pitfall 1: D-13 "nạp 3 model vào RAM" vượt RAM máy 8 GB
**What goes wrong:** warm-up giữ cả ba model resident ⇒ swap, UI/trình duyệt giật, Demucs/Whisper OOM.
**Evidence:** `footprint -p <pid>` trong một process: wav2vec2 trên MPS **2489 MB** → + whisper turbo (ModelHolder resident) **4618 MB** → + Demucs (5 s audio) **6048 MB**; sau `del` Demucs 4656 MB; sau xoá `ModelHolder.model` + `mx.clear_cache()` 2561 MB; sau `del` wav2vec2 481 MB `[VERIFIED: local run]`. (`ps -o rss` cho số sai vì bộ nhớ GPU thống nhất của Apple Silicon không nằm trong RSS; **đừng dùng RSS để kiểm tra.**) Máy có 8589934592 byte RAM `[VERIFIED: sysctl hw.memsize]`; Phase 1 Pitfall 10 đã cảnh báo cùng điều này.
**How to avoid:** diễn giải D-13 "warm-up" thành **load → 1 suy luận mẫu → giải phóng, tuần tự từng model** (làm nóng page cache của đĩa, xác nhận load được), trạng thái "Model đang nạp…" kéo dài vài giây đến khi cả ba xong, rồi `ready`; **không** giữ resident. Nếu Liam muốn `extend-end` nhanh, giữ riêng wav2vec2 (≈ 2.5 GB) là mức tối đa chấp nhận được. Cần Liam duyệt cách diễn giải này (Open Q1).
**Warning signs:** `memory_pressure`/Activity Monitor đỏ, UAT "tạo 2 bài liên tiếp" chậm bất thường.

### Pitfall 2: `mlx_whisper.ModelHolder` giữ model sau khi `transcribe` xong
`ModelHolder.model`/`model_path` là thuộc tính lớp, `get_model` chỉ nạp khi `None` `[VERIFIED: mlx_whisper/transcribe.py:50-58]`. Trong script smoke, process thoát nên không ai để ý; trong FastAPI dài hơi, ~2.1 GB bị giữ vĩnh viễn. `deps.free_memory` hiện chỉ `gc.collect()` + `torch.mps.empty_cache()` `[VERIFIED: separate.py]`. **Fix:** sau `transcribe_words`, `sys.modules["mlx_whisper.transcribe"].ModelHolder.model = None; .model_path = None; gc.collect(); mx.clear_cache()` (đã chạy thử: 4656 → 2561 MB). Đặt trong `free_memory` thật + test kiểm `ModelHolder.model is None` sau stage.

### Pitfall 3: `video.mp4` tải về là AV1 + Opus
`ffprobe` file smoke: `codec_name=av1` (854×480) + `opus`, `compatible_brands=isomav01iso2mp41` `[VERIFIED: ffprobe]`, vì `_FORMAT = "bv*[height<=480]+ba/b[height<=480]/b"` `[VERIFIED: download.py:22]` rơi vào format 397 (AV1) + 251 (Opus). Chrome phát được; Safari trên M1 không giải mã phần cứng AV1 và Opus-trong-mp4 hỗ trợ không đồng đều `[ASSUMED: A5]` ⇒ `<video>` đen/không tiếng (PLY-01 vỡ). Selector `"bv*[height<=480][vcodec^=avc1]+ba[acodec^=mp4a]/b[height<=480][vcodec^=avc1]/bv*[height<=480]+ba/b[height<=480]/b"` đã được yt-dlp chọn đúng `135 (avc1.4D401E) + 140 (mp4a.40.2)` cho video smoke `[VERIFIED: local run]`.
**How to avoid:** đổi `_FORMAT` (đây là việc ở rìa pipeline, không phải đổi model), thêm bước `ffprobe -select_streams v:0 -show_entries stream=codec_name` sau tải; nếu không phải `h264` thì transcode `ffmpeg -c:v libx264 -preset veryfast -crf 26 -c:a aac` (480p ngắn, vài chục giây) làm dự phòng. Cache hiện có (bài đã tạo ở Phase 1) giữ AV1 ⇒ `Tải lại video` (D-17) nên xoá `video.mp4` rồi tải lại. Hỏi Liam trình duyệt chính (Open Q3b).

### Pitfall 4: Demucs chạy trên toàn bộ video thay vì range
`run_lesson` đọc `audio.wav` cả video (44.1 kHz, stereo, float32) và gọi `deps.separate` rồi ghi `vocals.wav`/`no_vocals.wav` cache theo `videoId` `[VERIFIED: pipeline.py]`. Video 1 giờ = 1.27 GB đầu vào + 4 stem × 1.27 GB đầu ra + bản sao `no_vocals` ⇒ vượt 8 GB, và Demucs ≈ 42 s / 5 phút (bảng smoke) ⇒ ~8.5 phút cho 1 giờ, phá ngân sách "5 phút" dù người dùng chỉ chọn 5 phút. LES-02 tồn tại chính để tránh điều này.
**How to avoid:** `extract_audio` và tách giọng chỉ trên `[range.start − 1 s, range.end + 1 s]`, cache theo `(videoId, start_ms, end_ms)` dưới `videos/{videoId}/stems/{start}-{end}/…`; mọi mốc cắt tuyệt đối trừ `base_offset`. Đây chạm D-07/D-08 (cache theo `videoId`, vẫn giữ `video.mp4` theo `videoId`; chỉ stems theo range) ⇒ cần Liam đồng ý (Open Q3). Với video ≤ 6 phút (toàn bộ) thì hành vi giống hiện tại.

### Pitfall 5: `null` ≠ vắng mặt khi dựng lại Lesson (retry, rebuild)
`error: LessonError | None = None` `[VERIFIED: contracts_gen.py:255]` nhưng `dump_contract` dùng `exclude_unset=True`: gán `error=None` qua `model_copy(update=…)` đánh dấu "đã set" ⇒ ghi `"error": null` ⇒ Zod `.optional()` ở web **từ chối cả lesson** (S1 vỡ). `contract_io.py` đã ghi chú nguyên tắc này `[VERIFIED: contract_io.py docstring]`. **Fix:** rebuild từ dict đã `pop("error")`/`pop("audioQuality")`. Thêm test: lesson `failed` → retry → JSON không còn khoá `error` (parse lại bằng Zod qua `cli-parse.ts`).

### Pitfall 6: `python-multipart` chưa cài
`grep uv.lock` không thấy `python-multipart`; FastAPI báo lỗi khi khai báo `UploadFile`/`Form` mà thiếu gói `[CITED: fastapi.tiangolo.com/tutorial/request-forms-and-files]`. Lỗi chỉ lộ khi import router `attempts`, nên test import app phải nằm trong CI sớm.

### Pitfall 7: CORS chỉ GET + yêu cầu "simple" từ trang web khác
`allow_methods=["GET"]` `[VERIFIED: main.py:30]` ⇒ POST/PUT/PATCH từ `localhost:3000` bị preflight chặn, cần mở rộng. Mặt trái: `POST multipart` tới `127.0.0.1:8000` là "simple request" (không preflight) nên **một trang web bất kỳ trong trình duyệt của Liam có thể gửi multipart** tới API. Hậu quả giới hạn (tạo lượt ghi rác) nhưng rẻ để chặn: thêm `TrustedHostMiddleware(allowed_hosts=["127.0.0.1","localhost"])` (chống DNS rebinding) và kiểm `Origin` ∈ `{http://localhost:3000}` cho mọi method ≠ GET/HEAD/OPTIONS. Mọi endpoint ghi khác dùng JSON `Content-Type` ⇒ luôn qua preflight.

### Pitfall 8: `uvicorn --reload` trong `make dev-api` giết job đang chạy
`dev-api` chạy `uvicorn … --reload` `[VERIFIED: Makefile]`; sửa bất kỳ file Python nào làm restart process ⇒ job dở thành `failed/bị gián đoạn` (D-03) và warm-up chạy lại. Đúng thiết kế nhưng gây hiểu nhầm lúc UAT: **UAT phải chạy khi không sửa code**; ghi vào checklist. Tuyệt đối không dùng `--workers N` (hàng đợi/khoá nằm trong process).

### Pitfall 9: `Segment.text` ≠ `join(words.text)` sau "Sửa câu"
Phase 3/5 dùng `words[]` (ranh giới, prominence, `ref_unclear`); nếu text đổi số từ mà `words` giữ nguyên, hai nguồn lệch nhau. Quy tắc ở Pattern 2b giữ bất biến "words[i] là từ thật ở audio"; text hiển thị tự do. Ghi rõ trong ADR để Phase 3/5 không giả định `text == " ".join(words)`.

### Pitfall 10: Heuristic gộp câu không giới hạn số từ
`_merge_short` chỉ kiểm `MAX_MERGED_S` `[VERIFIED: segment.py:129]`; baseline đã có câu tới **23 từ** (> `MAX_WORDS = 15`, `segment.py:23`), tăng `MIN_DUR_S` lên làm tệ hơn (29 từ). Xem bảng D-04 dưới "Code Examples" và Open Q5.

### Pitfall 11: Tailwind 3 + token `var(--hex)` + shadcn mặc định
Đã nêu trong UI-SPEC (không opacity modifier, bỏ `/90` ở Button, ghi đè `hsl()` của init, `-b radix` không `-d`). Bổ sung kiểm chứng: Figtree chỉ có subset `latin`/`latin-ext` `[VERIFIED: next/dist/compiled/@next/font/dist/google/font-data.json]` (JetBrains Mono và Noto Sans có `vietnamese`) ⇒ khai Noto Sans làm font thứ hai là bắt buộc để chữ có dấu không rơi sang font hệ thống tuỳ ý. Noto Sans `latin-ext` có bao phủ hết ký hiệu IPA trong vocab (vd `ᵻ`, `ɑ̃`) hay không là `[ASSUMED]` (A6) — kiểm bằng một trang thử render toàn bộ 392 token.

### Pitfall 12: Phím `Space` cuộn trang / kích hoạt nút đang focus
`Space` mặc định cuộn trang và click nút đang focus. Quy tắc UI-SPEC (nút bấm chuột `blur()` khi pointer-up; bỏ qua phím khi focus ở `input/textarea/select/[role=combobox|listbox]` hoặc trong `[role=dialog]`) phải ở **hàm thuần** `shouldHandleShortcut(event)` + `preventDefault()` có điều kiện, có test; đây là nơi tiêu chí "30 câu chỉ bằng chuột và chỉ bằng bàn phím" dễ vỡ nhất.

### Pitfall 13: SQLite trong FastAPI đa luồng
Mỗi request/luồng mở `sqlite3.connect(path, timeout=5)` riêng (không chia sẻ connection giữa luồng, `check_same_thread` mặc định False không có nghĩa là an toàn); bật `PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON`; schema qua `PRAGMA user_version` (migration thật là HRD-05, hoãn). Đặt khoá duy nhất `PRIMARY KEY (lesson_id, segment_index, attempt)`.

### Pitfall 14: Poll làm remount lưới / trạng thái nhảy
`useQuery` với `refetchInterval` hàm: trả `2000` khi còn lesson ∉ {ready,failed}, ngược lại `false`; `placeholderData: keepPreviousData`; key thẻ = `lesson.id` (UI-SPEC). Danh sách trả bản **nhẹ** (không `segments`/`words`): 10 bài × ~100 KB mỗi 2 s là phung phí (Open Q2, shape `LessonListItem`).

### Pitfall 15: `yt-dlp` metadata cho preview
`fetch_info` hiện không đọc `channel`, `live_status`, `availability`; UI-SPEC cần tên kênh và chặn livestream/riêng tư. Đã xác nhận trên video smoke: `channel: HBO Max`, `live_status: not_live`, `availability: public` `[VERIFIED: local run]`. Thêm các field vào `VideoInfo`/`info.json` (đọc `.get()` để không vỡ cache cũ thiếu khoá). Lỗi yt-dlp (`DownloadError`) ánh xạ về mã `unavailable` với thông báo cố định tiếng Việt, **không** lộ message gốc/đường dẫn. Nhận diện link kênh (`/@…`, `/channel/…`, `/c/…`, `/user/…`) cần mã riêng `channel_url`: `parse_youtube_url` hiện chỉ raise `InvalidYoutubeUrl` chung `[VERIFIED: urls.py]`.

## Code Examples

### D-04 — số liệu thực đo trên video smoke (62 câu baseline, 577 từ)
Chạy `split_sentences` với các hằng số khác nhau trên danh sách từ của `lesson.json` vừa tạo (script ở scratchpad, không commit) `[VERIFIED: local run]`:

| `MIN_DUR_S` | `MAX_MERGED_S` | cap từ khi gộp | Số câu | < 3 s | 3–8 s | > 8 s | Median (s) | Từ nhiều nhất |
|-------------|----------------|----------------|--------|-------|-------|-------|-----------|--------------|
| **1.5 (hiện tại)** | 9.0 | — | 62 | 39 | 23 | 0 | 2.51 | 23 |
| 2.0 | 8.0 | — | 47 | 14 | 33 | 0 | 4.10 | 23 |
| 2.5 | 8.0 | — | 42 | 9 | 33 | 0 | 4.57 | 29 |
| 3.0 | 8.0 | — | 39 | 5 | 34 | 0 | 4.86 | 29 |
| 3.0 | 8.0 | 15 | 54 | 17 | 37 | 0 | 3.61 | 15 |
| **3.0** | **8.0** | **18** | **46** | **8** | **38** | **0** | **4.09** | **18** |
| 3.0 | 8.0 | 20 | 44 | 9 | 35 | 0 | 4.53 | 20 |

Đề xuất: `MIN_DUR_S = 3.0`, `MAX_MERGED_S = 8.0`, **thêm `MAX_MERGED_WORDS = 18`** (chỉ áp dụng khi gộp; quy tắc cắt > 15 từ giữ nguyên). Kết quả: 38/46 (83%) câu rơi vào 3–8 s, không câu nào > 8 s, không câu nào > 18 từ. Cap 15 đúng chữ product.md cho 37/54 (69%). 46 câu / 5 phút ≈ 9.2 câu/phút, nằm trong khoảng "8–12 câu mỗi phút" của product.md M1. Video smoke là sitcom nhiều câu thoại ngắn; video phỏng vấn sẽ ít câu ngắn hơn. Cập nhật `tests/test_segment.py`, báo bảng "trước/sau" trong SUMMARY/PR. Công thức ước lượng của S2 (`d/8–d/5` câu, UI-SPEC G16) cho 5 phút ra 37–60 câu — vẫn bao 46.

### Baseline thời gian tạo bài (đo lại hôm nay, DATA_DIR sạch, `make smoke END=300`)
`download 3.48 · extract_audio 0.51 · demucs 42.01 · quality 0.08 · resample 0.13 · whisper 42.06 · segment 0.00 · ppg 20.67 · f0 1.09 · write_features 0.81 · total 110.87 s`, wall 111.4 s, 62 câu, `nonVocalRatio` 1.775e-02 → `clean` `[VERIFIED: local run]`. Còn ~189 s dư so với 300 s. IPA (argmax trên `.npz`) cộng < 1 s. Hai bài 5 phút tạo liên tiếp: bài 2 xong ≈ 2 × 111 ≈ 222 s kể từ lúc tạo bài 1 (tải bài 2 chạy song song với model bài 1) — vẫn < 300 s; từ bài thứ 3 trở đi vượt, LES-05 chỉ nói về một video.

### Giải mã IPA cho một câu (thuần, hàm mảng vào/ra)
```python
# services/audio/src/audio_service/lesson/ipa.py (phác thảo; kiểu dữ liệu và tên do planner chốt)
BLANK_AND_SPECIAL = frozenset({0, 1, 2, 3})   # <pad>/<s>/</s>/<unk> trong vocab espeak [VERIFIED: vocab.json]

def ipa_for_segment(ppg: np.ndarray, window_start: float, fps: float,
                    words: Sequence[tuple[float, float]], inv_vocab: Mapping[int, str],
                    *, tol_frames: int = 2, min_conf: float = 0.7) -> dict[int, str]:
    """-> {word_index: ipa} chỉ gồm từ đủ tin cậy; từ vắng mặt = hiện '—'."""
    am, mx = ppg.argmax(1), ppg.max(1)
    emitted, prev = [], None
    for t, k in enumerate(am):
        if k != prev and int(k) not in BLANK_AND_SPECIAL:
            emitted.append((t, inv_vocab[int(k)], float(mx[t])))
        prev = k
    spans = [((s - window_start) * fps, (e - window_start) * fps) for s, e in words]
    per_word: list[list[tuple[str, float]]] = [[] for _ in words]
    for t, tok, p in emitted:
        inside = [i for i, (a, b) in enumerate(spans) if a - tol_frames <= t < b + tol_frames]
        if inside:
            i = min(inside, key=lambda i: 0 if spans[i][0] <= t < spans[i][1] else 1)
            per_word[i].append((tok, p))
    out = {}
    for i, toks in enumerate(per_word):
        if toks and float(np.mean([p for _, p in toks])) >= min_conf:
            out[i] = "".join(tok for tok, _ in toks)
    return out
```

### Chuẩn hoá bản ghi (REC-02) — `ffmpeg` argv, `-f` whitelist
```python
# services/audio/src/audio_service/lesson/normalize.py (phác thảo)
def sniff_demuxer(head: bytes) -> str | None:
    if head.startswith(b"\x1aE\xdf\xa3"): return "matroska,webm"
    if head[4:8] == b"ftyp": return "mov,mp4,m4a,3gp,3g2,mj2"
    return None                                           # -> HTTP 415

def normalize_to_wav16k(src: Path, dst: Path, demuxer: str) -> None:
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", demuxer, "-i", str(src),
           "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-f", "wav", str(dst)]
    subprocess.run(cmd, check=True, timeout=30)
```

### Poll S1 và provider (Next 14 app router)
```tsx
// Source: tanstack.com/query (polling + advanced-ssr), v5
'use client'
const { data } = useQuery({
  queryKey: ['lessons'],
  queryFn: fetchLessons,                       // Zod parse bên trong
  refetchInterval: (q) =>
    q.state.data?.some((l) => l.status !== 'ready' && l.status !== 'failed') ? 2000 : false,
  placeholderData: keepPreviousData,
})
```

### Dừng đoạn mẫu bằng rAF (không dùng `timeupdate`)
```ts
function playRange(video: HTMLVideoElement, startS: number, endS: number, rate: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    video.currentTime = Math.max(0, startS); video.playbackRate = rate
    let raf = 0
    const tick = () => { if (video.currentTime >= endS) { video.pause(); resolve() } else raf = requestAnimationFrame(tick) }
    signal.addEventListener('abort', () => { cancelAnimationFrame(raf); video.pause(); reject(new DOMException('aborted','AbortError')) })
    video.play().then(() => { raf = requestAnimationFrame(tick) }, reject)
  })
}
```

### Lifespan: đánh dấu job gián đoạn (D-03) và khởi động runner
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    recover_interrupted()          # quét lessons/*/lesson.json: status ∉ {ready,failed} -> failed{step,'bị gián đoạn'}
    ensure_schema()                # sqlite attempts
    app.state.runner = JobRunner(...); app.state.runner.start()
    threading.Thread(target=warm_up_models, daemon=True).start()   # load -> 1 suy luận -> giải phóng (Pitfall 1)
    yield
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `shadcn init` mặc định Base UI | `--base radix` rõ ràng (CLI 4.21.3) | 2026-03/07 | UI-SPEC đã khoá radix; không dùng `-d` |
| XState v4 `interpret`/`machine.transition` | v5 `createActor`, `getNextSnapshot`, `setup()`, `machine.provide()` | 2023-12 | Mọi ví dụ cũ dùng `interpret` là sai `[CITED: stately.ai migration]` |
| `@xstate/react` `useMachine(machine, {actions})` | truyền `machine.provide({...})` vào hook | v5 | Implementations không còn là tham số thứ hai `[CITED: stately.ai migration]` |
| Chat Completions | Responses API (`responses.parse`/`text.format`) | 2025–2026 | Dùng cho dịch nếu Liam chọn SDK; REST vẫn ổn định |
| yt-dlp tự chọn codec cao nhất | cần chỉ định codec khi trình duyệt đích hạn chế | — | Pitfall 3 |

**Deprecated/outdated:** `@app.on_event("startup")` (dùng `lifespan`) `[CITED: fastapi.tiangolo.com]`; `timeupdate` để dừng chính xác; Tailwind 4 cho dự án này (đã khoá 3.4).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Ngưỡng VAD (nền + 12 dB, ≥ 150 ms tổng, ≥ 100 ms liên tục, sàn −50 dB) đủ cho micro MacBook | Pattern 5b | Báo "không tiếng" oan hoặc bỏ sót; cần chỉnh ở UAT bằng micro thật |
| A2 | Ngưỡng IPA 0.7 là điểm khởi đầu hợp lý | Pattern 6 | Ẩn quá nhiều/ít từ; Liam duyệt (D-15) |
| A3 | Payload OpenAI cho dịch (Responses/structured output) và tham số của họ GPT-5 | Pattern 7 | Lỗi 400 lúc chạy; đọc tài liệu model đã chọn khi hiện thực |
| A4 | Hỗ trợ constraint `noiseSuppression/autoGainControl` khác nhau theo trình duyệt (Chrome ép tắt AEC mới tắt AGC) | Pattern 5a | Bản ghi vẫn bị AGC; chỉ ảnh hưởng chất lượng Phase 3, không vỡ P1 |
| A5 | Safari trên Apple M1 không phát AV1 trong mp4 và Opus-trong-mp4 không đồng đều | Pitfall 3 | Nếu Liam dùng Chrome thì đổi H.264 là nâng cấp tuỳ chọn, không phải sửa lỗi |
| A6 | Noto Sans `latin-ext` bao phủ mọi ký hiệu IPA của 392 token (`ᵻ`, `ɑ̃`, `ʁ`…) | Pitfall 11 | Một số phone hiện ô vuông; thêm font IPA (vd Noto Sans, Charis SIL) |
| A7 | Ánh xạ lỗi yt-dlp → mã `unavailable`/`live` đủ dựa vào `availability`/`live_status` + bắt `DownloadError` chung | Pitfall 15 | Thông báo lỗi kém chính xác (không vỡ) |
| A8 | `timeupdate` quá thưa cho biên đệm 100–200 ms; rAF đủ chính xác (±16 ms) | Pattern 4 | Dừng trễ/sớm vài chục ms; tăng `padMs` không giúp cho đuôi câu |
| A9 | Starlette không tự giới hạn kích thước file upload | Pattern 5b | Nếu có giới hạn riêng, kiểm tra vẫn vô hại |
| A10 | Permissions API `microphone` không hỗ trợ ở Firefox; Safari hỗ trợ từng phần | Pattern/UI | Trạng thái micro phải rơi về `unknown` (không banner) khi `query()` ném lỗi |
| A11 | Hầu hết video YouTube có biến thể avc1 ≤ 480p; còn không thì fallback transcode | Pitfall 3 | Bước transcode kéo dài 20–40 s cho video đó |
| A12 | `fromPromise` truyền `signal` để huỷ khi rời state (tài liệu chỉ nêu ví dụ `fetch`) | Pattern 3 | Hủy phát lặp phải tự quản `AbortController` trong actor |

## Open Questions

> Câu 1–6 nên hỏi Liam **trước Plan** (thay đổi cấu trúc task); 7–9 có thể chốt trong PR.

1. **D-13 warm-up vs 8 GB RAM.** Footprint đo: 2.5 / 4.6 / 6.0 GB (wav2vec2 / +whisper / +Demucs). Đề xuất: warm-up = load → 1 suy luận → giải phóng (không resident); tuỳ chọn giữ wav2vec2 resident. *Recommendation:* chấp nhận diễn giải "làm nóng rồi giải phóng". Cần Liam duyệt vì D-13 viết "nạp vào RAM".
2. **Contract bổ sung ngoài `AttemptAck`/`AppSettings`** (CONTEXT: "không tự thêm khái niệm", nhưng UI-SPEC G24 và các endpoint cần shape để web `parse` bằng Zod). Đề xuất danh sách tối thiểu, Liam duyệt ở PR contract: `VideoPreview {videoId, title, durationSec, channel?, thumbnailUrl?, existingLessonId?}`; `CreateLessonRequest {url, start?, end?}`; `LessonListItem {lesson (Lesson bỏ segments), segmentCount, practicedCount, firstUnpracticedIndex | null}`; `LessonProgress {lessonId, practicedIndexes[], attempts:[{segmentIndex,count}]}`; `SystemStatus {models{demucs,whisper,wav2vec2: missing|loading|ready}, hasKey, maskedKey?, activeDataDir}`; `OpenAiKeyCheckRequest {apiKey?}` / `OpenAiKeyCheckResult {valid: boolean|null, saved, reason?}`; `UpdateSegmentTextRequest {text}` (response = `Segment`); `ApiError {code, message}`. `extend-end`/`translate` trả `Segment`; eval-clip trả `AttemptAck`.
3. **Tách giọng theo range (Pitfall 4) và codec video (Pitfall 3).** (a) Đồng ý cache stems theo `(videoId, start, end)` thay vì toàn video (chạm D-07)? *Recommendation:* có. (b) Liam dùng trình duyệt nào? Nếu Safari thì đổi sang H.264/AAC là bắt buộc; Chrome thì vẫn nên đổi để chắc chắn.
4. **IPA không có dấu trọng âm** (vocab không có `ˈ`/`ˌ`), UI-SPEC có ví dụ `ˈɑnɪstli`. Chấp nhận hiển thị không dấu trọng âm và sửa ví dụ trong UI-SPEC/copy? Và chốt ngưỡng 0.7 + dung sai ±2 frame (D-15).
5. **D-04:** chốt `MIN_DUR_S=3.0`, `MAX_MERGED_S=8.0`, `MAX_MERGED_WORDS=18` (hay 15 đúng chữ product.md)? Cần cập nhật product.md M1 nếu 18.
6. **Tên model OpenAI cho dịch** (D-16, ứng viên `gpt-5-nano`/`gpt-5-mini`/`gpt-5.4-nano`) và cho phép dùng httpx thay vì SDK `openai`.
7. **Đánh số lượt & nút eval (D-05/D-09).** (a) Lượt không tiếng có tăng `attempt` không? Đề xuất: có (mỗi upload một dòng, `voiced=0`), UI "Lượt k" chỉ đếm lượt `voiced`. (b) "Lưu clip cho eval" sau khi đã upload: đề xuất `PUT …/attempts/{n}/eval-clip` gửi **lại blob** từ client (đúng D-07/REC-04: backend không giữ WAV), không tạo lượt mới.
8. **ADR bổ sung:** ngoài 0004 (D-17), nên có ADR cho (i) kiến trúc job runner + cổng model + diễn giải D-13, (ii) schema `attempts` + thứ tự ưu tiên `dataDir`, (iii) quy tắc "Sửa câu" (`text` ≠ `join(words)`). Gộp thành 1–2 ADR để PR nhỏ.
9. **`extend-end` khi cổng model bận** (job tạo bài đang chạy): chờ đồng bộ (tới ~2 phút) hay trả "đang bận, thử lại"? *Recommendation:* chờ có timeout 150 s + nút pending; `endExtraMs` đã lưu và phát lại dùng ngay.
10. **Trùng bài ("Video đã được tạo bài trước đó", UI-SPEC)** vs D-07 (nhiều bài trên một video, khác range). Đề xuất: "trùng" = cùng `videoId` **và cùng range** và không `failed`; preview trả `existingLessonId`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| macOS Apple Silicon, RAM | cả phase | ✓ | MacBookPro17,1 / Apple M1 / **8 GB** | — (ràng buộc cứng, xem Pitfall 1) |
| ffmpeg / ffprobe | REC-02, Pitfall 3, tải video | ✓ | 9.0.2 | — |
| espeak-ng | `make setup` check (D-25); đo ngoại tuyến IPA | ✓ | 1.52.0 | — (không cần lúc chạy, Phase 1 Pitfall 11) |
| Node / pnpm / uv | web, workspace, Python | ✓ | v24.16.0 / 11.9.0 / 0.12.10 | — |
| deno (JS runtime của yt-dlp) | tải YouTube | ✓ trong venv (`uv run`), không có trên PATH hệ thống | — | luôn chạy qua `uv run` |
| Model trong HF cache | pipeline | ✓ | Demucs `adefossez/HTDemucs`, `facebook/wav2vec2-lv-60-espeak-cv-ft`, `mlx-community/whisper-large-v3-turbo` | `make setup` |
| Mạng (YouTube, thumbnail `i.ytimg.com`, OpenAI) | tạo bài, preview, dịch, kiểm tra key | ✓ lúc nghiên cứu (yt-dlp chạy được) | — | không mạng: không tạo bài mới; tập bài cũ vẫn được; dịch/kiểm tra key báo lỗi mạng |
| `python-multipart` | upload | ✗ (chưa trong `uv.lock`) | — | **cài (Wave 0)**, không có đường vòng |
| Trình duyệt (Chrome/Safari) để UAT video/mic | PLY-01/REC | không thể dò từ shell | — | Liam xác nhận trình duyệt chính (Open Q3b) |
| `timeout` (GNU) | — | ✗ (macOS) | — | không dùng trong recipe/test (Phase 1 Pitfall 13) |

**Missing dependencies with no fallback:** `python-multipart` (cài ở Wave 0).
**Missing dependencies with fallback:** không có gì chặn ngoài mục trên.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (+ `fastapi.testclient`, httpx) cho Python; vitest ^4.1.11 cho web (thêm mới `apps/web`) |
| Config file | `services/audio/pyproject.toml` `[tool.pytest.ini_options]` (có sẵn); `apps/web/vitest.config.ts` — **Wave 0** |
| Quick run command | `cd services/audio && uv run --frozen pytest -x -q tests/<file>.py` · `pnpm --filter @shadowenglab/web test -- <file>` |
| Full suite command | `make test` (drift gate → `pnpm -r --if-present test` → pytest) `[VERIFIED: Makefile]` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SET-01/02 | `/system/status` trả model missing/loading/ready + `hasKey`; thiếu key vẫn `200` và tạo bài được | unit/API | `pytest tests/test_system_status.py` | ❌ Wave 0 |
| SET-03 | key sai định dạng bị 422 (không ghi `.env`); 200/401/lỗi mạng ánh xạ đúng (httpx mock); `.env` giữ biến khác, mode 0600; key không xuất hiện trong response | unit/API | `pytest tests/test_openai_key.py` | ❌ Wave 0 |
| SET-04 | `GET/PUT /settings` (mặc định khi thiếu file, validate `repeat`/`recordFactor`/`dataDir` tồn tại+ghi được, `accent` khoá); ưu tiên `dataDir` | unit/API | `pytest tests/test_settings_api.py` | ❌ Wave 0 |
| LES-01 | preview: URL kênh/không hợp lệ/livestream/riêng tư → `{code}`; `fetch_info` giả | unit/API | `pytest tests/test_videos_preview.py` | ❌ Wave 0 |
| LES-02 | range hợp lệ, mặc định 0–300 s; stems theo range (nếu Open Q3a duyệt) | unit | `pytest tests/test_pipeline.py -k range` | ✅ (mở rộng) |
| LES-03 | job 2 vào `downloading` khi job 1 ở bước model; không bao giờ hai job ở bước model cùng lúc; FIFO | unit (thread + Event) | `pytest tests/test_jobs.py` | ❌ Wave 0 |
| LES-04/05 | pipeline đầu–cuối + IPA; thời gian 5 phút | smoke (thủ công, mạng+model) | `make smoke` (≤ 300 s) | ✅ |
| LES-06 | `audioQuality` có trong list item | unit/API | `pytest tests/test_lessons_list.py` | ❌ Wave 0 |
| LES-07 | `retry` cùng `lessonId`; JSON sau retry không có khoá `error` (Zod parse lại); lifespan đánh dấu gián đoạn | unit | `pytest tests/test_jobs.py -k "retry or interrupted"` + `tests/test_contracts_roundtrip.py` | ❌ Wave 0 |
| PLY-01 | `GET …/video` trả 206 + `Content-Range`, 404 khi chưa `ready`, 416 range hỏng | API | `pytest tests/test_video_range.py` | ❌ Wave 0 |
| PLY-02 | các transition chính của machine (Pattern 3) | unit (vitest, node) | `pnpm --filter @shadowenglab/web test -- playerMachine` | ❌ Wave 0 |
| PLY-03 | rAF stop-at-end, lặp ×N, `rate` (actor với video giả) | unit | `pnpm --filter @shadowenglab/web test -- playRange` | ❌ Wave 0 |
| PLY-04 | `progress` + `firstUnpracticedIndex` từ SQLite; `PATCH` text xoá `translation`, giữ words khi cùng số token | unit/API | `pytest tests/test_progress.py tests/test_segment_edit.py` | ❌ Wave 0 |
| PLY-05 | `extend-end`: `endExtraMs += 300`, `.npz` `window` đổi, IPA tính lại (deps giả) | unit | `pytest tests/test_extend_end.py` | ❌ Wave 0 |
| PLY-06 | `ipa_for_segment` trên `.npz` tổng hợp: gán phone theo từ, nới ±2 frame, ẩn dưới ngưỡng, bỏ blank, không sinh `null` | unit | `pytest tests/test_ipa.py` | ❌ Wave 0 |
| PLY-07 | `shouldHandleShortcut` (bỏ qua input/select/dialog), bảng phím theo state | unit (vitest) | `pnpm --filter @shadowenglab/web test -- shortcuts` | ❌ Wave 0 |
| REC-01 | hàm thuần mức âm/im lặng 1 s (nền ồn, bắt đầu nói, dừng) | unit (vitest) | `pnpm --filter @shadowenglab/web test -- level` | ❌ Wave 0 |
| REC-02 | webm/mp4/fragmented mp4 → WAV 16 kHz mono (ffmpeg thật, tín hiệu tổng hợp); file lạ (m3u8, text) → 415 | unit/API | `pytest tests/test_normalize.py` (cần ffmpeg) | ❌ Wave 0 |
| REC-03 | VAD: im lặng/nhiễu thấp → `voiced=false`; tone/giọng → true; upload lỗi giữ blob (machine test) | unit | `pytest tests/test_vad.py` + machine test | ❌ Wave 0 |
| REC-04 | file tạm bị xoá; `saveForEval` ghi `eval_clips/` + sidecar; `PUT eval-clip` không tạo lượt mới | API | `pytest tests/test_attempts_api.py` | ❌ Wave 0 |
| UI khớp design (SC5) | không dùng `score-*`; token web = `docs/design/tokens.css`; font Vietnamese | unit (vitest) + thủ công | `pnpm --filter @shadowenglab/web test -- tokens` + `grep -R "score-" apps/web/components` | ❌ Wave 0 |
| SC3 | 30 câu chỉ chuột / chỉ phím | **thủ công UAT** (không tự động hoá được), có checklist | — | — |

### Sampling Rate
- **Per task commit:** test file liên quan (`pytest -x -q …` hoặc `vitest run <file>`), < 30 s.
- **Per wave merge:** `make test` (gồm drift gate contract) và `make lint`.
- **Phase gate:** `make test` + `make lint` xanh, `make smoke` ≤ 300 s, UAT thủ công (SC1–SC5) trước `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `apps/web/vitest.config.ts`, `package.json` script `test`, `lib/player/*.test.ts`, `tokens.test.ts` (đồng bộ `app/tokens.css` ↔ `docs/design/tokens.css`, theo UI-SPEC)
- [ ] `services/audio/tests/`: `test_jobs.py`, `test_attempts_api.py`, `test_normalize.py`, `test_vad.py`, `test_ipa.py`, `test_settings_api.py`, `test_openai_key.py`, `test_system_status.py`, `test_videos_preview.py`, `test_video_range.py`, `test_lessons_list.py`, `test_progress.py`, `test_segment_edit.py`, `test_extend_end.py`; cập nhật `test_segment.py` (D-04), `test_pipeline.py` (tách stage), `test_api.py` (CORS methods)
- [ ] Fixture dùng chung: `data_dir` (đã có) + `config_dir` (ghi đè thư mục settings), fixture tín hiệu tổng hợp (sine, nhiễu, im lặng) và `.npz` tổng hợp
- [ ] `uv add python-multipart httpx python-dotenv`; `shadcn init`; cài `vitest`
- [ ] Fixture contract cho mọi kiểu mới trong `packages/contracts/fixtures/` + round-trip

## Security Domain

`security_enforcement` đang bật (ASVS L1, block on high) — phase này mở nhiều ranh giới mới: upload file, ghi `.env`, URL → yt-dlp, gọi OpenAI.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (ứng dụng cá nhân, local, không đăng nhập) | — |
| V3 Session Management | no | — |
| V4 Access Control | limited | bind `127.0.0.1`, `TrustedHostMiddleware`, kiểm `Origin` cho method ghi (Pitfall 7) |
| V5 Input Validation | **yes** | Zod ở web (parse response), pydantic ở API; `parse_youtube_url` allow-list (đã có); regex id (`ULID_RE`, `VIDEO_ID_RE`); `index >= 0` và `< len(segments)`; giới hạn kích thước/thời lượng upload |
| V6 Cryptography | no hand-roll | không tự mã hoá; key chỉ lưu `.env` 0600 theo D-11 |
| V8 Data Protection | **yes** | key không bao giờ trả về/log; `maskedKey`; WAV tạm xoá trong `finally` (REC-04); `eval_clips/` nằm ngoài repo |
| V12 File / Resources | **yes** | sniff magic bytes + `-f` demuxer whitelist cho ffmpeg; file tạm trong thư mục riêng; timeout ffmpeg; giới hạn 10 MB |
| V13 API | **yes** | CORS chỉ `http://localhost:3000` với đúng method cần; lỗi tiếng Việt cố định, không lộ đường dẫn/stack |
| V14 Configuration | **yes** | `.env` gitignore (đã có), ghi `chmod 600`; không đưa secrets vào `lesson.json`/log |

### Known Threat Patterns for FastAPI + ffmpeg + yt-dlp + `.env`

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Upload dụ ffmpeg mở playlist/URL/file cục bộ (SSRF/LFI) | Information Disclosure / Tampering | sniff + `-f matroska,webm` hoặc `-f mov,mp4,…` + argv list; thử nghiệm đã xác nhận m3u8 bị từ chối `[VERIFIED: local run]`; không bao giờ `shell=True` |
| Upload quá lớn / dài (DoS đĩa/CPU) | Denial of Service | chặn `Content-Length` + đọc theo khúc ≤ 10 MB, `-t 60`, `timeout=30` |
| Path traversal qua `lessonId`/`index`/`videoId` | Tampering | helper `config.*_path` (regex + `_contained`) — **mọi** đường dẫn mới (`app.db`, `eval_clips/…`, `tmp/…`, stems theo range) phải đi qua helper tương tự; tên file eval clip dựng từ giá trị đã validate, không từ input thô |
| Chèn biến vào `.env` qua key có newline | Tampering | regex `^[A-Za-z0-9_\-]{20,256}$` trước `set_key` |
| Lộ key (log, response, exception, `lesson.json`) | Information Disclosure | không log body; `maskedKey`; không đưa key vào message lỗi; test khẳng định response không chứa key |
| CSRF/DNS rebinding tới API local | Spoofing / Tampering | `TrustedHostMiddleware` + kiểm `Origin` (Pitfall 7); mutate bằng JSON → preflight |
| Prompt injection qua text câu đưa vào LLM dịch | Tampering | text là dữ liệu: khối phân tách, đầu ra structured `{translation}` cắt độ dài, không tool; LLM không nhận audio (CLAUDE) |
| yt-dlp nhận URL người dùng | Tampering | chỉ `canonical_watch_url(videoId)` (đã có `[VERIFIED: download.py]`); preview cũng đi qua `parse_youtube_url` |
| SQLite injection | Tampering | tham số hoá mọi câu lệnh (`?`), không f-string |
| Thư mục `dataDir` do người dùng nhập trỏ vào vị trí nhạy cảm | Tampering | `PUT /settings` yêu cầu đường dẫn tuyệt đối, tồn tại, là thư mục, ghi được; không tạo/di chuyển file (D-12); local single-user nên rủi ro thấp |

## Gợi ý chia wave (cho planner, không ràng buộc)

- **Wave 0 (nền, có checkpoint Liam):** PR contract (`AttemptAck`, `AppSettings` + shape ở Open Q2) và schema `attempts` · checkpoint lockfile gộp · scaffold web (Tailwind 3, shadcn radix, token, font, vitest, providers) · `uv add python-multipart …` · tách `pipeline.py` + chỉnh `segment.py` (D-04) · CORS/TrustedHost.
- **Wave 1 (song song, độc lập):** (A) backend job runner + create/list/retry/lifespan + video Range + system/settings/key; (B) `playerMachine` + test + `shortcuts`/`level` thuần; (C) IPA + VAD + normalize + attempts + translate + segment edit/extend-end.
- **Wave 2:** S1 + S2 + S8 (UI nối API) → S3 (VideoPane/Controls/Transcript/SentenceStatePanel/ResultActionBar gắn machine).
- **Wave 3:** đo lại `make smoke` + 2 bài song song; ADR 0004 + ADR job runner/schema; cập nhật product.md M2, REQUIREMENTS PLY-01, CLAUDE.md "Lệnh" nếu đổi; UAT thủ công (SC1–SC5, Chrome và trình duyệt chính của Liam).

## Sources

### Primary (HIGH confidence)
- Mã nguồn repo đã đọc: `services/audio/src/audio_service/{config,main,contract_io,models}.py`, `lesson/{pipeline,segment,download,audio_io,features,urls,transcribe,quality,separate}.py`, `routers/lesson.py`, `contracts_gen.py`, `packages/contracts/src/{lesson,common,index,generate}.ts`, `Makefile`, `scripts/contracts_gen.sh`, `.env.example`, `apps/web/*`.
- Phép đo chạy trong session (scratchpad, không commit): `make smoke END=300` (bảng thời gian), thử nghiệm `split_sentences` với hằng số khác, giải mã IPA + so espeak-ng ngoại tuyến, `footprint` RAM của 3 model, `ffprobe` codec `video.mp4`, `yt-dlp` format selection, `ffmpeg` webm/mp4/m3u8, kiểm `starlette/responses.py`, `mlx_whisper/transcribe.py`, `dotenv/main.py`, `next` `font-data.json`.
- Context7 `/statelyai/docs` (XState v5: testing, `waitFor`, `fromPromise`, `fromCallback`, delayed transitions, `machine.provide`), `/tanstack/query` (refetchInterval hàm, Next app router provider), `/websites/fastapi_tiangolo` (UploadFile/Form + python-multipart), `/shadcn-ui/ui/shadcn_4.21.0` (init `--base`, preflight v3), `/openai/openai-python` (Responses `parse`, `models.list`).
- npm registry / PyPI JSON API (`npm view`, `pypi.org/pypi/<pkg>/json`) ngày 2026-10-06.

### Secondary (MEDIUM confidence)
- developers.openai.com/api/docs/models/gpt-5-nano; benchlm.ai/openai/api-pricing (tên model/giá 10/2026).
- blog.addpipe.com/getusermedia-audio-constraints; testmuai.com/learning-hub/mediarecorder-browser-support; buildwithmatija.com (MediaRecorder Safari mp4/webm).

### Tertiary (LOW confidence / `[ASSUMED]`)
- Hành vi trình duyệt chưa chạy thật (Safari AV1/Opus, Permissions API, `preservesPitch`), ngưỡng VAD/IPA, tham số model OpenAI — xem Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — version đọc từ registry hôm nay, seam legitimacy đã chạy, trùng stack đã khoá.
- Architecture (job runner, endpoint, machine): HIGH — thiết kế dựa trên mã Phase 1 đã đọc và hành vi starlette/dotenv/mlx đã kiểm.
- Số đo (RAM, thời gian, D-04, IPA, codec): HIGH cho video smoke; MEDIUM khi suy rộng (một video sitcom, một máy).
- Hành vi trình duyệt (ghi âm, Safari, Permissions): MEDIUM/LOW — chưa chạy trên trình duyệt thật.
- Pitfalls: HIGH cho các mục có bằng chứng `[VERIFIED]`; MEDIUM cho phần còn lại.

**Research date:** 2026-10-06
**Valid until:** 2026-11-05 (30 ngày; yt-dlp và openai/shadcn đổi nhanh — kiểm lại version khi bắt đầu thực thi)
