# Roadmap seed cho GSD

> Đầu vào để GSD tạo project context, roadmap và state theo format riêng của nó. Sau khi GSD đã tạo các file đó, **chúng là nguồn sự thật về kế hoạch và tiến độ**; file này chỉ giữ lại để tham khảo, không cập nhật song song.
> Spec sản phẩm vẫn là `docs/product.md`. Luồng người dùng: `docs/flows.md`. UI: `docs/design/`.

## Mục tiêu dự án (cho phần vision / project context)

ShadowEngLab: web app chạy local để Liam tự luyện shadowing tiếng Anh (giọng Mỹ) từ bất kỳ video YouTube nào. Chấm điểm bằng cách so audio của người học với **audio của chính người nói trong video** (âm, ngữ điệu, trọng âm, ngắt nghỉ), không so với từ điển. Kèm app eval online để 2 người chấm bản xứ kiểm chứng điểm (human review). Đồng thời là dự án portfolio AI Engineering, public trên GitHub.

**Step 1** (roadmap này): app đầy đủ tính năng để học hằng ngày; clone, điền `.env`, `make setup && make dev` là dùng được.
**Step 2** (milestone sau): hardening (test, CI eval regression, logging, job queue, backup, Docker).

## Quyết định đã khoá (không bàn lại trong Discuss trừ khi Liam mở lại)

- Chấm hoàn toàn theo audio gốc; IPA hiển thị là IPA nhận dạng từ audio mẫu.
- Lớp A (âm): wav2vec2-espeak → PPG → DTW với khoảng cách `−log(p_ref · p_user)`; chuỗi phone chỉ để giải thích.
- Lớp B (ngữ điệu): parselmouth, F0 đổi sang semitone so với median của từng người.
- Lớp C: rule engine sinh `issues`; gợi ý bằng template, sau đó LLM (OpenAI) chỉ nhận JSON lỗi, không nhận audio.
- Precision trước recall. Bản gốc không đủ rõ → `ref_unclear`, không chấm âm.
- Stack: Next.js 14 + TS + Tailwind + shadcn/ui (token Radix, `docs/design/tokens.md`), XState cho trình phát; FastAPI + Python 3.11 quản lý bằng uv; SQLite local; app eval Next.js + Supabase trên Vercel.
- Tự host video (yt-dlp), IFrame API làm dự phòng. Transcribe bằng mlx-whisper local; tách giọng bằng Demucs.
- Web app: nút là chính, phím tắt là phụ. Điểm: đỏ < 60, vàng 60–79, xanh lá ≥ 80; teal/cam chỉ nhận diện Bản gốc/Bạn.
- `packages/contracts` (Zod) là nguồn sự thật cho kiểu dữ liệu; Liam chốt contract trước khi plan.

## Phases

Mỗi phase: mục tiêu · phạm vi · tiêu chí hoàn thành (dùng cho bước Verify) · phụ thuộc.

### P0 · Nền tảng (phần thiết kế UI đã xong)

- **Mục tiêu:** dựng monorepo và contract, chứng minh pipeline audio chạy đầu–cuối bằng script.
- **Đã xong:** design system và 13 màn (`docs/design/`), user flows, product doc.
- **Phạm vi còn lại:**
    - B1 · Monorepo: pnpm workspace (`apps/web`, `apps/eval`, `packages/contracts`) + `services/audio` (uv). ESLint, Prettier, ruff, `.gitignore`.
    - B2 · Contracts: Zod cho `Segment`, `Lesson`, `ScoreResult`, `IssueCode`, `ClipManifest`, `Label` theo `product.md` mục 3, 4; sinh JSON Schema; pydantic validate phía Python.
    - B3 · Makefile: `setup`, `dev`, `test`, `eval` (eval là stub).
    - B4 · `.env.example` (đã có, kiểm lại).
    - C1 · FastAPI skeleton: `/health`, router `lesson`, `scoring` rỗng, response validate theo B2.
    - C2 · `make setup` tải Demucs, mlx-whisper, `facebook/wav2vec2-lv-60-espeak-cv-ft`; kiểm tra parselmouth, espeak-ng, ffmpeg.
    - C3 · `scripts/smoke_lesson.py <youtube_url>`: yt-dlp → Demucs → mlx-whisper (word timestamps) → tách câu 3–8 s → F0 + PPG mỗi câu → JSON theo `Lesson`, in thời gian từng bước.
- **Tiêu chí hoàn thành:**
    - `make setup && make dev` chạy trên máy sạch (macOS Apple Silicon).
    - Test round-trip TS ↔ JSON Schema ↔ pydantic cho `ScoreResult` pass.
    - Smoke script chạy trên một video phỏng vấn giọng Mỹ audio sạch; video 5 phút xử lý ≤ 5 phút.
- **Phụ thuộc:** không. Bộ 3–4 video eval chưa chọn; dùng tạm một video bất kỳ có audio sạch.

### P1 · Tạo bài và trình phát

- **Mục tiêu:** tập được trọn một video (chưa chấm điểm).
- **Phạm vi:** M0 cài đặt + Settings (S8), M1 tạo bài và tách câu (S1, S2, job nền có tiến độ từng bước), M2 trình phát theo câu với XState (S3 phần trái + thanh điều khiển), M3 ghi âm và chuẩn hoá WAV 16 kHz mono, IPA nhận dạng từ audio mẫu. Flow F0, F1, F2 (đến bước ghi âm).
- **Tiêu chí hoàn thành:** tạo bài từ video 5 phút ≤ 5 phút; tạo 2 bài liên tiếp không chặn nhau; tập trọn 30 câu chỉ bằng chuột và chỉ bằng bàn phím; thiếu API key vẫn chạy; UI khớp `docs/design/`.
- **Phụ thuộc:** P0.

### P2 · Chấm ngữ điệu

- **Mục tiêu:** có phản hồi ngữ điệu đầu tiên dùng được để học.
- **Phạm vi:** Lớp B (F0, semitone, căn theo từ, 3 chỉ số, prominence), rule engine Lớp C dạng template (`STRESS_MISMATCH`, `EXTRA_PAUSE`, `FINAL_CONTOUR`, `FLAT_PITCH`, `PITCH_DEVIATION`), UI: `ScoreHero` (phần ngữ điệu), `IntonationChart`, `TipList`, 6 trạng thái vùng câu (S3).
- **Tiêu chí hoàn thành:** bản gốc so với chính nó ≈ 100%; câu đọc sai hẳn cho điểm thấp; chấm ≤ 3 s; mỗi tip trỏ tới một issue.
- **Phụ thuộc:** P1.

### P3 · Eval nội bộ và hiệu chỉnh ngưỡng ngữ điệu

- **Mục tiêu:** ngưỡng ngữ điệu có số liệu chứng minh.
- **Phạm vi:** thu ~100 clip lỗi cố ý (mỗi clip 1 lỗi), `eval/analyze.py` bản đầu (precision/recall theo rule, test-retest), tách 30% held-out, chỉnh ngưỡng. Từ đây mọi thay đổi model/ngưỡng phải chạy `make eval`.
- **Tiêu chí hoàn thành:** precision các rule ngữ điệu ≥ 90% trên held-out; `report.md` sinh tự động.
- **Phụ thuộc:** P2. Liam tự thu âm clip.

### P4 · Chấm âm (PPG + DTW)

- **Mục tiêu:** chấm âm so với bản gốc, giải thích được.
- **Phạm vi:** Lớp A đầy đủ (PPG, DTW, chiếu ranh giới từ, trọng số confidence, `ref_unclear`), giải thích bằng chuỗi phone, UI `ScoredSentence`, `PhonemeDiff`, điểm tổng.
- **Tiêu chí hoàn thành:** chấm một câu ≤ 3 s; bắt được lỗi weak form và nuốt âm trong bộ lỗi cố ý; kiểm tra cơ bản bản gốc so với chính nó ≈ 100%.
- **Phụ thuộc:** P3. **Chạy song song được với P5.**

### P5 · App eval và đợt chấm

- **Mục tiêu:** có nhãn của người nghe bản xứ.
- **Phạm vi:** app eval (E1–E4, Supabase auth magic link + allowlist, RLS, bucket private, signed URL, phím tắt, autosave, xáo trộn theo người chấm, 8 gold clip); `eval/export_clips.py`; pilot 5 clip với 1 người chấm; sau đó cả hai chấm ~68 clip.
- **Tiêu chí hoàn thành:** 2 người chấm xong; Cohen's kappa giữa hai người ≥ 0.4; gold check pass.
- **Phụ thuộc:** P3 (cần clip tự nhiên đã lưu). **Chạy song song được với P4.**

### P6 · Ôn luyện và báo cáo

- **Mục tiêu:** dùng app làm công cụ học duy nhất.
- **Phạm vi:** M5 tổng kết buổi (S5), M6 hàng ôn 1 → 3 → 7 ngày với ngưỡng 70% (S6), TTS đọc chậm, chế độ chỉ ngữ điệu, dashboard tiến bộ (S7), thư viện có nhãn (S1). Flow F3, F4.
- **Tiêu chí hoàn thành:** câu yếu hôm qua tự xuất hiện hôm nay; từ S7 tới câu cần tập lại ≤ 2 click; tự luyện trọn một tuần chỉ bằng app.
- **Phụ thuộc:** P4.

### P7 · Hiệu chỉnh và hoàn thiện

- **Mục tiêu:** điểm số đáng tin, repo sẵn sàng public.
- **Phạm vi:** fit logistic cho điểm %, chỉnh ngưỡng theo nhãn người chấm, gợi ý bằng LLM (structured output), sửa lỗi UX từ `docs/feedback.md`, `report.md`, README portfolio (ghi chung là có human review).
- **Tiêu chí hoàn thành:** Spearman hệ thống–người chấm xấp xỉ mức đồng thuận giữa hai người chấm; máy mới clone, điền `.env`, `make setup && make dev` là dùng được.
- **Phụ thuộc:** P4, P5, P6.

## Ngoài phạm vi Step 1

Nhiều người dùng, thương mại hoá, mobile app chính, dark mode, "Nói với AI", chế độ chính tả, giọng UK, lưu lịch sử ghi âm.
