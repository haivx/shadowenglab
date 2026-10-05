# 0001 · Python dùng uv, trình phát dùng XState

Ngày: 2026-10-05 · Trạng thái: Chấp nhận · Người quyết: Liam

## Bối cảnh

P0 cần chốt công cụ quản lý môi trường Python cho `services/audio`, và cách hiện thực state machine của trình phát theo câu (`idle → playing → recording → scoring → reviewing`, cùng các nhánh lỗi, thử lại, chế độ ôn luyện).

## Quyết định

1. **uv** quản lý Python và dependency của `services/audio` (`uv sync`, `uv run`, lockfile `uv.lock`).
2. **XState** hiện thực state machine trình phát trong `apps/web`.

## Lý do

- uv cài nhanh, một công cụ lo cả phiên bản Python lẫn dependency, hợp với yêu cầu "clone, `make setup`, chạy được".
- Trình phát có nhiều trạng thái và nhánh (mất tiếng, lỗi chấm, chế độ chỉ ngữ điệu, TTS). XState cho state chart tường minh, kiểm thử được từng transition, và là spec rõ ràng để review khi giao cho Claude Code.

## Hệ quả

- `make setup` gọi `uv sync`; README ghi yêu cầu cài uv.
- Machine của trình phát nằm ở một file riêng (ví dụ `apps/web/features/player/machine.ts`), có test cho các transition chính trước khi gắn UI.
- Không dùng `useReducer` cho luồng trình phát; state UI đơn giản khác vẫn dùng React state bình thường.
