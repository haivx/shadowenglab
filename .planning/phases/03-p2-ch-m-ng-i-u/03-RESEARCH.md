# Phase 3: P2 · Chấm ngữ điệu - Research

**Researched:** 2026-10-08
**Domain:** chấm ngữ điệu so với audio gốc (parselmouth F0 → semitone → DTW trên MFCC → 3 chỉ số + prominence → rule engine template), endpoint chấm đồng bộ trả `ScoreResult`, SQLite migration v2, UI kết quả (ScoreHero, IntonationChart bằng Recharts, TipList, 6 trạng thái vùng câu) trên XState + TanStack Query
**Confidence:** HIGH cho tích hợp với code hiện có (đã đọc nguồn) và cho tính khả thi/ngân sách thời gian (đã chạy prototype trên máy này: M1, 8 GB); MEDIUM cho các ngưỡng rule (chỉ đo trên nhiễu loạn tổng hợp từ 2 bài thật, chưa có bản ghi của Liam); LOW cho recall của `STRESS_MISMATCH` và `FINAL_CONTOUR` (xem Pitfall 8).

Quy ước tag: `[VERIFIED: local prototype run]` = tôi đã chạy trong session này (script prototype nằm ở scratchpad, KHÔNG nằm trong repo; các hàm cốt lõi được chép lại ở "Code Examples"); `[VERIFIED: path:dòng]` = đã đọc file nguồn kèm trích nguyên văn; `[CITED: url]` = tài liệu chính thức/Context7/nguồn học thuật; `[ASSUMED]` = chưa kiểm chứng (xem Assumptions Log). Prose tiếng Việt, định danh/code giữ tiếng Anh (khớp `02-RESEARCH.md`).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

> Kế thừa: contract `ScoreResult`/`Issue`/`Tip`/`Prosody` đã chốt ở Phase 1 (`01-CONTEXT.md` D-10..D-15, `packages/contracts/src/score.ts`) — **không đổi shape**. Phase 2 D-05 (state `scoring` trong XState có sẵn), D-06 (endpoint lượt ghi sẽ trả `ScoreResult`, không nới `ScoreResult` cho "chưa chấm"), D-08 (chấm màu danh sách câu chuyển sang `scoreLevel()`), D-18 (không giữ model resident, máy 8 GB). Các quyết định dưới đây là **Liam đã chốt** trong Discuss Phase 3.

#### Căn thời gian người học ↔ bản gốc
- **D-01:** **Căn bằng DTW trên MFCC, không dùng model.** Chiếu ranh giới từ (Whisper) của bản gốc sang audio người học qua đường DTW giữa MFCC hai bên. Không tranh `model_gate` với job tạo bài, không nạp wav2vec2/Whisper khi chấm. Viết thành hàm thuần `align(ref_feats, user_feats) → path` (array in → array out) sau một giao diện thay được, để Phase 5 thay bằng PPG-DTW mà rule Lớp C không đổi. — **Reversibility:** reversible — đổi bộ căn là cục bộ sau giao diện `align`.
- **D-02:** **Căn không đáng tin → giữ chỉ số mức câu, bỏ issue theo từ.** Khi chất lượng căn kém (chi phí DTW chuẩn hoá vượt ngưỡng, đường đi suy biến, người học nói thiếu/khác câu), vẫn trả `speed`, `pitchRange`, và các rule mức câu `FLAT_PITCH`, `FINAL_CONTOUR`; `melodyMatch` tính trên contour căn theo tỉ lệ thời gian; **không** sinh `STRESS_MISMATCH`, `PITCH_DEVIATION`, `EXTRA_PAUSE`. Không thêm field/trạng thái mới vào contract. Ngưỡng "căn kém" Claude đề xuất trong file ngưỡng (D-10), Liam duyệt ở PR.
- **D-03:** **Feature bản gốc mới → tính bù lười khi chấm lần đầu, ghi cache.** Nếu Lớp B cần feature bản gốc chưa có trong `seg/NNNN.npz` (ví dụ F0 hai lượt theo khoảng pitch riêng người nói, intensity cho prominence, MFCC cho căn), bài mới tính sẵn trong bước `analyzing`; bài cũ thiếu key thì lần chấm đầu tính từ audio vocals của câu đó (không cần model) rồi ghi lại `.npz`. Không bắt tạo lại bài, không script migrate. Ngân sách ≤ 3 s áp cho lượt chấm thường (đã có cache); lần tính bù đầu được phép chậm hơn nhưng phải ghi trong `timingMs`.

#### Điểm tổng và hiển thị ở P2
- **D-04:** **Công thức gộp (P2, `sound = null`):** `intonation = mean(pitchRange, melodyMatch)`; `rhythm = speed`; `overall = mean(speed, pitchRange, melodyMatch)`. Ngắt thừa báo qua issue `EXTRA_PAUSE`, không trừ vào `rhythm`. Phase 8 hiệu chỉnh lại bằng logistic.
- **D-05:** **`melodyMatch = max(0, r)`** với `r` là Pearson của hai contour semitone đã căn (chỉ frame hữu thanh cả hai bên). Không tương quan hoặc ngược chiều → 0; bản gốc so với chính nó → 1.
- **D-06:** **Chip từ ở P2: câu trơn, không tô điểm từng từ.** `words[]` vẫn điền đủ (`status: 'scored'`, `start`/`end` trên audio người học từ D-01, `similarity` = độ khớp ngữ điệu của từ đó để Phase 4 dùng cho eval). UI **không tô màu chip** khi `scores.sound === null`, để màu chip không đổi nghĩa khi Phase 5 thêm điểm âm. Từ chỉ được highlight khi hover tip (FBK-03).
- **D-07:** **Ẩn hẳn các phần Lớp A của S3-S4 ở P2** (panel PhonemeDiff "Bạn đọc … khác ở âm nào?", điểm dưới từng từ). Panel kết quả P2 = `ScoreHero` + nút "So sánh ngữ điệu"/`IntonationChart` + `TipList` + thanh nút (O/M/B/R/→). Không thêm UI giữ chỗ ngoài thiết kế. Phase 5 gắn lại.
- **D-08:** **Trạng thái vùng câu thứ 6 ở P2 = "lỗi"** (toast + Thử lại, giữ bản ghi — đã có từ P1), đúng FBK-05. Biến thể "Bản gốc không đủ rõ — chỉ chấm ngữ điệu" trong `S3-trang-thai-cau` làm cùng PHN-02 ở Phase 5.

#### Lưu điểm, endpoint và lượt tốt nhất
- **D-09:** **`POST /lessons/{id}/segments/{index}/attempts` trả `ScoreResult`** trong cùng request (upload → chuẩn hoá WAV → chấm). Không thu được tiếng → `ApiError` với mã mới (đề xuất `no_speech`) thay cho `voiced: false`; state `scoring` của XState chờ chính request này và rẽ nhánh "không thu được tiếng" theo mã lỗi. `AttemptAck` chỉ còn dùng cho `PUT …/attempts/{n}/eval-clip`. Thêm mã vào `ApiErrorCode` là đổi contract → đi qua checkpoint PR contract (Zod → JSON Schema → pydantic, drift gate). — **Reversibility:** one-way — contract dùng chung web/Python, đổi response của endpoint công khai.
- **D-10:** **SQLite migration `user_version` 1 → 2:** thêm vào `attempts` các cột `overall`, `intonation`, `rhythm`, `sound` (REAL, nullable) và `result_json` (TEXT, nguyên `ScoreResult`). Lượt P1 cũ giữ NULL. Phase 7 thống kê `IssueCode` từ `result_json`. Schema cụ thể Liam duyệt ở PR. — **Reversibility:** costly — Phase 7 (ôn luyện, dashboard) xây trên bảng này; migration idempotent theo pattern `ensure_schema` hiện có.
- **D-11:** **Lượt tốt nhất = `overall` cao nhất, hoà thì lấy lượt sau.** Chấm màu danh sách câu = `scoreLevel(best.overall)`; câu chỉ có lượt P1 chưa điểm giữ chấm xám "đã tập" (D-08 P2). Bấm chip lượt cũ trong `AttemptStrip` → hiện `ScoreResult` đã lưu của lượt đó; nút `M` chỉ dùng được khi blob còn trong phiên (D-07 P2). `R` thử lại hiển thị "Lượt N" và giữ nhãn "tốt nhất" (FBK-06).

#### Rule engine và gợi ý
- **D-12:** **Thêm cổng chắc chắn ngoài ngưỡng lệch của product.md — Claude đề xuất, Liam duyệt ở PR.** Ví dụ hướng: đủ tỉ lệ frame hữu thanh mỗi bên trong từ/câu; `STRESS_MISMATCH` chỉ khi từ nổi nhất của bản gốc vượt từ thứ hai một biên δ; `FINAL_CONTOUR` cần |refSlope| đủ lớn và đủ frame hữu thanh trong 300 ms cuối hai bên; `FLAT_PITCH` bỏ qua khi chính bản gốc phẳng. Mọi ngưỡng nằm trong **một file ngưỡng có version**, giá trị ghi vào `versions.thresholds`. Không chắc → không báo.
- **D-13:** **Ngưỡng ban đầu:** giữ nguyên product.md §3 Lớp C, riêng `PITCH_DEVIATION` = **3 semitone** (đầu trên của khoảng 2–3, ưu tiên precision). Phase 4 chỉnh qua eval.
- **D-14:** **Chọn tip: ưu tiên cố định, mỗi mã tối đa 1 tip, tối đa 3 tip.** Thứ tự `STRESS_MISMATCH > FINAL_CONTOUR > EXTRA_PAUSE > PITCH_DEVIATION > FLAT_PITCH`; cùng mã lấy issue lệch nhiều nhất. `issues` vẫn chứa đủ mọi issue (cho eval, thống kê). Mỗi tip có `issueRef` hợp lệ, `source: 'template'`.
- **D-15:** **Không có issue → câu nhận xét theo `scoreLevel(overall)`, không phải tip** (contract buộc tip trỏ issue): ≥ 80 → khen ngắn theo trạng thái 5 của thiết kế ("Rất sát bản gốc…"); < 80 → câu trung tính ("Chưa thấy lỗi cụ thể nào chắc chắn; nghe lại bản gốc rồi thử lại"). Không khen khi điểm thấp. Sinh phía client từ `ScoreResult`, `tips` rỗng.

### Claude's Discretion
- Tham số MFCC/DTW (số hệ số, cửa sổ, ràng buộc band), cách cắt lặng hai đầu bản ghi trước khi căn, độ đo chất lượng căn.
- F0 người học: hai lượt (ước lượng khoảng pitch theo người rồi trích lại) hay giữ `pitch_floor=75, pitch_ceiling=500` hiện có; lọc lỗi quãng tám, nội suy, làm mượt (PRO-01) — miễn bản gốc và người học xử lý cùng một cách.
- Số điểm resample contour mỗi từ, cách tính `wordBounds`, `stress[]`, `pauses[]` cho `Prosody`.
- Văn phong template tiếng Việt cho 5 mã (bám ví dụ product.md và thiết kế S3-S4), dạng `IntonationChart` bằng Recharts theo `docs/design/components.md`.
- Vị trí `scoreLevel()` (`packages/contracts` hoặc `apps/web/lib`, theo `docs/design/tokens.md`).
- Endpoint đọc lại lượt cũ (ví dụ `GET …/attempts/{n}`) và mở rộng `LessonProgress` với điểm tốt nhất — đi kèm checkpoint contract nếu đổi shape.

### Deferred Ideas (OUT OF SCOPE)
- **Nợ Phase 2 — chạy riêng trước khi Plan Phase 3:** `/gsd-code-review 02 --fix` cho 17 finding open (8 warning, `02-REVIEW-DISPOSITION.md`). Ba điểm chờ Liam chốt khi tiện: `EXTEND_MAX_MS = 3000`; WR-04 (`live_video` thay `invalid_range`); WR-05 (trần độ dài đoạn phía server).
- Trạng thái "Bản gốc không đủ rõ — chỉ chấm ngữ điệu" và tô màu chip từ theo điểm âm — Phase 5.
- Rhythm có tính phạt ngắt nghỉ, trọng số điểm tổng khác TB đều — xem lại khi hiệu chỉnh Phase 8.
- Chế độ chỉ ngữ điệu (`mode: intonationOnly`) — Phase 7 (REV-04).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRO-01 | F0 ~10 ms bằng parselmouth, lọc lỗi quãng tám, giới hạn khoảng pitch theo người, semitone so với median, nội suy, làm mượt, căn theo từ | Pattern 1 (F0 hai lượt Hirst & De Looze, bộ lọc quãng tám 6 st, smooth, nội suy khe ≤ 120 ms); Pattern 2 (căn từ qua DTW) |
| PRO-02 | 3 chỉ số + prominence từng từ theo công thức product.md §3 | Pattern 3 (speed theo thời gian có tiếng, pitchRange, melodyMatch D-05, prominence 0.4/0.4/0.2); số đo prototype |
| PRO-03 | Bản gốc tự so ≈ 100%; câu sai hẳn điểm thấp | Self = 1.00 (20/20 câu, không issue) khi **cùng một hàm trim hai phía** (Pitfall 1); câu sai: 0.40–0.78 theo công thức D-04 — **khoảng trống cần Liam quyết (Open Question 1)** |
| PRO-04 | ≤ 3 s, chỉ xử lý audio người học | Đo: normalize 40–80 ms + feature người học ~25 ms + DTW 15–45 ms ⇒ < 0.3 s; feature bản gốc cache/bù lười ≈ 30 ms |
| RUL-01 | Rule engine 5 mã, ngưỡng product.md, không chắc thì không báo | Bảng ngưỡng đề xuất + cổng chắc chắn (D-12) đã đo FP/recall trên prototype; Pattern 4 |
| RUL-02 | 2–3 tip template tiếng Việt, mỗi tip một `issueRef`; không lỗi → khen | Pattern 5 (chọn tip D-14, template + quy ước `*từ*`), D-15 sinh phía client |
| FBK-01 | `ScoreHero` + 3 chỉ số | `scoreLevel()` (Pattern 8), dữ liệu từ `ScoreResult.scores` + `prosody.*` |
| FBK-02 | `IntonationChart` 2 contour + baseline + thanh trọng âm + dấu ‖ | Pattern 6 (Recharts 3.10.1, `connectNulls=false`, `ReferenceLine`/`ReferenceArea`) |
| FBK-03 | `TipList`, hover tip → highlight từ | State UI cục bộ `hoveredWord` (không vào machine); `issues[issueRef].wordIndex` |
| FBK-04 | Nghe O/M/B | Đã có từ P1 (`playerMachine`, `ResultActionBar`); chỉ cần giữ nguyên khi `scoring` đổi output |
| FBK-05 | 6 trạng thái vùng câu; màu qua `scoreLevel()` | Pattern 7 (machine `scoring` trả `ScoreResult`, rẽ `no_speech`); panel kết quả mới trong `SentenceStatePanel` |
| FBK-06 | `R` giữ lượt tốt nhất + "Lượt N" | Pattern 9 (SQL best attempt, danh sách lượt cho `AttemptStrip`); Open Question 3, 4 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Từ `./CLAUDE.md` và `./.claude/CLAUDE.md` (coi như khoá, ngang CONTEXT.md):
- Không tự đổi contract, schema DB, ngưỡng chấm hay model; cần đổi → dừng và đề xuất. **Hệ quả:** `no_speech` trong `ApiErrorCode`, migration SQLite v2, mọi shape bổ sung (Open Question 3), file ngưỡng và giá trị `versions.*` đều qua checkpoint của Liam.
- Chấm **luôn so với audio gốc**; precision trước recall; không dùng LLM đa phương thức để chấm; LLM (Phase 8) chỉ nhận JSON `issues`. Ở P2 tip là template, `source: 'template'`.
- **Tính sẵn toàn bộ feature của bản gốc khi tạo bài**; lượt chấm chỉ xử lý audio người học (≤ 3 s). Tính bù lười (D-03) chỉ là đường lùi cho bài cũ.
- App chạy được khi thiếu API key — Phase 3 không dùng key nào.
- Không commit audio eval, nhãn thô, `.env`. Test **không được dựa vào audio thật** trong repo → dùng tín hiệu tổng hợp (đã kiểm chứng khả thi, Validation Architecture).
- UI bám `docs/design/`; không thêm màn/component ngoài thiết kế; nút là chính, phím tắt phụ; màu điểm qua `scoreLevel()` (đỏ < 60, vàng 60–79, xanh ≥ 80); teal = Bản gốc, cam = Bạn.
- Code style: TS strict không `any`, Zod ở mọi ranh giới I/O; Python type hints + ruff + pytest, **hàm audio thuần (array in → array out)**, I/O ở rìa (router/pipeline).
- Mỗi PR nhỏ, review tại ranh giới (schema, state machine, output pipeline); quyết định mới/lệch product.md → ADR `docs/decisions/NNNN-<slug>.md` trong cùng PR (ADR tiếp theo là 0006).
- Từ P3 trở đi mọi thay đổi model/ngưỡng/rule phải chạy `make eval` — nhưng `make eval` còn là stub tới Phase 4 (`Makefile`: `echo "make eval: stub — Phase 4 (EVL-02)…"`), nên ở P2 ghi rõ "chưa có eval" trong PR; không bịa bảng metric.
- Cập nhật mục "Lệnh" của CLAUDE.md nếu thêm lệnh Makefile (ví dụ `make smoke-score`).
- Mọi sửa file đi qua lệnh GSD (executor dưới `/gsd-execute-phase`).

## Summary

Phase 3 không cần thư viện Python mới: parselmouth (F0 và MFCC của Praat), numpy, scipy đã có trong `pyproject.toml` `[VERIFIED: services/audio/pyproject.toml]` (`"praat-parselmouth>=0.4.7"`, `"numpy>=2.4"`, `"scipy>=1.17.1"`). Tôi đã dựng prototype Lớp B + Lớp C hoàn chỉnh và chạy trên hai bài thật trong `~/shadowenglab-data` (46 + 43 câu; dùng 20 câu dài 3–8 s) với nhiễu loạn tổng hợp (đổi giới tính/formant bằng Praat, nhiễu hồng/trắng, co giãn thời gian, chèn ngắt, ép phẳng pitch, sửa pitch một từ, đảo lên/xuống cuối câu, câu khác hẳn, nhiễu trắng). Kết quả cho thấy thiết kế D-01 (DTW trên MFCC, không model) **khả thi và rất rẻ**: toàn bộ phần chấm sau khi có feature bản gốc mất 24 ms (trung vị) đến 47 ms (tối đa) mỗi cặp; ffmpeg chuẩn hoá webm mất 40–80 ms; vậy ngân sách 3 s dư hơn 10 lần `[VERIFIED: local prototype run]`.

Bốn phát hiện làm đổi cách lập kế hoạch (chi tiết ở Pitfalls/Open Questions): (1) **"Bản gốc tự so ≈ 100%" chỉ đạt chính xác 1.00 khi bản gốc và bản ghi đi qua cùng một hàm cắt lặng/trích feature**; nếu cắt bản gốc theo mốc Whisper còn người học cắt theo năng lượng, điểm tự so tụt còn 0.94–0.99 và sinh issue giả. (2) **Cắt lặng bằng `vad._voiced_mask` (ngưỡng = phân vị 10 + 12 dB) không dùng được cho cửa sổ bản gốc** vì cửa sổ gần như không có đoạn lặng: có câu chỉ 7% frame được coi là "có tiếng". Cần hàm cắt riêng có kiểm tra dải động. (3) **Công thức D-04 (trung bình đều) cho câu đọc sai hẳn điểm 0.40–0.78 (trung vị 0.58)**: 6/20 câu sai vẫn ≥ 0.65 vì `speed` và `pitchRange` là chỉ số "thang đo" không kiểm tra hình dạng giai điệu — tiêu chí thành công #2 cần Liam quyết (Open Question 1). (4) **Chất lượng căn đo được tách tốt câu đúng và câu sai** (chi phí chuẩn hoá: câu đúng bị nhiễu loạn p95 = 1.07; câu sai min 1.10, trung vị 1.18; thang 0–1.41) nên ngưỡng "căn kém" đề xuất 1.10 hoạt động trên dữ liệu tổng hợp, **nhưng chưa thử với giọng người Việt thật**.

Về phía web: Recharts 3.10.1 tương thích React 18.3 (peer `^18.0.0`), hỗ trợ đúng những thứ `IntonationChart` cần (`connectNulls=false` để ngắt đường ở frame vô thanh, `ReferenceLine`, `ReferenceArea`, tick tuỳ biến) `[CITED: Context7 /recharts/recharts]`. Không cần đổi hình dạng machine XState: chỉ đổi output của actor `uploadAttempt` từ `AttemptAck` sang `ScoreResult` và rẽ nhánh `no_speech` theo mã lỗi. Phần việc đòi hỏi checkpoint của Liam: thêm `no_speech`, migration SQLite v2, và (khuyến nghị) một endpoint danh sách lượt + trường `bestOverall` để vẽ chấm màu/`AttemptStrip`.

**Primary recommendation:** Dựng `audio_service/scoring/` gồm các hàm thuần (`prosody` → `align` → `metrics` → `rules` → `tips`) dùng **một hàm chuẩn bị feature duy nhất cho cả bản gốc và người học**, cache feature bản gốc ở **file kề bên** `seg/NNNN.prosody.npz` (không ghi đè `seg/NNNN.npz`, Pitfall 5), và gate "căn kém" bằng chi phí DTW chuẩn hoá ≤ 1.10 + tỉ lệ độ dài trong [0.5, 2]. Wave 0 là PR contract/DB (`no_speech`, migration v2, shape lượt) để Liam duyệt trước khi viết rule.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Chuẩn hoá bản ghi, chấm ngữ điệu (F0, DTW, chỉ số, rule) | API / Backend (FastAPI, hàm thuần) | — | Cần parselmouth/scipy; D-09 chấm trong cùng request upload |
| Feature bản gốc (F0 hai lượt, năng lượng dB, MFCC) | API / Backend (pipeline `analyzing` + bù lười) | Database / Storage (`seg/NNNN.prosody.npz`) | CLAUDE.md: tính sẵn khi tạo bài; D-03 bù lười cho bài cũ |
| Lưu điểm, `result_json`, lượt tốt nhất | Database / Storage (SQLite `attempts` v2) | API / Backend | D-10/D-11; Phase 7 thống kê từ đây |
| Văn bản tip template (tiếng Việt) | API / Backend (`tips.py`) | — | Contract buộc `Tip.issueRef` trỏ `issues`; sinh cùng lúc với issues để nhất quán chỉ số |
| Lời khen / câu trung tính khi không có issue (D-15) | Browser / Client | — | Hợp đồng nói rõ sinh phía client từ `ScoreResult`, `tips` rỗng |
| `scoreLevel()` và màu điểm | Browser / Client (`apps/web/lib`) | — | Chỉ UI dùng màu; Python không cần (Open Question 7) |
| ScoreHero, TipList, hover highlight | Browser / Client | — | State hover cục bộ, không đi vào machine |
| IntonationChart | Browser / Client (Recharts) | — | Nhận `Contour` đã căn; chỉ dựng dữ liệu hiển thị |
| Trạng thái `scoring` → kết quả / `no_speech` / lỗi | Browser / Client (XState) | API / Backend | Machine chờ chính request chấm (D-09) |
| Đọc lại lượt cũ, danh sách lượt, điểm tốt nhất | API / Backend (SQLite) | Browser (TanStack Query cache) | D-11; chấm màu danh sách câu cần điểm tốt nhất toàn bài trong một truy vấn |

## Standard Stack

### Core (đã có, không thêm gì phía Python)
| Library | Version | Purpose | Ghi chú |
|---------|---------|---------|---------|
| praat-parselmouth | 0.4.7 | F0 (`to_pitch_ac`) và MFCC (`to_mfcc`) | `[VERIFIED: local prototype run]` import được trong venv; `to_pitch_ac(... pitch_ceiling=600.0 mặc định ...)`, `to_mfcc(number_of_coefficients=12, window_length=0.015, time_step=0.005 ...)` — hàm `extract_f0` hiện có đặt `time_step=0.01, pitch_floor=75.0, pitch_ceiling=500.0` `[VERIFIED: services/audio/src/audio_service/lesson/features.py:28]`: `sound.to_pitch_ac(time_step=0.01, pitch_floor=75.0, pitch_ceiling=500.0)` |
| numpy | 2.4.6 | mảng, Pearson (`np.corrcoef`), DTW vector hoá | `[VERIFIED: venv]` |
| scipy | 1.17.1 | `scipy.ndimage.median_filter/uniform_filter1d`, `scipy.stats.theilslopes` (độ dốc cuối câu bền vững) | `[VERIFIED: venv]` |
| FastAPI / pydantic | 0.142.2 / 2.13.5 | endpoint chấm, `ScoreResult` | `[VERIFIED: 02-RESEARCH.md, uv.lock]` |
| Recharts | **3.10.1** (mới) | `IntonationChart` | `[VERIFIED: npm view recharts version]` = `3.10.1`, `time.modified = 2026-10-03`; peer: `react ^16.8 \|\| ^17 \|\| ^18 \|\| ^19`, `react-is` cùng dải, `react-dom` — khớp React 18.3.1 hiện có |
| xstate / @xstate/react | 5.33.2 / 6.1.0 | machine `scoring` | `[VERIFIED: apps/web/package.json]` giữ nguyên |
| @tanstack/react-query | 5.104.1 | đọc lượt cũ, danh sách lượt, cache `ScoreResult` | `[VERIFIED: apps/web/package.json]` giữ nguyên |

### Supporting
| Library | Version | Purpose | Khi dùng |
|---------|---------|---------|----------|
| react-is | 18.3.1 (ghim) | peer dependency của Recharts 3 | Cài cùng Recharts; **cờ SUS** từ cổng legitimacy (xem Audit) |
| sqlite3 (stdlib) 3.51.0 | — | migration + truy vấn lượt tốt nhất (`ROW_NUMBER() OVER`) | `[VERIFIED: local prototype run]` ALTER ADD COLUMN có CHECK + window function chạy được |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DTW tự viết ~40 dòng numpy | librosa / dtw-python / fastdtw | librosa không có trong dự án, kéo numba (numba 0.68.0 chỉ có vì mlx-whisper, **không phải dependency khai báo**, có độ trễ JIT lần đầu) `[VERIFIED: uv tree --invert numba]`; các gói DTW nhỏ chưa qua cổng legitimacy và không cần: bản tự viết với tập bước {(1,1),(1,2),(2,1)} vector hoá theo hàng chạy 15–45 ms |
| MFCC Praat (parselmouth) | MFCC tự cài bằng FFT/mel | Bản Praat có sẵn, đo 5 ms/6 s; log-mel tự cài cho kết quả căn tương đương (sai số đường đi 1–2 khung) nhưng thêm code phải bảo trì |
| Recharts (khoá stack) | SVG thuần như `S3-S4-phong-tap.html` | Thiết kế là `<svg>` polyline đơn giản; Recharts đã là stack khoá (CLAUDE.md) và cho trục/ReferenceArea miễn phí. Giữ Recharts |

**Installation:**
```bash
# Python: không có package mới
pnpm --filter @shadowenglab/web add recharts@3.10.1 react-is@18.3.1
```

**Version verification:** `npm view recharts version` → `3.10.1`; `npm view recharts@3.10.1 peerDependencies` → react/react-is/react-dom đều chấp nhận ^18 `[VERIFIED: npm registry]`. `npm view react-is@18 version` → `18.3.1`.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| recharts | npm | nhiều năm (3.10.1 phát hành 2026-07-25) | 71.3M/tuần | github.com/recharts/recharts | OK | Approved (đã là stack khoá trong CLAUDE.md và Context7 xác nhận API) |
| react-is | npm | nhiều năm (lõi React) | 452.7M/tuần | github.com/facebook/react (seam báo `github.com/react/react`) | **SUS** (lý do duy nhất: `too-new` — bản mới nhất phát hành 2026-09-09) | Flagged — planner thêm `checkpoint:human-verify` trước khi cài; **ghim `18.3.1`** (bản cũ, khớp `react@18.3.1`), không dùng bản mới nhất |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** `react-is` — chỉ vì bản mới nhất quá mới; tên gói là gói lõi React nổi tiếng. Planner chèn `checkpoint:human-verify` (cùng kiểu cổng 02-02 của Phase 2) rồi mới `pnpm add`. Kiểm tra `postinstall`: seam báo `postinstall: null` cho cả hai gói. Các dependency bắc cầu của Recharts (immer, reselect, es-toolkit, react-redux, @reduxjs/toolkit, victory-vendor…) chưa được kiểm từng cái `[ASSUMED]` — cổng cài đặt nên chạy `pnpm install --frozen-lockfile` sau khi lockfile được Liam duyệt, như Phase 2.

*Không có package Python mới; không có gói nào khám phá qua WebSearch được đưa vào khuyến nghị.*

## Architecture Patterns

### System Architecture Diagram

```
Browser (S3)                               FastAPI (127.0.0.1:8000)                               Đĩa / SQLite
-------------                              ------------------------                               -------------
MediaRecorder blob ─POST multipart────────▶ routers/attempts.create_attempt
(machine: recording→scoring)                 │  _receive (≤10 MB, magic bytes) ── ffmpeg ─▶ WAV 16k mono   (40–80 ms)
                                             │  durationMs > 60 s ─▶ 422 recording_too_long
                                             │  vad.is_voiced? ──không──▶ 422 ApiError{code:"no_speech"}  (ghi dòng voiced=0)
                                             ▼ có tiếng
                                      scoring.pipeline.score_attempt(lesson, index, user_audio)
                                             │ 1. ref features  ◀── seg/NNNN.prosody.npz (cache)  ──thiếu/ sai window/version──▶
                                             │      bù lười: đọc lát vocals.wav (sf.read start/stop, 5 ms) → prepare_features() → ghi sidecar
                                             │ 2. user features = prepare_features(user_audio)   ← CÙNG HÀM với bản gốc
                                             │ 3. align(ref_mfcc, user_mfcc) → path, cost, ratio  (DTW 15–45 ms)
                                             │      ratio ∉ [0.5, 2] hoặc cost > 1.10 ─▶ align_ok = False (D-02)
                                             │ 4. metrics: speed · pitchRange · melodyMatch · prominence · pauses · contour
                                             │ 5. rules (thresholds.py, version): 5 mã; align_ok=False ─▶ chỉ FLAT_PITCH, FINAL_CONTOUR
                                             │ 6. tips.select (≤3, mỗi mã ≤1) + template tiếng Việt
                                             ▼
                                      db.insert_scored_attempt(...)  (một giao dịch: cấp số lượt → ghi overall/intonation/rhythm/sound/result_json)
                                             │
◀──────────────── 201 ScoreResult ──────────┘                                                    ┌────────────────────────────────┐
machine: scoring.onDone → reviewing (ScoreResult trong context)                                  │ attempts (user_version 2):     │
 ├─ ScoreHero / TipList / IntonationChart (state UI hover)                                       │  + overall,intonation,rhythm,  │
 ├─ queryClient.setQueryData(attempt result) + invalidate progress                               │    sound REAL, result_json TEXT│
 └─ AttemptStrip: GET …/attempts (danh sách lượt, tốt nhất) · GET …/attempts/{n} (ScoreResult)   └────────────────────────────────┘
scoring.onError(code=no_speech) → noVoice;  lỗi khác → error (toast + Thử lại, giữ blob)
```

### Recommended Project Structure
```
services/audio/src/audio_service/
├── scoring/                 # CLAUDE.md đã dự kiến thư mục này; hàm THUẦN (array in → array out)
│   ├── features.py          # prepare_features(audio16k) -> ProsodyFeatures  (F0 hai lượt, semitone, năng lượng dB, MFCC c1–12, trim)
│   ├── align.py             # align(ref_mfcc, user_mfcc) -> Alignment(path, cost, ratio, ok)   [giao diện thay được, D-01]
│   ├── metrics.py           # speed, pitch_range, melody_match, prominence, pauses, contour resample
│   ├── thresholds.py        # MỘT file ngưỡng có version (D-12) -> versions.thresholds
│   ├── tips.py              # chọn tip (D-14) + template tiếng Việt
│   ├── ref_cache.py         # I/O: đọc/ghi seg/NNNN.prosody.npz, bù lười từ vocals.wav (rìa I/O)
│   └── pipeline.py          # score_attempt(...) -> ScoreResult  (ghép; I/O chỉ ở ref_cache)
├── rules/                   # (tuỳ chọn) rules.py tách riêng theo cấu trúc CLAUDE.md: 5 hàm rule thuần
├── routers/attempts.py      # create_attempt trả ScoreResult; GET danh sách / chi tiết lượt (đề xuất)
└── db.py                    # migration v2 + insert_scored_attempt + best_attempts + list_attempts
apps/web/
├── lib/scoreLevel.ts        # scoreLevel(score01|null) làm tròn % trước khi so ngưỡng (Pitfall 9)
├── lib/chartData.ts         # buildChartRows(prosody) -> {rows, ticks, pauses}  (thuần, test node)
├── lib/tipMarkup.ts         # tách "*từ*" thành segments (không dangerouslySetInnerHTML)
├── lib/player/playerMachine.ts   # actor uploadAttempt -> ScoreResult; rẽ no_speech
└── components/{ScoreHero,IntonationChart,TipList,ResultPanel}.tsx
```

### Pattern 1: Một hàm chuẩn bị feature cho cả hai phía (PRO-01)
**What:** `prepare_features(audio16k)` làm tuần tự: (a) cắt lặng hai đầu bằng mặt nạ có kiểm tra dải động, (b) F0 hai lượt, (c) semitone theo median người nói + lọc quãng tám, (d) nội suy khe ≤ 120 ms + làm mượt, (e) năng lượng dB mỗi 10 ms, (f) MFCC c1–c12. Bản gốc (cửa sổ vocals) và người học (WAV chuẩn hoá) đi qua **đúng hàm này** — đó là điều kiện để tự so = 1.00.
**When to use:** mọi nơi tạo feature (bước `analyzing`, bù lười, lượt chấm).
**Chi tiết đã kiểm chứng `[VERIFIED: local prototype run]`:**
- Mặt nạ cắt lặng: `thr = peak − 30 dB` khi `peak(p95) − noise(p10) < 20 dB` (không có đoạn lặng thật); ngược lại `thr = max(noise + 12, −60)`; margin 5 frame mỗi đầu. Đây là bản sửa của `vad._voiced_mask` (Pitfall 2).
- F0 hai lượt theo Hirst & De Looze: lượt 1 floor/ceiling rộng 60–700 Hz → q1, q3 của F0 hữu thanh → lượt 2 `floor = 0.75·q1`, `ceiling = 2·q3` `[CITED: Hirst, Speech Prosody ch.2 (ResearchGate): "floor = q1·0.75, ceiling = q3·2", lượt đầu 60–700 Hz]`. Prototype dùng `min(800, 2·q3)` và `max(50, 0.75·q1)` làm chặn an toàn.
- Semitone: `12·log2(f0/median)`; bỏ frame lệch > 6 st so với median trượt 9 frame hữu thanh (bắt lỗi quãng tám ±12 st).
- Nội suy tuyến tính qua khe vô thanh ≤ 12 frame (120 ms); khe dài hơn để `NaN`/`null`. Làm mượt: median 5 rồi trung bình trượt 3 (`scipy.ndimage`).
- MFCC: `Sound.to_mfcc(number_of_coefficients=12, window_length=0.025, time_step=0.01)` → mảng `(frames, 13)` với **cột 0 là c0** (tương quan 0.78 với năng lượng) nên bỏ cột 0 `[VERIFIED: local prototype run]`; chuẩn hoá trung bình/độ lệch chuẩn **chỉ trên frame có tiếng** của chính bản ghi.
- Lưới thời gian: frame i của Praat Pitch nằm ở `0.02 + 0.01·i` s, MFCC ở `0.025 + 0.01·i` s, `frame_energy` ở `0.01·i` s (cửa sổ đặt giữa khung) `[VERIFIED: local prototype run]` — dựng lưới chung hoặc chấp nhận lệch ≤ 25 ms giống nhau ở hai phía.

### Pattern 2: `align` — DTW với tập bước {(1,1),(1,2),(2,1)} và biên nới (D-01, D-02)
**What:** DTW vector hoá theo hàng (mỗi bước chỉ phụ thuộc hàng trước ⇒ không cần vòng lặp trong hàng), điểm đầu/cuối nới `slack = 30` khung (300 ms) trên trục người học, chi phí chuẩn hoá theo độ dài đường đi, khoảng cách Euclid / √d trên MFCC c1–c12 đã chuẩn hoá.
**Số đo `[VERIFIED: local prototype run]`:** sai số đường đi trung bình so với sự thật (nhiễu loạn giữ nguyên thời gian): đổi giới tính ≈ 1.5–2.5 khung (10 ms/khung), co giãn ×0.85/×1.25 ≈ 1–1.5 khung, nhiễu hồng/trắng SNR 25/15/10 dB ≈ 0.7/1.0/1.4–2.2 khung (với cách cắt lặng thích nghi của Pattern 1). DTW **không** cắt đầu cuối thì nhạy với nhiễu: cắt bằng `vad._voiced_mask` hay ngưỡng tuyệt đối làm sai số nhảy lên 16–31 khung ở SNR ≤ 15 dB.
**Giao diện (để Phase 5 thay):**
```python
@dataclass(frozen=True)
class Alignment:
    path: np.ndarray        # (K, 2) int: (ref_frame, user_frame)
    cost: float             # chi phí / bước, thang 0..~1.41
    ratio: float            # (user_frames_matched / ref_frames)
    ok: bool                # cost <= thresholds.ALIGN_COST_MAX and 0.5 <= ratio <= 2.0
def align(ref_mfcc: np.ndarray, user_mfcc: np.ndarray) -> Alignment: ...
```
Gate `ok` đo được: câu đúng bị nhiễu loạn có cost p95 = 1.07 (giữa 0.39–1.37), câu **sai** (20 cặp) min 1.10, trung vị 1.18 → ngưỡng đề xuất **1.10**; ở dữ liệu benign 6/100 cặp (khắc nghiệt: giới tính/co giãn) bị coi là "căn kém" `[VERIFIED: local prototype run]`. Tập bước giới hạn độ dốc cục bộ trong [0.5, 2] nên người học nói chậm/nhanh hơn ×2 hoặc ngắn hơn một nửa → **không có đường đi** (cost = INF): coi là căn kém (kiểm `ratio` **trước** khi dựng ma trận, Pitfall 6).

### Pattern 3: 3 chỉ số, prominence, ngắt nghỉ (PRO-02)
- **speed** = `min(r, 1/r)` với `r = speech_user / speech_ref`, `speech` = độ dài đoạn đã căn trừ các đoạn lặng ≥ 250 ms; "lặng" xác định bằng mặt nạ **tương đối** `db > p95 − 35 dB` (bất biến theo mức tín hiệu; mặt nạ nhiễu-thích-nghi cho kết quả không ổn định, đo được `speed` 0.13–0.55 sai) `[VERIFIED: local prototype run]`. Đo: tự so 1.00, ×0.85 → 0.87–0.89, ×1.25 → 0.80, giới tính 0.90–0.96.
- **pitchRange** = `min(r, 1/r)` với `r = std(st_user) / std(st_ref)` (trên đoạn đã căn của người học).
- **melodyMatch** = `max(0, pearson)` trên frame hữu thanh cả hai bên sau căn (D-05); `< 10` frame chung → 0 (đề xuất, ghi vào ngưỡng).
- **prominence** từ `Word` = `0.4·z(F0max) + 0.4·z(intensityMax) + 0.2·z(duration)` với z-score **trong câu** (product.md); từ có `< 3` frame hữu thanh → `NaN` (không xếp hạng). Chỉ đáng tin với câu ≥ 5 từ.
- **EXTRA_PAUSE**: lặng của người học ≥ 250 ms (mặt nạ tương đối) nằm giữa đoạn đã căn (cách hai đầu > 3 khung); ánh xạ ngược sang trục bản gốc bằng `np.argmin(|ju − i|)`; ref phải **không có** run lặng ≥ 100 ms trong `[ri−10, rj+10]`; `afterWord` = từ có đuôi gần nhất vị trí đó (Pitfall 7: lệch một từ ở 1/3 ca thử).

### Pattern 4: Rule engine với cổng chắc chắn (RUL-01, D-12, D-13)
Bộ ngưỡng đề xuất — chạy trên 20 câu × (5 nhiễu loạn benign) + 4 loại lỗi tiêm `[VERIFIED: local prototype run]`:

| Khoá ngưỡng | Giá trị đề xuất | Căn cứ |
|---|---|---|
| `ALIGN_COST_MAX` | 1.10 | câu sai min 1.10, benign p95 1.07 |
| `ALIGN_RATIO` | [0.5, 2.0] | giới hạn tập bước DTW |
| `PITCH_DEVIATION_ST` | 3.0 | D-13 |
| `PD_MIN_FRAMES` / `PD_VOICED_RATIO` | 10 / 0.5 | cổng D-12 (đủ frame hữu thanh chung) |
| `PD_USE_MEDIAN` + trừ offset câu | median của hiệu `st_user − st_ref − median_toàn_câu` | giảm FP |
| `PD_SIGN_CONSISTENCY` | ≥ 0.8 số frame cùng dấu | giảm FP |
| `PAUSE_USER_MS` / `PAUSE_REF_MS` | 250 / 100 | product.md |
| `FLAT_RATIO` | 0.6 | product.md (`pitchRange < 0.6`) |
| `FLAT_REF_MIN_STD_ST` | 2.0 và `std_user < std_ref` | D-12 "bỏ qua khi bản gốc phẳng" |
| `FINAL_WINDOW_FRAMES` | 30 (300 ms), ≥ 15 frame hữu thanh mỗi bên | product.md + D-12 |
| `FINAL_SLOPE_ABS` | 6 ≤ \|slope\| ≤ 30 st/s, hai bên ngược dấu, ước lượng Theil–Sen | cổng đo được (Pitfall 4) |
| `STRESS_MARGIN` | 0.5 (z) cho cả hai bên | Pitfall 8: recall rất thấp |

Hiệu quả cổng (100 cặp benign; 20 câu mỗi loại lỗi tiêm): `PITCH_DEVIATION` FP 22 → **6**, `FINAL_CONTOUR` FP 10 → **2**, `EXTRA_PAUSE` FP 2; recall giữ: `FLAT_PITCH` 19/20, `EXTRA_PAUSE` 20/20, `PITCH_DEVIATION` (+4 st một từ) 11/20, `FINAL_CONTOUR` (đảo lên giọng cuối câu) 5/20, `STRESS_MISMATCH` 1/20. Tự so: 0 issue, overall 1.00 ở 20/20 câu. Cổng phải áp **trước** khi chọn tip (D-14); `issues` vẫn chứa mọi issue đã qua cổng.

### Pattern 5: Chọn tip và template tiếng Việt (RUL-02, D-14, D-15)
- Chọn: sắp issue theo ưu tiên `STRESS_MISMATCH > FINAL_CONTOUR > EXTRA_PAUSE > PITCH_DEVIATION > FLAT_PITCH`, mỗi mã lấy issue "lệch nhiều nhất" (STRESS: biên lớn nhất; PD: \|meanDiffSt\| lớn nhất; EXTRA_PAUSE: `userMs` lớn nhất; FINAL: \|userSlope − refSlope\| lớn nhất), tối đa 3. `issueRef` = **chỉ số thật trong mảng `issues` đã sắp ổn định** (giữ thứ tự sinh, không sắp lại sau khi gán `issueRef`).
- Template đề xuất (văn phong để Liam duyệt; bám ví dụ product.md và thiết kế S3-S4). **Quy ước đánh dấu từ: `*từ*`** giống ví dụ product.md ("Nhấn mạnh *Brown*, không phải *Heat*") — client tách chuỗi thành đoạn có gạch chân, tuyệt đối không `dangerouslySetInnerHTML` (từ lấy từ Whisper/ô "Sửa câu" là dữ liệu không tin cậy):
  - `STRESS_MISMATCH`: `Nhấn vào *{refWord}*, không phải *{userWord}*.`
  - `EXTRA_PAUSE`: `Đọc liền qua *{word}*, đừng ngắt ({userMs} ms).`
  - `FINAL_CONTOUR` (refSlope < 0, userSlope > 0): `Xuống giọng ở cuối câu; bạn đang lên giọng.` — ngược lại: `Lên giọng ở cuối câu; bạn đang xuống giọng.`
  - `PITCH_DEVIATION` (meanDiffSt > 0): `Bạn đang đọc cao hơn bản gốc ở *{word}*; hạ giọng xuống.` — âm: `…thấp hơn…; nâng giọng lên.`
  - `FLAT_PITCH`: `Giọng hơi phẳng; lên xuống rõ hơn theo bản gốc.`
- D-15 (không issue): khen/nhận xét **sinh ở client** theo `scoreLevel(overall)`; `tips = []`.

### Pattern 6: `IntonationChart` bằng Recharts 3 (FBK-02)
**Dữ liệu:** trục chung = trục thời gian bản gốc, hạ mẫu 20 ms (mỗi điểm = 2 frame) → ~250–400 điểm/câu; làm tròn 0.1 st (payload ≈ 10 KB). `wordBounds[i]` = chỉ số điểm bắt đầu từ i (`round((refWordStart − trim)/0.02)`). `contour.user` lấy theo đường đi (`ju`). `pauses[]` chỉ gồm khe giữa từ có `max(refMs, userMs) ≥ 100`; dấu ‖ vẽ cho issue `EXTRA_PAUSE` tại `wordBounds[afterWord + 1]`.
**Chart:** `LineChart` + `XAxis type="number" dataKey="x" domain={[0, N-1]} ticks={wordBounds} tick={<WordTick/>}`; hai `Line` (`connectNulls={false}` — mặc định, đường **đứt** tại `null` `[CITED: Context7 /recharts/recharts, Curve.tsx getPath]`, `dot={false}`, `isAnimationActive={false}` để test/ảnh tĩnh ổn định), `ReferenceLine y={0} strokeDasharray` (baseline = median từng người), `ReferenceLine x=` cho ‖, `ReferenceArea x1 x2` cho từ đang hover (nền `soft`). Recharts 3 bật `accessibilityLayer` mặc định `[CITED: Recharts 3.0 migration guide]` — chart vẫn cần `<title>`/`aria-label` mô tả (thiết kế có `aria-label` tiếng Việt). Màu: dùng `style={{ stroke: "var(--original)" }}` / `var(--you)` (token đã có trong `apps/web/app/tokens.css`).
**Thanh trọng âm theo từ:** vẽ ngoài `LineChart` (hàng `<div>` căn theo `wordBounds`) hoặc `Bar` trong `ComposedChart`; dùng `prosody.stress[].ref/user` (z-score, có thể âm → chuẩn hoá theo max dương). Chỉ highlight "từ nổi nhất" bằng chữ đậm như thiết kế.
**Kiểm thử:** `apps/web` chạy vitest ở môi trường `node` (không DOM) — kiểm thử **hàm dựng dữ liệu thuần** (`chartData.ts`), không kiểm thử render.

### Pattern 7: Machine XState — chỉ đổi output của `scoring`
Hình dạng machine giữ nguyên (PLY-02, D-09). Thay đổi:
```ts
// apps/web/lib/player/playerMachine.ts (ý tưởng; không import fetch)
uploadAttempt: fromPromise<ScoreResult, UploadInput>(async () => { throw new Error("chưa cung cấp"); }),
// scoring.invoke.onDone: lưu result vào recordings[idx] = { ...rec, status: "scored", attempt: event.output.attempt, result: event.output } -> reviewing
// scoring.invoke.onError: [{ guard: ({event}) => isNoSpeech(event.error), target: "noVoice", actions: markNoVoice },
//                          { target: "error", actions: markFailed }]
// lib/player/errors.ts: isNoSpeech(e: unknown): boolean  // duck-type {error:{code:"no_speech"}} để machine không import api.ts
```
`PlayerRecording.status` đổi `"uploaded"` → `"scored"` (hoặc giữ `"uploaded"` kèm `result`); guard `hasUploaded` đổi tương ứng. **Sửa test** `playerMachine.test.ts` (hiện dùng `AttemptAck`). `PracticeRoom` đang `invalidateQueries(lessonProgress)` khi `scoring → reviewing|noVoice` `[VERIFIED: PracticeRoom.tsx:323-334]` — giữ, thêm `setQueryData` cho `ScoreResult` vừa nhận và invalidate danh sách lượt.
**TanStack Query:** (1) `useAttempts(lessonId, index)` → danh sách lượt cho `AttemptStrip`; (2) `useAttemptResult(lessonId, index, n)` bật khi bấm chip lượt cũ và không có trong `recordings`; (3) `progress` mang `bestOverall` cho `SegmentedProgress`/`TranscriptList`. Khoá mới trong `queryKeys`.

### Pattern 8: `scoreLevel()` làm tròn trước khi so ngưỡng
```ts
// apps/web/lib/scoreLevel.ts — chỗ đặt khuyến nghị (Open Question 7)
export type ScoreLevel = "good" | "ok" | "bad" | "unrated";
export function scoreLevel(score01: number | null): ScoreLevel {
  if (score01 === null) return "unrated";
  const pct = Math.round(score01 * 100); // màu theo SỐ ĐANG HIỂN THỊ (79.6 hiển thị "80" phải xanh)
  return pct >= 80 ? "good" : pct >= 60 ? "ok" : "bad";
}
```
Ngưỡng `[VERIFIED: docs/design/tokens.md:79]` hàm `scoreLevel(score: number | null): 'good' | 'ok' | 'bad' | 'unrated'`; đỏ < 60, vàng 60–79, xanh ≥ 80 (CLAUDE.md).

### Pattern 9: SQLite v2 và lượt tốt nhất (D-10, D-11)
```python
SCHEMA_VERSION = 2  # hiện 1 [VERIFIED: db.py:20]
_V2 = (
    "ALTER TABLE attempts ADD COLUMN overall REAL CHECK (overall IS NULL OR (overall >= 0 AND overall <= 1))",
    "ALTER TABLE attempts ADD COLUMN intonation REAL CHECK (intonation IS NULL OR (intonation >= 0 AND intonation <= 1))",
    "ALTER TABLE attempts ADD COLUMN rhythm REAL CHECK (rhythm IS NULL OR (rhythm >= 0 AND rhythm <= 1))",
    "ALTER TABLE attempts ADD COLUMN sound REAL CHECK (sound IS NULL OR (sound >= 0 AND sound <= 1))",
    "ALTER TABLE attempts ADD COLUMN result_json TEXT",
)
# ensure_schema: user_version 0 -> DDL v1 rồi v2; user_version 1 -> chạy _V2; luôn trong BEGIN IMMEDIATE, kiểm lại user_version
# sau khi giữ khoá (pattern hiện có) — ALTER ADD COLUMN KHÔNG idempotent nên cổng user_version là bắt buộc.
BEST = """
SELECT segment_index, attempt, overall FROM (
  SELECT segment_index, attempt, overall,
         ROW_NUMBER() OVER (PARTITION BY segment_index ORDER BY overall DESC, attempt DESC) AS rn
  FROM attempts WHERE lesson_id = ? AND overall IS NOT NULL) WHERE rn = 1"""
```
`[VERIFIED: local prototype run]` (sqlite 3.51.0): ALTER ADD COLUMN có CHECK hợp lệ; CHECK chặn `overall = 1.5`; truy vấn trên trả lượt 3 khi lượt 2 và 3 hoà 0.78 ("hoà thì lấy lượt sau"); câu chỉ có lượt P1 (NULL) không xuất hiện.
**Thứ tự ghi:** dòng nên được ghi **sau** khi chấm thành công (một `BEGIN IMMEDIATE`: cấp `attempt = MAX+1`, dựng `ScoreResult` với `attempt` đó, `INSERT` kèm điểm và `result_json`), để lỗi giữa chừng không để lại dòng "đã tập" không điểm. Lượt `no_speech` vẫn `INSERT … voiced = 0` (hành vi P1). Xem Open Question 4.

### Anti-Patterns to Avoid
- **Cắt bản gốc theo mốc Whisper nhưng cắt người học theo năng lượng** → điểm tự so 0.94–0.99 + issue giả (Pitfall 1).
- **Dùng `vad._voiced_mask` để cắt/đo ngắt nghỉ** (phân vị 10 + 12 dB): với cửa sổ liên tục không lặng chỉ 7% frame được tính là tiếng (Pitfall 2).
- **Ghi đè `seg/NNNN.npz` từ đường chấm** (D-03 nguyên văn): có thể đè lên file vừa được `extend-end` ghi lại (Pitfall 5).
- **DTW kết thúc cố định cả hai đầu mà không nới biên**: lệch 100–300 ms giữa hai cách cắt kéo cả contour.
- **Dựng ma trận khoảng cách bằng broadcast 3 chiều** `R[:,None,:]-U[None,:,:]` (n·m·d·8 B): 800×6000 khung × 12 hệ số ≈ 460 MB trên máy 8 GB (Pitfall 6).
- **Màu điểm trên số chưa làm tròn** (Pitfall 9).
- **Hiển thị `AttemptAck.voiced`** sau D-09: không còn; "không thu được tiếng" đến qua mã lỗi.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Trích F0 | autocorrelation/YIN tự viết | `parselmouth` `to_pitch_ac` (đã dùng ở `extract_f0`) | Praat đã xử lý ứng viên, chi phí quãng tám, vô/hữu thanh |
| MFCC | FFT + mel + DCT tự viết | `Sound.to_mfcc` (parselmouth) | 5 ms/6 s, bỏ cột c0 |
| Lọc median/trung bình trượt | vòng lặp | `scipy.ndimage.median_filter`, `uniform_filter1d` | đúng biên, nhanh |
| Độ dốc cuối câu | `np.polyfit` | `scipy.stats.theilslopes` | polyfit cho độ dốc ±40–69 st/s vô lý khi F0 cuối nhiễu (đo được); Theil–Sen bền vững + cổng 6–30 st/s |
| Pearson | tự cộng | `np.corrcoef` | — |
| DTW | thư viện DTW / librosa | hàm numpy ~40 dòng (Code Examples) | tránh phụ thuộc mới/numba JIT; đã đo 15–45 ms |
| Biểu đồ | `<svg>` tự dựng trục/tick | Recharts (`ReferenceArea`, tick tuỳ biến) | stack khoá; hover highlight bằng `ReferenceArea` |
| Chọn lượt tốt nhất | sắp xếp phía client trên toàn bộ lượt | SQL `ROW_NUMBER()` (Pattern 9) | một truy vấn cho cả bài |
| Parse markup tip | regex + `dangerouslySetInnerHTML` | hàm tách `*…*` → mảng đoạn → React element | XSS qua từ Whisper/ô "Sửa câu" |

**Key insight:** phần khó của phase này không phải thuật toán mà là **tính đối xứng và độ bền của tiền xử lý** (cắt lặng, mặt nạ, lưới thời gian) — mọi con số đã đo cho thấy lỗi nằm ở đó, không ở DTW hay Pearson.

## Common Pitfalls

### Pitfall 1: Tự so không ra 100% vì tiền xử lý bất đối xứng
**What goes wrong:** bản gốc cắt theo mốc từ Whisper ± 3 frame, người học cắt theo năng lượng → hai chuỗi lệch 14–30 khung ở biên; tự so cho 0.94–0.99 và một `PITCH_DEVIATION` giả 7.2 st trên từ đầu.
**Why:** mốc Whisper kéo dài quá năng lượng thật; DTW với biên cố định kéo lệch.
**How to avoid:** cùng một `prepare_features` hai phía (Pattern 1) + biên DTW nới 300 ms (Pattern 2). Khi đó tự so = 1.00 ở 20/20 câu, 0 issue, bất biến theo mức tín hiệu (×0.1) và đệm lặng 0.6/0.5 s `[VERIFIED: local prototype run]`.
**Warning signs:** `speed`/`pitchRange` ≠ 1 khi tự so; `cost` tự so > 0.1.

### Pitfall 2: Mặt nạ "có tiếng" của VAD không dùng được cho bản gốc
**What goes wrong:** `vad._voiced_mask` đặt ngưỡng = max(−50 dB, p10 + 12 dB) `[VERIFIED: services/audio/src/audio_service/lesson/vad.py:18-20]` (`FLOOR_DB = -50.0`, `NOISE_PERCENTILE = 10.0`, `MARGIN_DB = 12.0`). Cửa sổ bản gốc (đệm 150 ms) không có đoạn lặng nên p10 chính là mức tiếng nói: seg 4 chỉ 7% frame "có tiếng" (p10 = −30.8 dB), seg 7 32%.
**How to avoid:** hàm riêng: nếu `p95 − p10 < 20 dB` thì `thr = p95 − 30`, ngược lại `max(p10 + 12, −60)`. Giữ `vad.is_voiced` nguyên cho việc "có tiếng hay không" (REC-03).

### Pitfall 3: Chỉ số "thang đo" làm điểm câu sai bị thổi phồng
**What goes wrong:** `speed` và `pitchRange` so độ dài/biên độ chứ không so hình dạng; câu hoàn toàn khác vẫn có thể cho 0.9–1.0 ở hai chỉ số này.
**Số đo (20 câu sai, `ok=false` cả 20):** overall `0.52 0.54 0.58 0.47 0.63 0.64 0.59 0.54 0.40 0.48 0.56 0.75 0.78 0.61 0.70 0.44 0.54 0.74 0.62 0.63` — trung vị 0.58, 6/20 ≥ 0.65 `[VERIFIED: local prototype run]`; nhiễu trắng 0.17–0.29.
**How to avoid:** không tự đổi công thức D-04 (locked). Lên Open Question 1; verify "câu sai hẳn" bằng ngưỡng đã được Liam chọn.

### Pitfall 4: Độ dốc cuối câu vô lý và `FINAL_CONTOUR` giả
`polyfit` trên 300 ms F0 có lỗi cho ±40…±69 st/s; Theil–Sen + cổng 6 ≤ |slope| ≤ 30 st/s + ≥ 15 frame hữu thanh (Pattern 4) đưa FP benign từ 10/100 xuống 2/100. Phân vị độ dốc cuối câu của bản gốc: 5/25/50/75/95% = −33.7/−14.1/−5.9/+12.9/+52.1 st/s (16 câu hợp lệ, 4 câu không đủ frame) — nghĩa là **cổng \|slope\| ≥ 6 loại một nửa số câu khỏi rule này** (chủ ý: precision).

### Pitfall 5: Ghi cache đè `seg/NNNN.npz` gây race với `extend-end`
`analyze_segment` ghi toàn bộ `.npz` bằng `np.savez_compressed` chỉ 7 khoá `[VERIFIED: pipeline.py:558-567]` (`f0_hz`, `energy`, `ppg`, `window`, `sr`, `f0_hop_s`, `ppg_fps`). Nếu đường chấm đọc `.npz` cũ, thêm khoá rồi ghi lại toàn bộ, nó có thể đè lên `.npz` mới của "Mất chữ cuối?" (cửa sổ khác) → feature và `window` sai âm thầm. Cũng ngược lại: `extend-end` ghi lại `.npz` sẽ xoá khoá mới.
**How to avoid (khuyến nghị lệch nhẹ khỏi chữ D-03, Open Question 2):** sidecar `seg/NNNN.prosody.npz` ghi atomic (`.part` + `os.replace`) chứa `feat_version`, `window` (bản sao), `trim_frames`, `f0_st`, `energy_db`, `mfcc`; hợp lệ chỉ khi `feat_version` khớp **và** `window` khớp `seg/NNNN.npz` hiện tại; `shutil.rmtree(seg_dir)` của retry dọn luôn sidecar. Bài mới: `analyze_segment` ghi sidecar ngay (thêm ~30 ms/câu); bài cũ: bù lười (đọc lát vocals bằng `sf.read(start=, stop=)` = 5 ms so với 206 ms khi đọc cả khoảng `[VERIFIED: local prototype run]`, dùng `pipeline._stem_span` để đổi giây tuyệt đối → chỉ số mẫu). `np.load(..., allow_pickle=False)`.

### Pitfall 6: Bộ nhớ/thời gian DTW khi bản ghi dài hoặc lệch tỉ lệ
Trần 60 s hiện có `[VERIFIED: attempts.py:37]` (`MAX_RECORDING_MS = 60_000`, `MAX_UPLOAD_BYTES = 10 * 1024 * 1024`) vẫn cho ma trận 800 × 6000. **Kiểm tỉ lệ độ dài (sau cắt lặng) trước khi dựng ma trận**; ngoài [0.5, 2] → `ok=False` ngay, không DTW. Dựng khoảng cách bằng khai triển `‖a‖² + ‖b‖² − 2a·b` (BLAS) thay vì broadcast 3 chiều; ma trận `D` float64 + `back` int8.

### Pitfall 7: Gán ngắt nghỉ/từ lệch một từ
Chèn ngắt 500 ms trước "you": prototype báo `afterWord = "I've"` (lệch một từ) ở 1/3 ca; 2 ca còn lại đúng. Cổng: chỉ báo `EXTRA_PAUSE` khi khoảng cách từ vị trí ánh xạ tới đuôi từ gần nhất ≤ 100 ms, ngược lại không báo (hoặc báo mức câu không có). Tip nói sai từ thì mất niềm tin hơn là bỏ sót.

### Pitfall 8: `STRESS_MISMATCH` gần như không bao giờ bắn
Biên giữa từ nổi nhất và từ thứ hai của bản gốc có trung vị ≈ 0.18 z; chỉ 4–5/20 câu có biên ≥ 0.45; ngay cả khi tiêm lỗi mạnh (từ nổi nhất bị hạ 3 st + 6 dB, một từ khác nâng 6 st + 6 dB) chỉ 1/20 được phát hiện `[VERIFIED: local prototype run]`. Đây là hành vi "precision trước recall" nhưng nghĩa là tip ưu tiên số 1 hiếm xuất hiện; **không** hạ δ để "cho có tip" — chờ Phase 4. Kế hoạch phải có test đơn vị cho rule bằng dữ liệu tổng hợp (rule đúng khi điều kiện đúng), không bằng audio thật.

### Pitfall 9: Màu điểm lệch với số hiển thị
`0.796 → "80"` hiển thị nhưng `0.796 < 0.8` → vàng. `scoreLevel` phải làm tròn theo % hiển thị (Pattern 8) và mọi chỗ hiển thị dùng cùng `Math.round(score*100)`.

### Pitfall 10: `no_speech` đốt số lượt, nhãn "Lượt N" lệch
`insert_attempt` hiện đếm mọi lượt (kể cả `voiced = 0`) `[VERIFIED: db.py:132-169]`. Sau D-09, lượt không tiếng vẫn có `attempt` nhưng không có điểm; nhãn "Lượt N" của FBK-06 nên là **thứ tự trong các lượt đã chấm** (suy từ danh sách lượt có `overall`), không phải số `attempt` thô, để không thấy "Lượt 1, Lượt 3". Open Question 4.

### Pitfall 11: Recharts + Next 14 + vitest
Biểu đồ phải nằm trong client component (`"use client"`); `ResponsiveContainer` cần kích thước cha khi mount; vitest ở `node` nên chỉ test hàm dựng dữ liệu; chạy `pnpm --filter @shadowenglab/web build` ngay sau khi thêm Recharts (Wave 0) vì chưa build thử `[ASSUMED]`.

### Pitfall 12: Lệch lưới thời gian 20–25 ms giữa F0, MFCC, năng lượng
Xem Pattern 1. Cắt về `min(len)` mà không bù offset tạo lệch cố định giống nhau ở hai phía (vô hại cho tỉ lệ, nhưng `wordBounds`/`words[].start` lệch ≤ 25 ms). Ghi chú trong test, hoặc dựng lưới chung bằng `np.interp` theo `xs()`.

## Code Examples

### DTW vector hoá, biên nới (prototype đã chạy; viết lại sạch)
```python
# services/audio/src/audio_service/scoring/align.py  (ý tưởng — prototype đã đo 15–45 ms cho 500–800 khung)
import numpy as np

_INF = 1e18

def pairwise_dist(ref: np.ndarray, user: np.ndarray) -> np.ndarray:
    """Euclid / sqrt(d) bằng khai triển BLAS (không broadcast 3 chiều)."""
    d2 = (ref**2).sum(1)[:, None] + (user**2).sum(1)[None, :] - 2.0 * ref @ user.T
    return np.sqrt(np.maximum(d2, 0.0)) / np.sqrt(ref.shape[1])

def dtw_slack(cost_matrix: np.ndarray, slack: int = 30) -> tuple[np.ndarray, float]:
    """Tập bước {(1,1),(1,2),(2,1)} chỉ phụ thuộc hàng trước -> vector hoá theo hàng ref.
    Điểm bắt đầu: cột 0..slack; điểm kết thúc: m-slack..m. Trả (path[(i,j)], cost/len(path))."""
    n, m = cost_matrix.shape
    acc = np.full((n + 1, m + 1), _INF)
    acc[0, : min(slack + 1, m + 1)] = 0.0
    back = np.zeros((n + 1, m + 1), np.int8)
    for i in range(1, n + 1):
        c0 = acc[i - 1, 0:m]
        c1 = np.full(m, _INF); c1[1:] = acc[i - 1, 0 : m - 1]
        c2 = acc[i - 2, 0:m] if i >= 2 else np.full(m, _INF)
        stack = np.stack([c0, c1, c2]); k = stack.argmin(0)
        acc[i, 1:] = stack[k, np.arange(m)] + cost_matrix[i - 1]
        back[i, 1:] = k
    lo = max(1, m - slack)
    j = lo + int(np.argmin(acc[n, lo : m + 1]))
    if acc[n, j] >= _INF / 2:                      # không có đường đi (tỉ lệ ngoài [0.5, 2])
        return np.empty((0, 2), np.int64), float("inf")
    path, i = [], n
    total = acc[n, j]
    while i > 0 and j > 0:
        path.append((i - 1, j - 1)); k = back[i, j]
        if k == 0: i, j = i - 1, j - 1
        elif k == 1: i, j = i - 1, j - 2
        else: i, j = i - 2, j - 1
    path.reverse()
    return np.asarray(path, np.int64), total / max(len(path), 1)
```
`n` là số khung của **bản gốc đã cắt**; kiểm `0.5 <= m/n <= 2` trước khi gọi.

### F0 hai lượt + semitone + bộ lọc quãng tám (đã chạy)
```python
def f0_two_pass(x16k: np.ndarray) -> np.ndarray:
    f = _pitch_ac(x16k, 60.0, 700.0)                        # lượt 1 rộng
    voiced = f[f > 0]
    if voiced.size >= 10:
        q1, q3 = np.percentile(voiced, [25, 75])
        f = _pitch_ac(x16k, max(50.0, 0.75 * q1), min(800.0, 2.0 * q3))   # Hirst & De Looze
    return f                                                  # Hz, 0 = vô thanh

def to_semitone(f0: np.ndarray) -> np.ndarray:                # NaN = vô thanh
    st = np.full(f0.shape, np.nan)
    v = f0 > 0
    if v.sum() < 5:
        return st
    st[v] = 12.0 * np.log2(f0[v] / np.median(f0[v]))
    idx = np.where(v)[0]
    roll = median_filter(st[idx], size=min(9, len(idx) | 1), mode="nearest")
    st[idx[np.abs(st[idx] - roll) > 6.0]] = np.nan             # lỗi quãng tám ±12 st
    return st
```

### `ScoreResult.versions` và `timingMs`
```python
versions = {"scorer": "prosody-1", "thresholds": THRESHOLDS_VERSION}   # tên/giá trị để Liam duyệt
timing_ms = {"normalize": ..., "ref_features": 0.0 or ..., "user_features": ..., "align": ..., "metrics": ..., "rules": ..., "total": ...}
```
`[VERIFIED: packages/contracts/src/score.ts:176-178]` `Versions = { scorer: z.string(), thresholds: z.string() }`; `timingMs: z.record(z.string(), z.number().min(0))` (dòng 188).

### Thêm `no_speech` vào contract (checkpoint)
```ts
// packages/contracts/src/api.ts — chèn vào ApiErrorCode (hiện 20 mã, KHÔNG có no_speech, dòng 6–27)
//   "recording_too_long",
//   "no_speech",            // <— mới (D-09), HTTP 422
//   "busy",
// sau đó: make contracts (Zod → JSON Schema → pydantic) và drift gate
```
Backend: `raise ApiErrorException(422, "no_speech", "Không nghe thấy tiếng nói trong lượt vừa rồi.")` — cùng nhóm với `recording_too_long` (422) `[VERIFIED: attempts.py:138]`.

### Recharts — dựng dữ liệu thuần (test được ở node)
```ts
// apps/web/lib/chartData.ts
export interface ChartRow { x: number; ref: number | null; user: number | null }
export function buildChartRows(c: { ref: (number|null)[]; user: (number|null)[]; wordBounds: number[] }): ChartRow[] {
  const n = Math.min(c.ref.length, c.user.length);
  return Array.from({ length: n }, (_, x) => ({ x, ref: c.ref[x] ?? null, user: c.user[x] ?? null }));
}
// IntonationChart.tsx ("use client"):
// <ResponsiveContainer width="100%" height={150}>
//   <LineChart data={rows} margin={{top:8,right:8,bottom:24,left:8}}>
//     <XAxis type="number" dataKey="x" domain={[0, rows.length-1]} ticks={wordBounds} tick={<WordTick words={words} bold={topIndex}/>} />
//     <YAxis hide domain={[-12, 12]} />
//     <ReferenceLine y={0} strokeDasharray="4 4" />
//     {hovered != null && <ReferenceArea x1={bounds[hovered]} x2={bounds[hovered+1] ?? n-1} />}
//     {pauseXs.map(x => <ReferenceLine key={x} x={x} label="ngắt thừa" />)}
//     <Line dataKey="ref"  dot={false} connectNulls={false} isAnimationActive={false} style={{stroke:"var(--original)"}} strokeWidth={3} />
//     <Line dataKey="user" dot={false} connectNulls={false} isAnimationActive={false} style={{stroke:"var(--you)"}} strokeWidth={3} />
//   </LineChart>
// </ResponsiveContainer>
```
Mẫu thành phần theo Context7 (`ReferenceLine`, `connectNulls`, tick tuỳ biến) `[CITED: Context7 /recharts/recharts]`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| F0 một lượt 75–500 Hz | hai lượt theo phân vị người nói (Hirst & De Looze) | — (khuyến nghị P3) | giảm lỗi quãng tám; ref ví dụ có median 322 Hz và p95 448 Hz (sát trần 500) |
| Recharts 2 (`accessibilityLayer` tắt mặc định) | Recharts 3 (bật mặc định) | 3.0 | cần `aria-label` cho chart |
| `AttemptAck` + `voiced` | `ScoreResult` hoặc `ApiError{no_speech}` | D-09 | machine rẽ nhánh theo mã lỗi |

**Deprecated/outdated:** `voiced: false` trong response chấm (bỏ theo D-09); `PlayerRecording.status = "uploaded"` kèm `AttemptAck` (đổi sang kèm `ScoreResult`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Ngưỡng `ALIGN_COST_MAX = 1.10` hợp với giọng người Việt thật (đã đo chỉ trên nhiễu loạn tổng hợp của giọng Mỹ sạch) | Pattern 2/4 | Nếu cost thật cao hơn, phần lớn lượt rơi vào "căn kém" → mất `PITCH_DEVIATION`/`EXTRA_PAUSE`/`STRESS_MISMATCH` (an toàn nhưng vô dụng); cần UAT với bản ghi thật của Liam |
| A2 | Các ngưỡng cổng chắc chắn (6–30 st/s, ≥ 0.8 nhất quán dấu, ≥ 10 frame, δ = 0.5) là điểm khởi đầu tốt | Pattern 4 | Phase 4 phải chỉnh bằng eval; số FP/recall đo trên nhiễu loạn tổng hợp, không phải lỗi người học |
| A3 | Recharts 3.10.1 build được trong Next 14.2 App Router (chưa chạy build) | Pitfall 11 | Cần xử lý `transpilePackages`/dynamic import; kiểm bằng `pnpm --filter @shadowenglab/web build` ở Wave 0 |
| A4 | `style={{ stroke: "var(--original)" }}` trong SVG của Recharts nhận biến CSS | Pattern 6 | Dùng hex trực tiếp từ token hoặc className `stroke-original` |
| A5 | Dependency bắc cầu của Recharts không có script cài đặt rủi ro | Package Audit | Chạy `pnpm install` có kiểm tra lockfile ở checkpoint |
| A6 | Sidecar `NNNN.prosody.npz` được Liam chấp nhận thay cho "ghi lại `.npz`" | Pitfall 5 | Nếu Liam muốn đúng chữ D-03, cần khoá tệp + kiểm `window` — phức tạp hơn |
| A7 | Chạy chấm đồng bộ trong threadpool FastAPI cạnh job Demucs vẫn ≤ 3 s (đo chỉ khi máy rảnh) | Summary | Có thể chậm hơn khi job model đang chạy; thêm `timingMs` và đo trong UAT |
| A8 | Lớp "chấm giảm" khi `align_ok=False` (melody theo tỉ lệ thời gian tuyến tính) cho điểm thấp ổn | D-02 | Chưa đo nhánh tuyến tính (prototype dùng đường DTW cả khi căn kém); đo ở plan đầu tiên của scoring |
| A9 | Chuẩn hoá `similarity` theo từ (đề xuất: `1 − min(1, RMS(st diff)/6)`; từ < 5 frame chung → dùng `melodyMatch` câu) | Open Q 8 | Chỉ ảnh hưởng eval Phase 4; Liam duyệt |
| A10 | Recall `FINAL_CONTOUR` 5/20 và `STRESS_MISMATCH` 1/20 là đặc trưng của cổng chứ không phải lỗi cài đặt | Pitfall 4, 8 | Nếu là lỗi, rule vô dụng; test đơn vị rule bằng dữ liệu tổng hợp để loại trừ |

## Open Questions

1. **Công thức D-04 và tiêu chí "câu đọc sai hẳn điểm thấp" (BLOCKING cho kế hoạch kiểm thử PRO-03).**
   - Biết: 20 câu sai cho `overall` 0.40–0.78 (trung vị 0.58), 6/20 ≥ 0.65, trong khi `ok=false` đúng cả 20 (cost 1.11–1.32). Nhiễu trắng 0.17–0.29.
   - Chưa rõ: Liam chấp nhận "thấp" nghĩa là gì (ví dụ < 0.65 ở ≥ 80% câu sai?) hay muốn chặn trên.
   - Khuyến nghị: giữ D-04; thêm vào PR contract một lựa chọn để Liam chọn: (A) giữ nguyên và dùng tiêu chí verify "median(overall câu sai) < 0.6 và `align_ok = false`"; (B) khi `align_ok = false`, `speed` và `pitchRange` không được tính (đặt = melodyMatch) — đổi D-04/D-02, cần Liam; (C) chỉ hiện nhãn "chưa khớp bản gốc" ở client khi `align_ok=false` không cần field mới (client không biết `align_ok`; phải suy từ `issues`/`words` ⇒ không khả thi). Planner **không tự chọn**.

2. **Sidecar thay vì ghi đè `.npz` (D-03)** — xem Pitfall 5. Cần Liam đồng ý lệch chữ D-03 (ghi trong ADR 0006).

3. **Contract bổ sung để vẽ `AttemptStrip` và chấm màu (Claude's Discretion nhưng đổi shape ⇒ checkpoint).**
   - Đề xuất tối thiểu: (a) `SegmentProgress.bestOverall: Score01.nullable()` + `bestAttempt: int>=1 .nullable()` (vẽ `SegmentedProgress`/`TranscriptList` bằng 1 truy vấn); (b) `AttemptSummary { attempt: int>=1, overall: Score01.nullable(), createdAt: string }` + `GET /lessons/{id}/segments/{index}/attempts` → `AttemptSummary[]`; (c) `GET …/attempts/{n}` → `ScoreResult` (không đổi shape, đọc `result_json`, validate lại bằng pydantic trước khi trả).
   - Chưa rõ: Liam muốn gộp (a)+(b) vào `LessonProgress` hay giữ tách.

4. **Thứ tự ghi dòng `attempts` và nhãn "Lượt N" (Pitfall 10).** Khuyến nghị: ghi sau khi chấm thành công trong một giao dịch; `no_speech` ghi `voiced = 0` như P1; "Lượt N" = thứ tự trong lượt có điểm. Cần Liam duyệt cùng migration.

5. **HTTP status của `no_speech`:** đề xuất 422 (cùng `recording_too_long`). 

6. **Lưu `align_ok` / chất lượng căn:** không có chỗ trong `ScoreResult` (không đổi shape). Đề xuất đưa vào `timingMs` **không** (sai ngữ nghĩa); thay vào đó chỉ lưu trong log. Eval Phase 4 cần biết căn kém → có thể suy từ việc thiếu mọi issue theo từ + `versions`. Nếu Liam muốn field riêng thì là thay đổi contract (ngoài D-02).

7. **Vị trí `scoreLevel()`:** khuyến nghị `apps/web/lib/scoreLevel.ts` (chỉ web cần màu; tránh biến `packages/contracts` thành nơi chứa logic ngoài schema). App eval không hiện điểm hệ thống cho người chấm.

8. **Định nghĩa `WordScore.similarity` ở P2** (D-06) — đề xuất ở A9; Liam duyệt.

9. **Xác thực bằng bản ghi thật (UAT cuối phase):** Liam ghi ~5 câu thật (đọc đúng, đọc phẳng, ngắt thừa, đọc sai câu) và xem `cost`/issue để chốt ngưỡng sơ bộ trước khi Phase 4.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 (uv venv) | scoring | ✓ | venv `services/audio/.venv` | — |
| uv | `make test`, chạy prototype | ✓ | 0.12.10 | — |
| praat-parselmouth | F0, MFCC | ✓ | 0.4.7 | — |
| numpy / scipy | DTW, filter, Theil–Sen | ✓ | 2.4.6 / 1.17.1 | — |
| ffmpeg | chuẩn hoá webm/mp4 | ✓ | 9.0.2 | — |
| Node / pnpm | web | ✓ | v24.16.0 / 11.9.0 | — |
| SQLite (stdlib) | migration v2, window function | ✓ | 3.51.0 (≥ 3.25 cần cho `ROW_NUMBER`) | — |
| Dữ liệu bài thật trong `~/shadowenglab-data` | smoke tự so (không commit) | ✓ (2 bài `ready`, `seg/*.npz`, `stems/*/vocals.wav`) | — | test tổng hợp |
| RAM | an toàn khi DTW | 8 GB (`hw.memsize = 8589934592`) | — | giới hạn tỉ lệ độ dài (Pitfall 6) |
| Recharts | web | ✗ (chưa cài) | 3.10.1 | SVG thuần nếu build lỗi (A3) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** Recharts chưa cài — Wave 0 cài sau cổng legitimacy.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + fastapi `TestClient` (`services/audio`); vitest ^4.1 (node env) cho `apps/web` và `packages/contracts` |
| Config file | `services/audio/pyproject.toml [tool.pytest.ini_options]`; `tests/conftest.py` (autouse cách ly settings/env); web: không có file config vitest (mặc định node) |
| Quick run command | `uv run --project services/audio --frozen pytest services/audio/tests/<file>.py -q` · `pnpm --filter @shadowenglab/web test -- <tên>` |
| Full suite command | `make test` (drift gate → vitest → pytest) + `make lint` + `pnpm --filter @shadowenglab/web build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRO-01 | F0 hai lượt, lọc quãng tám, semitone, nội suy khe ≤ 120 ms | unit (tín hiệu hài tổng hợp) | `pytest tests/test_scoring_features.py -q` | ❌ Wave 0 |
| PRO-02 | speed/pitchRange/melodyMatch/prominence trên cặp tổng hợp (kích thước biết trước) | unit | `pytest tests/test_scoring_metrics.py -q` | ❌ Wave 0 |
| PRO-03 | tự so = 1.00, 0 issue; phẳng → `FLAT_PITCH`; câu khác → `align_ok=False`; mức tín hiệu ×0.1 và đệm lặng không đổi điểm | unit (tổng hợp) + `@pytest.mark.slow` trên bài thật nếu có | `pytest tests/test_scoring_pipeline.py -q` | ❌ Wave 0 |
| PRO-04 | `timingMs.total` ≪ 3000 trên tổng hợp 8 s; ghi `timingMs` đủ khoá | unit/API | `pytest tests/test_scoring_api.py::test_timing -q` | ❌ Wave 0 |
| RUL-01 | từng mã rule: điều kiện đúng → issue; cổng chắc chắn không đạt → không issue; `align_ok=False` → chỉ 2 mã mức câu | unit (tổng hợp) | `pytest tests/test_scoring_rules.py -q` | ❌ Wave 0 |
| RUL-02 | ≤ 3 tip, mỗi mã ≤ 1, `issueRef` hợp lệ, thứ tự ưu tiên D-14, template có `*từ*` | unit | `pytest tests/test_scoring_tips.py -q` | ❌ Wave 0 |
| FBK-01/02/03 | `scoreLevel` ngưỡng + làm tròn; `buildChartRows`; `tipMarkup` tách `*từ*` an toàn | unit (vitest node) | `pnpm --filter @shadowenglab/web test -- scoreLevel chartData tipMarkup` | ❌ Wave 0 |
| FBK-05 | machine: `scoring → reviewing` mang `ScoreResult`; `no_speech → noVoice`; lỗi khác → `error` + `RETRY_UPLOAD` | unit (XState) | `pnpm --filter @shadowenglab/web test -- playerMachine` | ✅ (sửa) |
| FBK-06 | SQL lượt tốt nhất (hoà → lượt sau); migration v2 idempotent; danh sách lượt | unit | `pytest tests/test_db.py -q` | ✅ (mở rộng) |
| D-09 | POST attempts trả `ScoreResult`; `no_speech` → 422 `ApiError`; eval-clip vẫn `AttemptAck` | API (ffmpeg thật như `test_attempts_api.py`) | `pytest tests/test_attempts_api.py tests/test_scoring_api.py -q` | ✅ (sửa) + ❌ |
| contract | `no_speech` có trong JSON Schema/pydantic; round-trip `ScoreResult` | drift + round-trip | `make contracts-check` | ✅ (mở rộng) |

**Fixture tổng hợp đã kiểm chứng khả thi `[VERIFIED: local prototype run]`:** câu 4 "từ" hữu thanh giả (chuỗi hài + đường bao formant khác nhau mỗi từ, glide F0, khe 40 ms, đệm lặng 0.5/0.4 s, nhiễu 2e-4). Kết quả: tự so overall 1.00; `pitch×1.5` (khác giọng) 0.90 không issue; phẳng 0.26 + `FLAT_PITCH`; chèn 500 ms sau từ 1 → `EXTRA_PAUSE` đúng từ ("alpha", 520 ms vs 20 ms); đảo cuối câu → `FINAL_CONTOUR` (−10.8 vs +9.7 st/s); chậm ×1.3 → speed 0.80, không issue. Không cần file audio thật trong repo.

### Sampling Rate
- **Per task commit:** test file của task (≤ 30 s mỗi lệnh).
- **Per wave merge:** `make test` + `make lint`.
- **Phase gate:** `make test` + `make lint` + `pnpm --filter @shadowenglab/web build` xanh; smoke tự so trên bài thật (đề xuất `scripts/smoke_score.py` hoặc `@pytest.mark.slow`) báo `overall ≈ 1.00` và `timingMs.total`; UAT người ghi âm thật (Open Question 9). `make eval` vẫn là stub — ghi rõ "chưa có eval" trong PR.

### Wave 0 Gaps
- [ ] `services/audio/tests/test_scoring_{features,metrics,rules,tips,pipeline}.py` + helper tổng hợp `tests/synth.py` (sinh câu giả giọng, deterministic seed)
- [ ] `services/audio/tests/test_scoring_api.py` (POST trả `ScoreResult`, `no_speech`, eval-clip)
- [ ] `apps/web/lib/{scoreLevel,chartData,tipMarkup}.test.ts`
- [ ] Cập nhật `playerMachine.test.ts`, `api.test.ts`, `test_attempts_api.py`, `test_db.py`, contract round-trip
- [ ] Cài Recharts (cổng legitimacy) + `pnpm --filter @shadowenglab/web build`

## Security Domain

`security_enforcement` bật (`workflow.security_enforcement: true`, ASVS 1, block on high — `[VERIFIED: .planning/config.json]`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (app local, một người dùng) | — |
| V3 Session Management | no | — |
| V4 Access Control | no (nhưng Origin/Host guard hiện có vẫn áp: POST/PUT từ `localhost:3000`) | middleware Origin + TrustedHost đã có `[VERIFIED: main.py]` |
| V5 Input Validation | **yes** | upload: ≤ 10 MB, magic bytes, ffmpeg `-f`, ≤ 60 s (đã có); thêm: kiểm tỉ lệ độ dài trước DTW; Zod parse `ScoreResult` ở client; pydantic validate trước khi ghi/đọc `result_json` |
| V6 Cryptography | no | — |
| V12 File & Resources | **yes** | `np.load(allow_pickle=False)` cho sidecar; ghi atomic `.part` → `os.replace`; đường dẫn qua `config.segment_features_path`/`_contained` |
| V13 API | yes | mã lỗi mới `no_speech` thông qua contract; thông điệp cố định, không lộ đường dẫn |

### Known Threat Patterns

| Pattern | STRESS | Standard Mitigation |
|---------|--------|---------------------|
| DoS bằng bản ghi dài/lệch tỉ lệ làm DTW ăn RAM | Denial of Service | trần 60 s + kiểm `ratio ∈ [0.5, 2]` trước ma trận + khoảng cách BLAS (Pitfall 6) |
| XSS qua từ trong tip (`*từ*` lấy từ Whisper/ô Sửa câu) | Tampering | tách markup thành React element, không `dangerouslySetInnerHTML` |
| SQL injection khi ghi `result_json`/điểm | Tampering | tham số `?`, id kiểm `ULID_RE` (pattern `db.py` hiện có) |
| JSON hỏng/đã sửa tay trong `result_json` | Tampering | `ScoreResult.model_validate_json` khi đọc lại; lỗi → 404/`internal_error`, không 500 lộ nội dung |
| Race ghi cache sidecar | Tampering/Repudiation | ghi atomic + kiểm `window`/`feat_version` (Pitfall 5) |
| CSRF cross-origin POST multipart | Spoofing | guard Origin sẵn có (`forbidden_origin`) |

## Sources

### Primary (HIGH confidence)
- Mã nguồn repo đã đọc trong session: `packages/contracts/src/{score,attempt,api,lesson,common,index}.ts`, `services/audio/src/audio_service/{db,config,main}.py`, `routers/{attempts,library,scoring}.py`, `lesson/{features,pipeline,vad,segment_ops,ipa,audio_io,store}.py`, `apps/web/lib/{api,queries}.ts`, `lib/player/{playerMachine,shortcuts}.ts`, `components/{PracticeRoom,SentenceStatePanel,AttemptStrip,ReviewBlock,ResultActionBar,TranscriptList,PracticeHeader}.tsx`, `docs/product.md` §3, `docs/design/{components,tokens}.md`, `S3-S4-phong-tap.{html,png}`, `S3-trang-thai-cau.png`
- Prototype chạy trên máy này (script ở scratchpad, kết quả trích trong tài liệu): F0/MFCC/DTW/rules trên bài `01M4C1HEW5RJ475HSYQHWAFWCW` (46 câu) và `01M4CS7EGSP0EBXMAJH7S2APSK` (43 câu)
- Context7 `/recharts/recharts` — `connectNulls`/`ReferenceLine`/tick tuỳ biến/`accessibilityLayer`/`isAnimationActive`
- npm registry (`npm view recharts`, `react-is`) + cổng legitimacy `gsd-tools query package-legitimacy check`

### Secondary (MEDIUM confidence)
- Hirst, *Speech Prosody* ch.2 (ResearchGate) và Hirst & De Looze: phương pháp F0 hai lượt (`floor = 0.75·q1`, `ceiling = 2·q3`, lượt đầu 60–700 Hz) — truy cập qua tìm kiếm web, nguồn học thuật

### Tertiary (LOW confidence)
- Không có

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — không có package Python mới; Recharts đã kiểm registry + peer + cổng legitimacy
- Architecture: HIGH — đọc code tích hợp và đã chạy toàn bộ luồng chấm ở dạng prototype (24–47 ms/cặp)
- Thuật toán/ngưỡng: MEDIUM — số đo trên nhiễu loạn tổng hợp của giọng Mỹ sạch; chưa có giọng người học thật
- Pitfalls: HIGH cho 1, 2, 5, 6, 9 (đo/đọc code trực tiếp); MEDIUM cho 3, 4, 7, 8 (phụ thuộc phân bố dữ liệu thật)

**Research date:** 2026-10-08
**Valid until:** 2026-11-07 (ổn định; Recharts/XState có thể ra bản mới — ghim phiên bản như đã nêu)
