# services/audio — Pipeline audio (Python 3.11, FastAPI, quản lý bằng uv)

Sau P0 service có: FastAPI skeleton (`/health`, `GET /lessons/{id}`, router `/scoring` rỗng) và pipeline tạo bài đầu–cuối (yt-dlp → ffmpeg → Demucs → mlx-whisper → tách câu → F0 + energy + PPG của bản gốc). Chưa có chấm điểm: package `scoring/` (Lớp A và B) và `rules/` (Lớp C) chưa tồn tại, được thêm ở Phase 3 và Phase 5 của GSD (P2 chấm ngữ điệu, P4 chấm âm).

Spec: `docs/product.md` mục 3. Quyết định: `docs/decisions/0003-contract-toolchain-va-moi-truong-p0.md`.

## Bản đồ module (`src/audio_service/`)

| File | Vai trò |
| --- | --- |
| `main.py` | `create_app()`: `/health` (model `Health` riêng của Python), CORS chỉ cho `http://localhost:3000` với method GET |
| `routers/lesson.py` | `GET /lessons/{lesson_id}` trả `lesson.json` validate theo `Lesson`; id sai hoặc không có file thì 404, file hỏng thì 500 |
| `routers/scoring.py` | router `/scoring` rỗng (Phase 3/5 thêm endpoint) |
| `config.py` | `Settings` (đọc `.env` ở gốc repo), `data_root()` (expand `~`), helper đường dẫn D-08 kiểm tra id bằng regex và xác nhận đường dẫn nằm trong `DATA_DIR` |
| `contract_io.py` | `dump_contract` (by_alias + exclude_unset), `write_json_atomic`, `write_contract_json` (ghi qua file tạm rồi `os.replace`) |
| `contracts_gen.py` | **GENERATED** từ `packages/contracts/schema/contracts.schema.json`, không sửa tay; chạy `make contracts` |
| `models.py` | nguồn duy nhất của id model đã khoá (whisper-large-v3-turbo, wav2vec2-lv-60-espeak-cv-ft, htdemucs); đổi model cần Liam duyệt |
| `setup_models.py` | `python -m audio_service.setup_models`: tải hoặc tìm cache ba model, kiểm tra parselmouth, ffmpeg, MPS, in bảng trạng thái (`--no-download` chỉ kiểm tra cache) |
| `lesson/urls.py` | `parse_youtube_url`, `canonical_watch_url`: cổng URL YouTube (chỉ nhận id 11 ký tự từ host cho phép) |
| `lesson/download.py` | `fetch_info`, `download_video` bằng yt-dlp Python API, cache theo `videoId` |
| `lesson/audio_io.py` | `extract_audio` (ffmpeg), `read_audio`, `write_audio`, `to_mono_16k`, `slice_seconds` |
| `lesson/separate.py` | Demucs `htdemucs` (`shifts=0`, `overlap=0.25`, `split=True`), MPS và fallback CPU |
| `lesson/transcribe.py` | mlx-whisper với `word_timestamps=True` |
| `lesson/segment.py` | `split_sentences`: tách câu từ danh sách từ Whisper (hàm thuần) |
| `lesson/quality.py` | `non_vocal_ratio`, `audio_quality_label` (nhãn `clean` hoặc `music`) |
| `lesson/features.py` | `extract_f0` (parselmouth), `frame_energy`, `compute_ppg` (wav2vec2), `segment_window` |
| `lesson/timing.py` | `StepTimer` và bảng thời gian từng bước |
| `lesson/pipeline.py` | `run_lesson(url, start, end)`: chạy cả chuỗi, ghi lại `lesson.json` ở mọi lần đổi trạng thái; stage nặng tiêm qua `PipelineDeps` nên test dùng stage giả |

Quy ước: hàm xử lý audio thuần (mảng vào, mảng ra); chỉ `audio_io`, `download`, `pipeline` chạm file. Kiểu dữ liệu dùng model sinh từ contract, không tự định nghĩa lại.

## Cấu hình và bố cục `DATA_DIR`

`DATA_DIR` đọc từ `.env` ở gốc repo (mặc định `~/shadowenglab-data`, service tự expand `~`). Không có API key nào cần cho phần đã có.

```
DATA_DIR/
  videos/{videoId}/
    video.mp4  audio.wav  vocals.wav  no_vocals.wav   # cache theo videoId, dùng chung giữa các bài
    info.json                                          # metadata yt-dlp: title, durationSec, thumbnailUrl
  lessons/{lessonId}/
    lesson.json                                        # Lesson (contract), ghi lại ở mọi lần đổi trạng thái
    seg/0000.npz, 0001.npz, ...                        # feature bản gốc mỗi câu: f0_hz, energy, ppg, window (+ sr, f0_hop_s, ppg_fps)
    timing.json                                        # chỉ do scripts/smoke_lesson.py ghi: thời gian từng bước
```

`lessonId` là ulid, `videoId` là id YouTube 11 ký tự. Feature bản gốc nằm ngoài contract (D-08).

## Lệnh

```bash
make setup                                  # cài deps từ lockfile và tải model (xem README gốc)
make dev-api                                # chỉ FastAPI, 127.0.0.1:8000, có --reload
make smoke                                  # chạy pipeline trên video smoke (xem scripts/README.md)
cd services/audio && uv run --frozen pytest # toàn bộ test (stage giả, không nạp model; test round-trip gọi pnpm/tsx nên cần đã chạy make setup)
cd services/audio && uv run --frozen ruff check --config pyproject.toml . ../../scripts
```

`make test` chạy drift gate contract rồi vitest rồi pytest; `make lint` gọi ruff đúng như dòng cuối ở trên (chạy từ `services/audio` để đọc `[tool.ruff]`).
