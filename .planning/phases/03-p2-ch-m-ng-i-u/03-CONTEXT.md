# Phase 3: P2 · Chấm ngữ điệu - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Sau mỗi lượt ghi ở S3, Liam nhận **kết quả chấm ngữ điệu** so với chính người nói gốc: `ScoreHero` (điểm tổng + Tốc độ, Lên xuống, Giai điệu), `IntonationChart` (contour bản gốc teal / bạn cam, baseline, thanh trọng âm theo từ, dấu ‖ ngắt thừa), `TipList` 2–3 gợi ý template tiếng Việt, mỗi gợi ý trỏ một `issueRef`. Lượt chấm chỉ xử lý audio người học, ≤ 3 s.

Trong phạm vi: Lớp B (parselmouth F0 → semitone theo median từng người → căn theo từ → 3 chỉ số + prominence), Lớp C với 5 mã ngữ điệu (`STRESS_MISMATCH`, `EXTRA_PAUSE`, `FINAL_CONTOUR`, `FLAT_PITCH`, `PITCH_DEVIATION`) dạng template, UI kết quả và 6 trạng thái vùng câu, lưu điểm và "lượt tốt nhất".

Ngoài phạm vi: Lớp A (PPG + DTW âm, `PHONE`, `WORD_MISSING`, `ref_unclear`) — Phase 5; eval và hiệu chỉnh ngưỡng — Phase 4; gợi ý LLM, logistic calibration — Phase 8; chế độ chỉ ngữ điệu (`mode: intonationOnly`) — Phase 7.

Requirements: PRO-01..04, RUL-01..02, FBK-01..06.

</domain>

<decisions>
## Implementation Decisions

> Kế thừa: contract `ScoreResult`/`Issue`/`Tip`/`Prosody` đã chốt ở Phase 1 (`01-CONTEXT.md` D-10..D-15, `packages/contracts/src/score.ts`) — **không đổi shape**. Phase 2 D-05 (state `scoring` trong XState có sẵn), D-06 (endpoint lượt ghi sẽ trả `ScoreResult`, không nới `ScoreResult` cho "chưa chấm"), D-08 (chấm màu danh sách câu chuyển sang `scoreLevel()`), D-18 (không giữ model resident, máy 8 GB). Các quyết định dưới đây là **Liam đã chốt** trong Discuss Phase 3.

### Căn thời gian người học ↔ bản gốc
- **D-01:** **Căn bằng DTW trên MFCC, không dùng model.** Chiếu ranh giới từ (Whisper) của bản gốc sang audio người học qua đường DTW giữa MFCC hai bên. Không tranh `model_gate` với job tạo bài, không nạp wav2vec2/Whisper khi chấm. Viết thành hàm thuần `align(ref_feats, user_feats) → path` (array in → array out) sau một giao diện thay được, để Phase 5 thay bằng PPG-DTW mà rule Lớp C không đổi. — **Reversibility:** reversible — đổi bộ căn là cục bộ sau giao diện `align`.
- **D-02:** **Căn không đáng tin → giữ chỉ số mức câu, bỏ issue theo từ.** Khi chất lượng căn kém (chi phí DTW chuẩn hoá vượt ngưỡng, đường đi suy biến, người học nói thiếu/khác câu), vẫn trả `speed`, `pitchRange`, và các rule mức câu `FLAT_PITCH`, `FINAL_CONTOUR`; `melodyMatch` tính trên contour căn theo tỉ lệ thời gian; **không** sinh `STRESS_MISMATCH`, `PITCH_DEVIATION`, `EXTRA_PAUSE`. Không thêm field/trạng thái mới vào contract. Ngưỡng "căn kém" Claude đề xuất trong file ngưỡng (D-10), Liam duyệt ở PR.
- **D-03:** **Feature bản gốc mới → tính bù lười khi chấm lần đầu, ghi cache.** Nếu Lớp B cần feature bản gốc chưa có trong `seg/NNNN.npz` (ví dụ F0 hai lượt theo khoảng pitch riêng người nói, intensity cho prominence, MFCC cho căn), bài mới tính sẵn trong bước `analyzing`; bài cũ thiếu key thì lần chấm đầu tính từ audio vocals của câu đó (không cần model) rồi ghi lại `.npz`. Không bắt tạo lại bài, không script migrate. Ngân sách ≤ 3 s áp cho lượt chấm thường (đã có cache); lần tính bù đầu được phép chậm hơn nhưng phải ghi trong `timingMs`.

### Điểm tổng và hiển thị ở P2
- **D-04:** **Công thức gộp (P2, `sound = null`):** `intonation = mean(pitchRange, melodyMatch)`; `rhythm = speed`; `overall = mean(speed, pitchRange, melodyMatch)`. Ngắt thừa báo qua issue `EXTRA_PAUSE`, không trừ vào `rhythm`. Phase 8 hiệu chỉnh lại bằng logistic.
- **D-05:** **`melodyMatch = max(0, r)`** với `r` là Pearson của hai contour semitone đã căn (chỉ frame hữu thanh cả hai bên). Không tương quan hoặc ngược chiều → 0; bản gốc so với chính nó → 1.
- **D-06:** **Chip từ ở P2: câu trơn, không tô điểm từng từ.** `words[]` vẫn điền đủ (`status: 'scored'`, `start`/`end` trên audio người học từ D-01, `similarity` = độ khớp ngữ điệu của từ đó để Phase 4 dùng cho eval). UI **không tô màu chip** khi `scores.sound === null`, để màu chip không đổi nghĩa khi Phase 5 thêm điểm âm. Từ chỉ được highlight khi hover tip (FBK-03).
- **D-07:** **Ẩn hẳn các phần Lớp A của S3-S4 ở P2** (panel PhonemeDiff "Bạn đọc … khác ở âm nào?", điểm dưới từng từ). Panel kết quả P2 = `ScoreHero` + nút "So sánh ngữ điệu"/`IntonationChart` + `TipList` + thanh nút (O/M/B/R/→). Không thêm UI giữ chỗ ngoài thiết kế. Phase 5 gắn lại.
- **D-08:** **Trạng thái vùng câu thứ 6 ở P2 = "lỗi"** (toast + Thử lại, giữ bản ghi — đã có từ P1), đúng FBK-05. Biến thể "Bản gốc không đủ rõ — chỉ chấm ngữ điệu" trong `S3-trang-thai-cau` làm cùng PHN-02 ở Phase 5.

### Lưu điểm, endpoint và lượt tốt nhất
- **D-09:** **`POST /lessons/{id}/segments/{index}/attempts` trả `ScoreResult`** trong cùng request (upload → chuẩn hoá WAV → chấm). Không thu được tiếng → `ApiError` với mã mới (đề xuất `no_speech`) thay cho `voiced: false`; state `scoring` của XState chờ chính request này và rẽ nhánh "không thu được tiếng" theo mã lỗi. `AttemptAck` chỉ còn dùng cho `PUT …/attempts/{n}/eval-clip`. Thêm mã vào `ApiErrorCode` là đổi contract → đi qua checkpoint PR contract (Zod → JSON Schema → pydantic, drift gate). — **Reversibility:** one-way — contract dùng chung web/Python, đổi response của endpoint công khai.
- **D-10:** **SQLite migration `user_version` 1 → 2:** thêm vào `attempts` các cột `overall`, `intonation`, `rhythm`, `sound` (REAL, nullable) và `result_json` (TEXT, nguyên `ScoreResult`). Lượt P1 cũ giữ NULL. Phase 7 thống kê `IssueCode` từ `result_json`. Schema cụ thể Liam duyệt ở PR. — **Reversibility:** costly — Phase 7 (ôn luyện, dashboard) xây trên bảng này; migration idempotent theo pattern `ensure_schema` hiện có.
- **D-11:** **Lượt tốt nhất = `overall` cao nhất, hoà thì lấy lượt sau.** Chấm màu danh sách câu = `scoreLevel(best.overall)`; câu chỉ có lượt P1 chưa điểm giữ chấm xám "đã tập" (D-08 P2). Bấm chip lượt cũ trong `AttemptStrip` → hiện `ScoreResult` đã lưu của lượt đó; nút `M` chỉ dùng được khi blob còn trong phiên (D-07 P2). `R` thử lại hiển thị "Lượt N" và giữ nhãn "tốt nhất" (FBK-06).

### Rule engine và gợi ý
- **D-12:** **Thêm cổng chắc chắn ngoài ngưỡng lệch của product.md — Claude đề xuất, Liam duyệt ở PR.** Ví dụ hướng: đủ tỉ lệ frame hữu thanh mỗi bên trong từ/câu; `STRESS_MISMATCH` chỉ khi từ nổi nhất của bản gốc vượt từ thứ hai một biên δ; `FINAL_CONTOUR` cần |refSlope| đủ lớn và đủ frame hữu thanh trong 300 ms cuối hai bên; `FLAT_PITCH` bỏ qua khi chính bản gốc phẳng. Mọi ngưỡng nằm trong **một file ngưỡng có version**, giá trị ghi vào `versions.thresholds`. Không chắc → không báo.
- **D-13:** **Ngưỡng ban đầu:** giữ nguyên product.md §3 Lớp C, riêng `PITCH_DEVIATION` = **3 semitone** (đầu trên của khoảng 2–3, ưu tiên precision). Phase 4 chỉnh qua eval.
- **D-14 (sửa 2026-10-10, gap tips, xem D-16):** ~~mỗi mã tối đa 1 tip~~ → lượt 1 mỗi mã một tip theo thứ tự ưu tiên; lượt 2 thêm issue lệch nhiều thứ hai của mã theo từ (`EXTRA_PAUSE`, `PITCH_DEVIATION`), không lặp từ; mỗi mã tối đa 2, tổng tối đa 3. Bản gốc: **Chọn tip: ưu tiên cố định, mỗi mã tối đa 1 tip, tối đa 3 tip.** Thứ tự `STRESS_MISMATCH > FINAL_CONTOUR > EXTRA_PAUSE > PITCH_DEVIATION > FLAT_PITCH`; cùng mã lấy issue lệch nhiều nhất. `issues` vẫn chứa đủ mọi issue (cho eval, thống kê). Mỗi tip có `issueRef` hợp lệ, `source: 'template'`.
- **D-15:** **Không có issue → câu nhận xét theo `scoreLevel(overall)`, không phải tip** (contract buộc tip trỏ issue): ≥ 80 → khen ngắn theo trạng thái 5 của thiết kế ("Rất sát bản gốc…"); < 80 → câu trung tính ("Chưa thấy lỗi cụ thể nào chắc chắn; nghe lại bản gốc rồi thử lại"). Không khen khi điểm thấp. Sinh phía client từ `ScoreResult`, `tips` rỗng.
- **D-16 (Liam, 2026-10-10, gap-closure sau UAT):** **Tip template dùng số đo và có nhiều cách nói.** Mỗi mã 3–4 biến thể chèn số từ `issue.data` (FLAT_PITCH `%` độ lên xuống, EXTRA_PAUSE ms, PITCH_DEVIATION "nửa cung"); biến thể chọn xác định theo `(segmentIndex + attempt − 1) mod n` (cùng lượt luôn cùng chữ, lượt sau đổi cách nói). Lời văn duyệt nguyên văn theo `03-GAP-TIPS-PROPOSAL.md`. Không đổi contract, ngưỡng, rule hay D-15.

### Claude's Discretion
- Tham số MFCC/DTW (số hệ số, cửa sổ, ràng buộc band), cách cắt lặng hai đầu bản ghi trước khi căn, độ đo chất lượng căn.
- F0 người học: hai lượt (ước lượng khoảng pitch theo người rồi trích lại) hay giữ `pitch_floor=75, pitch_ceiling=500` hiện có; lọc lỗi quãng tám, nội suy, làm mượt (PRO-01) — miễn bản gốc và người học xử lý cùng một cách.
- Số điểm resample contour mỗi từ, cách tính `wordBounds`, `stress[]`, `pauses[]` cho `Prosody`.
- Văn phong template tiếng Việt cho 5 mã (bám ví dụ product.md và thiết kế S3-S4), dạng `IntonationChart` bằng Recharts theo `docs/design/components.md`.
- Vị trí `scoreLevel()` (`packages/contracts` hoặc `apps/web/lib`, theo `docs/design/tokens.md`).
- Endpoint đọc lại lượt cũ (ví dụ `GET …/attempts/{n}`) và mở rộng `LessonProgress` với điểm tốt nhất — đi kèm checkpoint contract nếu đổi shape.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec sản phẩm và chấm điểm
- `docs/product.md` §3 — Lớp B (công thức 3 chỉ số, prominence), Lớp C (bảng 7 mã + ngưỡng ban đầu), contract `ScoreResult`
- `docs/product.md` §2 M4 — nội dung kết quả hiển thị cho mỗi câu
- `docs/flows.md` — F2 (luồng tập, ghi, chấm)
- `.planning/REQUIREMENTS.md` — PRO-01..04, RUL-01..02, FBK-01..06
- `.planning/ROADMAP.md` — Phase 3 success criteria (≈100% tự so, sai hẳn điểm thấp, ≤ 3 s, tip→issueRef, UI khớp design)

### Contract
- `packages/contracts/src/score.ts` — `ScoreResult`, `Issue` (discriminated union), `Prosody`, `Contour`, `Tip`, `Versions`
- `packages/contracts/src/attempt.ts` — `AttemptAck` (chỉ còn cho eval-clip sau D-09)
- `packages/contracts/src/api.ts` — `ApiErrorCode` (thêm `no_speech`, D-09)
- `.planning/phases/01-p0-n-n-t-ng/01-CONTEXT.md` — D-10..D-15 (shape ScoreResult), D-18..D-21 (toolchain contract, drift gate)
- `.planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-CONTEXT.md` — D-02 (bảng attempts), D-05..D-08 (flow ghi, AttemptAck, blob client, chấm màu), D-18 (không giữ model resident)
- `docs/decisions/0003-contract-toolchain-va-moi-truong-p0.md`, `docs/decisions/0005-job-runner-attempts-settings-p1.md` — contract toolchain; job runner, model gate, attempts, dataDir

### UI
- `docs/design/screens/S3-S4-phong-tap.html` (+ `.png`) — panel kết quả, ScoreHero, IntonationChart, TipList, AttemptStrip
- `docs/design/screens/S3-trang-thai-cau.html` (+ `.png`) — 6 trạng thái vùng câu (P2 dùng "lỗi" cho trạng thái 6, D-08)
- `docs/design/components.md` — `ScoreHero`, `IntonationChart`, `TipList`, `ScoredSentence`, `SegmentedProgress`
- `docs/design/tokens.md` — `scoreLevel()` (đỏ < 60, vàng 60–79, xanh ≥ 80), teal/cam cho Bản gốc/Bạn
- `.planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-UI-SPEC.md` — spec UI S3 đã hiện thực ở P1

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `services/audio/src/audio_service/lesson/features.py`: `extract_f0` (Praat AC, hop 10 ms, 75–500 Hz), `frame_energy`, `segment_window` — dùng chung cho người học để bản gốc và người học xử lý giống nhau.
- `seg/NNNN.npz` (ghi ở `lesson/pipeline.py` ~dòng 518): `f0_hz`, `energy`, `ppg`, `f0_hop_s=0.01`, `ppg_fps`, cửa sổ có đệm theo giây tuyệt đối của video — nguồn feature bản gốc; key mới thêm theo D-03.
- `routers/attempts.py`: `_normalize` (upload → WAV 16 kHz mono + `vad.is_voiced`), `insert_attempt`, `_store_eval_clip` — điểm gắn chấm cho D-09.
- `routers/scoring.py`: router rỗng sẵn (FND-06) — chỗ đặt endpoint đọc lại kết quả nếu cần.
- `db.py`: `ensure_schema` theo `user_version` — mở rộng cho migration v2 (D-10); `segment_progress`, `practiced_indexes`.
- `apps/web/lib/player/playerMachine.ts`: state `scoring` invoke `uploadAttempt`, rẽ theo `voiced` — đổi sang `ScoreResult` / lỗi `no_speech` mà không đổi hình dạng machine (PLY-02).
- `apps/web/components/`: `ReviewBlock`, `SentenceStatePanel`, `AttemptStrip`, `ResultActionBar`, `TranscriptList` — khung UI P1 để gắn ScoreHero/IntonationChart/TipList; shadcn `skeleton` cho trạng thái "đang chấm".

### Established Patterns
- Hàm audio thuần (array in → array out), không đọc file bên trong; I/O ở router/pipeline.
- Contract-first: Zod → JSON Schema → pydantic, drift gate trong `make test`; đổi contract qua checkpoint PR.
- Model chỉ chạy dưới `model_gate` trong thread model-worker; Phase 3 không dùng model khi chấm (D-01).
- `scoreLevel()` chưa có trong code — tạo theo `docs/design/tokens.md`.

### Integration Points
- `POST /lessons/{id}/segments/{index}/attempts` → trả `ScoreResult`, ghi điểm vào `attempts`.
- `LessonProgress` / danh sách câu S3 → cần điểm tốt nhất mỗi câu cho chấm màu.
- `apps/web/lib/api.ts` + `queries.ts` — client Zod-validated cho endpoint mới.

</code_context>

<specifics>
## Specific Ideas

- Thiết kế S3-S4 là mốc: hero "74 giống bản gốc · 86 tốc độ · 58 lên xuống · 79 giai điệu", tip đánh số 01–03 gạch chân từ liên quan ("Nhấn vào *expect*, không phải *honestly*", "Xuống giọng ở *out*").
- Trạng thái 5 của S3-trang-thai-cau ("Rất sát bản gốc. Qua câu tiếp, hoặc thử nói nhanh hơn một chút…") là mẫu cho lời khen D-15.
- Tiêu chí kiểm: bản gốc (vocals) gửi như bản ghi người học → điểm ngữ điệu ≈ 100%, không issue; câu đọc sai hẳn → điểm thấp. Báo `timingMs` để chứng minh ≤ 3 s.

</specifics>

<deferred>
## Deferred Ideas

- **Nợ Phase 2 — chạy riêng trước khi Plan Phase 3:** `/gsd-code-review 02 --fix` cho 17 finding open (8 warning, `02-REVIEW-DISPOSITION.md`). Ba điểm chờ Liam chốt khi tiện: `EXTEND_MAX_MS = 3000`; WR-04 (`live_video` thay `invalid_range`); WR-05 (trần độ dài đoạn phía server).
- Trạng thái "Bản gốc không đủ rõ — chỉ chấm ngữ điệu" và tô màu chip từ theo điểm âm — Phase 5.
- Rhythm có tính phạt ngắt nghỉ, trọng số điểm tổng khác TB đều — xem lại khi hiệu chỉnh Phase 8.
- Chế độ chỉ ngữ điệu (`mode: intonationOnly`) — Phase 7 (REV-04).

</deferred>

---

*Phase: 03-p2-ch-m-ng-i-u*
*Context gathered: 2026-10-08*
