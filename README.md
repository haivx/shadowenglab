# ShadowEngLab

Web app luyện shadowing tiếng Anh từ bất kỳ video YouTube nào, chạy local. Điểm số so sánh trực tiếp giọng của người học với **audio của chính người nói trong video** (âm, ngữ điệu, trọng âm, ngắt nghỉ), không so với từ điển. Đi kèm một app eval nhỏ để người nghe bản xứ kiểm chứng điểm của hệ thống bằng human review.

> Trạng thái: P0 · thiết kế đã chốt, đang dựng repo và contract. Build được điều phối bằng [GSD](https://github.com/open-gsd/gsd-core), xem [`docs/gsd/kickoff.md`](docs/gsd/kickoff.md).

## Tài liệu

| File | Nội dung |
| --- | --- |
| [`docs/product.md`](docs/product.md) | Product document: phạm vi, hệ thống chấm, app eval, kiến trúc, lộ trình, chi phí |
| [`docs/flows.md`](docs/flows.md) | User flow F0–F5 và bản đồ màn hình |
| [`docs/design/`](docs/design/README.md) | Thiết kế UI v0.2: ảnh và HTML từng màn, token, component |
| [`docs/gsd/`](docs/gsd/) | Roadmap seed P0–P7 và hướng dẫn khởi động GSD |
| [`docs/decisions/`](docs/decisions/) | ADR |
| [`docs/feedback.md`](docs/feedback.md) | Nhật ký dùng thử |
| [`CLAUDE.md`](CLAUDE.md) | Quy tắc làm việc cho Claude Code |

## Cấu trúc

```
apps/web/             Next.js 14 · app chính
apps/eval/            Next.js · app eval (Vercel + Supabase)
services/audio/       FastAPI · pipeline audio và chấm điểm (uv)
packages/contracts/   Zod schema dùng chung
eval/                 export clip, phân tích eval
scripts/              smoke test pipeline
```

## Bắt đầu (sau P0)

```bash
cp .env.example .env
make setup   # cài deps, tải model
make dev     # chạy Next.js + FastAPI
```

Yêu cầu dự kiến: macOS Apple Silicon (mlx-whisper), Node 20+, pnpm, uv, ffmpeg, espeak-ng.
