# 0005 · Job runner và cổng model, bảng `attempts`, settings, pipeline và biên API của P1

Ngày: 2026-10-08 · Trạng thái: Chấp nhận (riêng mục 5.7 `EXTEND_MAX_MS` chờ Liam xác nhận) · Người quyết: Liam

## Bối cảnh

Phase 2 (P1) biến script tạo bài của P0 thành app dùng được: tạo bài nền qua API, tập từng câu, ghi âm, chưa chấm điểm. Việc đó kéo theo một loạt quyết định kỹ thuật mà Liam chốt rải rác ở Discuss (`02-CONTEXT.md` D-01..D-23), ở checkpoint contract (`02-01-SUMMARY.md`, các mục A1..A10 và B..H, trả lời "approved" ngày 2026-10-07) và ở checkpoint chọn model dịch (`02-16-SUMMARY.md`, 2026-10-08). Theo CLAUDE.md, quyết định kỹ thuật mới phải có ADR trong cùng PR. ADR 0004 đã ghi riêng D-17 (bỏ IFrame) và phần codec của D-19; ADR này gom phần còn lại để các phase sau (P3 chấm điểm, P4 eval, P7 ôn luyện) đọc một chỗ.

Mọi con số dưới đây lấy từ code đã merge của P1, không chép lại từ plan.

## Quyết định

### 1. Job runner và cổng model

- **D-01:** `JobRunner` (`lesson/jobs.py`) chạy trong process FastAPI. Bước `downloading` chạy trên `ThreadPoolExecutor` 2 slot nên nhiều bài tải song song. Các bước dùng model (`separating → transcribing → segmenting → analyzing`) chạy tuần tự bởi **một** thread `model-worker` giữ `model_gate` (một `threading.Lock`). Thứ tự bước model là thứ tự `submit`: hàng đợi giữ (lessonId, future tải) theo thứ tự nộp, nên bài nộp sau dù tải xong trước vẫn chờ đến lượt. Bài tải lỗi bị đánh dấu `failed` và bỏ qua, không chặn bài sau. Bài chờ cổng model có `status: queued`. Thread chỉ tạo trong `start()`, không bao giờ lúc import.
- `model_gate` dùng chung cho ba bên: job tạo bài, "Mất chữ cuối?" (extend-end, chờ tối đa 150 s) và warm-up lúc khởi động. Không bên nào nạp model khi chưa giữ cổng, nên trên máy 8 GB không bao giờ có hai model nặng cùng nằm trong RAM.
- Chạy **một** process: không dùng `--workers N` (job runner và cổng model sống trong process này). `make dev-api` chạy `uvicorn --reload`: reload giữa lúc có job sẽ làm job dở thành "bị gián đoạn", nên UAT phải chạy `make dev` mà không sửa code.
- **D-03:** khi khởi động, `recover_interrupted()` đổi mọi bài có `status` ngoài `ready`/`failed` thành `failed` với `error = {step: <bước dở>, message: "bị gián đoạn"}`. Không tự chạy lại. `POST /lessons/{id}/retry` (202) dựng lại cùng `lessonId` từ dict contract đã bỏ `error`/`audioQuality`, `segments = []`, `status = queued`, xoá `seg/`, nộp lại; cache theo `videoId` giúp bỏ qua tải và tách giọng khi đã có. Chỉ bài `failed` được thử lại (409 `invalid_state` nếu không).
- Hai bài cùng video cùng đi qua bước tải: khoá theo video (`download.video_lock`, `RLock`) bao cả bước kiểm tra cache lẫn bước tải, **và** bước trích `audio.wav` (xem Hệ quả: lỗi này lộ ra ở `make smoke-jobs`, bài thứ hai thoát khoá tải ngay khi bài đầu xong rồi cả hai chạy ffmpeg ghi chung `audio.wav.part`).
- `lesson.json` là nguồn sự thật của `Lesson`; mọi lần đọc-sửa-ghi đi qua `store.update_lesson` (khoá theo bài, ghi atomic). Việc dài (model) không giữ khoá bài: chạy dưới `model_gate` rồi chỉ gộp kết quả của chính nó vào bản mới nhất.

### 2. D-13 sửa bởi D-18: warm-up model

- **D-18:** warm-up = **nạp → chạy 1 suy luận mẫu → giải phóng**, lần lượt từng model (demucs → whisper → wav2vec2), mỗi model dưới `model_gate`. Không model nào nằm lại trong RAM. Lý do: đo được 2.5 / 4.6 / 6.0 GB cho ba model trên máy M1 8 GB, không vừa nếu giữ thường trú.
- "Có trong cache" kiểm bằng cache Hugging Face với `download=False` (không bao giờ gọi mạng, giữ D-25 của P0). Model không có trong cache → `missing` (banner S1 đỏ "Chạy `make setup`"); có → `loading` đến khi warm-up xong thì `ready`. Một loader lỗi chỉ đánh dấu model đó `missing` và ghi log.
- Giải phóng Whisper phải tường minh: `release_whisper()` xoá `mlx_whisper.ModelHolder.model/model_path`, `gc.collect()`, `mx.clear_cache()`; pipeline gọi nó trước `free_accelerator_memory` sau mỗi bài. Demucs trên MPS lỗi thì thử lại một lần trên CPU (cả ở pipeline lẫn warm-up).
- `create_app(warm_up=None)` chỉ bật warm-up khi không tiêm `deps`, để test không bao giờ nạp model thật.

### 3. Lưu trữ: bảng `attempts` và clip eval

- **D-02 (đã duyệt ở 02-01 mục B):** SQLite `DATA_DIR/app.db` (stdlib `sqlite3`, WAL, `PRAGMA user_version = 1`), một bảng duy nhất:

  ```sql
  CREATE TABLE attempts (
      lesson_id TEXT NOT NULL,
      segment_index INTEGER NOT NULL CHECK (segment_index >= 0),
      attempt INTEGER NOT NULL CHECK (attempt >= 1),
      created_at TEXT NOT NULL,                       -- ISO-8601 UTC "...Z"
      duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
      voiced INTEGER NOT NULL CHECK (voiced IN (0, 1)),
      saved_for_eval INTEGER NOT NULL DEFAULT 0 CHECK (saved_for_eval IN (0, 1)),
      PRIMARY KEY (lesson_id, segment_index, attempt)
  )
  ```

  Một test khẳng định `sqlite_master` chỉ có bảng này với đúng 7 cột. Phase 3 thêm cột điểm; danh sách bài vẫn là quét `DATA_DIR/lessons/*/lesson.json` (không index bài trong SQLite). Đây là quyết định khó đảo ngược: P3, P7 xây trên bảng này.
- **Đánh số lượt (02-01 mục C):** mọi lần upload, có tiếng hay không, đều thêm một dòng và tăng `attempt` theo (bài, câu), trong `BEGIN IMMEDIATE`. UI "Lượt k" chỉ đếm lượt `voiced`. "Đã tập" của một câu = có ≥ 1 lượt `voiced` (D-08); S3 mở ở câu đầu tiên chưa tập (PLY-04).
- **Clip eval gửi lại (02-01 mục D, D-09):** "Lưu clip cho eval" sau khi ghi dùng `PUT /lessons/{id}/segments/{i}/attempts/{n}/eval-clip`: trình duyệt gửi lại blob đang giữ (D-07), server chuẩn hoá lại, ghi `DATA_DIR/eval_clips/{lessonId}_{index:04d}_{attempt:02d}.wav` kèm `.json` (lessonId, segmentIndex, attempt, text) rồi đặt `saved_for_eval = 1`; không tạo lượt mới. `POST` với `saveForEval=true` đi cùng đường lưu. Dòng chỉ được đánh dấu sau khi file đã nằm trên đĩa. `eval_clips/` nằm ngoài git (CLAUDE.md).
- **REC-04:** file tạm của lượt ghi nằm trong `mkdtemp` dưới `DATA_DIR/tmp` và bị `rmtree` trong `finally` ở mọi đường (thành công, 4xx, ffmpeg lỗi). Không có bản ghi nào còn trên đĩa nếu không `saveForEval`.
- Upload: whitelist magic byte (EBML → `matroska,webm`; `ftyp` ở byte 4..8 → `mov,mp4,m4a,3gp,3g2,mj2`) trước khi gọi ffmpeg với `-f` tường minh, `-t 61`, WAV 16 kHz mono PCM16, timeout 30 s, không shell. Giới hạn: file 10 MB (413 `payload_too_large`, cả theo `content-length` lẫn đếm byte khi stream), 60 s (422 `recording_too_long`), định dạng lạ 415 `unsupported_media`. VAD năng lượng (`lesson/vad.py`): khung 10 ms, sàn −50 dB, nền ồn = phân vị 10, có tiếng khi > nền + 12 dB, tổng ≥ 150 ms và một đoạn liên tục ≥ 100 ms. Các ngưỡng này là giá trị khởi đầu, chỉnh ở UAT bằng micro thật.

### 4. Settings

- **D-10:** `AppSettings` lưu ở `~/.config/shadowenglab/settings.json` (ghi atomic; đổi vị trí thư mục bằng `SHADOWENGLAB_CONFIG_DIR`, chỉ để test). Không nằm trong `DATA_DIR` vì `dataDir` là một setting. Thiếu hoặc hỏng file → giá trị mặc định (1×, lặp ×1, ghi +50%, `dataDir` hiện hành, `US`). `PUT /settings` kiểm `dataDir` là đường dẫn tuyệt đối, tồn tại, là thư mục, ghi được; sai → 422 `invalid_settings`.
- **Thứ tự ưu tiên `dataDir` (02-01 mục G):** `settings.json` (nếu có khoá hợp lệ) > `DATA_DIR` từ env/`.env` > `~/shadowenglab-data`. Phân giải **một lần** mỗi process (`lru_cache`), và `lifespan` gọi `get_settings()` ngay đầu để `PUT /settings` không bao giờ đổi thư mục đang dùng trước khi restart.
- **D-12:** đổi thư mục dữ liệu chỉ áp dụng sau restart, không chuyển file. `GET /settings` trả giá trị đã lưu (chờ áp dụng), `GET /system/status.activeDataDir` trả giá trị đang dùng; S8 hiện "Khởi động lại `make dev` để áp dụng; dữ liệu cũ vẫn ở …".
- **D-11:** key OpenAI dán ở S8 chỉ được ghi sau khi OpenAI trả 200 cho `GET /v1/models` (httpx, timeout 10 s): ghi `.env` ở gốc repo (`dotenv.set_key`, giữ nguyên các dòng khác, mode 0600) rồi nạp nóng vào `os.environ`. Key sai định dạng (`^[A-Za-z0-9_\-]{20,256}\Z`, chặn xuống dòng, `=`, khoảng trắng) trả `valid: false` mà không gọi mạng và không ghi gì. Key không bao giờ xuất hiện trong response, log hay exception: ra ngoài chỉ có `hasKey` và bản che `sk-…abcd`. `OpenAiKeyCheckResult.saved` nghĩa là "sau lệnh gọi này có một key đã xác minh được lưu" (đúng khi và chỉ khi `valid` là true). `SHADOWENGLAB_ENV_FILE` đổi file `.env` (test, smoke).
- Thiếu key không chặn gì: `/system/status` vẫn 200 với `hasKey: false`; Dịch trả 409 `no_openai_key` chỉ khi câu chưa có bản dịch trong cache.

### 5. Pipeline

1. **D-19, tách giọng theo đoạn:** Demucs chỉ chạy trên `[range.start − 1 s, range.end + 1 s]` (kẹp trong video), stem cache theo `(videoId, startMs, endMs)` tại `videos/{id}/stems/{startMs}-{endMs}/{vocals,no_vocals}.wav`; cùng khoảng thì dùng lại, khác khoảng thì tách lại. Mốc cắt trong stem là tương đối stem, còn cửa sổ trong `.npz` và `Word` vẫn là giây tuyệt đối của video. `vocals.wav`/`no_vocals.wav` cũ của cả video không còn được đọc. Video tải theo H.264/AAC: xem ADR 0004.
2. **D-14, D-20 (IPA):** `Word.ipa` = argmax PPG wav2vec2-espeak của **người nói gốc** trong ranh giới từ, không G2P, không phonemizer. Gán phone cho từ với dung sai ±2 frame (`IPA_TOL_FRAMES = 2`, 40 ms ở 50 fps). Độ tin cậy của từ = trung bình xác suất các frame phát phone; **dưới 0.7 (`IPA_MIN_CONF`) thì bỏ khoá `ipa`** (không bao giờ null) và UI hiện "—". Không có dấu trọng âm vì vocab không có `ˈ`/`ˌ`. Khoảng 30% từ bị ẩn trên video smoke (409/580 từ có IPA ở lần đo 02-12): đã chốt, hiện lại ở UAT. Vocab đọc từ cache HF (`local_files_only`); thiếu vocab thì không có IPA, không làm hỏng bài.
3. **D-21 (tách câu):** `MIN_DUR_S = 3.0`, `MAX_MERGED_S = 8.0`, `MAX_MERGED_WORDS = 18`; quy tắc cắt câu dài `MAX_WORDS = 15`, `MAX_DUR_S = 8.0`, `HARD_GAP_S = 0.7`, `SOFT_GAP_S = 0.25` giữ nguyên. Kết quả đo trên video smoke 0–300 s: 35 → 7 câu dưới 3 s, 39 câu trong 3–8 s, 0 câu trên 8 s, tối đa 18 từ, 46 câu (≈ 9.2 câu/phút). `docs/product.md` M1 đã sửa thành "3–8 s, tối đa 18 từ". Hệ quả cần biết: vì gộp được tới 18 từ, một đoạn bị luật 15 từ cắt đôi mà cả hai nửa đều dưới 3 s sẽ được gộp lại thành một câu 18 từ.
4. **`Segment.text` và `words` sau "Sửa câu":** `PATCH /lessons/{id}/segments/{i}` chuẩn hoá NFC, trim, gộp khoảng trắng, rồi kiểm 1–500 code point. Nếu số token bằng số `words`, từng `words[k].text` được thay và giữ nguyên mốc, `asrProb`, `ipa`; nếu khác, `words` **giữ nguyên** vì chúng mô tả audio. Vì vậy sau khi sửa, `Segment.text` có thể khác chuỗi ghép từ `words`. **Phase 3 và Phase 5 phải dùng `words` (không dùng `text`) để chấm và căn chỉnh.** Sửa câu luôn xoá `translation`.
5. **"Mất chữ cuối?" (02-01 mục E):** `endExtraMs += 300` (`EXTEND_STEP_MS`) được lưu ngay để phát lại dùng liền; sau đó F0/energy/PPG và IPA của câu được tính lại dưới `model_gate`, chờ tối đa 150 s (`RECOMPUTE_TIMEOUT_S`), quá hạn trả 503 `busy` (phần nới vẫn được lưu). Bài tạo bằng bản cũ không có stem khoảng → 409 `invalid_state`. Kết quả tính lại chỉ gộp `ipa` vào bản mới nhất, nên sửa text xen giữa không bị ghi đè.
6. **Dịch (D-16, D-23):** xem mục 7.
7. **`EXTEND_MAX_MS = 3000` — chờ Liam xác nhận.** Đây là trần do planner đề xuất ở 02-15, **không có trong `02-CONTEXT.md`**: tổng phần nới tối đa 3000 ms mỗi câu (2900 + 300 bị kẹp về 3000; ở 3000 thì 409 `invalid_state` "Đã nới tối đa cho câu này."). Một câu nới được tối đa 10 lần. Đổi giá trị là sửa một hằng ở `lesson/segment_ops.py`; nếu Liam không xác nhận thì giữ nguyên cho tới khi có phản hồi.

### 6. Biên API

- **CORS:** chỉ origin `http://localhost:3000`; methods `GET`, `POST`, `PUT`, `PATCH`; header `Content-Type`; không credentials.
- **TrustedHost:** chỉ `127.0.0.1` và `localhost` (Host lạ → 400), chống DNS rebinding. Bind `127.0.0.1` do Makefile.
- **Origin guard:** POST multipart là "simple request" nên CORS không chặn trước khi handler chạy (Pitfall 7). Middleware HTTP từ chối mọi request ghi (không phải GET/HEAD/OPTIONS) có header `Origin` khác `http://localhost:3000` bằng 403 `forbidden_origin`. Request không có `Origin` (script, curl, TestClient, `make smoke-jobs`) không bị ảnh hưởng.
- **`ApiError`:** mọi lỗi nghiệp vụ trả `{code, message, lessonId?}` với `message` tiếng Việt cố định, không bao giờ chứa đường dẫn, stack hay text của yt-dlp/ffmpeg/OpenAI (có test). 20 mã: `invalid_request`, `invalid_url`, `channel_url`, `video_unavailable`, `live_video`, `invalid_range`, `duplicate_lesson`, `not_found`, `invalid_state`, `invalid_segment`, `unsupported_media`, `payload_too_large`, `recording_too_long`, `busy`, `no_openai_key`, `upstream_error`, `network_error`, `invalid_settings`, `forbidden_origin`, `internal_error`. Lỗi validate của FastAPI cũng đi qua envelope này: 422 `invalid_request`, không echo input.
- **Trùng bài (02-01 mục F):** trùng = cùng `videoId` **và** cùng khoảng đã resolve **và** `status ≠ failed`. `POST /lessons` trả 409 `duplicate_lesson` kèm `lessonId` của bài có sẵn; `GET /videos/preview` trả `existingLessonId` chỉ cho khoảng mặc định (cả video nếu ≤ 360 s, ngược lại 0–300 s). Kiểm tra trùng và ghi bài nằm chung một khoá để hai POST đồng thời không cùng qua.
- Lỗi tải (yt-dlp) → bài `failed` với message cố định; mọi chi tiết thật chỉ vào log.

### 7. Dịch câu

- **D-16:** dịch theo yêu cầu, chỉ gửi **text** (câu đích + tối đa 2 câu ngữ cảnh mỗi phía, mỗi câu cắt ở 500 ký tự, bỏ `<` `>` để không giả mạo dấu phân cách), không bao giờ gửi audio. Kết quả cache vào `segment.translation` trong `lesson.json`; lần sau đọc cache, không cần key hay mạng. Sửa câu xoá bản dịch cũ. Nếu text đổi trong lúc request đang bay thì không ghi cache.
- **D-23:** `TRANSLATE_MODEL = "gpt-6-luna"` (`models.py`, nơi duy nhất có id model), gửi với `reasoning.effort = "none"`. Liam chọn ngày 2026-10-08 ở checkpoint 02-16, sau khi các ứng viên của research (`gpt-5-nano`, `gpt-5-mini`, `gpt-5.4-nano`) bị đánh dấu deprecated (đọc `developers.openai.com`, 2026-10-08); giá Standard 0.10 / 0.50 USD mỗi 1M token vào/ra, ước ≈ 0.0036 USD cho 60 câu. Gọi OpenAI Responses API (`POST /v1/responses`) bằng **httpx**, không thêm SDK `openai`: `json_schema` strict `{translation}`, `store: false`, `max_output_tokens: 400`, không `temperature`/`top_p`. Lỗi trả theo lớp status: thiếu key và chưa có cache → 409 `no_openai_key`; 4xx/5xx hoặc đầu ra hỏng/bị từ chối → 502 `upstream_error`; mạng/timeout → 503 `network_error`.
- Chưa có eval chất lượng dịch và chưa có lần gọi thật với key thật trong CI; Liam kiểm một lần ở UAT. Đổi model là sửa một dòng ở `models.py`.

## Hệ quả

- **Chấp nhận:** một process, một worker model: tạo bài hai video cùng lúc thì bước model xếp hàng (đúng ý D-01); thời gian chờ của bài sau cộng thời gian bài trước. Tập bài đã `ready` không cần model nên không bị chặn.
- **Chấp nhận:** restart giữa chừng làm bài dở thành `failed` + "bị gián đoạn"; người dùng bấm Thử lại. Không có hàng đợi bền vững, huỷ job hay tự retry (hoãn sang Step 2, `product.md` mục 6).
- **Chấp nhận:** warm-up tốn thời gian khởi động và giữ `model_gate` trong lúc chạy, nên bài tạo ngay sau `make dev` có thể chờ warm-up xong; đổi lại không giữ 6 GB thường trú.
- **Cache cũ:** `video.mp4` AV1/VP9 của P0 không được migrate (ADR 0004); `vocals.wav`/`no_vocals.wav` cả video bị bỏ qua; bài tạo bằng bản cũ không "nới" được câu (409).
- **Ràng buộc cho Phase 3 và 5:** chấm theo `words`, không theo `Segment.text`; bảng `attempts` thêm cột điểm bằng migration, `user_version` tăng; `ScoreResult` thay `AttemptAck` ở endpoint upload, không nới `ScoreResult` cho trường hợp "chưa chấm".
- **Lỗi đã sửa trong lúc ghi ADR (02-19):** `make smoke-jobs` lần đầu cho thấy hai bài cùng video bị lỗi `FileNotFoundError` ở `os.replace(audio.wav.part)` do cùng chạy ffmpeg; bước trích audio nay nằm dưới khoá video (test `test_two_lessons_of_one_video_extract_the_audio_once`). Mọi bước ghi chung file theo `videoId` phải nằm dưới `download.video_lock`.
- **Khả năng đảo ngược:** D-02 (schema `attempts`) và các shape contract là khó đảo ngược; các hằng số (D-20, D-21, VAD, `EXTEND_MAX_MS`) và `TRANSLATE_MODEL` đảo ngược được bằng một dòng; cơ chế hàng đợi (thread pool + một worker) có thể thay mà không đổi contract.

## Tài liệu liên quan

- `.planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-CONTEXT.md` (D-01..D-23), `02-01-SUMMARY.md` (mục A1..A10, B..H), `02-12-SUMMARY.md`, `02-15-SUMMARY.md`, `02-16-SUMMARY.md`.
- ADR 0003 (toolchain contract, ngân sách thời gian), ADR 0004 (bỏ IFrame, H.264/AAC).
- `docs/product.md` M1 (tách câu 3–8 s, tối đa 18 từ), M2.
