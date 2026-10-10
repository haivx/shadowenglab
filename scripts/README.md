# scripts

Script của P0. Chạy từ gốc repo; hầu hết đã có lệnh `make` bọc sẵn.

| Script | Dùng qua | Việc |
| --- | --- | --- |
| `smoke_lesson.py` | `make smoke` | chạy pipeline tạo bài đầu–cuối trên một video YouTube |
| `smoke_video.url` | `make smoke` | URL video smoke mặc định (một dòng) |
| `check_deps.sh` | dòng đầu của `make setup` | kiểm tra system dependency, chỉ in lệnh cài |
| `contracts_gen.sh` | `make contracts` | sinh JSON Schema từ Zod và pydantic từ JSON Schema |
| `contracts_check.sh` | `make test` (qua `contracts-check`) | drift gate: sinh lại vào thư mục tạm và so với bản đã commit |
| `dev_smoke.sh` | chạy trực tiếp | kiểm tra tự động `make dev` |

## `smoke_lesson.py <youtube_url>`

```bash
make smoke                                   # dùng URL trong scripts/smoke_video.url
make smoke URL=<link youtube> START=60 END=180 BUDGET=300

# hoặc gọi thẳng
uv run --project services/audio --frozen python scripts/smoke_lesson.py <url> [--start S] [--end E] [--budget-s N]
```

- `--start`, `--end`: khoảng giây của video cần tạo bài (mặc định cả video). `--budget-s`: tổng thời gian tối đa, vượt thì thoát 3.
- Dữ liệu ghi vào `DATA_DIR` (xem `services/audio/README.md`); lần chạy thứ hai trên cùng video dùng lại cache `videos/{videoId}`.
- Output: dòng `LESSON_ID=<ulid>` (ngay khi bài được tạo), mỗi lần đổi trạng thái một dòng `[status]`, bảng thời gian từng bước (download, demucs, whisper, segment, f0, ppg, …, tổng) cùng wall time, `nonVocalRatio` và số segment, rồi `SELF-CHECK OK` (đọc lại `lesson.json` bằng model của contract và kiểm mỗi segment có `f0_hz`, `energy`, `ppg`, `window`). Có `--budget-s` thì in thêm `BUDGET OK` hoặc `BUDGET EXCEEDED`.
- Mã thoát: `0` thành công; `1` pipeline lỗi hoặc `SELF-CHECK FAILED`; `2` URL hoặc khoảng sai; `3` vượt ngân sách.

Đo trên máy của Liam (Apple Silicon 8 GB): video 308 s, khoảng 0–300 s, từ `DATA_DIR` rỗng xong trong 125.3 s và 115.8 s (ngân sách 300 s).

## `smoke_score.py` (`make smoke-score`)

Chấm ngữ điệu trên một bài thật trong `DATA_DIR`, không cần micro (Phase 3, PRO-03, PRO-04).

```sh
make smoke-score                       # bài ready mới tạo nhất
make smoke-score LESSON=<lessonId>     # chọn bài
uv run --project services/audio --frozen python scripts/smoke_score.py --limit 20 --data-dir PATH
```

- Lấy tối đa `--limit` câu dài 3–8 s, rải đều trong bài. "Người học" là chính lát vocal của câu, đệm 0.3 s lặng hai đầu, mã hoá webm/opus bằng ffmpeg rồi chuẩn hoá như một lượt tải lên. Tự so: chấm với bản gốc của chính câu đó. Chéo câu: chấm với bản gốc của câu kế tiếp.
- In bảng (tự so, issue, ms, cặp chéo, căn, cost, tỉ lệ độ dài) và các dòng tóm tắt, rồi `SCORE OK` hoặc `SCORE FAILED: <lý do>`. Hỏng khi: trung vị tự so < 0.97, một câu tự so < 0.90, tự so sinh issue, p95 thời gian chấm ≥ 3000 ms, hoặc trung vị chéo câu ≥ 0.6 (tiêu chí D-a, ADR 0006). Cặp chéo câu vẫn căn ok chỉ được in ra để theo dõi.
- **Chỉ đọc:** không ghi sidecar (`write_cache=False`), không đụng SQLite, file tạm nằm trong thư mục tạm của hệ thống và bị xoá khi thoát. Chỉ in số, không ghi gì vào repo.
- Mã thoát: `0` OK; `1` SCORE FAILED; `2` tham số sai, không có bài `ready`, thiếu audio bản gốc hoặc dưới 2 câu dùng được.

## Các script còn lại

- `check_deps.sh`: kiểm tra macOS Apple Silicon, ffmpeg, espeak-ng, uv, Node ≥ 22.13, pnpm. Thoát 0 khi đủ, 1 khi thiếu (kèm lệnh `brew install …` hoặc `npm install -g pnpm@11.9.0`). Không bao giờ tự cài gì.
- `contracts_gen.sh [schema_dir] [pydantic_file]`: không tham số thì ghi `packages/contracts/schema/contracts.schema.json` và `services/audio/src/audio_service/contracts_gen.py`; hai tham số tuỳ chọn để ghi ra nơi khác (drift gate dùng).
- `contracts_check.sh`: thoát 0 và in "contracts: không lệch", hoặc in diff và "CONTRACT DRIFT" rồi thoát 1. Tạo thư mục tạm `services/audio/.contracts-check.*` (nằm trong `services/audio` để ruff đọc đúng cấu hình) và xoá khi thoát.
- `dev_smoke.sh`: chạy `make dev`, đợi `http://127.0.0.1:8000/health` và `http://localhost:3000/` cùng trả lời, tuỳ chọn kiểm `GET /lessons/$LESSON_ID` trả `ready`, rồi gửi một SIGTERM tới process group của `make dev` và kiểm hai cổng đã đóng. In `DEV-SMOKE OK` (thoát 0) hoặc `DEV-SMOKE FAIL` kèm 40 dòng log cuối (thoát 1). Từ chối chạy nếu cổng 8000 hoặc 3000 đang bị chiếm. Ví dụ: `DATA_DIR=... LESSON_ID=<ulid> sh scripts/dev_smoke.sh`.
