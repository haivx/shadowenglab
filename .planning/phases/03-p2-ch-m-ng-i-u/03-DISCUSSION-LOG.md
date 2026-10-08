# Phase 3: P2 · Chấm ngữ điệu - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-08
**Phase:** 03-p2-ch-m-ng-i-u
**Areas discussed:** Căn thời gian user↔gốc, Điểm tổng & chip từ ở P2, Lưu điểm & lượt tốt nhất, Rule: cổng chắc chắn & chọn tip

---

## Căn thời gian user↔gốc

| Option | Description | Selected |
|--------|-------------|----------|
| DTW trên MFCC | Không model, < 100 ms, không tranh model_gate; giao diện `align` để Phase 5 thay PPG-DTW | ✓ |
| PPG wav2vec2 + DTW ngay | Bền với giọng nhưng phải nạp model mỗi lượt hoặc giữ resident (trái D-18), xếp hàng sau job | |
| Whisper trên bản ghi | Model nặng, dễ vượt 3 s, nhận dạng sai thì không ghép được | |

| Option (căn kém) | Description | Selected |
|--------|-------------|----------|
| Giữ chỉ số câu, bỏ issue theo từ | Precision trước recall, không đổi contract | ✓ |
| Trạng thái riêng "không khớp câu" | Cần đổi contract, trạng thái thứ 7 | |
| Cứ chấm bình thường | Dễ issue sai vị trí | |

| Option (bài cũ thiếu feature) | Description | Selected |
|--------|-------------|----------|
| Tính bù lười khi chấm lần đầu, ghi cache | Không cần model, bài mới tính sẵn | ✓ |
| Phải tạo lại bài | Code đơn giản hơn | |
| Script migrate một lần | | |

**User's choice:** Cả ba theo đề xuất.

---

## Điểm tổng & chip từ ở P2

| Option (công thức) | Description | Selected |
|--------|-------------|----------|
| TB đều | intonation = TB(pitchRange, melodyMatch); rhythm = speed; overall = TB 3 chỉ số | ✓ |
| Nghiêng về giai điệu | overall = 0.5·melody + 0.25·range + 0.25·speed | |
| Rhythm có tính ngắt nghỉ | speed × hệ số phạt ngắt thừa | |

| Option (Pearson) | Description | Selected |
|--------|-------------|----------|
| max(0, r) | Sai hẳn → 0 | ✓ |
| (r + 1) / 2 | Không tương quan vẫn 50% | |
| Claude quyết | | |

| Option (chip từ) | Description | Selected |
|--------|-------------|----------|
| Câu trơn, không điểm từng từ | similarity điền nhưng UI không tô khi sound = null | ✓ |
| Chip theo điểm ngữ điệu từng từ | Nghĩa màu đổi ở Phase 5 | |

| Option (phần Lớp A) | Description | Selected |
|--------|-------------|----------|
| Ẩn hẳn | Không thêm UI ngoài thiết kế | ✓ |
| Giữ chỗ kèm ghi chú | UI ngoài thiết kế | |

**User's choice:** Cả bốn theo đề xuất.

---

## Lưu điểm & lượt tốt nhất

| Option (endpoint) | Description | Selected |
|--------|-------------|----------|
| POST attempts trả ScoreResult | Một request; không tiếng → ApiError `no_speech`; AttemptAck chỉ cho eval-clip | ✓ |
| Hai bước: ack rồi chấm | Phải giữ WAV tạm, thêm một vòng request | |

| Option (lưu trữ) | Description | Selected |
|--------|-------------|----------|
| Cột điểm + JSON đầy đủ | Migration v1→v2, `result_json` | ✓ |
| Cột điểm + bảng issues | Không xem lại chi tiết lượt cũ | |
| Cả hai | Trùng dữ liệu | |

| Option (tốt nhất) | Description | Selected |
|--------|-------------|----------|
| Theo overall, bấm chip xem lại | Hoà lấy lượt sau; lượt P1 giữ chấm xám | ✓ |
| Theo overall, chip chỉ để xem | | |

**User's choice:** Cả ba theo đề xuất.

---

## Rule: cổng chắc chắn & chọn tip

| Option (cổng chắc chắn) | Description | Selected |
|--------|-------------|----------|
| Có, Claude đề xuất, Liam duyệt | Frame hữu thanh, biên δ prominence, slope tối thiểu, bản gốc phẳng; file ngưỡng có version | ✓ |
| Chỉ dùng ngưỡng product.md | | |

| Option (PITCH_DEVIATION) | Description | Selected |
|--------|-------------|----------|
| 3 st | Ưu tiên precision | ✓ |
| 2 st | | |
| 2.5 st | | |

| Option (chọn tip) | Description | Selected |
|--------|-------------|----------|
| Ưu tiên cố định, mỗi mã 1 tip | STRESS > FINAL > PAUSE > PITCH_DEV > FLAT, tối đa 3 | ✓ |
| Theo mức lệch chuẩn hoá | Có thể trùng mã | |

| Option (không có issue) | Description | Selected |
|--------|-------------|----------|
| Theo scoreLevel(overall) | ≥ 80 khen, < 80 câu trung tính | ✓ |
| Luôn khen ngắn | Có thể khen lượt điểm thấp | |

**User's choice:** Cả bốn theo đề xuất.

---

## Câu hỏi thêm

| Option (trạng thái 6) | Description | Selected |
|--------|-------------|----------|
| P2 làm "lỗi", ref_unclear để Phase 5 | Khớp FBK-05 | ✓ |
| Làm cả hai | Code chết tới Phase 5 | |

| Option (nợ Phase 2) | Description | Selected |
|--------|-------------|----------|
| Chạy riêng trước khi Plan | `/gsd-code-review 02 --fix`; 3 điểm chờ chốt vào Deferred | ✓ |
| Gộp vào Wave 0 Phase 3 | | |
| Để sau | | |

## Claude's Discretion

- Tham số MFCC/DTW, cắt lặng, độ đo chất lượng căn
- F0 hai lượt hay giữ 75–500 Hz; lọc quãng tám, nội suy, làm mượt
- Resample contour, `wordBounds`, `stress[]`, `pauses[]`
- Văn phong template, `IntonationChart` bằng Recharts
- Vị trí `scoreLevel()`, endpoint đọc lại lượt cũ

## Deferred Ideas

- Nợ Phase 2 (17 finding, EXTEND_MAX_MS, WR-04, WR-05) — xử lý riêng trước Plan
- ref_unclear + chip theo điểm âm — Phase 5
- Rhythm phạt ngắt nghỉ / trọng số khác — Phase 8
- intonationOnly — Phase 7
