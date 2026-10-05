# Bắt đầu với GSD

## 1. Cài

```bash
cd shadowenglab
npx @opengsd/gsd-core@latest    # chọn runtime: Claude Code
```

Sau khi cài, xem danh sách lệnh thật của bản bạn cài (gõ `/` trong Claude Code, lọc "gsd"). Tên lệnh dưới đây là theo tài liệu công khai; nếu khác, dùng lệnh tương ứng của bản cài.

## 2. Khởi tạo project context

Repo đã có tài liệu nhưng chưa có code, nên dùng lệnh khởi tạo project (new project). Nếu GSD phát hiện repo đã có nội dung và gợi ý onboard thì làm theo gợi ý đó. Khi được hỏi về dự án, dán prompt sau:

```text
Đây là ShadowEngLab. Đừng phỏng vấn lại từ đầu: mọi quyết định đã có trong tài liệu.
Đọc theo thứ tự:
1. docs/product.md        — spec sản phẩm (nguồn sự thật cấp sản phẩm)
2. docs/gsd/roadmap-seed.md — phases P0–P7, phạm vi, tiêu chí hoàn thành, phụ thuộc, quyết định đã khoá
3. docs/flows.md và docs/design/README.md — luồng người dùng và spec UI
4. CLAUDE.md và docs/decisions/ — quy tắc làm việc và ADR

Tạo project context và roadmap của GSD từ các tài liệu này, giữ đúng 8 phase P0–P7 và tiêu chí hoàn thành của từng phase làm điều kiện Verify.
Đánh dấu phần thiết kế UI của P0 là đã xong.
Chỉ hỏi tôi những điểm tài liệu thật sự chưa trả lời.
```

## 3. Vòng lặp cho mỗi phase

| Bước GSD | Liam làm gì |
| --- | --- |
| Discuss | Chốt contract trong `packages/contracts` và các quyết định còn mở **trước** khi cho plan. Không bỏ qua bước này. |
| Plan | Đọc kế hoạch GSD đề xuất; sửa nếu chia task sai ranh giới (schema, state machine, pipeline). |
| Execute | Để GSD chạy. Song song chỉ cho phần độc lập (P4 với P5). |
| Verify | Đối chiếu với "tiêu chí hoàn thành" của phase. Từ P3: kèm kết quả `make eval`. |
| Ship | Review PR tại ranh giới, merge. Ghi ADR nếu có quyết định mới. |

## 4. Giữa các phase

- Ghi chỗ vướng khi tự dùng app vào `docs/feedback.md`.
- Thay đổi lớn về UI: sửa trên canvas thiết kế trước, export lại vào `docs/design/`, rồi mới cho GSD làm.
