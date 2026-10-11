# Roadmap: ShadowEngLab

## Overview

Hành trình Step 1 đi từ nền móng đến một app luyện shadowing dùng được hằng ngày và có số liệu đáng tin. Trước hết dựng monorepo, contract (Zod) và chứng minh pipeline audio chạy đầu–cuối bằng script (Phase 1). Tiếp theo là tạo bài từ YouTube và trình phát theo câu để tập trọn một video, chưa chấm điểm (Phase 2), rồi chấm ngữ điệu có phản hồi đầu tiên dùng được (Phase 3). Ngưỡng ngữ điệu được chứng minh bằng eval nội bộ trên held-out (Phase 4). Sau đó hai nhánh độc lập chạy song song được: chấm âm bằng PPG + DTW, giải thích được (Phase 5) và app eval online cùng đợt chấm của 2 người bản xứ (Phase 6). Ôn luyện và báo cáo biến app thành công cụ học duy nhất (Phase 7), cuối cùng hiệu chỉnh điểm % theo nhãn người chấm, gợi ý bằng LLM và README (Phase 8).

Cấu trúc phase do Liam chốt trong `docs/gsd/roadmap-seed.md`. File này là nguồn sự thật về kế hoạch và tiến độ; seed chỉ để tham khảo.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

**Ánh xạ seed → GSD** (GSD dành riêng Phase 0): P0 → Phase 1, P1 → Phase 2, P2 → Phase 3, P3 → Phase 4, P4 → Phase 5, P5 → Phase 6, P6 → Phase 7, P7 → Phase 8. Nhãn "P0…P7" giữ trong tên phase để đối chiếu với seed.

- [x] **Phase 1: P0 · Nền tảng** - Monorepo, contract, FastAPI skeleton, `make setup`, smoke script pipeline audio (completed 2026-10-06)
- [x] **Phase 2: P1 · Tạo bài và trình phát** - Cài đặt, tạo bài nền từ YouTube, trình phát theo câu XState, ghi âm (chưa chấm điểm) (completed 2026-10-08)
- [x] **Phase 3: P2 · Chấm ngữ điệu** - Lớp B (F0, semitone, 3 chỉ số, prominence), rule template Lớp C, UI kết quả ngữ điệu (completed 2026-10-11)
- [ ] **Phase 4: P3 · Eval nội bộ và hiệu chỉnh ngưỡng ngữ điệu** - ~100 clip lỗi cố ý, `make eval` → `report.md`, held-out 30%, precision ≥ 90%
- [ ] **Phase 5: P4 · Chấm âm (PPG + DTW)** - Lớp A đầy đủ, `ref_unclear`, giải thích bằng chuỗi phone, UI `ScoredSentence` / `PhonemeDiff` (song song được với Phase 6)
- [ ] **Phase 6: P5 · App eval và đợt chấm** - App eval online (Supabase + Vercel), `export_clips.py`, 2 người chấm bản xứ, kappa ≥ 0.4 (song song được với Phase 5)
- [ ] **Phase 7: P6 · Ôn luyện và báo cáo** - Hàng ôn 1 → 3 → 7 ngày, TTS đọc chậm, chế độ chỉ ngữ điệu, tổng kết buổi, dashboard, thư viện có nhãn
- [ ] **Phase 8: P7 · Hiệu chỉnh và hoàn thiện** - Logistic điểm %, ngưỡng theo nhãn người chấm, gợi ý LLM, sửa UX từ feedback, README

## Phase Details

### Phase 1: P0 · Nền tảng

**Goal:** Dựng monorepo và contract, chứng minh pipeline audio chạy đầu–cuối bằng script.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: FND-01, FND-02, FND-03, FND-04, FND-05, FND-06, FND-07
**Success Criteria** (what must be TRUE):
  1. `make setup && make dev` chạy được trên máy sạch macOS Apple Silicon (cài deps Python + Node, tải model, khởi động Next.js và FastAPI).
  2. Test round-trip TS ↔ JSON Schema ↔ pydantic cho `ScoreResult` pass.
  3. `scripts/smoke_lesson.py <youtube_url>` chạy trên một video phỏng vấn giọng Mỹ audio sạch, ra JSON theo `Lesson` và in thời gian từng bước.
  4. Video 5 phút được xử lý xong trong ≤ 5 phút.

**Plans:** 9/9 plans complete

Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Cổng khởi động: Liam chốt 10 quyết định mở, manifest + lockfile, duyệt package trước khi cài (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — Walking skeleton: contract Lesson (Zod) → JSON Schema → pydantic sinh tự động → FastAPI /lessons/{id}, /health, /scoring (wave 2)
- [x] 01-03-PLAN.md — make setup: check_deps.sh (kiểm tra và hướng dẫn) + setup_models; Liam brew install ffmpeg espeak-ng (wave 2)
- [x] 01-04-PLAN.md — Hàm thuần pipeline (TDD): split_sentences, cổng URL YouTube, nhãn audio, ghi JSON atomic (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-05-PLAN.md — Contract đầy đủ (ScoreResult, IssueCode, Label, ClipManifest) + round-trip TS ↔ JSON Schema ↔ pydantic (wave 3)
- [x] 01-06-PLAN.md — Pipeline smoke_lesson.py: yt-dlp → Demucs → mlx-whisper → tách câu → F0/PPG → Lesson JSON + thời gian từng bước (wave 3)
- [x] 01-07-PLAN.md — Khung Next.js apps/web (import contracts) và apps/eval (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 01-08-PLAN.md — Makefile (setup/dev/test/lint/eval/smoke), drift gate, đo video 5 phút ≤ 5 phút (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 01-09-PLAN.md — ADR 0003, product.md mục 3–4, CLAUDE.md Lệnh, README (wave 5)

**Notes**:
- Phần thiết kế UI của P0 **đã xong, ngoài phạm vi còn lại**: design system và 13 màn (S1–S8, E1–E4) trong `docs/design/`, user flows `docs/flows.md`, product doc `docs/product.md`.
- Phạm vi còn lại (seed): B1 monorepo (pnpm workspace `apps/web`, `apps/eval`, `packages/contracts` + `services/audio` bằng uv; ESLint, Prettier, ruff, `.gitignore`), B2 contracts (Zod cho `Segment`, `Lesson`, `ScoreResult`, `IssueCode`, `ClipManifest`, `Label` theo `product.md` mục 3–4; sinh JSON Schema; pydantic phía Python), B3 Makefile (`setup`, `dev`, `test`, `eval` là stub), B4 `.env.example` (đã có, kiểm lại), C1 FastAPI skeleton (`/health`, router `lesson` và `scoring` rỗng, response validate theo B2), C2 `make setup` tải Demucs, mlx-whisper, `facebook/wav2vec2-lv-60-espeak-cv-ft` và kiểm tra parselmouth, espeak-ng, ffmpeg, C3 `scripts/smoke_lesson.py`.
- B4 không có requirement ID riêng; nó hỗ trợ FND-04 và FND-05 (chạy được khi có/không `OPENAI_API_KEY`).
- **Discuss gate**: ở bước Discuss, Liam phải chốt contract trong `packages/contracts` (`Segment`, `Lesson`, `ScoreResult`, `IssueCode`, `ClipManifest`, `Label`) và các quyết định còn mở trước khi Plan. Claude không tự đổi contract.
- Bộ 3–4 video eval chưa chọn; dùng tạm một video bất kỳ có audio sạch.

### Phase 2: P1 · Tạo bài và trình phát

**Goal:** Liam tạo bài từ link YouTube và tập trọn một video theo từng câu, đến bước ghi âm (chưa chấm điểm).
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: SET-01, SET-02, SET-03, SET-04, LES-01, LES-02, LES-03, LES-04, LES-05, LES-06, LES-07, PLY-01, PLY-02, PLY-03, PLY-04, PLY-05, PLY-06, PLY-07, REC-01, REC-02, REC-03, REC-04
**Success Criteria** (what must be TRUE):
  1. Tạo bài từ video 5 phút xong trong ≤ 5 phút.
  2. Tạo 2 bài liên tiếp không chặn nhau (Liam vẫn tập bài khác trong lúc chờ).
  3. Liam tập trọn 30 câu chỉ bằng chuột, và cũng tập trọn 30 câu chỉ bằng bàn phím.
  4. Thiếu API key app vẫn chạy: banner vàng không chặn, vẫn tạo bài và tập được.
  5. UI khớp `docs/design/`.

**Plans:** 19/19 plans complete
**UI hint**: yes

Plans:
**Wave 1**
- [x] 02-01-PLAN.md — Cổng contract: Liam duyệt shape bổ sung, schema SQLite attempts, mặc định Q7–Q10; hiện thực Zod → JSON Schema → pydantic (wave 1)
- [x] 02-02-PLAN.md — Cổng dependency: khai báo package, resolve lockfile, Liam duyệt, cài frozen (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-03-PLAN.md — Backend tracer: job runner tạo bài nền (pool tải + worker model FIFO), retry, gián đoạn, ranh giới API (wave 2)
- [x] 02-04-PLAN.md — Web tracer: client API Zod + TanStack Query, token/font, shadcn primitives, AppHeader (wave 2)
- [x] 02-05-PLAN.md — Player machine XState + phím tắt + đo mức âm, test trước UI (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 02-06-PLAN.md — Thư viện + tiến độ: SQLite attempts, GET /lessons, progress, helper đường dẫn (wave 3)
- [x] 02-07-PLAN.md — Video: preview, Range, tải lại, H.264/AAC, ADR 0004 bỏ IFrame (wave 3)
- [x] 02-08-PLAN.md — S1 thư viện: thẻ 4 trạng thái, JobSteps, Thử lại, banner hệ thống (wave 3)
- [x] 02-09-PLAN.md — S3 phát theo câu: video tự host, điều khiển, danh sách câu, phím tắt (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 02-10-PLAN.md — Lượt ghi backend: chuẩn hoá WAV 16 kHz, VAD, attempts, lưu clip eval (wave 4)
- [x] 02-11-PLAN.md — Trạng thái hệ thống, Settings, OpenAI key, warm-up nạp → giải phóng (wave 4)
- [x] 02-12-PLAN.md — Pipeline: IPA từ PPG, tách câu D-21, tách giọng theo đoạn, đo 5 phút (wave 4)
- [x] 02-13-PLAN.md — S2 tạo bài: preview, lỗi link, RangePicker (wave 4)
- [x] 02-14-PLAN.md — S3 ghi âm: Lượt của bạn, upload, nghe so sánh, không tiếng/lỗi, lưu clip eval (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 02-15-PLAN.md — Backend Sửa câu + Mất chữ cuối? (tính lại feature + IPA dưới cổng model) (wave 5)
- [x] 02-16-PLAN.md — Dịch câu: Liam chọn model (D-23), httpx → OpenAI, cache (wave 5)
- [x] 02-17-PLAN.md — S8 Settings: key, mặc định luyện tập, micro, model và thư mục dữ liệu (wave 5)
- [x] 02-18-PLAN.md — S3 công cụ câu: IPA, Dịch, Sửa câu, Mất chữ cuối? (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 02-19-PLAN.md — make smoke-jobs (2 bài không chặn, không key), đo 5 phút, ADR 0005, checklist UAT (wave 6)

**Notes**:
- Phạm vi (seed): M0 cài đặt + Settings (S8), M1 tạo bài và tách câu (S1, S2, job nền có tiến độ từng bước), M2 trình phát theo câu với XState (S3 phần trái + thanh điều khiển), M3 ghi âm và chuẩn hoá WAV 16 kHz mono, IPA nhận dạng từ audio mẫu. Flow F0, F1, F2 (đến bước ghi âm).
- State machine XState nằm ở file riêng và có test cho các transition chính trước khi gắn UI (PLY-02). Mọi hành động có nút rõ ràng, phím tắt là phụ (PLY-07).

### Phase 3: P2 · Chấm ngữ điệu

**Goal:** Liam nhận phản hồi ngữ điệu đầu tiên dùng được để học: 3 chỉ số, contour so với bản gốc và gợi ý bám số liệu đo được.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: PRO-01, PRO-02, PRO-03, PRO-04, RUL-01, RUL-02, FBK-01, FBK-02, FBK-03, FBK-04, FBK-05, FBK-06
**Success Criteria** (what must be TRUE):
  1. Bản gốc so với chính nó cho điểm ngữ điệu ≈ 100%.
  2. Câu đọc sai hẳn cho điểm thấp.
  3. Chấm một câu ≤ 3 giây (chỉ xử lý audio người học, feature bản gốc đã tính sẵn).
  4. Mỗi tip trỏ tới một issue (`issueRef`).
  5. UI khớp `docs/design/`: đủ 6 trạng thái vùng câu (`S3-trang-thai-cau`), hover gợi ý highlight từ liên quan, Ghi lại (`R`) giữ lượt chấm tốt nhất.

**Plans:** 12/12 plans complete (03-12 gap closure sau UAT: gợi ý)
**UI hint**: yes

Plans:
**Wave 1**
- [x] 03-01-PLAN.md — Cổng quyết định: Liam duyệt A–K (no_speech, endpoint lượt, SQLite v2, ngưỡng, tiêu chí "câu sai hẳn", sidecar, gap UI); hiện thực contract (wave 1)
- [x] 03-02-PLAN.md — Cổng dependency: recharts 3.10.1 + react-is 18.3.1 (duyệt lockfile), shadcn collapsible (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 03-03-PLAN.md — Lõi chấm Lớp B: prepare_features, align MFCC-DTW, 3 chỉ số, ScoreResult; tự so = 1.0 (wave 2)
- [x] 03-04-PLAN.md — Web tracer: lượt ghi → ScoreResult, no_speech, ScoreHero + scoreLevel, trạng thái đang chấm, khen/trung tính (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 03-05-PLAN.md — API + SQLite v2: POST trả ScoreResult, cache sidecar ngữ điệu, danh sách/chi tiết lượt, điểm tốt nhất (wave 3)
- [x] 03-06-PLAN.md — Prominence/ngắt + rule engine Lớp C (5 mã, cổng chắc chắn) + tip template (wave 3)
- [x] 03-07-PLAN.md — IntonationChart (Recharts) sau nút "So sánh ngữ điệu" (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 03-08-PLAN.md — TipList + hover/focus highlight từ trong câu và biểu đồ (wave 4)
- [x] 03-09-PLAN.md — Chấm màu danh sách câu và thanh tiến độ theo lượt tốt nhất (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 03-10-PLAN.md — AttemptStrip: chip lượt, lượt tốt nhất, xem lượt cũ, M/B theo lượt đang xem (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 03-11-PLAN.md — make smoke-score trên bài thật, ADR 0006, CLAUDE.md, cổng cuối phase + UAT (wave 6)

**Wave 7** *(gap closure, blocked on Wave 6 completion)*
- [x] 03-12-PLAN.md — Gợi ý sau UAT: biến thể có số đo theo lượt (D-16), chọn tip hai lượt (D-14 sửa), nhận xét theo chỉ số khi không có issue (D-15b) (wave 7)

**Notes**:
- Phạm vi (seed): Lớp B (F0, semitone, căn theo từ, 3 chỉ số Tốc độ / Độ lên xuống / Khớp giai điệu, prominence), rule engine Lớp C dạng template (`STRESS_MISMATCH`, `EXTRA_PAUSE`, `FINAL_CONTOUR`, `FLAT_PITCH`, `PITCH_DEVIATION`), UI `ScoreHero` (phần ngữ điệu), `IntonationChart`, `TipList`, 6 trạng thái vùng câu (S3).
- Precision trước recall: không chắc thì không báo lỗi. Gợi ý chỉ là template tiếng Việt ở phase này; LLM ở Phase 8.

### Phase 4: P3 · Eval nội bộ và hiệu chỉnh ngưỡng ngữ điệu

**Goal:** Ngưỡng ngữ điệu có số liệu chứng minh trên bộ lỗi cố ý, `make eval` sinh báo cáo tự động.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: EVL-01, EVL-02, EVL-03, EVL-04
**Success Criteria** (what must be TRUE):
  1. Precision của các rule ngữ điệu ≥ 90% trên held-out (tập 30% tách cố định, không dùng khi chỉnh ngưỡng).
  2. `make eval` chạy `eval/analyze.py` và sinh `eval/report.md` tự động (precision/recall theo rule, test-retest).
  3. Từ phase này trở đi, mọi thay đổi về model, ngưỡng hoặc rule đều chạy `make eval` và dán bảng metric vào PR.

**Plans:** 12 plans

Plans:
**Wave 1**
- [ ] 04-01-PLAN.md — Cổng quyết định: Liam duyệt EvalCase, cách đếm D-10, split, khoá held-out, sweep, cờ rule, gate; hiện thực contract (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 04-02-PLAN.md — Tracer make eval: cases.jsonl → kiểm D-05 → chấm lại WAV → đếm TP/FP/FN → report.md (tuning), mốc tự so (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 04-03-PLAN.md — sweep.py: quét ngưỡng trên tuning, đề xuất theo biên 95 %, không ghi file (wave 3)
- [ ] 04-04-PLAN.md — tag_clips.py: words / add / split / tag / check, make eval-tag (wave 3)
- [ ] 04-05-PLAN.md — Cờ tắt rule D-15 (thresholds → run_rules → report) và gate D-14/D-21 (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 04-06-PLAN.md — Khoá held-out: make eval HOLDOUT=1, log mở, digest đóng băng nhãn, tag_clips also, make eval-sweep (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [ ] 04-07-PLAN.md — Test-retest + ICC, kiểm tất định, đo điểm tổng D-17; ADR 0007, README, CLAUDE.md (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [ ] 04-08-PLAN.md — Liam chọn bài, viết kịch bản, chốt split (một chiều), commit cases.jsonl (wave 6)

**Wave 7** *(blocked on Wave 6 completion)*
- [ ] 04-09-PLAN.md — Thu 3 clip + tracer thật, rồi Liam thu và gắn toàn bộ (wave 7)

**Wave 8** *(blocked on Wave 7 completion)*
- [ ] 04-10-PLAN.md — Kiểm phủ, make eval + sweep trên tuning, Liam chọn ngưỡng và alsoPresent (wave 8)

**Wave 9** *(blocked on Wave 8 completion)*
- [ ] 04-11-PLAN.md — Mở held-out (một chiều), đo SC1, Liam duyệt tắt rule D-15 (wave 9)

**Wave 10** *(blocked on Wave 9 completion)*
- [ ] 04-12-PLAN.md — Áp D-15, gate held-out xanh, make eval mặc định hai tập, ADR 0007 chấp nhận, cổng cuối (wave 10)

**Notes**:
- Phạm vi (seed): thu ~100 clip lỗi cố ý (mỗi clip 1 lỗi) cùng ~8 clip mốc đúng, `eval/analyze.py` bản đầu, tách 30% held-out, chỉnh ngưỡng. Liam tự thu âm clip.
- Không commit audio eval, nhãn thô của người chấm hay `.env` (`eval/clips/` và `eval/labels.jsonl` gitignored).

### Phase 5: P4 · Chấm âm (PPG + DTW)

**Goal:** Liam thấy từ nào mình phát âm lệch khỏi người nói gốc, kèm giải thích bằng chuỗi phone, chấm đủ âm + ngữ điệu trong ≤ 3 giây.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: PHN-01, PHN-02, PHN-03, PHN-04, PHN-05, PHN-06
**Success Criteria** (what must be TRUE):
  1. Chấm một câu (âm + ngữ điệu) ≤ 3 giây.
  2. Bắt được lỗi weak form và nuốt âm trong bộ lỗi cố ý, có số liệu từ `make eval`.
  3. Kiểm tra cơ bản: bản gốc so với chính nó ≈ 100%.
  4. Mọi thay đổi về model, ngưỡng hoặc rule trong phase này có chạy `make eval` và bảng metric được dán vào PR.

**Plans**: TBD
**UI hint**: yes

**Notes**:
- **Chạy song song được với Phase 6**: hai phase độc lập (Phase 5 làm Lớp A trong `services/audio` và `apps/web`, Phase 6 làm `apps/eval` và đợt chấm); đợt chấm của người bản xứ diễn ra trong lúc làm Lớp A.
- Phạm vi (seed): Lớp A đầy đủ (PPG, DTW với khoảng cách `−log(p_ref · p_user)`, chiếu ranh giới từ, trọng số confidence, `ref_unclear`), giải thích bằng chuỗi phone (chỉ để giải thích, không để chấm), UI `ScoredSentence`, `PhonemeDiff`, điểm tổng.
- Bổ sung tỉ lệ câu `ref_unclear` vào nhãn chất lượng audio của bài (LES-06) để tinh chỉnh nhãn "Audio sạch" / "Có nhạc nền" vốn tính từ tỉ lệ năng lượng non-vocal/vocal của Demucs ở Phase 2.

### Phase 6: P5 · App eval và đợt chấm

**Goal:** Có nhãn của người nghe bản xứ: 2 người chấm hoàn thành đợt chấm trên app eval online với mức đồng thuận đạt ngưỡng.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: RAT-01, RAT-02, RAT-03, RAT-04, RAT-05, RAT-06, RAT-07, RAT-08, RAT-09
**Success Criteria** (what must be TRUE):
  1. Cả 2 người chấm xong đợt chấm (pilot 5 clip với 1 người chấm, sau đó cả hai chấm ~68 clip).
  2. Cohen's kappa giữa hai người chấm ≥ 0.4.
  3. Gold check pass (8 gold clip lẫn trong thứ tự clip của mỗi người).
  4. Nếu phase có thay đổi về model, ngưỡng hoặc rule thì chạy `make eval` và dán bảng metric vào PR.

**Plans**: TBD
**UI hint**: yes

**Notes**:
- **Chạy song song được với Phase 5**. Phụ thuộc Phase 4 vì cần clip tự nhiên đã lưu (và `make eval` / `export_clips.py` từ eval nội bộ).
- Phạm vi (seed): app eval (E1–E4, Supabase auth magic link + allowlist, RLS, bucket private, signed URL, phím tắt, autosave, xáo trộn theo người chấm, 8 gold clip), `eval/export_clips.py`, pilot 5 clip với 1 người chấm, sau đó cả hai chấm ~68 clip. App eval phải responsive mobile dọc.
- Nhãn thô của người chấm và audio eval không được commit; `gold` và `system_score` không bao giờ trả về client.
- Cần 2 người chấm bản xứ Mỹ sẵn sàng (email vào allowlist) trước khi bắt đầu đợt chấm.

### Phase 7: P6 · Ôn luyện và báo cáo

**Goal:** Liam dùng app làm công cụ học duy nhất: câu yếu tự vào hàng ôn, có tổng kết buổi, dashboard tiến bộ và thư viện có nhãn.
**Mode:** mvp
**Depends on**: Phase 5
**Requirements**: REV-01, REV-02, REV-03, REV-04, RPT-01, RPT-02, RPT-03, RPT-04
**Success Criteria** (what must be TRUE):
  1. Câu yếu hôm qua tự xuất hiện hôm nay trong hàng ôn.
  2. Từ S7 tới câu cần tập lại trong ≤ 2 click.
  3. Liam tự luyện trọn một tuần chỉ bằng app.
  4. Mọi thay đổi về model, ngưỡng hoặc rule trong phase này (nếu có) chạy `make eval` và bảng metric được dán vào PR.

**Plans**: TBD
**UI hint**: yes

**Notes**:
- Phạm vi (seed): M5 tổng kết buổi (S5), M6 hàng ôn 1 → 3 → 7 ngày với ngưỡng 70% (S6), TTS đọc chậm (`gpt-4o-mini-tts`, thiếu key thì báo không khả dụng), chế độ chỉ ngữ điệu, dashboard tiến bộ (S7), thư viện có nhãn (S1). Flow F3, F4.
- Phụ thuộc Phase 5 (cần chấm âm để tổng kết 3 chiều và nhãn thư viện); không cần chờ Phase 6.

### Phase 8: P7 · Hiệu chỉnh và hoàn thiện

**Goal:** Điểm số đáng tin theo nhãn người chấm và repo sẵn sàng public: máy mới clone về là dùng được.
**Mode:** mvp
**Depends on**: Phase 5, Phase 6, Phase 7
**Requirements**: CAL-01, CAL-02, CAL-03, CAL-04, CAL-05
**Success Criteria** (what must be TRUE):
  1. Spearman giữa điểm hệ thống và người chấm xấp xỉ mức đồng thuận giữa hai người chấm.
  2. Máy mới clone, điền `.env`, `make setup && make dev` là dùng được.
  3. Mọi thay đổi ngưỡng, model hoặc rule (logistic, ngưỡng theo nhãn) đều chạy `make eval` và bảng metric được dán vào PR; `report.md` có calibration curve và precision/recall theo loại cờ.

**Plans**: TBD
**UI hint**: yes

**Notes**:
- Phạm vi (seed): fit logistic cho điểm %, chỉnh ngưỡng theo nhãn người chấm, gợi ý bằng LLM (OpenAI model nhỏ, structured output; chỉ nhận JSON `issues`, mỗi tip trỏ một `issueRef` hợp lệ; thiếu key hoặc LLM lỗi thì rơi về template), sửa lỗi UX 🔴/🟡 từ `docs/feedback.md`, `report.md`, README (ghi chung là có human review).

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. Ngoại lệ: Phase 5 và Phase 6 độc lập với nhau (cùng chỉ phụ thuộc Phase 4) nên chạy song song được; Phase 7 chỉ cần Phase 5 xong; Phase 8 cần cả Phase 5, 6, 7.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. P0 · Nền tảng | 9/9 | Complete    | 2026-10-06 |
| 2. P1 · Tạo bài và trình phát | 19/19 | Complete    | 2026-10-08 |
| 3. P2 · Chấm ngữ điệu | 12/12 | Complete    | 2026-10-11 |
| 4. P3 · Eval nội bộ và hiệu chỉnh ngưỡng ngữ điệu | 0/0 | Not started | - |
| 5. P4 · Chấm âm (PPG + DTW) | 0/0 | Not started | - |
| 6. P5 · App eval và đợt chấm | 0/0 | Not started | - |
| 7. P6 · Ôn luyện và báo cáo | 0/0 | Not started | - |
| 8. P7 · Hiệu chỉnh và hoàn thiện | 0/0 | Not started | - |
