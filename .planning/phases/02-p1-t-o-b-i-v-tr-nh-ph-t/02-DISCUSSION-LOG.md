# Phase 2: P1 · Tạo bài và trình phát - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-06
**Phase:** 02-p1-t-o-b-i-v-tr-nh-ph-t
**Areas discussed:** Job nền & lưu trữ, Ghi âm khi chưa chấm, Settings & API key, IPA/bản dịch/IFrame

---

## Job nền & lưu trữ

| Option | Description | Selected |
|--------|-------------|----------|
| Tải song song, model xếp hàng | yt-dlp song song; bước model tuần tự từng job, job chờ = queued | ✓ |
| Toàn bộ job xếp hàng FIFO | 1 job một lúc từ tải tới phân tích | |
| Chạy song song hoàn toàn | Tranh MPS/RAM, có thể vượt ngân sách | |

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite cho tiến độ, JSON cho Lesson | lesson.json giữ nguyên; bảng `attempts` trong SQLite | ✓ |
| Chỉ file JSON ở P1 | SQLite để Phase 3/7, phải migrate | |
| Toàn bộ vào SQLite | Lệch D-08, cần ADR | |

| Option | Description | Selected |
|--------|-------------|----------|
| Đánh dấu lỗi + Thử lại | failed 'bị gián đoạn', nút Thử lại, cache videoId | ✓ |
| Tự chạy lại khi khởi động | Có thể lặp mãi nếu lỗi do video | |

| Option | Description | Selected |
|--------|-------------|----------|
| Chỉnh tách câu trong P1 | Gộp mạnh hơn về 3–8 s, báo phân bố trước/sau | ✓ |
| Giữ nguyên | Chỉnh sau khi có trải nghiệm | |

**User's choice:** Tất cả theo khuyến nghị.

---

## Ghi âm khi chưa chấm

| Option | Description | Selected |
|--------|-------------|----------|
| Nghe so sánh, không điểm | Upload chuẩn hoá + phát hiện im lặng → reviewing O/M/B/R/→; giữ state scoring | ✓ |
| Chỉ báo 'Đã ghi' rồi sang câu | Không nghe lại | |

| Option | Description | Selected |
|--------|-------------|----------|
| Contract nhỏ riêng (AttemptAck), P3 trả ScoreResult | Không nới ScoreResult | ✓ |
| Dùng ScoreResult với field null | Đổi contract P0 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Xám trung tính = đã tập | P3 chuyển scoreLevel() | ✓ |
| Ẩn chấm tới P3 | Chỉ highlight câu hiện tại | |

| Option | Description | Selected |
|--------|-------------|----------|
| Backend hỗ trợ + nút nhỏ ở reviewing | eval_clips/, nút ghost, lệch nhẹ design ghi vào UI-SPEC | ✓ |
| Chỉ backend, UI để Phase 4 | Cờ saveForEval, chưa có nút | |
| Hoãn toàn bộ sang Phase 4 | Không lưu bản ghi nào | |

**User's choice:** Tất cả theo khuyến nghị.

---

## Settings & API key

| Option | Description | Selected |
|--------|-------------|----------|
| Backend, file JSON vị trí cố định | GET/PUT /settings, AppSettings, ~/.config/shadowenglab/settings.json | ✓ |
| localStorage + backend cho dataDir | Dữ liệu nằm hai nơi | |

| Option | Description | Selected |
|--------|-------------|----------|
| Ghi vào .env + nạp nóng | Không trả key về client; Kiểm tra qua GET /v1/models | ✓ |
| Chỉ giữ trong bộ nhớ | Mất khi restart | |
| macOS Keychain | Thêm phụ thuộc, lệch M0 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Áp dụng sau restart, không chuyển dữ liệu | Kiểm tra tồn tại + ghi được | ✓ |
| Chuyển dữ liệu cũ sang | Rủi ro hơn | |
| Chỉ hiển thị, đổi qua .env | Lệch SET-04 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Kiểm tra cache + warm-up lúc khởi động | Thiếu → 'chạy make setup'; đủ → 'Model đang nạp…' | ✓ |
| Chỉ kiểm tra cache | Không có trạng thái progress | |
| Tải model ngay trong app | Trùng make setup (D-25) | |

**User's choice:** Tất cả theo khuyến nghị.

---

## IPA, bản dịch, IFrame

| Option | Description | Selected |
|--------|-------------|----------|
| Argmax PPG wav2vec2 trong ranh giới từ | Dùng PPG có sẵn, không G2P từ text | ✓ |
| Recognizer riêng trên từng từ | Chậm hơn, mất ngữ cảnh | |

| Option | Description | Selected |
|--------|-------------|----------|
| Ẩn IPA từ không chắc, hiện '—' | Ngưỡng tạm Claude đề xuất, Liam duyệt | ✓ |
| Luôn hiện, làm mờ | Dễ gây hiểu nhầm | |

| Option | Description | Selected |
|--------|-------------|----------|
| OpenAI theo yêu cầu, cache vào bài | Không key → disable + tooltip; model chốt ở PR | ✓ |
| OpenAI dịch cả bài lúc tạo | Thêm thời gian vào ngân sách 5 phút | |
| Hoãn, ẩn nút Dịch | Lệch design S3 và PLY-07 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Bỏ IFrame ở Step 1 + ADR | Chỉ `<video>`, lỗi file → Tải lại video | ✓ |
| Giữ làm dự phòng khi file lỗi | Seek kém chính xác | |
| Dùng IFrame để xem trước ở S2 | Phải đối chiếu design S2 | |

**User's choice:** Tất cả theo khuyến nghị.

---

## Claude's Discretion

- Cơ chế hàng đợi/khoá model, chu kỳ poll S1
- Endpoint preview S2 và chọn đoạn > 6 phút
- Xử lý `words` khi "Sửa câu"; tính lại feature khi "Mất chữ cuối?"
- Phát hiện không có tiếng, im lặng 1 s, MIME MediaRecorder
- Áp token/font/component design
- Ngưỡng ẩn IPA (Liam duyệt), heuristic tách câu cụ thể
- Mở rộng CORS

## Deferred Ideas

- Màu điểm danh sách câu theo scoreLevel() — Phase 3
- Tinh chỉnh nhãn audio bằng ref_unclear — Phase 5
- Job queue bền vững, huỷ job, tự retry — Step 2
- YouTube IFrame — sau Step 1
