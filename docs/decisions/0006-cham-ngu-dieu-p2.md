# 0006 · Chấm ngữ điệu P2: căn MFCC-DTW, feature dùng chung, công thức điểm, cache sidecar, lượt chấm và ngưỡng có version

Ngày: 2026-10-10 · Trạng thái: Chấp nhận · Người quyết: Liam

## Bối cảnh

Phase 3 (P2) thêm lớp chấm đầu tiên: sau mỗi lượt ghi, người học nhận ba chỉ số ngữ điệu, contour so với bản gốc và gợi ý bám issue đo được. Liam chốt các quyết định ở Discuss (`03-CONTEXT.md` D-01..D-13), ở checkpoint contract (`03-01-SUMMARY.md` mục A–K, "approved" ngày 2026-10-09, chọn C1 và D-a) và ở smoke trên dữ liệu thật của 03-11 (2026-10-10). Theo CLAUDE.md, quyết định kỹ thuật mới phải có ADR trong cùng PR. ADR này gom chúng lại để Phase 4 (eval), Phase 5 (chấm âm, thay bộ căn) và Phase 8 (hiệu chỉnh điểm) đọc một chỗ.

Mọi con số dưới đây lấy từ code đã merge và từ các SUMMARY, không chép lại từ plan.

## Quyết định

### 1. Căn thời gian: MFCC-DTW sau giao diện `align` (D-01, D-02)

- `scoring/align.py`: MFCC c1–c12 (Praat, 25 ms, bước 10 ms), z-chuẩn hoá theo từng clip; khoảng cách Euclid / √12; DTW với tập bước {(1,1),(1,2),(2,1)}, điểm đầu và điểm cuối tự do trong `ALIGN_SLACK_FRAMES = 30` khung (300 ms) trên trục người học. Hàm thuần, không model.
- Tỉ lệ độ dài người học / bản gốc được kiểm **trước** khi dựng ma trận: ngoài [`ALIGN_RATIO_MIN` 0.5, `ALIGN_RATIO_MAX` 2.0] thì không căn (chống DoS, T-03-05).
- Cổng D-02: `Alignment.ok` khi chi phí chuẩn hoá ≤ `ALIGN_COST_MAX = 1.10` và tỉ lệ nằm trong khoảng trên. Căn kém thì các rule theo từ (STRESS_MISMATCH, PITCH_DEVIATION, EXTRA_PAUSE) im lặng; chỉ FLAT_PITCH và FINAL_CONTOUR (mức câu) còn chạy.
- `score_prosody` nhận một `Aligner` (Protocol). Phase 5 thay bằng PPG-DTW mà không sửa rule hay scorer; rule chỉ đọc `Alignment.path` và `Alignment.ok`.

### 2. Một hàm `prepare_features` cho cả hai phía (RESEARCH Pitfalls 1–2)

- Bản gốc (lúc tạo bài) và người học (lúc chấm) đi qua **cùng** `scoring/features.prepare_features`: năng lượng dB theo khung 10 ms, cắt lặng, F0 Praat hai lượt (lượt 1: 60–700 Hz; lượt 2: [max(50, 0.75·q1), min(800, 2·q3)] của chính người nói), semitone so với trung vị, nội suy khe ≤ 120 ms, median 5 + trung bình 3, MFCC.
- Lọc nghi lỗi quãng tám trong `to_semitone`: (a) lệch > 6 st so với trung vị 9 khung; (b) **03-11:** lệch 9–15 st so với trung vị 41 khung (~410 ms). Lượt (b) bắt các cụm nhảy dài 5–15 khung mà (a) để lọt; chỉ bỏ khung lệch gần đúng một quãng tám, nên lên giọng thật (< 9 st) vẫn còn.
- **03-11:** ngưỡng cắt lặng dùng **một** quy tắc cho cả hai phía, `max(p95 − 30 dB, −60 dB)`. Quy tắc cũ (`p10 + 12 dB` khi clip có lặng thật) làm ngưỡng của lượt ghi tụt xuống sàn và giữ phần đuôi nhỏ mà bản gốc đã cắt (smoke: tỉ lệ độ dài 1.15, speed 0.87 khi tự so).
- `FEAT_VERSION = "pf-2"` (tăng ở 03-11). Sidecar có `feat_version` cũ thì tự tính lại ở lần chấm đầu.

### 3. Công thức điểm (D-04, D-05) và `similarity` (03-01 mục G)

- `speed = min(r, 1/r)` với r = thời gian có tiếng của người học / của bản gốc (bỏ các đoạn lặng ≥ 250 ms, lặng = dB ≤ p95 − 35).
- `pitchRange = min(r, 1/r)` với r = độ trải semitone người học / bản gốc. **03-11:** độ trải là std bền `1.4826 · MAD` thay cho std. Smoke cho thấy chỉ ~3 % khung nhảy quãng tám sau khi mã hoá opus đã kéo pitchRange khi tự so xuống 0.64.
- `melodyMatch = max(0, Pearson)` của hai contour semitone trên các khung hữu hạn ở cả hai bên, sau khi đặt người học lên trục bản gốc qua path. Dưới `MIN_COMMON_VOICED_FRAMES = 10` khung chung, hoặc khi một bên phẳng, thì bằng 0.
- `overall = (speed + pitchRange + melodyMatch) / 3`, `intonation = (pitchRange + melodyMatch) / 2`, `rhythm = speed`, `sound = null` (P4).
- `WordScore.similarity = 1 − min(1, RMS(st_user − st_ref − offset câu) / 6)` trên các khung chung của từ; dưới 5 khung thì dùng `melodyMatch` của câu.
- `SCORER_VERSION = "prosody-2"` (tăng ở 03-11 vì đổi pitchRange).
- **Đã thử và bỏ ở 03-11:** lọc khung ngoại lai của melodyMatch theo hiệu (người học − bản gốc) lệch trung vị > 6 st. Cách này làm melodyMatch chéo câu ở bài 2 tăng từ 0.00 lên 0.71, vì nó bỏ đúng những khung khác nhau. Lỗi quãng tám được xử lý ở nguồn (mục 2) để không dùng dữ liệu của phía kia.

### 4. Cache feature bản gốc dạng sidecar `seg/NNNN.prosody.npz` (lệch chữ D-03, 03-01 mục F)

- D-03 viết "ghi vào `seg/NNNN.npz`". Ta ghi một file riêng `seg/NNNN.prosody.npz` để không ghi lại `.npz` của P1, tránh race với "Mất chữ cuối?" (extend-end) đang ghi cùng file.
- Ghi atomic (`.part` + `os.replace`), đọc bằng `allow_pickle=False`, chỉ hợp lệ khi `feat_version` và `window` khớp cửa sổ câu hiện tại. Bài mới ghi sidecar ở bước `analyzing` (và lại ghi khi extend-end, vì dùng chung `analyze_segment`). Bài cũ tính lười ở lần chấm đầu từ lát vocal (không model); thời gian đó nằm ở `timingMs.ref_backfill`.
- `ref_prosody_for_segment(..., write_cache=False)` là đường chỉ đọc mà `make smoke-score` dùng.

### 5. `no_speech`, POST trả `ScoreResult`, danh sách và chi tiết lượt (D-09, 03-01 A1–A6)

- `ApiErrorCode` thêm `no_speech` (HTTP 422, "Không nghe thấy tiếng nói trong lượt vừa rồi."); shape `ScoreResult` không đổi.
- `POST /lessons/{id}/segments/{index}/attempts` → 201 `ScoreResult`. `GET .../attempts` → `AttemptSummary[]` (chỉ lượt đã chấm, tăng dần). `GET .../attempts/{n}` → `ScoreResult` đọc từ `result_json` và validate lại; không có thì 404, JSON hỏng thì 500 với thông báo cố định.
- `SegmentProgress.bestOverall` / `bestAttempt` có mặt cùng nhau khi câu có ít nhất một lượt đã chấm; best = `overall` cao nhất, hoà thì lấy lượt sau (D-11).
- Thiếu audio bản gốc (không sidecar, không stem vocal) → 409 `invalid_state`.
- **03-11 (VAD):** khung > −35 dBFS cũng tính là có tiếng khi clip có dao động năng lượng (p95 − p10 ≥ 6 dB). Câu nói liền không có lặng thì p10 chính là tiếng nói, nên nhánh tương đối cũ (`p10 + 12 dB`) trả `no_speech` oan (smoke: một câu thật ra 0.000). Điều kiện dao động giữ đúng hành vi P2 với tiếng ồn đều (quạt), đây là chi tiết Claude thêm khi hiện thực hướng Liam duyệt.

### 6. Migration SQLite `user_version` 2 và đánh số lượt (D-10, 03-01 mục B, C)

- `attempts` thêm `overall`, `intonation`, `rhythm`, `sound` (REAL, CHECK trong [0, 1] hoặc NULL) và `result_json` (`ScoreResult` đầy đủ, camelCase). Hàng P1 giữ NULL. Migration chạy trong mẫu `BEGIN IMMEDIATE` + kiểm lại của `ensure_schema`: 0 → DDL v1 rồi ALTER v2; 1 → ALTER v2; rồi `PRAGMA user_version = 2`.
- **C1:** chỉ chèn hàng đã chấm sau khi chấm xong, trong một `BEGIN IMMEDIATE` cấp `attempt = MAX + 1`. Lượt `no_speech` vẫn chèn một hàng `voiced = 0` (tiêu một số lượt, không tính là "đã tập"). Chấm lỗi thì không chèn gì (500), trình duyệt giữ blob cho "Thử lại". Nhãn UI "Lượt k" là thứ tự trong các lượt đã chấm (P3-G15).

### 7. File ngưỡng có version (D-12, D-13, 03-01 mục E)

- Một file `scoring/thresholds.py`; `THRESHOLDS_VERSION` và `SCORER_VERSION` đi vào `ScoreResult.versions`. Giá trị như bảng E của `03-01-SUMMARY.md`; 03-11 không đổi ngưỡng nào trong file này, nên `THRESHOLDS_VERSION` vẫn là `"p2-1"`.
- Rule Lớp C (product.md §3) đều ưu tiên precision: PITCH_DEVIATION 3.0 st (đầu trên của khoảng 2–3 st, D-13), EXTRA_PAUSE người học ≥ 250 ms khi bản gốc < 100 ms, FLAT_PITCH pitchRange < 0.6 (bỏ qua khi bản gốc phẳng < 2 st), FINAL_CONTOUR độ dốc Theil-Sen ngược dấu với |độ dốc| trong [6, 30] st/s, STRESS_MISMATCH biên z 0.5 ở cả hai phía và câu từ 5 từ.
- **03-11 (FINAL_CONTOUR):** khi căn ok, đuôi người học là các khung được căn vào 300 ms cuối của bản gốc (`user_st_on_ref`). Khi căn kém thì vẫn dùng đuôi riêng của mỗi bên (D-02). Trước đây mép cắt lệch vài khung làm hai cửa sổ rơi vào hai đoạn khác nhau và rule báo nhầm khi tự so (−8.2 so với +8.4 st/s). Ngưỡng không đổi.

### 8. Eval gate: `make eval` là stub tới Phase 4 (03-01 mục K)

- PR của Phase 3 ghi "chưa có eval (make eval là stub tới Phase 4)". Thay cho bảng metric là kết quả `make smoke-score` (tự so, chéo câu, thời gian trên bài thật) và bảng phát hiện tổng hợp của 03-06, mỗi mục ghi rõ là thật hay tổng hợp. Không bịa metric.
- `make smoke-score` (03-11) chỉ đọc DATA_DIR: lượt "người học" là chính lát vocal của câu, đệm 0.3 s lặng hai đầu, mã hoá webm/opus rồi chuẩn hoá như một lượt tải lên.
- **Tiêu chí D-a nới ở 03-11 (Liam duyệt):** smoke chỉ đòi trung vị chéo câu < 0.6. Cặp chéo vẫn căn ok được in ra để theo dõi `ALIGN_COST_MAX`, không làm hỏng smoke: trên dữ liệu thật có 2–7/20 cặp chéo câu có cost 1.03–1.10, trong khi tự so qua opus chỉ ~0.04.

### 9. Khoảng trống UI-SPEC đã được Liam xác nhận (03-01 mục J)

P3-G2, G3, G4, G5, G7, G9, G13, G15, G16, G17, G21 được chấp nhận như đề xuất trong `03-UI-SPEC.md`. P3-G18 (câu chữ của tip) được review trong PR của phase.

## Hệ quả

- Đổi công thức (mục 3) hoặc feature (mục 2) phải tăng `SCORER_VERSION` / `FEAT_VERSION`; đổi ngưỡng phải tăng `THRESHOLDS_VERSION`. Từ Phase 4, mọi thay đổi như vậy phải chạy `make eval` và dán bảng metric vào PR.
- **Rủi ro mở:**
  - RESEARCH A1: `ALIGN_COST_MAX = 1.10` chưa đo trên giọng Việt đọc tiếng Anh. Cặp chéo câu thật có cost 1.03–1.29 (vài cặp không căn được), tự so qua opus ~0.04, còn giọng Liam đọc đúng câu chưa biết nằm đâu. UAT giọng thật của 03-11 và eval Phase 4 sẽ đo.
  - RESEARCH A7: độ trễ khi worker model đang chạy Demucs chưa đo. Smoke đo p95 75–92 ms trên máy rảnh (chuẩn hoá + VAD + feature người học + chấm, không tính HTTP).
  - Câu sai của **cùng một người nói** cùng nhịp vẫn đạt ~60 % overall (bài 1: trung vị chéo 0.616 > 0.6), vì speed (~0.81) và pitchRange (~0.73) gần nhau, chỉ melodyMatch thấp (~0.26). Đây là tính chất của D-04 (trung bình cộng ba chỉ số). Liam chọn giữ mốc 0.6; Phase 4 / Phase 8 cân lại trọng số.
  - Recall của STRESS_MISMATCH và FINAL_CONTOUR trên giọng thật thấp theo thiết kế (RESEARCH Pitfalls 4, 8): precision trước recall.
