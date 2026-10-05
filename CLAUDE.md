# CLAUDE.md — ShadowEngLab

App luyện shadowing chạy local, chấm điểm bằng cách so audio của người học với audio gốc trong video.
Nguồn sự thật: `docs/product.md`. Đọc file đó trước khi đề xuất hay làm bất kỳ task nào.

## Vai trò

- **Liam (owner):** quyết định sản phẩm, contract (`packages/contracts`), kiến trúc, và duyệt danh sách task mỗi phase.
- **Claude Code:** đề xuất task, hiện thực theo spec, viết test, báo cáo kết quả eval.
- Không tự ý đổi contract, schema DB, ngưỡng chấm hay model. Nếu cần đổi, dừng lại và đề xuất kèm lý do.

## Quy trình mỗi phase

1. Đọc `docs/product.md` (mục của phase) và `docs/phases/Px.md`.
2. Nếu `Px.md` chưa có danh sách task được duyệt: vào plan mode, đề xuất task (mỗi task có tiêu chí hoàn thành đo được), chờ Liam duyệt, rồi ghi vào `Px.md`.
3. Mỗi task: một branch `px/<slug>`, một PR nhỏ. Tick task trong `Px.md` khi merge.
4. Quyết định kỹ thuật mới hoặc lệch khỏi `product.md` → thêm ADR `docs/decisions/NNNN-<slug>.md` trong cùng PR.
5. Từ P3 trở đi: mọi thay đổi về model, ngưỡng hoặc rule phải chạy `make eval` và dán bảng metric vào PR.

## Nguyên tắc không được vi phạm

- Chấm điểm **luôn so với audio gốc**, không so với từ điển hay "phát âm chuẩn". Text chỉ để chia câu, chia từ, hiển thị.
- **Precision trước recall**: khi không chắc, không báo lỗi. Bản gốc không đủ rõ → `ref_unclear`, không chấm.
- LLM chỉ viết gợi ý từ JSON `issues`, không bao giờ nhận audio. Mỗi tip phải trỏ tới một `issueRef`.
- Không dùng LLM đa phương thức để chấm điểm.
- Tính sẵn toàn bộ feature của bản gốc khi tạo bài. Lượt chấm chỉ xử lý audio người học (mục tiêu ≤ 3 giây).
- App phải chạy được khi thiếu API key (gợi ý rơi về template, tắt TTS).
- Không commit audio eval, nhãn thô của người chấm, hay file `.env`.

## Cấu trúc repo

```
apps/web/             Next.js 14 app chính (TS, Tailwind, shadcn/ui, TanStack Query, Recharts, XState cho trình phát)
apps/eval/            Next.js app eval (Vercel + Supabase)
services/audio/       FastAPI (Python 3.11): lesson/, scoring/, rules/
packages/contracts/   Zod schema dùng chung — nguồn sự thật cho mọi kiểu dữ liệu
eval/                 export_clips.py, analyze.py, labels.jsonl (gitignored), clips/ (gitignored)
docs/                 product.md, decisions/, phases/, design/
```

Kiểu Python ở `services/audio` phải khớp với `packages/contracts` (sinh JSON Schema từ Zod, validate bằng pydantic).

## Lệnh

```
make setup     # cài deps Python + Node, tải model (Demucs, mlx-whisper, wav2vec2)
make dev       # chạy Next.js + FastAPI
make test      # pytest + vitest
make eval      # python eval/analyze.py → eval/report.md
```

(Các lệnh được tạo trong P0; cập nhật mục này khi thay đổi.)

## Code style

- TypeScript strict, không `any`. Zod ở mọi ranh giới I/O.
- Python: quản lý bằng uv (`uv sync`, `uv run`), type hints, ruff, pytest. Hàm xử lý audio thuần (input array → output), không đọc file bên trong.
- UI bám theo `docs/design/`. Không tự thêm màn hình hay component ngoài thiết kế đã chốt.
