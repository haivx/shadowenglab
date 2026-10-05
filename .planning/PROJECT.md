# ShadowEngLab

## What This Is

Web app chạy local để Liam tự luyện shadowing tiếng Anh (giọng Mỹ) từ bất kỳ video YouTube nào: dán link, tập từng câu, và biết chính xác mình nói khác **chính người nói trong video** ở đâu (âm, trọng âm, lên xuống giọng, ngắt nghỉ), kèm gợi ý cụ thể để sửa. Đi kèm một app eval nhỏ deploy online để 2 người chấm bản xứ kiểm chứng điểm của hệ thống (human review). Đồng thời là dự án portfolio AI Engineering, public trên GitHub.

Spec sản phẩm chi tiết: `docs/product.md` (nguồn sự thật cấp sản phẩm). Luồng: `docs/flows.md`. UI: `docs/design/`.

## Core Value

Sau mỗi lượt nói, Liam biết **đáng tin** mình lệch khỏi người nói gốc ở đâu — so audio với audio gốc, precision trước recall: khi không chắc thì không báo lỗi.

## Requirements

### Validated

- ✓ Thiết kế UI v0.2: design system + 13 màn (S1–S8, E1–E4) trong `docs/design/` — P0 (trước GSD)
- ✓ User flows F0–F5 (`docs/flows.md`) và product doc (`docs/product.md`) — P0 (trước GSD)

### Active

- [ ] Monorepo + `packages/contracts` (Zod) làm nguồn sự thật kiểu dữ liệu, pydantic khớp phía Python
- [ ] `make setup && make dev` chạy trên máy sạch macOS Apple Silicon, có/không API key
- [ ] Tạo bài từ link YouTube (yt-dlp → Demucs → mlx-whisper → tách câu 3–8 s → feature bản gốc), job nền có tiến độ
- [ ] Trình phát theo câu (XState), ghi âm, IPA nhận dạng từ audio mẫu
- [ ] Chấm ngữ điệu (Lớp B) + rule engine template (Lớp C) + UI kết quả
- [ ] Eval nội bộ với ~100 clip lỗi cố ý, `make eval` → `report.md`, precision rule ngữ điệu ≥ 90% trên held-out
- [ ] Chấm âm PPG + DTW (Lớp A), `ref_unclear`, giải thích bằng chuỗi phone
- [ ] App eval online (Supabase + Vercel) và đợt chấm của 2 người bản xứ, kappa ≥ 0.4
- [ ] Ôn luyện (1 → 3 → 7 ngày), TTS đọc chậm, chế độ chỉ ngữ điệu, tổng kết buổi, dashboard tiến bộ, thư viện có nhãn
- [ ] Hiệu chỉnh điểm % (logistic) theo nhãn người chấm, gợi ý bằng LLM (structured output), README portfolio

### Out of Scope

- Nhiều người dùng, thương mại hoá — dự án học cá nhân + portfolio, cho phép lấy nguồn từ YouTube
- Mobile app chính, dark mode — ngoài phạm vi Step 1 (app eval vẫn phải responsive mobile)
- "Nói với AI", chế độ chính tả — mở rộng xa hơn (product.md mục 9)
- Giọng UK — Step 1 tập trung US; bộ eval và ngưỡng theo giọng Mỹ
- Lưu lịch sử ghi âm — Step 1 chỉ giữ features (trừ clip đánh dấu cho eval)
- Chấm bằng LLM đa phương thức / so với từ điển — không nhất quán, hay bịa lỗi; trái nguyên tắc so với bản gốc
- Hardening (CI eval regression, logging, job queue/retry, backup, Docker) — Step 2, milestone sau

## Context

- Repo mới: đã có tài liệu, thiết kế và thư mục khung (`apps/web`, `apps/eval`, `services/audio`, `packages/contracts`, `eval/`, `scripts/` chỉ có README). Chưa có code.
- Người dùng: Liam (learner kiêm builder, app chính local); 2 người chấm bản xứ Mỹ (app eval online).
- Hệ thống chấm 3 lớp độc lập, tất cả local $0:
  - **Lớp A (âm):** `facebook/wav2vec2-lv-60-espeak-cv-ft` → PPG → DTW với khoảng cách `−log(p_ref · p_user)` → chiếu ranh giới từ Whisper → điểm từ có trọng số confidence; chuỗi phone (argmax) chỉ để giải thích.
  - **Lớp B (ngữ điệu):** parselmouth F0 ~10 ms → semitone so với median từng người → căn theo từ → Tốc độ, Độ lên xuống, Khớp giai điệu, prominence.
  - **Lớp C (rule):** `STRESS_MISMATCH`, `EXTRA_PAUSE`, `FINAL_CONTOUR`, `FLAT_PITCH`, `PITCH_DEVIATION`, `PHONE`, `WORD_MISSING` → `issues`; gợi ý template trước, LLM sau (chỉ nhận JSON `issues`, mỗi tip trỏ `issueRef`).
- Contract `ScoreResult`, `ClipManifest`, data model eval (`clips`, `labels`) đã phác trong `product.md` mục 3–4; Liam chốt chính thức trong Discuss của P0.
- Bộ eval 3 tầng: mốc đúng (~8), lỗi cố ý (~100, Liam tự thu), lượt luyện tự nhiên (~60, người bản xứ chấm); 30% held-out.
- Ánh xạ phase: P0 → Phase 1, P1 → Phase 2, …, P7 → Phase 8 (GSD dành riêng Phase 0). Nhãn "P0…P7" giữ trong tên phase để đối chiếu `docs/gsd/roadmap-seed.md`.
- Nhật ký dùng thử: `docs/feedback.md` là backlog UX cho P7 và Step 2.

## Constraints

- **Tech stack (khoá):** Next.js 14 + TS strict + Tailwind + shadcn/ui (token Radix, `docs/design/tokens.md`) + TanStack Query + Recharts + XState; FastAPI + Python 3.11 qua uv; SQLite + file system; app eval Next.js + Supabase trên Vercel — ADR 0001, product.md mục 5
- **Nền tảng:** macOS Apple Silicon (mlx-whisper); cần Node 20+, pnpm, uv, ffmpeg, espeak-ng
- **Hiệu năng:** chấm một câu ≤ 3 s (chỉ xử lý audio người học; feature bản gốc tính sẵn khi tạo bài); tạo bài từ video 5 phút ≤ 5 phút
- **Chi phí:** local-first, ~$0–1/tháng; chỉ OpenAI (gợi ý, TTS) là trả phí và tuỳ chọn
- **Chạy khi thiếu key:** thiếu `OPENAI_API_KEY` → gợi ý template, tắt TTS, không chặn app
- **Contract-first:** `packages/contracts` (Zod) là nguồn sự thật; Liam chốt contract trong Discuss trước khi Plan; Claude không tự đổi contract, schema DB, ngưỡng chấm hay model
- **Eval gate:** từ P3 trở đi mọi thay đổi model/ngưỡng/rule phải chạy `make eval` và dán bảng metric vào PR
- **Dữ liệu:** không commit audio eval, nhãn thô người chấm, `.env`
- **UI:** bám `docs/design/`; không thêm màn/component ngoài thiết kế đã chốt; nút là chính, phím tắt phụ; màu điểm qua `scoreLevel()` (đỏ < 60, vàng 60–79, xanh ≥ 80); teal/cam chỉ cho Bản gốc/Bạn
- **Code style:** TS không `any`, Zod ở mọi ranh giới I/O; Python type hints + ruff + pytest, hàm audio thuần (array in → array out)
- **Quy trình:** mỗi phase đủ Discuss → Plan → Execute → Verify → Ship; PR nhỏ, review tại ranh giới (schema, state machine, output pipeline); quyết định mới → ADR trong `docs/decisions/`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Chấm hoàn toàn theo audio gốc, bỏ từ điển; IPA hiển thị là IPA nhận dạng từ audio mẫu | Mục tiêu là bắt chước chính người nói, kể cả weak form và nuốt âm | — Pending |
| PPG + DTW là bộ chấm âm chính; chuỗi phone chỉ giải thích | So phân phối xác suất dễ dãi ở chỗ bản gốc mơ hồ | — Pending |
| Precision trước recall; bản gốc không rõ → `ref_unclear` | Báo nhầm hại người học hơn bỏ sót | — Pending |
| LLM chỉ viết gợi ý từ JSON `issues`, không nhận audio; không dùng LLM đa phương thức để chấm | Gợi ý bám số liệu đo được; LLM audio không nhất quán | — Pending |
| Tự host video (yt-dlp), IFrame API dự phòng | Seek chính xác, dùng chung nguồn với pipeline | — Pending |
| uv cho Python, XState cho trình phát | ADR 0001 | — Pending |
| Điều phối bằng GSD; file `.planning/` là nguồn sự thật về kế hoạch/tiến độ, `roadmap-seed.md` chỉ tham khảo | ADR 0002 | — Pending |
| App eval: 2 người chấm toàn bộ clip, không đồng bộ, 8 gold clip | Có số liệu đồng thuận trên mọi clip | — Pending |
| P0→Phase 1 … P7→Phase 8 | GSD dành riêng Phase 0 | — Pending |
| P4 và P5 chạy song song được | Độc lập; đợt chấm diễn ra trong lúc làm Lớp A | — Pending |
| Nhãn chất lượng audio (LES-06) tính từ tỉ lệ năng lượng non-vocal/vocal của Demucs lúc tạo bài; Phase 5 bổ sung tỉ lệ `ref_unclear` | `ref_unclear` chỉ có từ Lớp A (Phase 5), Phase 2 vẫn cần nhãn | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-05 after initialization*
