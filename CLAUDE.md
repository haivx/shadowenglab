# CLAUDE.md — ShadowEngLab

App luyện shadowing chạy local, chấm điểm bằng cách so audio của người học với audio gốc trong video.
Nguồn sự thật: `docs/product.md`. Đọc file đó trước khi đề xuất hay làm bất kỳ task nào.

## Vai trò

- **Liam (owner):** quyết định sản phẩm, contract (`packages/contracts`), kiến trúc, và duyệt danh sách task mỗi phase.
- **Claude Code:** đề xuất task, hiện thực theo spec, viết test, báo cáo kết quả eval.
- Không tự ý đổi contract, schema DB, ngưỡng chấm hay model. Nếu cần đổi, dừng lại và đề xuất kèm lý do.

## Quy trình (GSD)

Dự án dùng GSD (gsd-core) để điều phối, xem `docs/decisions/0002-dung-gsd.md` và `docs/gsd/kickoff.md`.

1. Kế hoạch, roadmap và trạng thái nằm trong file của GSD. Đầu vào ban đầu: `docs/gsd/roadmap-seed.md`.
2. Mỗi phase đi đủ Discuss → Plan → Execute → Verify → Ship. **Không bỏ Discuss**: contract trong `packages/contracts` và quyết định còn mở phải được Liam chốt trước khi Plan.
3. Verify đối chiếu đúng "tiêu chí hoàn thành" của phase trong roadmap. Từ P3 trở đi: mọi thay đổi về model, ngưỡng hoặc rule phải chạy `make eval` và dán bảng metric vào PR.
4. Mỗi PR nhỏ, review được tại ranh giới (schema, state machine, output pipeline).
5. Quyết định kỹ thuật mới hoặc lệch khỏi `docs/product.md` → thêm ADR `docs/decisions/NNNN-<slug>.md` trong cùng PR. Đổi spec sản phẩm: sửa `product.md` trước, rồi cập nhật roadmap GSD.
6. Song song chỉ cho phần độc lập (ví dụ P4 với P5).

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
docs/                 product.md, flows.md, design/, decisions/, gsd/ (seed + kickoff)
```

Kiểu Python ở `services/audio` phải khớp với `packages/contracts` (sinh JSON Schema từ Zod, validate bằng pydantic).

## Lệnh

```
make setup     # kiểm tra system deps (thiếu thì in lệnh brew rồi dừng), cài deps Python + Node từ lockfile, tải model Demucs, mlx-whisper, wav2vec2
make dev       # chạy FastAPI (127.0.0.1:8000) + Next.js (localhost:3000)
make test      # drift gate contract + vitest + pytest
make lint      # eslint, prettier, tsc, ruff
make eval      # stub ở P0; Phase 4: python eval/analyze.py → eval/report.md
make smoke     # scripts/smoke_lesson.py trên scripts/smoke_video.url (tuỳ chọn: URL=, START=, END=, BUDGET=)
make contracts # sinh lại JSON Schema + pydantic từ Zod (packages/contracts)
make dev-eval  # khung app eval (localhost:3001)
```

(Cập nhật mục này khi đổi Makefile.)

## Code style

- TypeScript strict, không `any`. Zod ở mọi ranh giới I/O.
- Python: quản lý bằng uv (`uv sync`, `uv run`), type hints, ruff, pytest. Hàm xử lý audio thuần (input array → output), không đọc file bên trong.
- UI bám theo `docs/design/`. Không tự thêm màn hình hay component ngoài thiết kế đã chốt.
