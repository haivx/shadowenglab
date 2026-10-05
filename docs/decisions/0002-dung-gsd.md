# 0002 · Dùng GSD (gsd-core) để điều phối việc build Step 1

Ngày: 2026-10-05 · Trạng thái: Chấp nhận · Người quyết: Liam

## Bối cảnh

Step 1 có 8 phase (P0–P7, khoảng 11 tuần), làm một mình cùng Claude Code. Cần một khung để giữ ngữ cảnh giữa các phiên, lập kế hoạch từng phase, chạy song song phần độc lập và kiểm tra trước khi ship. Đã cân nhắc: GitHub spec-kit, Fission-AI OpenSpec, open-gsd gsd-core.

## Quyết định

Dùng **gsd-core** cho Step 1.

- spec-kit: nặng, tạo constitution và spec theo feature, trùng lặp với `product.md`, `flows.md`, `docs/design/` đã có.
- OpenSpec: gọn, mạnh cho thay đổi từng phần trên codebase đã chạy, nhưng không quản lý roadmap nhiều phase. Cân nhắc lại cho Step 2 và các cải tiến sau.
- GSD: vòng Discuss → Plan → Execute → Verify → Ship theo phase, state lưu bền giữa phiên, subagent context sạch, chạy trên Claude Code.

## Phân chia nguồn sự thật

| Nội dung | Nơi giữ |
| --- | --- |
| Spec sản phẩm, hệ thống chấm, kiến trúc | `docs/product.md` |
| Luồng người dùng, UI | `docs/flows.md`, `docs/design/` |
| Kiểu dữ liệu | `packages/contracts` |
| Kế hoạch, roadmap, trạng thái, kế hoạch từng phase | File của GSD (tạo từ `docs/gsd/roadmap-seed.md`) |
| Quyết định kỹ thuật | `docs/decisions/` |

`docs/phases/` bị bỏ; nội dung P0 chuyển vào `docs/gsd/roadmap-seed.md`.

## Hệ quả và rủi ro

- GSD có xu hướng tự làm nhiều. Bắt buộc chạy Discuss và chốt contract trước Plan; review PR tại ranh giới.
- Tốn token hơn do nhiều subagent.
- Khi đổi spec sản phẩm: sửa `product.md` trước, sau đó yêu cầu GSD cập nhật roadmap; không sửa hai nơi độc lập.
