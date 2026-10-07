# Requirements: ShadowEngLab

**Defined:** 2026-10-05
**Core Value:** Sau mỗi lượt nói, Liam biết đáng tin mình lệch khỏi người nói gốc ở đâu — so audio với audio gốc, precision trước recall.

Nguồn: `docs/product.md` (M0–M6, mục 3–4), `docs/flows.md` (F0–F5), `docs/gsd/roadmap-seed.md` (P0–P7). Màn hình tham chiếu `docs/design/`.

## v1 Requirements

Step 1: app đầy đủ tính năng để học hằng ngày. Mỗi requirement map tới đúng một phase.

### Nền tảng (FND)

- [x] **FND-01**: Repo là pnpm workspace (`apps/web`, `apps/eval`, `packages/contracts`) cộng `services/audio` quản lý bằng uv, có ESLint, Prettier, ruff và `.gitignore` cấu hình sẵn
- [x] **FND-02**: `packages/contracts` định nghĩa Zod cho `Segment`, `Lesson`, `ScoreResult`, `IssueCode`, `ClipManifest`, `Label` (theo product.md mục 3–4, Liam chốt trong Discuss) và sinh JSON Schema
- [x] **FND-03**: Kiểu pydantic ở `services/audio` khớp JSON Schema sinh từ contracts; test round-trip TS ↔ JSON Schema ↔ pydantic cho `ScoreResult` pass
- [x] **FND-04**: Liam chạy `make setup` trên máy sạch macOS Apple Silicon: cài deps Python + Node, tải Demucs, mlx-whisper, `facebook/wav2vec2-lv-60-espeak-cv-ft` có hiển thị tiến độ, kiểm tra parselmouth, espeak-ng, ffmpeg
- [x] **FND-05**: `make dev` chạy cả Next.js và FastAPI; `make test` chạy pytest + vitest; `make eval` tồn tại (stub ở P0)
- [x] **FND-06**: FastAPI có `/health`, router `lesson` và `scoring`, response validate theo contracts
- [x] **FND-07**: `scripts/smoke_lesson.py <youtube_url>` chạy yt-dlp → Demucs → mlx-whisper (word timestamps) → tách câu 3–8 s → F0 + PPG mỗi câu → JSON theo `Lesson`, in thời gian từng bước; video 5 phút xử lý ≤ 5 phút

### Cài đặt (SET) — M0, F0

- [ ] **SET-01**: S1 hiển thị banner trạng thái hệ thống: model đã tải chưa, có `OPENAI_API_KEY` chưa, micro đã cấp quyền chưa
- [ ] **SET-02**: Thiếu key → banner vàng không chặn ("Gợi ý sẽ dùng template, TTS tắt") kèm nút mở S8; app vẫn tạo bài và tập được
- [ ] **SET-03**: Ở S8, Liam dán key, bấm "Kiểm tra" và thấy kết quả hợp lệ / không hợp lệ
- [ ] **SET-04**: Ở S8, Liam chọn mặc định tốc độ phát, số lần lặp, thời gian ghi (+50%), thư mục lưu dữ liệu; giọng mục tiêu US hiển thị dạng khoá

### Tạo bài (LES) — M1, F1

- [ ] **LES-01**: Liam dán link YouTube ở S2 và thấy preview (tiêu đề, thời lượng, thumbnail); link không hợp lệ hoặc video không cho tải báo lỗi rõ ràng
- [ ] **LES-02**: Video > 6 phút → Liam chọn đoạn start–end bằng thanh kéo (mặc định 5 phút đầu); video ≤ 6 phút dùng toàn bộ
- [x] **LES-03**: Tạo bài chạy nền; card ở S1 hiện tiến độ theo bước (Tải video → Tách giọng → Phiên âm → Chia câu → Phân tích bản gốc); tạo 2 bài liên tiếp không chặn nhau và Liam vẫn tập bài khác trong lúc chờ
- [ ] **LES-04**: Pipeline tạo bài: yt-dlp (video 360–480p + audio, cache theo `videoId`), Demucs tách vocal, mlx-whisper word timestamps, tách câu 3–8 s (cắt câu > ~15 từ tại dấu phẩy/khoảng lặng, gộp mảnh < 1.5 s), tính sẵn F0, năng lượng, prominence theo từ và PPG cho từng câu
- [ ] **LES-05**: Video 5 phút sẵn sàng để tập trong ≤ 5 phút
- [ ] **LES-06**: Card bài sẵn sàng hiện số câu và nhãn chất lượng audio "Audio sạch" / "Có nhạc nền", tính lúc tạo bài từ output Demucs (tỉ lệ năng lượng phần non-vocal so với vocal); audio nhiều nhạc nền hiện cảnh báo nên chọn video khác. Ghi chú: Phase 5 bổ sung tỉ lệ câu `ref_unclear` để tinh chỉnh nhãn
- [ ] **LES-07**: Job lỗi hiện trên card kèm nút thử lại

### Trình phát (PLY) — M2, F2

- [ ] **PLY-01**: S3 phát video tự host bằng thẻ `<video>`; YouTube IFrame API làm dự phòng khi file chưa tải xong
- [ ] **PLY-02**: Trình phát chạy bằng state machine XState (`idle → playing → recording → scoring → reviewing` cùng nhánh lỗi, thử lại) ở file riêng, có test cho các transition chính trước khi gắn UI
- [ ] **PLY-03**: Liam phát câu mẫu có đệm 100–200 ms, lặp ×1/×2/×3 và tốc độ theo cài đặt; điều khiển câu trước, phát lại, phát, câu sau
- [ ] **PLY-04**: S3 mở ở câu đầu tiên chưa tập; danh sách câu bên phải highlight câu hiện tại, mỗi câu có chấm màu theo điểm tốt nhất; nút "Sửa" để chỉnh text câu
- [ ] **PLY-05**: Nút "Mất chữ cuối?" nới `end` của câu thêm 300 ms và lưu vào bài
- [ ] **PLY-06**: Liam xem IPA theo cách người nói gốc phát âm (nhận dạng từ audio mẫu), có ghi chú đây là nhận dạng tự động, bật/tắt được
- [x] **PLY-07**: Mọi hành động có nút rõ ràng (có chữ, cao 44–48 px) với phím tắt phụ hiện dạng gợi ý (`Space`, `R`, `←/→`, `O`, `M`, `B`, `I`, `T`); Liam tập trọn 30 câu chỉ bằng chuột, và cũng làm được chỉ bằng bàn phím

### Ghi âm (REC) — M3, F2

- [ ] **REC-01**: Câu mẫu phát xong tự chuyển "Lượt của bạn" với countdown = độ dài câu × 1.5 và thanh mức âm; `Space` hoặc im lặng 1 giây dừng sớm
- [ ] **REC-02**: Backend chuẩn hoá bản ghi (webm từ Chrome, mp4 từ Safari) về WAV 16 kHz mono
- [ ] **REC-03**: Không thu được tiếng → hiện trạng thái riêng và cho ghi lại; lỗi backend → toast kèm nút thử lại, không mất bản ghi vừa thu
- [ ] **REC-04**: Bản ghi không được lưu lâu dài (chỉ giữ features), trừ khi Liam đánh dấu "lưu clip này cho eval"

### Ngữ điệu (PRO) — Lớp B

- [ ] **PRO-01**: Service trích F0 ~10 ms bằng parselmouth (chỉ frame hữu thanh, lọc lỗi quãng tám, giới hạn khoảng pitch theo người), đổi sang semitone so với median từng người, nội suy, làm mượt và căn theo ranh giới từ
- [ ] **PRO-02**: Liam nhận 3 chỉ số Tốc độ, Độ lên xuống, Khớp giai điệu (0..1) và prominence từng từ, tính theo công thức product.md mục 3 Lớp B
- [ ] **PRO-03**: Bản gốc so với chính nó cho điểm ngữ điệu ≈ 100%; câu đọc sai hẳn cho điểm thấp
- [ ] **PRO-04**: Chấm ngữ điệu một câu ≤ 3 giây, chỉ xử lý audio người học (feature bản gốc đã tính sẵn)

### Rule và gợi ý (RUL) — Lớp C

- [ ] **RUL-01**: Rule engine sinh `issues` cho `STRESS_MISMATCH`, `EXTRA_PAUSE`, `FINAL_CONTOUR`, `FLAT_PITCH`, `PITCH_DEVIATION` với ngưỡng ban đầu trong product.md; không chắc thì không báo
- [ ] **RUL-02**: Liam nhận 2–3 gợi ý template bằng tiếng Việt, mỗi gợi ý trỏ tới đúng một `issueRef`; không có lỗi → lời khen ngắn

### Kết quả chấm (FBK) — M4, S3/S4

- [ ] **FBK-01**: Panel kết quả hiện `ScoreHero` (phần ngữ điệu) và 3 chỉ số
- [ ] **FBK-02**: Nút "So sánh ngữ điệu" mở `IntonationChart`: 2 contour (bản gốc teal, bạn cam) cùng baseline, thanh trọng âm theo từ và dấu ‖ tại chỗ ngắt thừa
- [ ] **FBK-03**: `TipList` hiện gợi ý; hover gợi ý → highlight từ liên quan
- [ ] **FBK-04**: Liam nghe bản gốc, bản của mình, hoặc lần lượt cả hai (`O`, `M`, `B`)
- [ ] **FBK-05**: Vùng câu hiện tại có đủ 6 trạng thái theo `S3-trang-thai-cau` (đang phát, đang ghi, không thu được tiếng, đang chấm dạng skeleton, có kết quả, lỗi); màu điểm luôn qua `scoreLevel()`
- [ ] **FBK-06**: `R` thử lại giữ lần chấm tốt nhất và hiển thị đây là lần thử thứ mấy

### Eval nội bộ (EVL)

- [ ] **EVL-01**: Liam lưu được clip lỗi cố ý kèm loại lỗi và vị trí từ (mỗi clip 1 lỗi), cùng ~8 clip mốc đúng, đủ ~100 clip
- [ ] **EVL-02**: `make eval` chạy `eval/analyze.py`: precision/recall theo từng rule, test-retest, và sinh `eval/report.md` tự động
- [ ] **EVL-03**: Tập held-out 30% được tách cố định và không dùng khi chỉnh ngưỡng
- [ ] **EVL-04**: Precision của các rule ngữ điệu ≥ 90% trên held-out

### Chấm âm (PHN) — Lớp A

- [ ] **PHN-01**: Service tính PPG bằng wav2vec2-espeak cho audio người học, chạy DTW với khoảng cách `−log(p_ref · p_user)` và chiếu ranh giới từ của bản gốc sang audio người học qua đường DTW
- [ ] **PHN-02**: Điểm mỗi từ là trung bình khoảng cách frame có trọng số confidence bản gốc; từ bản gốc confidence thấp → `ref_unclear` (chip xám + tooltip giải thích), chỉ chấm ngữ điệu
- [ ] **PHN-03**: Rule `PHONE` và `WORD_MISSING` sinh `issues`; từ lệch nhiều có giải thích bằng chuỗi phone argmax ("bản gốc /ən/ · bạn /ænd/")
- [ ] **PHN-04**: `ScoredSentence` hiện chip từng từ (xanh / vàng / đỏ / xám); click chip → popover `PhonemeDiff` có nút nghe riêng từ đó ở cả hai bản; có điểm tổng của câu
- [ ] **PHN-05**: Chấm đầy đủ một câu (âm + ngữ điệu) ≤ 3 giây; bản gốc so với chính nó ≈ 100%
- [ ] **PHN-06**: Bắt được lỗi weak form và nuốt âm trong bộ lỗi cố ý, có số liệu từ `make eval`

### App eval (RAT) — F5, E1–E4

- [ ] **RAT-01**: Người chấm đăng nhập bằng magic link Supabase, chỉ email trong allowlist; email ngoài allowlist nhận thông báo lịch sự không lộ thông tin; link hết hạn có trạng thái riêng
- [ ] **RAT-02**: Lần đầu, người chấm phải qua trang hướng dẫn (tiếng Anh): chấm độ giống *người nói này*, 3 ví dụ mẫu mức 5/3/1 có audio, giải thích 5 loại cờ
- [ ] **RAT-03**: Mỗi clip, người chấm nghe bản gốc / learner / lần lượt (`O`, `L`, `Space`), gắn cờ trên từ (sound, stress, pitch, pause, speed), chấm 1–5, chọn "Final rise/fall matches?", đánh dấu "I'm not sure" và ghi chú
- [ ] **RAT-04**: Next (`Enter`) chỉ bật khi đã nghe cả hai file và đã chấm; tự lưu khi chuyển clip; mất mạng thì giữ local và thử lại; thoát giữa chừng thì lần sau vào thẳng clip chưa chấm
- [ ] **RAT-05**: Thứ tự clip xáo trộn riêng mỗi người, 8 gold clip lẫn trong đó; người chấm không thấy điểm hệ thống hay nhãn người kia; xong thì thấy E4 cảm ơn kèm số clip đã chấm
- [ ] **RAT-06**: RLS chỉ cho người chấm đọc/ghi nhãn của chính mình; `gold` và `system_score` không bao giờ trả về client; audio nằm trong bucket private, phát qua signed URL hạn ~1 giờ
- [ ] **RAT-07**: App eval responsive trên mobile dọc; người chấm làm trọn một lượt trên điện thoại mà không cần hỏi Liam
- [ ] **RAT-08**: `eval/export_clips.py` xuất `manifest.json` theo `ClipManifest` (cắt lặng hai đầu, `ffmpeg loudnorm`, opus/mp3 ~64 kbps, audio gốc là bản trong video, không phải bản tách giọng), upload lên Supabase và kéo nhãn về local
- [ ] **RAT-09**: Pilot 5 clip với 1 người chấm, sau đó 2 người chấm xong ~68 clip; Cohen's kappa giữa hai người ≥ 0.4; gold check pass

### Ôn luyện (REV) — M6, F3

- [ ] **REV-01**: Câu có điểm tốt nhất < 70% tự vào hàng ôn với lịch 1 → 3 → 7 ngày; đạt ngưỡng ở lần ôn → lên mốc tiếp, trượt → về mốc 1; câu yếu hôm qua tự xuất hiện hôm nay
- [ ] **REV-02**: S1 hiện "Hôm nay cần ôn: N câu" → S6 dùng lại phòng tập với câu từ nhiều video (hiện tên video nguồn, tiến độ "4/12", không có danh sách câu); hết hàng ôn → tổng kết số câu lên mốc / về mốc 1; hàng trống có empty state
- [ ] **REV-03**: Câu sai ≥ 2 lần liên tiếp → gợi ý nghe chậm bằng TTS (`gpt-4o-mini-tts`), sau đó bắt buộc nghe lại bản gốc trước khi ghi; thiếu key → TTS hiện trạng thái không khả dụng
- [ ] **REV-04**: Chế độ chỉ ngữ điệu: ẩn chữ, chỉ hiện contour bản gốc, chỉ chấm phần ngữ điệu

### Báo cáo và thư viện (RPT) — M5, M6, F2, F4

- [ ] **RPT-01**: Hết bài hoặc bấm "Kết thúc buổi" → S5: số câu đã tập, điểm trung bình 3 chiều (âm, ngữ điệu, nhịp), 3 loại lỗi hay gặp nhất, danh sách câu yếu "đã thêm vào hàng ôn"
- [ ] **RPT-02**: S7 hiện số buổi tuần này so với mục tiêu (20 buổi/tháng), chuỗi ngày luyện, biểu đồ theo tuần điểm trung bình 3 chiều, bảng `IssueCode` tuần này so với tuần trước kèm xu hướng; có trạng thái chưa đủ dữ liệu và tuần không luyện
- [ ] **RPT-03**: Từ S7 click một loại lỗi → câu gần đây mắc lỗi đó → tập lại trong S3, tổng cộng ≤ 2 click
- [ ] **RPT-04**: Thư viện S1 liệt kê video đã tạo bài kèm nhãn chất lượng audio, giọng và tốc độ nói; lọc được theo nhãn

### Hiệu chỉnh và hoàn thiện (CAL)

- [ ] **CAL-01**: Điểm % được map bằng logistic regression fit trên dữ liệu eval; ngưỡng rule được chỉnh theo nhãn người chấm
- [ ] **CAL-02**: Spearman giữa điểm hệ thống và người chấm xấp xỉ mức đồng thuận giữa hai người chấm; `report.md` có calibration curve, precision/recall theo loại cờ và kiểm tra trung thực của gợi ý
- [ ] **CAL-03**: Gợi ý bằng LLM (OpenAI model nhỏ, structured output) chỉ nhận JSON `issues`, mỗi tip trỏ tới một `issueRef` hợp lệ; thiếu key hoặc LLM lỗi → rơi về template, không gắn nhãn "AI"
- [ ] **CAL-04**: Các mục 🔴/🟡 tích luỹ trong `docs/feedback.md` được xử lý
- [ ] **CAL-05**: README portfolio trình bày pipeline và số liệu eval (ghi chung là có human review); máy mới clone, điền `.env`, `make setup && make dev` là dùng được

## v2 Requirements

Step 2 — Hardening (milestone sau, bắt đầu khi Step 1 đã dùng ổn định ~2 tuần).

### Hardening (HRD)

- **HRD-01**: Unit test cho rule engine và các metric; integration test cho pipeline tạo bài và chấm
- **HRD-02**: CI chạy `analyze.py`, fail nếu Spearman hoặc precision giảm
- **HRD-03**: Logging có cấu trúc và trace từng lượt chấm (thời gian từng bước, lỗi)
- **HRD-04**: Job queue cho tạo bài, retry khi yt-dlp hoặc model lỗi, cho phép huỷ job
- **HRD-05**: Migration SQLite và backup dữ liệu học tập
- **HRD-06**: Đóng gói Docker hoặc script cài đặt một lệnh
- **HRD-07**: Bảo mật app eval: rate limit, rà lại RLS, xoá audio sau mỗi đợt eval

## Out of Scope

| Feature | Reason |
|---------|--------|
| Nhiều người dùng, thương mại hoá | Dự án học cá nhân + portfolio, chạy local |
| Mobile app chính | Step 1 là web app desktop; chỉ app eval cần mobile |
| Dark mode | Ngoài phạm vi Step 1 (docs/design/README.md) |
| "Nói với AI", chế độ chính tả | Mở rộng xa hơn (product.md mục 9) |
| Giọng UK | Step 1 tập trung US; bộ eval, ngưỡng, người chấm theo giọng Mỹ |
| Lưu lịch sử ghi âm để nghe lại tiến bộ | Step 1 chỉ giữ features; bản nâng cấp sau |
| Chấm bằng LLM đa phương thức | Không nhất quán, hay bịa lỗi |
| Chấm so với từ điển / "phát âm chuẩn" | Trái nguyên tắc so với bản gốc; Azure chỉ là lớp tham khảo tuỳ chọn |
| Màn hình / component ngoài `docs/design/` | Thiết kế v0.2 đã chốt; thay đổi đi qua canvas trước |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | Phase 1 | Complete |
| FND-02 | Phase 1 | Complete |
| FND-03 | Phase 1 | Complete |
| FND-04 | Phase 1 | Complete |
| FND-05 | Phase 1 | Complete |
| FND-06 | Phase 1 | Complete |
| FND-07 | Phase 1 | Complete |
| SET-01 | Phase 2 | Pending |
| SET-02 | Phase 2 | Pending |
| SET-03 | Phase 2 | Pending |
| SET-04 | Phase 2 | Pending |
| LES-01 | Phase 2 | Pending |
| LES-02 | Phase 2 | Pending |
| LES-03 | Phase 2 | Complete |
| LES-04 | Phase 2 | Pending |
| LES-05 | Phase 2 | Pending |
| LES-06 | Phase 2 | Pending |
| LES-07 | Phase 2 | Pending |
| PLY-01 | Phase 2 | Pending |
| PLY-02 | Phase 2 | Pending |
| PLY-03 | Phase 2 | Pending |
| PLY-04 | Phase 2 | Pending |
| PLY-05 | Phase 2 | Pending |
| PLY-06 | Phase 2 | Pending |
| PLY-07 | Phase 2 | Complete |
| REC-01 | Phase 2 | Pending |
| REC-02 | Phase 2 | Pending |
| REC-03 | Phase 2 | Pending |
| REC-04 | Phase 2 | Pending |
| PRO-01 | Phase 3 | Pending |
| PRO-02 | Phase 3 | Pending |
| PRO-03 | Phase 3 | Pending |
| PRO-04 | Phase 3 | Pending |
| RUL-01 | Phase 3 | Pending |
| RUL-02 | Phase 3 | Pending |
| FBK-01 | Phase 3 | Pending |
| FBK-02 | Phase 3 | Pending |
| FBK-03 | Phase 3 | Pending |
| FBK-04 | Phase 3 | Pending |
| FBK-05 | Phase 3 | Pending |
| FBK-06 | Phase 3 | Pending |
| EVL-01 | Phase 4 | Pending |
| EVL-02 | Phase 4 | Pending |
| EVL-03 | Phase 4 | Pending |
| EVL-04 | Phase 4 | Pending |
| PHN-01 | Phase 5 | Pending |
| PHN-02 | Phase 5 | Pending |
| PHN-03 | Phase 5 | Pending |
| PHN-04 | Phase 5 | Pending |
| PHN-05 | Phase 5 | Pending |
| PHN-06 | Phase 5 | Pending |
| RAT-01 | Phase 6 | Pending |
| RAT-02 | Phase 6 | Pending |
| RAT-03 | Phase 6 | Pending |
| RAT-04 | Phase 6 | Pending |
| RAT-05 | Phase 6 | Pending |
| RAT-06 | Phase 6 | Pending |
| RAT-07 | Phase 6 | Pending |
| RAT-08 | Phase 6 | Pending |
| RAT-09 | Phase 6 | Pending |
| REV-01 | Phase 7 | Pending |
| REV-02 | Phase 7 | Pending |
| REV-03 | Phase 7 | Pending |
| REV-04 | Phase 7 | Pending |
| RPT-01 | Phase 7 | Pending |
| RPT-02 | Phase 7 | Pending |
| RPT-03 | Phase 7 | Pending |
| RPT-04 | Phase 7 | Pending |
| CAL-01 | Phase 8 | Pending |
| CAL-02 | Phase 8 | Pending |
| CAL-03 | Phase 8 | Pending |
| CAL-04 | Phase 8 | Pending |
| CAL-05 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 73 total
- Mapped to phases: 73
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-05*
*Last updated: 2026-10-05 after roadmap creation (traceability filled)*
