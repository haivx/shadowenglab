# Phase 2: P1 Tạo bài và trình phát - Pattern Map

**Mapped:** 2026-10-06
**Files analyzed:** ~55 (mới/sửa), gom theo nhóm
**Analogs found:** backend Python + contracts: 100% có analog tracked. `apps/web` (UI, XState, TanStack): greenfield, chỉ analog theo vai trò từ tài liệu (UI-SPEC, tokens.md, RESEARCH Pattern 3-5).

Mọi analog đã kiểm bằng `git ls-files` (tracked, không có mirror gitignored). Số dòng lấy từ file hiện tại ở HEAD. Prose tiếng Việt, định danh/code giữ tiếng Anh. Khi CONTEXT D-18..D-23 mâu thuẫn với phần trên của CONTEXT hoặc RESEARCH, D-18..D-23 thắng (đã áp dụng bên dưới: IPA không dấu trọng âm, warm-up load-run-free, tách giọng theo range, `MAX_MERGED_WORDS=18`, httpx không SDK).

## File Classification

| File mới/sửa | Role | Data Flow | Analog gần nhất | Match |
|---|---|---|---|---|
| `packages/contracts/src/{attempt,settings,system,lesson-api}.ts` (hoặc nối vào `lesson.ts`): `AttemptAck`, `AppSettings`, `VideoPreview`, `CreateLessonRequest`, `LessonListItem`, `LessonProgress`, `SystemStatus`, `OpenAiKeyCheck*`, `UpdateSegmentTextRequest`, `ApiError` | model | transform | `packages/contracts/src/score.ts` + `lesson.ts` | exact |
| `packages/contracts/src/index.ts` (sửa: thêm vào `Schemas`) | config | transform | chính nó (dòng 10-19) | exact |
| `packages/contracts/fixtures/*.json`, `contracts.test.ts` (sửa), `schema/contracts.schema.json`, `contracts_gen.py` (sinh) | test/generated | transform | `fixtures/Lesson.json`, `contracts.test.ts` | exact |
| `services/audio/src/audio_service/config.py` (sửa: `app_db_path`, `eval_clips_dir`, `settings_file_path`, `tmp_dir`, `lesson_video_path`, ưu tiên `dataDir`) | config | file-I/O | chính nó | exact |
| `.../db.py` (sqlite3, `attempts`) | service | CRUD | không có sqlite trong repo; `config.py` cho quy ước đường dẫn | partial |
| `.../settings_store.py`, `.../secrets_env.py` | service | file-I/O | `contract_io.py` (`write_json_atomic`) + `config.py` (`get_settings`) | role-match |
| `.../system_status.py`, `routers/system.py` | service + controller | request-response | `main.py` `Health` + `routers/lesson.py` | role-match |
| `.../lesson/jobs.py` (`JobRunner`) | service | event-driven / batch | `lesson/pipeline.py` (`PipelineDeps`, `save()`) + RESEARCH Pattern 1 | role-match |
| `.../lesson/pipeline.py` (sửa: tách `create_lesson`/`stage_download`/`stage_model`, IPA, stems theo range) | service | batch / file-I/O | chính nó | exact |
| `.../lesson/ipa.py`, `.../lesson/vad.py` | utility | transform | `lesson/features.py` (`frame_energy`) + `lesson/segment.py` (hàm thuần) | exact |
| `.../lesson/normalize.py` | utility | file-I/O | `lesson/audio_io.py` (`extract_audio`) | exact |
| `.../lesson/translate.py` | service | request-response | `lesson/download.py` (biên ra mạng duy nhất) + RESEARCH Pattern 7 | role-match |
| `.../lesson/segment.py` (sửa D-21), `.../lesson/download.py` (sửa `_FORMAT`, `VideoInfo`) | utility | transform / file-I/O | chính chúng | exact |
| `routers/lesson.py` (sửa: POST/list/retry/video/progress/patch/extend-end/translate) | controller | CRUD / request-response | chính nó (dòng 10-22) | exact |
| `routers/{attempts,videos,settings}.py` | controller | request-response | `routers/lesson.py` | exact |
| `main.py` (sửa: lifespan, CORS, routers, TrustedHost) | config | request-response | chính nó | exact |
| `services/audio/tests/test_{jobs,ipa,vad,normalize,attempts_api,settings,system,lesson_api}.py`, sửa `test_segment.py`, `test_pipeline.py` | test | request-response / transform | `tests/test_api.py`, `test_pipeline.py` (`Fakes`), `test_segment.py` | exact |
| `scripts/smoke_lesson.py` (sửa: in phân bố câu trước/sau) | utility | batch | chính nó | exact |
| `docs/decisions/0004-<slug>.md` (+ ADR job runner/cổng model), `docs/product.md` M1/M2, REQUIREMENTS PLY-01 | doc | n/a | `docs/decisions/0003-contract-toolchain-va-moi-truong-p0.md` | exact |
| `apps/web/{tailwind.config.ts,postcss.config.js,app/globals.css,app/tokens.css}` | config | n/a | `docs/design/tokens.css` + `docs/design/tokens.md` "Map sang Tailwind" | role-match |
| `apps/web/app/{layout,page}.tsx` (sửa), `app/settings/page.tsx`, `app/lessons/[id]/page.tsx`, `app/providers.tsx` | component | request-response | `apps/web/app/layout.tsx`, `page.tsx` (shell) + `docs/design/screens/*.html` | partial |
| `apps/web/lib/api.ts` | utility | request-response | `packages/contracts/src/cli-parse.ts` (parse Zod ở biên) | role-match |
| `apps/web/lib/player/playerMachine.ts` + `.test.ts`, `shortcuts.ts` + `.test.ts`, `actors.ts` | store / test | event-driven | không có (RESEARCH Pattern 3, 4, Pitfall 12) | none |
| `apps/web/lib/audio/{recorder,level,mime}.ts` | utility | streaming | không có (RESEARCH Pattern 5a) | none |
| `apps/web/components/*.tsx` (AppHeader, Banner, LessonCard, JobSteps, RangePicker, PlayerControls, TranscriptList, SentenceStatePanel, ResultActionBar) | component | request-response | `docs/design/components.md` + UI-SPEC "Component Inventory" | none (HTML design làm nguồn) |
| `apps/web/package.json` (sửa deps), `pnpm-lock.yaml`, `services/audio/pyproject.toml` + `uv.lock` | config | n/a | chính chúng | exact |
| `Makefile`, `CLAUDE.md` mục Lệnh | config | n/a | chính chúng | exact |

## Pattern Assignments

### Contracts mới (model, transform)

**Analog:** `packages/contracts/src/score.ts` (object có `.meta({ id })`, export type cùng tên) và `lesson.ts`.

**Imports + primitives** (`lesson.ts` dòng 1-2, `common.ts` dòng 6-18):
```typescript
import * as z from "zod";
import { IsoTimestamp, Milliseconds, Probability, Seconds } from "./common";
// Seconds = z.number().min(0); Milliseconds = z.number().int().min(0); Probability 0..1
// IsoTimestamp = z.string()  (không dùng z.iso.datetime(), Pitfall 7)
```

**Core pattern** (`score.ts` dòng 181-195, `lesson.ts` dòng 45-47, 61-76): mỗi object một `.meta({ id })`; field tuỳ chọn dùng `.optional()` (không bao giờ `.nullable()` trừ khi cố ý, `Scores.sound` dòng 158-165 là ví dụ nullable cố ý); enum chuỗi gom ở một `z.enum([...])`.
```typescript
export const AttemptAck = z
  .object({
    lessonId: z.string(),
    segmentIndex: z.number().int().min(0),
    attempt: z.number().int().min(1),   // khớp ScoreResult.attempt (score.ts:185)
    durationMs: Milliseconds,
    voiced: z.boolean(),
    savedForEval: z.boolean(),
  })
  .meta({ id: "AttemptAck" });
export type AttemptAck = z.infer<typeof AttemptAck>;
```
Lưu ý: `LessonStatus` KHÔNG có meta id (inline thành Literal, `lesson.ts` dòng 49-59); `LessonListItem`/`LessonProgress` nên tái dùng bằng cách import `LessonStatus`, `AudioQuality`, `LessonError`, không nhân bản. `AppSettings.repeat` = `z.union([z.literal(1), z.literal(2), z.literal(3)])`, `accent: z.literal("US")`.

**Đăng ký** (`index.ts` dòng 1-19): thêm import + key vào `Schemas`, thêm `export * from "./<file>"`. `generate.ts` (dòng 20-26) sẽ fail nếu thiếu `.meta({ id })` hoặc sinh `__schemaN` ẩn danh, đó là kiểm tra miễn phí.

**Test/fixture** (`contracts.test.ts` dòng 21-50, `fixtures/Lesson.json`): fixture là mảng `[{ "name": "...", "data": {...} }]`, test "covers all four fixture files" (dòng 28-35) liệt kê cứng tên file, nên thêm fixture mới phải sửa danh sách đó. Cần thêm case phủ định "optional gửi null bị từ chối" như `Word.ipa` (dòng 57+).

**Quy trình:** `make contracts` (sinh `schema/contracts.schema.json` + `contracts_gen.py`), `make test` có drift gate. Đây là PR contract Wave 0 có `checkpoint:decision` (D-22); mọi plan sau import từ đây.

---

### `services/audio/src/audio_service/config.py` (sửa) (config, file-I/O)

**Analog:** chính file, dòng 17-85.

**Pattern helper đường dẫn** (dòng 48-67, 76-84): `_check_id` bằng regex rồi `_contained(...)` sau khi resolve. Mọi helper mới (`eval_clips_dir`, `app_db_path`, `tmp_dir`, đường dẫn stems theo `(videoId, start_ms, end_ms)`) phải đi qua `_contained`.
```python
def lesson_dir(lesson_id: str) -> Path:
    _check_id(lesson_id, ULID_RE, "lesson id")
    return _contained(data_root() / "lessons" / lesson_id)
```
**Cảnh báo:** `data_root()` dòng 39-41 là `lru_cache` qua `get_settings()` (dòng 34-36); fixture test `data_dir` gọi `get_settings.cache_clear()`. Ưu tiên `dataDir` (settings.json > DATA_DIR > mặc định, RESEARCH Pattern 7) phải nằm trong chính hàm cache này để D-12 "áp dụng sau restart" tự nhiên đúng. `VideoAsset` Literal (dòng 20, 82) cần mở rộng nếu thêm asset stems. `settings.json` đọc ở `~/.config/shadowenglab/` hoặc `SHADOWENGLAB_CONFIG_DIR` (test).

---

### `services/audio/src/audio_service/routers/lesson.py` (sửa) và `routers/{attempts,videos,settings,system}.py` (mới) (controller, CRUD / request-response)

**Analog:** `services/audio/src/audio_service/routers/lesson.py` dòng 1-22.

**Imports + router + lỗi không lộ đường dẫn** (dòng 1-22):
```python
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from audio_service.config import InvalidIdError, lesson_json_path
from audio_service.contracts_gen import Lesson

router = APIRouter(prefix="/lessons", tags=["lesson"])

@router.get("/{lesson_id}", response_model=Lesson, response_model_exclude_unset=True)
def get_lesson(lesson_id: str) -> Lesson:
    try:
        path = lesson_json_path(lesson_id)
    except InvalidIdError:
        raise HTTPException(status_code=404, detail="lesson not found") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="lesson not found")
    try:
        return Lesson.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, UnicodeDecodeError):
        # Không đưa đường dẫn hay chi tiết lỗi ra ngoài.
        raise HTTPException(status_code=500, detail="stored lesson is invalid") from None
```
Áp dụng cho mọi endpoint mới: handler `def` (không `async`, chạy trong threadpool anyio), `response_model=<Contract pydantic sinh sẵn>` + `response_model_exclude_unset=True` (giữ field optional vắng mặt, tránh `null`), `InvalidIdError` -> 404, lỗi lưu trữ -> 500 với chuỗi cố định, tuyệt đối không echo path. Thông báo tiếng Việt cho người dùng, `detail` kỹ thuật tiếng Anh cố định như hiện tại; shape lỗi mới chuẩn hoá bằng contract `ApiError`.

**Multipart (`attempts.py`)**: dùng `UploadFile` + `Form`; cần `python-multipart` (Pitfall 6). Chặn 10 MB bằng đọc theo khúc (RESEARCH 5b).
**Video (`GET /lessons/{id}/video`)**: đọc `videoId` từ `lesson.json` (client không gửi đường dẫn), `video_asset_path(video_id, "video.mp4")` rồi `FileResponse(path, media_type="video/mp4")`; chỉ khi `ready` (RESEARCH Pattern 8).
**Ghi `lesson.json` ngoài pipeline** (`PATCH` text, `extend-end`, `translate`): khoá theo lesson + `write_contract_json` (xem Shared Patterns).

---

### `services/audio/src/audio_service/main.py` (sửa) (config, request-response)

**Analog:** chính file, dòng 24-41.
```python
def create_app() -> FastAPI:
    app = FastAPI(title="ShadowEngLab audio service", version=__version__)
    # Chỉ web local được gọi; Phase 2 mở rộng methods khi thêm POST.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    ...
    app.include_router(lesson.router)
    app.include_router(scoring.router)
    return app
```
Thay đổi: `allow_methods` thêm `POST, PUT, PATCH`; thêm `lifespan=` (khởi `JobRunner` ở đây, KHÔNG ở import time, để `TestClient` và `--reload` sạch; gọi `recover_interrupted()` D-03 rồi warm-up nền D-18); thêm `TrustedHostMiddleware(["127.0.0.1","localhost"])` + kiểm `Origin` cho method ghi (Pitfall 7); `include_router` cho các router mới. Giữ `create_app()` factory vì `tests/test_api.py` dùng `TestClient(create_app())`. Test CORS hiện có (`test_api.py` dòng 103-115) khẳng định chỉ `localhost:3000`; mở rộng test, không nới origin.

---

### `services/audio/src/audio_service/lesson/pipeline.py` (sửa) (service, batch / file-I/O)

**Analog:** chính file. Giữ nguyên chữ ký `run_lesson(...)` làm wrapper mỏng (RESEARCH Pattern 1b): `tests/test_pipeline.py` và `scripts/smoke_lesson.py` phụ thuộc nó.

**DI + `save()` ghi atomic mỗi lần đổi trạng thái** (dòng 44-57, 185-191):
```python
@dataclass(frozen=True)
class PipelineDeps:
    fetch_info: Callable[[str], download.VideoInfo]
    download_video: Callable[[str], Path]
    ...
    free_memory: Callable[[], None]

def save(**update: Any) -> None:
    nonlocal lesson
    lesson = lesson.model_copy(update=update)
    with timer.step("write"):
        write_contract_json(path, lesson)
    if on_status is not None:
        on_status(lesson)
```
Tách thành `create_lesson` (dòng 156-183: parse URL, `fetch_info`, ghi `queued`), `stage_download` (dòng 200-211), `stage_model` (dòng 213-293). Stage giả mới (IPA, stems theo range) thêm vào `PipelineDeps` để test tiếp tục tiêm giả.

**Chỗ phải sửa theo quyết định:**
- Stems theo range, cache `(videoId, start, end)` (D-19): dòng 203-224 hiện đọc `audio.wav` cả video và cache `vocals.wav`/`no_vocals.wav` theo `videoId`. Cắt trước khi `deps.separate`, trừ `base_offset` ở các mốc cắt tuyệt đối (dòng 244-246, 262-270).
- IPA trong bước `analyzing` (D-14/D-20): sau `deps.compute_ppg` (dòng 275), gọi `ipa.ipa_for_segment(...)` thuần rồi gắn `ipa` vào `words` của segment (bỏ hẳn khi ẩn, không gán `None`).
- Khi vào `analyzing` thì `rmtree(seg/)` trước khi ghi (D-21 đổi số câu, `.npz` cũ mồ côi, RESEARCH 1b).
- `free_memory` thật phải xoá thêm `mlx_whisper.ModelHolder` (Pitfall 2, D-18); `_real_separate` (dòng 60-77) là mẫu nạp-chạy-giải phóng cho warm-up.

**Error handling** (dòng 294-303), giữ nguyên cho `stage_*`: `except BaseException` -> `save(status="failed", error=LessonError.model_validate({"step": lesson.status, "message": ...}))` -> ném lại. `ERROR_MESSAGE_MAX = 500`. `step` có thể là `queued` (UI cần fallback).

**Retry rebuild (Pitfall 5)**: dựng Lesson mới từ dict đã `pop("error")`/`pop("audioQuality")`/`segments`; KHÔNG `model_copy(update={"error": None})` (ghi `null`, Zod từ chối; xem docstring `contract_io.py` dòng 1-10, hàm `dump_contract` dòng 21-23 dùng `exclude_unset=True`).

---

### `services/audio/src/audio_service/lesson/jobs.py` (mới) (service, event-driven)

**Analog:** RESEARCH Pattern 1 (phác thảo `JobRunner`) + `PipelineDeps` DI ở trên. Không có analog threading trong repo.
Cấu trúc: `ThreadPoolExecutor(max_workers=2)` cho tải, một `threading.Thread(daemon=True)` đọc `queue.Queue` cho bước model, `model_gate: threading.Lock` dùng chung với `extend-end` và warm-up. Tiêm `stage_download`, `stage_model`, `mark_failed` như `PipelineDeps` để test không cần model. Test mẫu: dùng `threading.Event` giả (RESEARCH Pattern 1 "Test") với các khẳng định (a) không chặn, (b) không hai job cùng bước model, (c) FIFO; đó là bằng chứng tự động cho success criterion 2. `recover_interrupted()`: quét `DATA_DIR/lessons/*/lesson.json`, `status ∉ {ready, failed}` -> `failed {step, "bị gián đoạn"}` bằng cùng cách rebuild dict ở trên.

---

### `lesson/ipa.py`, `lesson/vad.py` (mới) (utility, transform)

**Analog:** `lesson/features.py` dòng 31-48 (`frame_energy`, hàm thuần mảng-vào-mảng, docstring nêu rõ shape/dtype) và `lesson/segment.py` (module thuần, dataclass `frozen, slots`, hằng số ở đầu file, docstring giải thích ngưỡng là giá trị khởi đầu).
```python
def frame_energy(audio16k: np.ndarray, sr: int = SR, hop_s: float = 0.01, win_s: float = 0.025) -> np.ndarray:
    """RMS theo khung ... float32."""
```
- `vad.voiced_ms(audio16k) -> int`: gọi lại `frame_energy`, không đọc file (CLAUDE.md "hàm audio thuần"). Hằng số (`MIN_VOICED_MS=150`, `MIN_RUN_MS=100`, sàn -50 dB, +12 dB so với percentile 10) đặt đầu file, đánh dấu `[ASSUMED]` như `segment.py` dòng 6-7.
- `ipa.ipa_for_segment(ppg, window_start, words, vocab, ...)`: nhận mảng + vocab, trả dict; không nạp model. Constants: `PPG_FPS=50.0`, dung sai ±2 frame, `blank={0,1,2,3}`, ngưỡng ẩn `0.7` (D-20). Dữ liệu từ `seg/{index:04d}.npz` có `ppg`, `window`, `ppg_fps` (`pipeline.py` dòng 279-288). Vocab qua `huggingface_hub.hf_hub_download(PPG_REPO, "vocab.json")` (`models.py` đã có `PPG_REPO`, `vocab.json` nằm trong `PPG_ALLOW_PATTERNS`).
- Test: tín hiệu tổng hợp, theo kiểu `tests/test_features.py`/`test_segment.py` (`make_words` helper dòng 20-36 của `test_segment.py` là mẫu dựng dữ liệu).

---

### `lesson/normalize.py` (mới) (utility, file-I/O)

**Analog:** `lesson/audio_io.py` `extract_audio` dòng 23-52 (argv list, `-nostdin -y -loglevel error`, file `.part` + `os.replace`, dọn trong `except BaseException`).
```python
cmd = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(video_path),
       "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", "-f", "wav", str(part)]
try:
    subprocess.run(cmd, check=True)
    os.replace(part, wav_path)
except BaseException:
    part.unlink(missing_ok=True)
    raise
```
Khác biệt bắt buộc: thêm `-f <demuxer>` TRƯỚC `-i` theo magic bytes (`1A45DFA3` -> `matroska,webm`; `ftyp` offset 4 -> `mov,mp4,m4a,3gp,3g2,mj2`), ngoài hai loại đó -> 415; đích `-ac 1 -ar 16000 -c:a pcm_s16le`; không loudnorm/AGC; ghi vào file tạm trong `DATA_DIR/tmp/` và xoá trong `finally`; không pipe stdin. Kết quả đọc lại bằng `audio_io.read_audio` + `to_mono_16k` (dòng 55-85).

---

### `lesson/translate.py` (mới) (service, request-response)

**Analog:** `lesson/download.py` (docstring dòng 1-6: "Đây là chỗ DUY NHẤT pipeline ra mạng"; biên bảo mật nêu rõ). `translate.py` + `secrets_env.py`/`settings` check là biên ra mạng thứ hai, ghi chú tương tự trong docstring. Dùng `httpx` (chuyển từ dev dep sang dependency chính, D-23), chỉ gửi text (câu mục tiêu + tối đa 2 câu quanh), validate đầu ra bằng pydantic, không SDK `openai`. Tên model là hằng số trong `models.py` (cạnh `WHISPER_REPO` dòng 9), do Liam chốt ở checkpoint (D-23); không hard-code ở chỗ khác. Thiếu key -> lỗi rõ để router trả mã cho UI disabled.

---

### `lesson/segment.py` (sửa D-21) (utility, transform)

**Analog:** chính file, hằng số dòng 20-25 và `_merge_short` dòng 113-134.
```python
HARD_GAP_S = 0.7
SOFT_GAP_S = 0.25
MAX_DUR_S = 8.0
MAX_WORDS = 15
MIN_DUR_S = 1.5
MAX_MERGED_S = 9.0
```
Đổi: `MIN_DUR_S=3.0`, `MAX_MERGED_S=8.0`, thêm `MAX_MERGED_WORDS=18` và kiểm trong `_merge_short` cạnh dòng 129 (`if _dur(words, merged) > MAX_MERGED_S: continue`) bằng số từ `merged[1]-merged[0]`. Lưu ý `MIN_DUR_S` còn dùng trong `_choose_cut.valid` (dòng 85-86) nên đổi hằng số làm đổi hành vi cắt: kiểm lại `test_segment.py` (nó import các hằng số, dòng 10-18, nên test theo hằng số sẽ tự theo, nhưng test có con số cứng cần xem). Sửa `product.md` M1 "~15 từ" -> 18. In phân bố độ dài câu trước/sau qua `scripts/smoke_lesson.py`.

---

### `lesson/download.py` (sửa) (service, file-I/O)

**Analog:** chính file. `_FORMAT` dòng 22 -> selector avc1/m4a (D-19, RESEARCH Pitfall 3):
`"bv*[height<=480][vcodec^=avc1]+ba[acodec^=mp4a]/b[height<=480][vcodec^=avc1]/bv*[height<=480]+ba/b[height<=480]/b"`; thêm `ffprobe` kiểm codec sau tải và transcode dự phòng. `VideoInfo` (dòng 25-30) thêm `channel`, `live_status`, `availability`; `fetch_info` đọc cache bằng `cached.get(...)` (dòng 53-58 hiện dùng `cached["title"]`, field mới phải `.get()` để không vỡ cache cũ) và ghi payload bỏ field `None` (dòng 71-78). Biên bảo mật giữ: yt-dlp chỉ nhận `canonical_watch_url(video_id)`.

---

### Tests Python mới (test, request-response / transform)

**Analog API:** `services/audio/tests/test_api.py` dòng 48-66, 68-95:
```python
@pytest.fixture
def data_dir(tmp_path, monkeypatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()

@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app())
```
Tái dùng `make_lesson()`/`store()` (dòng 15-65) cho test list/progress/retry/video; test id xấu parametrize như dòng 76-81; khẳng định `str(data_dir) not in res.text` như dòng 94. Thêm fixture đặt `SHADOWENGLAB_CONFIG_DIR` về tmp để không đụng `~/.config` thật (RESEARCH Pattern 7). **Analog pipeline/job:** `tests/test_pipeline.py` lớp `Fakes` (dòng 63-130) tiêm `PipelineDeps` giả, `STATUSES` (dòng 41-49), `_only_lesson_id` (dòng 133-136); `test_jobs.py` nên dùng cùng kiểu giả có sổ ghi `calls`.
**Analog thuần:** `test_segment.py` (`make_words`, test tham số) cho `ipa`, `vad`.

---

### `docs/decisions/0004-<slug>.md` (+ ADR job runner/cổng model) (doc)

**Analog:** `docs/decisions/0003-contract-toolchain-va-moi-truong-p0.md` dòng 1-25. Khung:
```markdown
# 0004 · <tiêu đề>

Ngày: 2026-10-NN · Trạng thái: Chấp nhận · Người quyết: Liam

## Bối cảnh
## Quyết định
1. **<nhóm>**
   - **D-NN:** ...
```
ADR 0004 bắt buộc cho D-17 (bỏ IFrame), cùng sửa `docs/product.md` M2 + REQUIREMENTS PLY-01. Một ADR (hoặc mục) cho job runner/cổng model ghi diễn giải D-18 (warm-up load-run-free), thứ tự ưu tiên `dataDir`, `Segment.text != join(words)` (Pitfall 9). Sửa `product.md` trước rồi mới cập nhật roadmap (CLAUDE.md quy trình mục 5).

---

### `apps/web` nền (config/component, request-response) — greenfield

**Analog hiện có:** `apps/web/app/layout.tsx` (`lang="vi"`, `metadata`), `apps/web/app/page.tsx` (import `@shadowenglab/contracts` từ web hoạt động), `apps/web/package.json` (chỉ `next`, `react`, `react-dom`, contracts). Cách import contract đã chứng minh:
```tsx
import { LessonStatus } from "@shadowenglab/contracts";
```
**Token/Tailwind:** nguồn là `docs/design/tokens.css` (copy sang `app/tokens.css`) + `docs/design/tokens.md` dòng 56-77 (cấu hình `tailwind.config.ts` v3, màu `var(--x)` nên KHÔNG dùng opacity modifier kiểu `bg-primary/90`; không dùng `--score-*` trong P1, D-08). `scoreLevel()` đặt ở `apps/web/lib` hoặc contracts (tokens.md dòng 79) nhưng P1 chưa dùng màu điểm. Cài đặt shadcn: `npx shadcn@latest init -b radix --css-variables`, không `-d`; chỉnh ghi đè `hsl()` theo UI-SPEC "Token Implementation Map" (dòng 350). Font: Figtree + Noto Sans (vietnamese) + JetBrains Mono, IPA font cần kiểm (Pitfall 11).
**Component:** không có analog code; nguồn là `docs/design/screens/{S1-thu-vien,S2-tao-bai,S3-S4-phong-tap,S3-trang-thai-cau,S8-settings}.html` + `docs/design/components.md` + UI-SPEC "Component Inventory" (dòng 45) và "Screen Contracts" (dòng 264). Ngoại lệ đã duyệt: nút ghost "Lưu clip cho eval" (D-09).

**`lib/api.ts`** — analog theo tinh thần `packages/contracts/src/cli-parse.ts` (parse Zod ở biên). Mọi response `Schema.parse()` (CLAUDE: Zod ở mọi ranh giới I/O); `NEXT_PUBLIC_API_URL` mặc định `http://127.0.0.1:8000`; lỗi map qua `ApiError`.

**Polling S1** (RESEARCH Pitfall 14, Don't Hand-Roll): `useQuery({ refetchInterval: (q) => hasActive(q.state.data) ? 2000 : false, placeholderData: keepPreviousData })`, key thẻ = `lesson.id`, danh sách trả `LessonListItem` nhẹ.

---

### `apps/web/lib/player/playerMachine.ts` (+ test) (store, event-driven) — không có analog

**Nguồn:** RESEARCH Pattern 3 (dòng 328-343): `setup({ types, actors, delays }).createMachine(...)`; actors là stub trong `setup`, thay bằng `machine.provide({ actors })` ở UI và test; file không import DOM/React/fetch. Trạng thái: `idle, previewing, playing, recording, scoring, reviewing{idle|original|yours|both}, noVoice, error`; `scoring` = upload ở P1 (D-05) để Phase 3 không đổi cấu trúc. Test vitest môi trường `node`: `createActor(machine.provide({actors:{...}}))`, `waitFor`; danh sách transition cần phủ ở RESEARCH dòng 332 (đặc biệt: upload reject giữ `recordings[i].blob`; `GOTO` trong `recording` bị bỏ qua). Vitest cùng major với contracts (`^4.1.11`; xem `packages/contracts/package.json`, test hiện dùng `import { describe, expect, it } from "vitest"` ở `contracts.test.ts` dòng 3).
**`shortcuts.ts`**: hàm thuần `shouldHandleShortcut(event)` + test (Pitfall 12; bỏ qua khi focus ở `input/textarea/select/[role=combobox|listbox]` hoặc trong `[role=dialog]`).
**`recorder.ts`/`level.ts`/`mime.ts`**: RESEARCH Pattern 5a; hàm RMS/im lặng thuần `(samples, state) -> state` để test, cleanup đầy đủ (StrictMode).

## Shared Patterns

### Ghi `lesson.json` an toàn
**Source:** `services/audio/src/audio_service/contract_io.py` dòng 21-23, 26-56, 59-60
**Apply to:** pipeline stages, `PATCH` text, `extend-end`, `translate`, retry, `recover_interrupted`
```python
def dump_contract(model): return model.model_dump(mode="json", by_alias=True, exclude_unset=True)
def write_contract_json(path: Path, model: BaseModel) -> None:
    write_json_atomic(path, dump_contract(model))
```
Quy tắc: bỏ hẳn field optional, không truyền `None`; `write_json_atomic` (tmp + `os.replace`, `allow_nan=False`) vì S1 đọc file đang ghi. Thêm khoá `dict[str, threading.Lock]` theo lesson cho read-modify-write ngoài pipeline (RESEARCH Pattern 2). Dùng `write_json_atomic` cho `settings.json` và sidecar `eval_clips/*.json`.

### Validate id và chặn path traversal
**Source:** `config.py` dòng 44-84; test mẫu `test_api.py` dòng 76-81
**Apply to:** mọi router có `lesson_id`/`index`/`videoId`, mọi helper đường dẫn mới
Client không bao giờ gửi `videoId` hay đường dẫn; luôn đọc từ `lesson.json`. `InvalidIdError` -> 404.

### Lỗi không lộ đường dẫn, thông báo tiếng Việt
**Source:** `routers/lesson.py` dòng 18-22; `test_api.py` dòng 88-94
**Apply to:** mọi endpoint; ánh xạ `DownloadError` -> mã `unavailable` với chuỗi cố định (Pitfall 15), không echo message yt-dlp.

### Pydantic sinh từ contract
**Source:** `audio_service/contracts_gen.py` (sinh), import ở `routers/lesson.py` dòng 5, `pipeline.py` dòng 30
**Apply to:** mọi request/response; không viết model tay cho thứ có trong Zod (model riêng của Python chỉ cho `Health`, `main.py` dòng 16-21). Alias camelCase + `populate_by_name`; build bằng `Model.model_validate({... camelCase ...})` như `build_segments` (`pipeline.py` dòng 115-134).

### DI để test không cần model/mạng
**Source:** `pipeline.py` `PipelineDeps` dòng 44-57; `tests/test_pipeline.py` `Fakes` dòng 63-130
**Apply to:** `JobRunner`, `translate`, key check, system status (model cache check có thể tiêm); không nạp model thật trong `make test`.

### Hàm audio thuần, I/O ở rìa
**Source:** `features.py` (docstring dòng 1-6), `audio_io.py` dòng 1-6
**Apply to:** `vad.py`, `ipa.py`; chỉ `normalize.py`/router chạm file.

### Quản lý bộ nhớ model (máy 8 GB)
**Source:** `pipeline.py` `_real_separate` dòng 60-77, `finally: del ppg_model; deps.free_memory()` dòng 289-291
**Apply to:** warm-up (D-18), `extend-end`, mọi chỗ nạp model: nạp -> chạy -> `del` -> `free_memory()` trong `finally`, dưới `model_gate`. Mở rộng `free_memory` cho `mlx_whisper.ModelHolder` (Pitfall 2).

### Zod ở mọi biên web
**Source:** `packages/contracts/src/cli-parse.ts`, `index.ts` `Schemas`
**Apply to:** `lib/api.ts`; không `any`; TS strict.

### Quy trình contract
**Source:** `scripts/contracts_gen.sh`, `scripts/contracts_check.sh`, `Makefile` mục `contracts`/`test`
**Apply to:** mọi plan chạm contract: Wave 0 riêng, `checkpoint:decision`, drift gate chạy trong `make test` (D-22).

## No Analog Found

| File | Role | Data Flow | Lý do |
|---|---|---|---|
| `apps/web/lib/player/playerMachine.ts` + test | store | event-driven | Chưa có XState trong repo; dùng RESEARCH Pattern 3 |
| `apps/web/lib/audio/*`, `lib/player/actors.ts` | utility | streaming | Không có code trình duyệt; dùng RESEARCH Pattern 4, 5a |
| `apps/web/components/*`, `app/*/page.tsx` | component | request-response | Chỉ có shell layout/page; nguồn là design HTML + UI-SPEC |
| `.../db.py` (sqlite3) | service | CRUD | Chưa có SQLite; theo RESEARCH Pitfall 13 (connection mỗi luồng, WAL, `PRAGMA user_version`, PK `(lesson_id, segment_index, attempt)`, `BEGIN IMMEDIATE`); schema do Liam duyệt (CLAUDE: không tự đổi schema DB) |
| `.../lesson/jobs.py` threading | service | event-driven | Chưa có threading/queue trong repo; theo RESEARCH Pattern 1 |
| `secrets_env.py` (`dotenv.set_key`) | service | file-I/O | Không có analog ghi `.env`; theo RESEARCH Pattern 7; `Settings.model_config` (`config.py` dòng 26-29) là chỗ đọc `.env` hiện tại |

## Metadata

**Analog search scope:** `services/audio/src/audio_service/**`, `services/audio/tests/**`, `packages/contracts/{src,fixtures}`, `apps/web`, `Makefile`, `scripts/`, `docs/decisions`, `docs/design/tokens.md`
**Files scanned:** ~35 (toàn bộ file tracked ngoài `.claude/` và `.planning/` đã liệt kê bằng `git ls-files`)
**Pattern extraction date:** 2026-10-06
