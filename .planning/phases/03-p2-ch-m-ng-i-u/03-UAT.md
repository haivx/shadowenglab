---
status: testing
phase: 03-p2-ch-m-ng-i-u
source: [03-VERIFICATION.md]
started: 2026-10-10T18:53:26.038Z
updated: 2026-10-10T18:53:26.038Z
---

## Current Test

number: 1
name: Quyết định SC2: chấp nhận hay nới 'Câu đọc sai hẳn cho điểm thấp'
expected: |
  Liam ghi override (có chữ ký) hoặc yêu cầu chỉnh công thức/trọng số. Trên bài mặc định, trung vị 20 cặp chéo câu = 0.616 (vùng vàng 60-79), `make smoke-score` thoát 1 với 'SCORE FAILED: trung vị chéo câu 0.616 >= 0.6'. Bài còn lại 0.518 (đỏ)
awaiting: user response

## Tests

### 1. Quyết định SC2: chấp nhận hay nới 'Câu đọc sai hẳn cho điểm thấp'
expected: Liam ghi override (có chữ ký) hoặc yêu cầu chỉnh công thức/trọng số. Trên bài mặc định, trung vị 20 cặp chéo câu = 0.616 (vùng vàng 60-79), `make smoke-score` thoát 1 với 'SCORE FAILED: trung vị chéo câu 0.616 >= 0.6'. Bài còn lại 0.518 (đỏ)
result: [pending]

### 2. UAT 03-11 mục 1: giọng thật, 3-5 câu đúng và 3-5 câu sai rõ (câu khác / phẳng / ngắt thêm / lên thay vì xuống)
expected: Câu đúng điểm cao, cost căn <= 1.10 (RESEARCH A1), không issue giả; câu sai điểm thấp và có issue hợp lý
result: [pending]

### 3. UAT 03-11 mục 2-3: sáu trạng thái vùng câu và panel kết quả so với design
expected: Khớp S3-trang-thai-cau.png, S3-S4-phong-tap.png; biểu đồ câu 1 từ và ~25 từ; tip dài / câu 18 từ ở 1280 px không tràn
result: [pending]

### 4. UAT 03-11 mục 4: O / M / B, R hai lần, danh sách câu và thanh tiến độ theo điểm tốt nhất
expected: 'tốt nhất' đứng yên; chip cũ hiện kết quả đã lưu; M/B tắt kèm tooltip; tải lại trang thì chip được khôi phục từ server
result: [pending]

### 5. UAT 03-11 mục 5: không có OPENAI_API_KEY
expected: Chấm và tip template vẫn chạy, không nhãn 'AI'
result: [pending]

### 6. UAT 03-12 Task 3 (5 mục): biến thể tip theo lượt, nhận xét theo chỉ số khi không có issue
expected: Lượt sau của cùng câu đổi cách nói; điểm thấp không issue thì có nhận xét theo chỉ số; mở lại lượt cũ ra đúng chữ lúc chấm. SUMMARY 03-12 ghi 'not run' cho cả 5 mục
result: [pending]

### 7. PRO-04 dưới tải: chấm một câu khi worker model đang chạy Demucs, và bài cũ chưa có sidecar (ref_backfill)
expected: Tổng thời gian <= 3 s
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
