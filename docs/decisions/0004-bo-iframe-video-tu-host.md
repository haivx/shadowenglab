# 0004 · Bỏ YouTube IFrame dự phòng, chỉ phát video tự host (H.264/AAC)

Ngày: 2026-10-07 · Trạng thái: Chấp nhận · Người quyết: Liam

## Bối cảnh

Bản nháp `docs/product.md` (M2, mục 8) và `PLY-01` hứa phát video tự host bằng thẻ `<video>` và dùng YouTube IFrame API làm dự phòng "trong lúc chờ tải xong". Ở Phase 1 (P1) mô hình job đã đổi: bài chỉ mở được khi `status = ready`, mà `ready` chỉ đến sau khi `video.mp4` đã tải xong (D-01, D-06). Nên không còn khoảng "đang chờ tải" nào để IFrame lấp chỗ.

Giữ IFrame nghĩa là có thêm đường phát thứ hai ở S3: một player khác, seek kém chính xác hơn, có quảng cáo, và không dùng chung file nguồn với pipeline chấm. Mỗi câu phải seek chính xác ở hai đầu (đệm 100–200 ms), đó là lý do ban đầu chọn tự host.

Một vấn đề thứ hai nằm cạnh: selector yt-dlp cũ (`bv*[height<=480]+ba/...`) có thể chọn AV1 hoặc VP9. Chrome phát được, nhưng không phải mọi trình duyệt/phần cứng phát được AV1 (nghiên cứu Phase 2, Pitfall 3), và một file không phát được sẽ trông như "bài hỏng" mà người học không có cách sửa.

## Quyết định

1. **D-17: bỏ IFrame dự phòng ở Step 1.** S3 chỉ dùng `<video>` tự host.
   - Backend phục vụ `DATA_DIR/videos/{videoId}/video.mp4` qua `GET /lessons/{id}/video` bằng `FileResponse` của Starlette, có Range (206 + `Content-Range` + `Accept-Ranges: bytes`, 416 khi range không thoả mãn) để seek. Không tự viết xử lý Range.
   - Client không bao giờ gửi `videoId` hay đường dẫn: `videoId` đọc từ `lesson.json` của bài `ready`.
   - File thiếu hoặc hỏng thì S3 hiện trạng thái lỗi kèm nút "Tải lại video" (`POST /lessons/{id}/video/reload`: xoá `video.mp4`, tải lại; tải lỗi thì giữ file cũ). `audio.wav` và stems đã cache không bị đụng tới vì không phụ thuộc codec video.
2. **D-19 (phần codec): video mới tải theo H.264 + AAC.**
   - Selector: `bv*[height<=480][vcodec^=avc1]+ba[acodec^=mp4a]/b[height<=480][vcodec^=avc1]/bv*[height<=480]+ba/b[height<=480]/b`, tức ưu tiên avc1 + mp4a ≤ 480p và giữ selector cũ làm đường lùi cuối cùng để không tải hỏng.
   - Sau khi tải, `ffprobe` kiểm tra codec; khác `h264` thì chuyển mã bằng `ffmpeg -c:v libx264 -preset veryfast -crf 26 -c:a aac -movflags +faststart` ra file tạm rồi `os.replace`.
   - Tải vào `video.dl.*`, chuyển mã xong mới đổi tên thành `video.mp4`: file nửa chừng không bao giờ hiện ra dưới tên `video.mp4`. Mỗi video có một khoá; hai job cùng video (hoặc một lần tải lại giữa lúc job chạy) không ghi file đồng thời, video khác nhau vẫn tải song song.
   - Trình duyệt chính của Liam là Chrome; UAT chạy trên Chrome.

## Lý do

- Một đường phát duy nhất thì seek chính xác, không quảng cáo và dùng chung file nguồn với pipeline chấm (đúng lý do gốc của "tự host video").
- Vì bài chỉ mở khi `ready`, IFrame dự phòng không còn tình huống nào để dùng; giữ lại chỉ thêm code và một hành vi phải kiểm thử.
- H.264/AAC phát được ở mọi trình duyệt phổ biến; transcode dự phòng tốn thêm thời gian chỉ ở các video không có biến thể avc1, và ffmpeg đã là phụ thuộc của pipeline.
- Nút "Tải lại video" cho một lối thoát cục bộ khi file thiếu/hỏng thay vì bắt tạo lại bài.

## Hệ quả và rủi ro

- Cache Phase 1 có thể chứa `video.mp4` AV1/VP9 (selector cũ). "Tải lại video" sửa từng video; không có migration tự động.
- Bài chỉ phát được khi file nằm trong `DATA_DIR`; xoá file tay thì S3 báo lỗi cho tới khi bấm "Tải lại video".
- Chuyển mã một video 5 phút làm tăng thời gian tạo bài trong trường hợp không có avc1; chấp nhận được vì ngân sách 5 phút ở P0 còn dư lớn (D-26 ở ADR 0003).
- `GET /lessons/{id}/video` chỉ phục vụ bài `ready`; bài đang xử lý trả 404 `not_found`.

## Khả năng đảo ngược

Đảo ngược được. Thêm lại IFrame sau này là việc cục bộ ở S3 (một nhánh player khác); không đổi contract, schema DB hay pipeline.

## Tài liệu liên quan

- `docs/product.md`: M2 và mục 8 đã sửa theo ADR này.
- `.planning/REQUIREMENTS.md`: `PLY-01` đã sửa.
- ADR 0003 (D-26, ngân sách thời gian); ADR 0005 (job runner, sẽ thêm ở plan 02-19).
