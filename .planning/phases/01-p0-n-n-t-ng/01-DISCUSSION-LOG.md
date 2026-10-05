# Phase 1: P0 · Nền tảng - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-05
**Phase:** 1-P0 · Nền tảng
**Areas discussed:** Contract Lesson/Segment, Contract ScoreResult, Label/Manifest/codegen, Model và ngân sách 5 phút

---

## Contract Lesson/Segment

| Câu hỏi | Các lựa chọn | Đã chọn |
|---------|--------------|---------|
| Đơn vị thời gian | Giây float + ms · Toàn bộ ms nguyên · Toàn bộ giây float | Giây float + ms ✓ |
| Feature bản gốc lưu ở đâu | File ngoài contract · Đường dẫn trong contract · Nhúng F0 vào Segment | File ngoài contract ✓ |
| Field của Word | Đủ, có optional · Tối thiểu | Đủ, có optional ✓ |
| Trạng thái job | Trong Lesson · Contract Job riêng | Trong Lesson ✓ |
| Kiểu đặt tên | camelCase · snake_case | camelCase ✓ |
| Lesson id | Nhiều bài / video · 1 bài / video | Nhiều bài / video ✓ |
| Đệm câu và "Mất chữ cuối?" | Giữ mốc gốc + extendMs · Ghi đè start/end | Giữ mốc gốc + extendMs ✓ |
| Field dịch | translation?: string · Chưa thêm | translation?: string ✓ |

---

## Contract ScoreResult

| Câu hỏi | Các lựa chọn | Đã chọn |
|---------|--------------|---------|
| Điểm tổng | scores 4 field · Chỉ overall | scores 4 field ✓ |
| Thang điểm | 0..1 float · 0..100 int | 0..1 float ✓ |
| issues.data | Union theo code · Record tự do | Union theo code ✓ |
| Contour | Cả câu + mốc từ · Chia theo từ · Như bản nháp | Cả câu + mốc từ ✓ |
| Nguồn tip | source trên mỗi tip · Không cần | source trên mỗi tip ✓ |
| Metadata | Có, kèm version · Chỉ ID câu | Có, kèm version ✓ |
| Status từ | status = phân loại · Giữ như bản nháp | status = phân loại ✓ |

---

## Label, Manifest, codegen

| Câu hỏi | Các lựa chọn | Đã chọn |
|---------|--------------|---------|
| wordFlags | Mảng theo từ · Map theo cờ | Mảng theo từ ✓ |
| Sinh JSON Schema | Zod v4 toJSONSchema · Zod v3 + zod-to-json-schema | Zod v4 toJSONSchema ✓ |
| Pydantic | Sinh tự động (datamodel-code-generator) · Viết tay + test | Sinh tự động ✓ |
| Vị trí schema | Commit trong contracts · Chỉ sinh khi build | Commit trong contracts ✓ |

**Notes:** ClipManifest giữ nguyên bản nháp product.md (không hỏi riêng). Đã tra Context7 (`/colinhacks/zod/v4.3.6`): `z.toJSONSchema` mặc định draft-2020-12, discriminatedUnion → `oneOf`.

---

## Model và ngân sách 5 phút

| Câu hỏi | Các lựa chọn | Đã chọn |
|---------|--------------|---------|
| mlx-whisper | large-v3-turbo · large-v3 · small.en/medium.en | large-v3-turbo ✓ |
| Demucs | htdemucs 2 stem · htdemucs_ft | htdemucs 2 stem ✓ |
| System deps | Kiểm tra và hướng dẫn · Tự brew install | Kiểm tra và hướng dẫn ✓ |
| Vượt 5 phút | Tối ưu, không đổi model · Được hạ model | Tối ưu, không đổi model ✓ |

---

## Claude's Discretion

- Thiết bị/batch cho wav2vec2, cấu trúc nội bộ `services/audio`, heuristic tách câu trong khuôn khổ spec, thư viện ulid, cấu hình lint, cách chạy `make dev`, đề xuất ngưỡng `nonVocalRatio`, rà `.env.example`.

## Deferred Ideas

- Nguồn bản dịch (P1); công thức gộp điểm (P2/P4); ngưỡng `nonVocalRatio` chính thức và tinh chỉnh bằng `ref_unclear` (P1/P5).
