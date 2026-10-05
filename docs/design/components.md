# Danh sách component

Mỗi component ghi: mục đích, biến thể / trạng thái, shadcn gốc (nếu có), màn hình dùng. Tên dùng làm tên file trong `apps/web/components/`.

## Nền tảng (đổi token shadcn)

| Component | shadcn gốc | Biến thể / trạng thái | Ghi chú |
| --- | --- | --- | --- |
| `Button` | Button | solid · soft-original · soft-you · outline · ghost; size md (44) / lg (48); có `kbd` gợi ý tuỳ chọn | Nút icon-only bắt buộc `aria-label` + `title` có phím tắt |
| `Kbd` | — | — | Gợi ý phím tắt nhỏ trong nút |
| `Select` (có nhãn trên) | Select | — | Tốc độ, Lặp, Thời gian ghi, Settings |
| `Badge` | Badge | neutral · score-good/ok/bad · warning | "Audio sạch", "Có nhạc nền", "32 câu" |
| `Banner` | Alert | warning (thiếu key) · unrated (bản gốc không đủ rõ) · error (có nút Thử lại) | Không chặn thao tác |
| `Tabs` (lọc) | Tabs | — | Thư viện: Tất cả / Đang tập / Đã xong |
| `Dialog` | Dialog | — | S2 Tạo bài |
| `Progress` | Progress | neutral · score-good | Tiến độ xử lý, tiến độ bài, buổi tháng này |

## Phòng tập (S3 + S4)

| Component | Mục đích | Trạng thái |
| --- | --- | --- |
| `PracticeHeader` | Quay lại, tên video, thanh tiến độ phân đoạn, Kết thúc buổi | — |
| `SegmentedProgress` | 1 đoạn / câu, tô theo `scoreLevel`; câu hiện tại slate-12; chưa tập slate-4 | — |
| `VideoPane` | Video tự host, mốc thời gian câu | đang tải · lỗi |
| `PlayerControls` | Trước · Nghe câu mẫu · Phát lại · Tiếp + Tốc độ / Lặp / Thời gian ghi | gắn với XState machine |
| `TranscriptList` | Danh sách câu kiểu Language Reactor: mốc giờ, câu, điểm tốt nhất; câu hiện tại có dịch | toggle Dịch · chế độ Sửa câu |
| `AttemptStrip` | Lượt 1/2/3 và lượt tốt nhất; nút "Mất chữ cuối?" | — |
| `ScoredSentence` | Câu cỡ lớn, mỗi từ gạch chân + điểm theo `scoreLevel`, bấm để chọn từ | từ đang chọn có nền `soft` |
| `SpokenIpa` | IPA nhận dạng từ audio mẫu, có nhãn nguồn | ẩn khi `ref_unclear` |
| `ScoreHero` | Số lớn "giống bản gốc" + Tốc độ, Lên xuống, Giai điệu | màu theo `scoreLevel` |
| `PhonemeDiff` | "Bạn đọc X khác ở âm nào?": hàng âm bản gốc và của bạn, ô sai màu `score-bad`, nút Nghe từng bản | ô trống gạch đứt = âm thiếu/thừa |
| `IntonationChart` | Hai contour (original / you), baseline đứt, nhãn từ, vạch "ngắt thừa" | chỉ ngữ điệu khi `ref_unclear` |
| `TipList` | 2–3 gợi ý đánh số, từ liên quan gạch chân theo nguồn hoặc mức điểm | template · LLM |
| `ResultActionBar` | Thanh dưới cố định: Nghe lại bản gốc / của bạn / lần lượt · Ghi lại · Câu tiếp | — |
| `SentenceStatePanel` | Trạng thái vùng câu: đang phát · đang ghi (mức âm) · không thu được tiếng · đang chấm · kết quả tốt · bản gốc không đủ rõ | xem `S3-trang-thai-cau.png` |

## Các màn khác

| Component | Màn | Ghi chú |
| --- | --- | --- |
| `AppHeader` | S1, S5–S8 | Logo + Thư viện · Ôn luyện (badge số câu) · Tiến bộ · Settings |
| `LessonCard` | S1 | 4 trạng thái: sẵn sàng · đang xử lý (danh sách bước) · có cảnh báo audio · lỗi |
| `JobSteps` | S1 | Tải video → Tách giọng → Phiên âm → Chia câu → Phân tích bản gốc |
| `ReviewCallout` | S1 | Khối nền slate-12 "Hôm nay cần ôn N câu" |
| `RangePicker` | S2 | Chọn đoạn video, hai ô thời gian |
| `StatRow` | S5, S7 | Hàng số lớn giữa hai đường kẻ, không card |
| `IssueList` / `IssueTrendTable` | S5, S7 | Loại lỗi, số lần, xu hướng (giảm = good, tăng = bad) |
| `ReviewAssist` | S6 | Gợi ý "Nghe chậm" / "Chỉ ngữ điệu" sau 2 lần trượt |
| `WeeklyChart` | S7 | 3 chuỗi `--series-1..3` |
| `KeyField` | S8 | Input key + Kiểm tra + trạng thái |
| `ModelStatusList` | S8 | Trạng thái tải model |

## App eval (giữ nguyên thiết kế v0.1)

`RaterHeader` · `ClipPlayers` (Original / Learner / Both) · `WordFlagger` (từ bấm được + nhóm 5 cờ) · `ScoreScale` (1–5) · `FinalContourChoice` · `NotSureToggle` + ghi chú · `NextButton` (khoá đến khi nghe đủ 2 file và chấm điểm).
