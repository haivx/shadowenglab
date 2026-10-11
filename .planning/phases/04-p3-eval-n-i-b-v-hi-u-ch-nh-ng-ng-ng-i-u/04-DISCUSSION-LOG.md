# Phase 4: P3 · Eval nội bộ và hiệu chỉnh ngưỡng ngữ điệu - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-11
**Phase:** 04-P3 · Eval nội bộ và hiệu chỉnh ngưỡng ngữ điệu
**Areas discussed:** Gắn nhãn clip lỗi cố ý, Bộ clip và cách đếm đúng, Held-out và quy trình chỉnh, Mốc đúng/test-retest/report

---

## Gắn nhãn clip lỗi cố ý

| Câu hỏi | Các lựa chọn | Đã chọn |
|---|---|---|
| Ghi loại lỗi và vị trí từ | Khai báo trước (cases.jsonl + tag_clips.py) / CLI gắn sau khi thu / Thêm ô trong app | Khai báo trước |
| Nhãn có thành contract? | Zod `EvalCase` / Chỉ pydantic trong eval/ | Zod `EvalCase` |
| errorType | Tập riêng theo product.md + ánh xạ / Dùng thẳng IssueCode | Tập riêng |
| Commit cases.jsonl | Commit / Gitignore | Commit |
| Chỗ lưu audio | Giữ ở DATA_DIR/eval_clips / Chép sang eval/clips/ | Giữ ở DATA_DIR/eval_clips (+ ghi chú) |

**Notes:** Liam bổ sung: EvalCase lưu dấu nhận diện câu (startMs/endMs của segment hoặc hash text câu). tag_clips.py và analyze.py báo lỗi, không chạy tiếp nếu bài bị xoá hoặc câu không còn khớp. Không xoá hoặc xử lý lại các bài eval. analyze.py chấm lại từ WAV (không dùng result_json cũ).

---

## Bộ clip và cách đếm đúng

| Câu hỏi | Các lựa chọn | Đã chọn |
|---|---|---|
| Phân bổ ~100 clip | Ngữ điệu + âm (~70/~30) / Chỉ ngữ điệu | Ngữ điệu + âm |
| TP cho rule theo từ | Đúng từ, riêng ngắt ±1 / ±1 mọi rule / Chỉ cần đúng loại | Đúng từ, riêng ngắt ±1 |
| Báo ngoài khai báo | Tính FP + cột xem lại / Chỉ FP trên mốc đúng / Đếm riêng | Tính FP + cột xem lại |
| Lỗi liên đới | Bảng mã chính/phụ / Chỉ mã chính | Bảng mã chính/phụ |
| Nguồn câu | 3–4 bài ~25–30 câu / 2 bài đang có / Nhiều câu 1–2 lỗi | 3–4 bài ~25–30 câu |
| Căn thất bại | Tính FN + tỉ lệ riêng / Loại khỏi mẫu số | Tính FN + tỉ lệ riêng |

---

## Held-out và quy trình chỉnh

| Câu hỏi | Các lựa chọn | Đã chọn |
|---|---|---|
| Đơn vị tách | Theo câu, phân tầng / Theo bài / Theo clip ngẫu nhiên | Theo câu, phân tầng |
| Cách chỉnh | Script quét + Liam chọn / Chỉnh tay theo report / Tối ưu tự động | Script quét + Liam chọn |
| Đơn vị 90% | Từng rule + gộp (Wilson CI, ≥5 lần báo) / Chỉ gộp / Từng rule không CI | Từng rule + gộp |
| Rule trượt | Tắt rule, ghi ADR / Một vòng chỉnh lại / Thu held-out mới | Tắt rule, ghi ADR |
| Khoá held-out | Cờ HOLDOUT=1 có log / Luôn in cả hai | Cờ HOLDOUT=1 |
| Trọng số điểm tổng | Chỉ đo, không đổi / Chỉnh luôn ở Phase 4 | Chỉ đo |

---

## Mốc đúng, test-retest, report

| Câu hỏi | Các lựa chọn | Đã chọn |
|---|---|---|
| Mốc đúng | Tự so + Liam đọc tốt / Có thêm người bản xứ / Chỉ tự so | Tự so + Liam đọc tốt |
| Test-retest | Hai lần đọc cùng ý định (+ tất định) / Chỉ kiểm tất định | Hai lần đọc |
| Report | Commit + khối tóm tắt / Gitignore, chỉ dán PR | Commit + khối tóm tắt |
| Gate | Exit code khi trượt / Chỉ báo cáo | Exit code khi trượt |

---

## Claude's Discretion

Dấu nhận diện câu cụ thể; UX tag_clips.py; ngưỡng chính và lưới cho sweep; cấu trúc eval/; cách sinh mốc tự so; bố cục chi tiết report.md; đề xuất bảng mã chính/phụ (Liam duyệt); ADR 0007.

## Deferred Ideas

- Trọng số điểm tổng (D-a) — Phase 8
- Người bản xứ đọc câu (speaker invariance) — Phase 6 hoặc sau
- CI eval regression — Step 2
- Rule bị tắt — Phase 8 xem lại
