# ShadowEngLab — User Flows

> Đầu vào cho Claude Design (P0 · A2, A3) và cho việc chia task P1–P6. Mỗi flow có: mục tiêu, các bước, màn hình, trạng thái phải thiết kế, và tiêu chí "flow chạy được".
> Tham chiếu: `docs/product.md` mục 2 (M0–M6) và mục 4.

## Bản đồ màn hình

| Mã | Màn hình | App | Module | Xuất hiện trong flow |
| --- | --- | --- | --- | --- |
| S1 | Thư viện (Home) | Chính | M1, M6 | F1, F3, F4 |
| S2 | Tạo bài (modal/trang) | Chính | M1 | F1 |
| S3 | Phòng tập (Practice) | Chính | M2, M3, M4 | F2, F3 |
| S4 | Panel kết quả (trong S3) | Chính | M4 | F2, F3 |
| S5 | Tổng kết buổi | Chính | M5 | F2 |
| S6 | Ôn luyện (Review queue) | Chính | M6 | F3 |
| S7 | Tiến bộ (Dashboard) | Chính | M5, M6 | F4 |
| S8 | Settings | Chính | M0 | F0 |
| E1 | Đăng nhập | Eval | — | F5 |
| E2 | Hướng dẫn chấm | Eval | — | F5 |
| E3 | Màn hình chấm | Eval | — | F5 |
| E4 | Kết thúc | Eval | — | F5 |

---

## F0. Lần đầu mở app (onboarding tối thiểu)

**Mục tiêu:** từ clone repo đến buổi tập đầu tiên trong ≤ 10 phút, không cần đọc tài liệu.

1. Liam chạy `make setup && make dev`, mở `localhost:3000` → S1 trống.
2. S1 hiển thị banner trạng thái hệ thống: model đã tải chưa, `OPENAI_API_KEY` có chưa, micro đã cấp quyền chưa.
3. Thiếu key → banner vàng "Gợi ý sẽ dùng template, TTS tắt" + nút mở S8. Không chặn việc dùng app.
4. S8: dán key → nút "Kiểm tra" → xanh/đỏ. Chọn mặc định: tốc độ phát, số lần lặp, thời gian ghi (+50%), giọng mục tiêu (US, khoá).
5. Quay lại S1 → empty state "Dán link YouTube để tạo bài đầu tiên" → vào F1.

**Trạng thái cần thiết kế:** model đang tải (progress), thiếu key, key sai, micro bị từ chối, empty library.
**Xong khi:** máy mới, không key, vẫn tạo được bài và tập được.

---

## F1. Tạo bài từ link YouTube

**Mục tiêu:** dán link → có bài tập được, không phải ngồi chờ trước màn hình.

1. S1 → nút "Tạo bài" → S2.
2. Dán link. App lấy metadata (tiêu đề, thời lượng, thumbnail) và hiển thị preview.
3. Video > 6 phút → gợi ý chọn đoạn (thanh kéo start–end, mặc định 5 phút đầu). Video ≤ 6 phút → dùng toàn bộ.
4. Bấm "Tạo bài" → job chạy nền. S2 đóng, card bài mới xuất hiện ở S1 với tiến độ theo bước:
   `Tải video → Tách giọng → Phiên âm → Chia câu → Phân tích bản gốc`
5. Trong lúc chờ: Liam có thể tập bài khác hoặc ôn luyện (F3).
6. Xong → card chuyển "Sẵn sàng · 32 câu · Audio: sạch / có nhạc nền". Nhãn chất lượng audio lấy từ tỉ lệ câu bị `ref_unclear`.
7. Bấm card → S3 ở câu 1.

**Trạng thái cần thiết kế:** link không hợp lệ, video không cho tải, video quá dài, job đang chạy (từng bước), job lỗi kèm nút thử lại, bài có nhiều câu không đủ rõ (cảnh báo nên chọn video khác).
**Xong khi:** video 5 phút sẵn sàng trong ≤ 5 phút; tạo 2 bài liên tiếp không chặn nhau.

---

## F2. Một buổi tập (flow chính)

**Mục tiêu:** vòng lặp nghe → nói → xem lệch ở đâu → nói lại, nhanh và không cần chuột.

1. S3 mở ở câu đầu tiên chưa tập. Bố cục: video + thanh điều khiển (trái), danh sách câu (phải), vùng câu hiện tại + kết quả (dưới video).
2. **Nghe:** `Space` phát câu mẫu (đã đệm 100–200ms), lặp theo cài đặt (×1/×2/×3), tốc độ theo cài đặt.
3. **Nói:** phát xong → tự chuyển "Lượt của bạn", chip đếm số giây đã ghi. Thanh mức âm cho biết micro đang thu. Chỉ dừng khi người dùng bấm "Dừng ghi" hoặc `Space`; không tự dừng theo độ dài câu hay khi im lặng (Liam, 2026-10-10). Trần an toàn 60 giây khớp giới hạn backend. Cài đặt "Thời gian ghi" (`recordFactor`) tạm không có tác dụng.
4. **Chấm:** trạng thái "Đang chấm" (≤ 3 giây) → S4 mở ra trong vùng câu hiện tại:
    - Hàng chip từng từ (xanh / vàng / đỏ / xám = bản gốc không đủ rõ). Click chip → popover: "bản gốc /ən/ · bạn /ænd/" + nút nghe riêng từ đó ở cả hai bản.
    - 3 chỉ số: Tốc độ · Độ lên xuống · Khớp giai điệu.
    - Nút "So sánh ngữ điệu" → biểu đồ 2 contour + thanh trọng âm + dấu ‖.
    - 2–3 gợi ý, mỗi gợi ý trỏ vào từ liên quan (hover gợi ý → highlight chip).
    - Nút nghe: bản gốc · bạn · lần lượt cả hai.
5. **Quyết định:**
    - `R` thử lại → về bước 3 (giữ lần chấm tốt nhất, hiển thị lần thử thứ mấy).
    - `→` câu tiếp; `←` câu trước.
    - "Mất chữ cuối?" → nới `end` câu thêm 300ms, lưu vào bài.
6. Danh sách câu bên phải: mỗi câu có chấm màu theo điểm tốt nhất; câu đang tập được highlight.
7. Hết bài hoặc bấm "Kết thúc buổi" → S5: số câu đã tập, điểm trung bình theo 3 chiều (âm, ngữ điệu, nhịp), 3 loại lỗi hay gặp nhất, danh sách câu yếu "đã thêm vào hàng ôn".

**Nguyên tắc thao tác:** đây là web app, nút bấm là cách thao tác chính. Mọi hành động đều có nút rõ ràng (có chữ, cao 44–48px). Phím tắt chỉ là lối tắt phụ, hiện dạng gợi ý nhỏ trong nút và tooltip.

**Phiên âm (Liam, 2026-10-10):** IPA từ chính giọng người nói mặc định **bật** và được nhớ trên máy; hiện dưới câu ở trạng thái chờ (khối đầy đủ kèm ghi chú), và một dòng gọn `/…/` dưới câu trong panel "Đang phát" và "Đang ghi". Nút `IPA` / phím `I` tắt/bật.

**Phím tắt (phụ):** `Space` phát/ghi/dừng · `R` thử lại · `←/→` câu trước/sau · `O` nghe bản gốc · `M` nghe bản của mình · `B` nghe lần lượt · `I` bật/tắt IPA · `T` dịch.
**Trạng thái cần thiết kế:** đang phát, đang ghi (có mức âm), không thu được tiếng, đang chấm, kết quả tốt (không có gợi ý → lời khen ngắn), kết quả có lỗi, câu `ref_unclear` (chỉ chấm ngữ điệu, giải thích vì sao), lỗi backend, thiếu key (gợi ý dạng template, không có nhãn "AI").
**Xong khi:** tập trọn 30 câu chỉ bằng chuột, và cũng làm được chỉ bằng bàn phím; mỗi vòng nghe–nói–xem kết quả ≤ 3 giây chờ.

---

## F3. Ôn luyện câu yếu

**Mục tiêu:** câu sai được tự động quay lại đúng lúc, không cần Liam tự nhớ.

1. Câu có điểm tốt nhất dưới ngưỡng (mặc định 70%) → vào hàng ôn với lịch 1 → 3 → 7 ngày. Đạt ngưỡng ở lần ôn → lên mốc tiếp; trượt → về mốc 1.
2. S1 hiển thị "Hôm nay cần ôn: 12 câu" → bấm → S6.
3. S6 dùng lại phòng tập S3 nhưng các câu đến từ nhiều video; mỗi câu hiện tên video nguồn. Không có danh sách câu bên phải, chỉ có tiến độ "4/12".
4. Với câu sai ≥ 2 lần liên tiếp, gợi ý 2 chế độ hỗ trợ:
    - **Nghe chậm (TTS):** phát bản đọc chậm, rõ; sau đó bắt buộc nghe lại bản gốc trước khi ghi.
    - **Chỉ ngữ điệu:** ẩn chữ, chỉ hiện contour bản gốc; chấm chỉ phần ngữ điệu.
5. Hết hàng ôn → tổng kết ngắn: bao nhiêu câu lên mốc, bao nhiêu câu về mốc 1.

**Trạng thái cần thiết kế:** hàng ôn trống, TTS không có (thiếu key), chế độ chỉ ngữ điệu.
**Xong khi:** câu yếu của hôm qua tự xuất hiện hôm nay mà Liam không cần thao tác gì.

---

## F4. Xem tiến bộ

**Mục tiêu:** trả lời được "tuần này mình có khá hơn không, và khá hơn ở đâu".

1. S1 → tab "Tiến bộ" → S7.
2. Khối trên: số buổi tuần này / mục tiêu (20 buổi/tháng), chuỗi ngày luyện.
3. Biểu đồ theo tuần: điểm trung bình 3 chiều (âm, ngữ điệu, nhịp).
4. Bảng loại lỗi: mỗi `IssueCode` một dòng, số lần tuần này so với tuần trước, xu hướng.
5. Click một loại lỗi → danh sách câu gần đây mắc lỗi đó → bấm để tập lại (vào S3).

**Trạng thái cần thiết kế:** chưa đủ dữ liệu (< 1 tuần), tuần không luyện.
**Xong khi:** từ S7 đi tới đúng câu cần tập lại trong ≤ 2 click.

---

## F5. Người chấm dùng app eval

**Mục tiêu:** người chấm bản xứ chấm ~68 clip trong ~45 phút, chia nhiều lần, không cần Liam hướng dẫn trực tiếp.

1. Liam gửi link. E1: nhập email → nhận magic link. Email ngoài allowlist → thông báo lịch sự, không lộ thông tin.
2. Lần đầu → E2 bắt buộc: mục đích (chấm độ giống *người nói này*, không chấm "đúng chuẩn"), 3 ví dụ mẫu mức 5/3/1 có audio, giải thích 5 loại cờ. Nút "I understand, start".
3. E3, mỗi clip:
    - Thanh tiến độ "12 / 68" + nút "Save & exit".
    - `O` nghe bản gốc · `L` nghe learner · `Space` nghe lần lượt.
    - Câu hiển thị thành các từ bấm được → popover chọn cờ: sound / stress / pitch / pause / speed.
    - Điểm 1–5 (`1`–`5`), "Final rise/fall matches?" Yes/No, ô "I'm not sure", ghi chú.
    - `Enter` = Next, chỉ bật khi đã nghe cả hai file và đã chấm điểm.
4. Thoát giữa chừng → lần sau vào thẳng clip chưa chấm.
5. Xong 68 clip → E4 cảm ơn + số clip đã chấm. Không hiển thị điểm hệ thống hay nhãn của người kia.

**Trạng thái cần thiết kế:** link hết hạn, audio lỗi tải, mất mạng khi lưu (giữ local, thử lại), mobile dọc.
**Xong khi:** người chấm làm trọn một lượt trên điện thoại mà không hỏi lại Liam.

---

## Trạng thái dùng chung (thiết kế một lần, dùng mọi nơi)

| Trạng thái | Dạng hiển thị |
| --- | --- |
| Job nền đang chạy | Card có progress theo bước |
| Đang chấm | Skeleton trong panel kết quả, ≤ 3 giây |
| Thiếu API key | Banner vàng, không chặn |
| Bản gốc không đủ rõ | Chip xám + tooltip giải thích |
| Lỗi backend | Toast + nút thử lại, không mất bản ghi vừa thu |
| Empty state | Một câu hướng dẫn + một hành động chính |
