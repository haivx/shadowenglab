# 0007 · Eval nội bộ P3: kịch bản lỗi cố ý, cách đếm, held-out khoá và cờ tắt rule

Ngày: 2026-10-12 · Trạng thái: Đề xuất (chốt ở 04-12 khi có số held-out) · Người quyết: Liam

## Bối cảnh

Phase 4 (P3) đo độ tin cậy của các rule ngữ điệu Lớp C của Phase 3 trên giọng thật, thay cho bảng phát hiện tổng hợp và `make smoke-score` mà PR của Phase 3 phải dùng (ADR 0006 mục 8). Yêu cầu: EVL-01 (bộ clip lỗi cố ý có nhãn), EVL-02 (`make eval` sinh report precision/recall theo rule, test-retest), EVL-03 (tách tuning và held-out, khoá held-out) và EVL-04 (chỉnh ngưỡng bằng số liệu, rule trượt thì tắt). Liam chốt các quyết định ở Discuss (`04-CONTEXT.md` D-01..D-21) và ở checkpoint contract (`04-01-SUMMARY.md`, bảng "Quyết định đã chốt" mục A–L, "approved" ngày 2026-10-11). CLAUDE.md đòi: từ Phase 3 trở đi mọi thay đổi model, ngưỡng hoặc rule phải chạy `make eval` và dán bảng metric vào PR. ADR này ghi lại quy trình đó để Phase 5, 6 và 8 đọc một chỗ.

Mọi giá trị dưới đây lấy từ bảng 04-01 và từ code đã merge của 04-02..04-07, không chép lại từ plan. ADR không có số đo nào: mục "Kết quả" được điền từ `eval/report.md` ở 04-12.

## Quyết định

### 1. Kịch bản trước rồi mới thu; ghép clip bằng `tag_clips.py` (D-01)

- Liam viết case vào `eval/cases.jsonl` trước khi nói (câu nào, lỗi gì, từ nào), rồi thu trong app như bình thường và bấm "Lưu clip cho eval". `eval/tag_clips.py tag` (`make eval-tag`) ghép từng clip chưa có nhãn trong `DATA_DIR/eval_clips/` với một case đang chờ. Không thêm UI vào app.
- Vì nhãn có trước khi nói, điểm của hệ thống không làm lệch nhãn. Lệnh `tag` không in điểm hay issue.
- Các lệnh còn lại của `tag_clips.py`: `words` (liệt kê bài, câu, chỉ số từ), `add` (viết case), `split` (chốt held-out, mục 6), `also` (thêm `alsoPresent`, mục 7) và `check` (bảng phủ).

### 2. Contract `EvalCase`, dấu nhận diện câu và `split` optional (D-02..D-05)

- `ErrorType` = `wrong_stress | flat | extra_pause | final_rise | pitch_off | weak_form | final_drop` (D-03), tách khỏi `IssueCode`. `EvalCase` nằm ở `packages/contracts/src/eval.ts`, sinh JSON Schema và pydantic qua `make contracts` (drift gate): `caseId`, `lessonId`, `segmentIndex`, dấu nhận diện câu, `kind` (`error | correct`), `errorType?`, `wordIndex?`, `alsoPresent?`, `split?`, `clip?`, `note?`. Optional là vắng mặt, không bao giờ `null`.
- **Lệch shape dự kiến của D-02: `split` là optional** (04-01 A4). Thuật toán split (D-12) phân tầng theo errorType nên chỉ tính được khi đã viết đủ kịch bản; trong lúc viết, case chưa có split là trạng thái hợp lệ ("chưa chốt"). `analyze.py` và `sweep.py` thoát 2 nếu còn case thiếu split.
- Dấu nhận diện câu (D-05) dùng cả mốc thời gian lẫn hash text: `segStartMs`, `segEndMs`, `segEndExtraMs` (mili giây của segment lúc viết case) và `segTextHash` (16 ký tự hex đầu của sha256 text UTF-8). Lệch bất kỳ trường nào (bài bị xoá, "Sửa câu", "Mất chữ cuối?") thì `tag_clips.py` và `analyze.py` báo lỗi nêu caseId và thoát 2, không bỏ qua.
- Bất biến kiểm ở Python (`eval/evalkit/cases.py`), không dùng `refine` của Zod vì `refine` không sinh sang JSON Schema: `kind = error` khi và chỉ khi có `errorType`; `correct` không có `errorType` hay `wordIndex`; errorType theo từ (`wrong_stress`, `extra_pause`, `pitch_off`, `weak_form`, `final_drop`) bắt buộc `wordIndex`, mức câu (`flat`, `final_rise`) thì không có; `caseId` và `clip` duy nhất; `wordIndex` nằm trong câu; câu có ít nhất `STRESS_MIN_WORDS` (5) từ (D-11).
- `eval/cases.jsonl` được commit (D-04): đó là kịch bản, không phải nhãn thô của người chấm, và là regression suite. Audio ở lại `DATA_DIR/eval_clips/`, không chép vào repo.

### 3. Chấm lại từ WAV bằng scorer hiện tại (D-06)

- `analyze.py` gọi thẳng hàm Python (`pipeline.ref_prosody_for_segment(..., write_cache=False)`, `score_prosody`), không HTTP, không SQLite, không đọc `result_json` cũ. Đổi ngưỡng rồi chạy `make eval` là ra số mới ngay.
- Chỉ đọc `DATA_DIR`: không tạo thư mục, không ghi sidecar; file tạm nằm trong thư mục tạm của hệ thống và bị xoá trong `finally`. Đường dẫn clip dựng từ stem đã qua kiểm dạng và `is_relative_to` (không thoát `eval_clips`). Report ghi atomic (`.part` rồi `os.replace`) và chỉ sau khi mọi bước thành công, nên lỗi dữ liệu (thoát 2) không đè report cũ.

### 4. Cách đếm TP/FP/FN và bảng mã chính/phụ (D-07..D-11b, D-10)

Hàm thuần ở `eval/evalkit/counting.py`; w là `wordIndex` đã khai báo.

| errorType | Mã chính (tính recall) | Vị trí TP | Mã phụ (trung tính) |
|---|---|---|---|
| `wrong_stress` | `STRESS_MISMATCH` | `data.userWord` đúng là chữ của từ w (B1-a) | `PITCH_DEVIATION` tại w |
| `pitch_off` | `PITCH_DEVIATION` | `wordIndex` = w | `STRESS_MISMATCH` có `data.userWord` = chữ của từ w |
| `extra_pause` | `EXTRA_PAUSE` | lệch không quá 1 từ (D-08) | không |
| `flat` | `FLAT_PITCH` | cả câu | `PITCH_DEVIATION` ở bất kỳ từ |
| `final_rise` | `FINAL_CONTOUR` | cả câu | `PITCH_DEVIATION` ở từ cuối |
| `weak_form`, `final_drop` | không (Lớp A, Phase 5) | mọi issue Lớp C là FP (D-07) | không |

- `wrong_stress.wordIndex` là từ Liam cố ý nhấn thay (từ sai); `tag_clips.py add` từ chối khi chữ của từ đó xuất hiện nhiều hơn một lần trong câu (B1-a).
- Mỗi case có tối đa một TP cho mã chính (C1): issue gần w nhất, hoà thì chỉ số từ nhỏ hơn; issue thừa của mã chính nằm đúng vị trí là FP. Mã phụ và issue khớp một mục `alsoPresent` là trung tính (C2, D-09). Mọi issue còn lại là FP, kể cả đúng mã sai từ (C3, D-08).
- Precision của rule = TP / (TP + FP); recall = số case có TP / số case có mã chính đó. Khoảng tin cậy Wilson 95 % cho cả hai (D-14, F1); có thêm dòng gộp các rule đang bật.
- Căn thời gian thất bại (`alignment.ok` sai, D-02 của Phase 3) làm rule theo từ không chạy: clip lỗi theo từ thành FN và vào bảng "tỉ lệ căn thất bại" theo bài x errorType để đo lại `ALIGN_COST_MAX` (D-11b). Clip không có tiếng (VAD) không có issue và cũng là FN (C4).
- Nguồn câu: 3–4 bài giọng Mỹ, khoảng 25–30 câu, mỗi câu 3–4 lỗi khác nhau. Clip `weak_form` và `final_drop` là negative cho rule ngữ điệu ở phase này và để sẵn cho PHN-06 ở Phase 5.

### 5. Mốc đúng: tự so và clip `correct` (D-18)

- **Tự so (D-18a):** mọi câu có case trong tập đang chấm. "Người học" là lát vocal của câu, đệm lặng 0.3 s hai đầu, mã hoá webm/opus rồi chuẩn hoá như một lượt tải lên, dùng chính các hàm của `scripts/smoke_score.py` (nạp bằng importlib, không chép lại để hai đường không lệch nhau). Kỳ vọng gần 100 % và không có issue; mọi issue ở đây là FP và vào gate (mục 10).
- **Clip `correct` (D-18b):** khoảng 8 clip Liam cố đọc sát bản gốc nhất, làm negative: báo bất kỳ rule nào cũng là FP.

### 6. Thuật toán split và thời điểm chốt (D-12)

- `tag_clips.py split` gán một lần cho mọi câu chưa có split: sắp các câu theo `sha256("{lessonId}:{segmentIndex}")` (16 hex đầu thành số trong [0, 1)), duyệt tăng dần; đưa câu vào held-out nếu với mọi tầng có trong câu (mỗi errorType là một tầng, `correct` là một tầng) số case held-out của tầng sau khi thêm không vượt `ceil(0.30 x tổng case của tầng)`. Mọi clip của một câu nằm cùng một phía. In bảng tỉ lệ đạt được của từng tầng; tầng nhỏ có thể lệch khỏi 30 % do trần `ceil`.
- Case viết sau khi chốt: câu đã có split thì nhận split đó; câu mới thì `heldout` khi số hash < 0.30, ngược lại `tuning`.
- Split được commit **trước khi thu clip nào**: app chấm mọi lượt ghi nên "trước khi chấm clip nào" nghĩa là trước khi thu. Split đã ghi không bao giờ đổi (one-way: tách lại sau khi mở held-out làm held-out mất giá trị).

### 7. Khoá held-out, nhật ký mở và `alsoPresent` (D-16, D-09)

- `make eval` và `sweep.py` chỉ đọc case tuning; WAV của case held-out không được nạp và `eval/holdout_log.jsonl` không bị chạm. `sweep.py` không có cách nào đọc held-out. Chỉ `make eval HOLDOUT=1` (`analyze.py --holdout`) chấm held-out.
- Mỗi lần mở thêm đúng một dòng vào `eval/holdout_log.jsonl` (commit, chỉ thêm): `openedAt`, `thresholdsVersion`, `scorerVersion`, `featVersion`, `gitSha` (thêm `-dirty` khi cây có thay đổi), `splits` {caseId: split} của mọi case và `digests` {caseId held-out: sha256 của JSON chuẩn hoá}. Log được ghi trước report; report in toàn bộ log.
- Đóng băng từ dòng đầu: case có ở dòng đầu mà split khác, bị xoá, hoặc (held-out) digest khác thì `analyze.py --holdout` thoát 2 "nhãn held-out đã đổi sau lần mở đầu (D-09)" trước khi chấm. Case held-out mới (không có ở dòng đầu) vẫn được chấm nhưng được liệt kê là "thêm sau lần mở đầu". Hệ quả: sau lần mở đầu không xoá được case tuning nào mà không lộ trong diff của `holdout_log.jsonl`.
- `tag_clips.py also` thêm `alsoPresent` (lỗi có thật Liam nghe thấy ngoài kịch bản, sau khi nghe lại các FP trong report). Cho case tuning bất kỳ lúc nào; cho case held-out chỉ khi log chưa có dòng nào; sau đó từ chối (thoát 2, D-09).
- Khi đóng phase (04-12) Makefile đổi thành `HOLDOUT ?= 1` để `make eval` mặc định in cả hai tập làm bảng metric cho PR; `HOLDOUT=0` chỉ chạy tuning. Công cụ chỉ chặn sửa nhãn và ghi dấu vết; kỷ luật "không chỉnh ngưỡng dựa trên số held-out" (D-15) là của Liam.

### 8. Sweep ngưỡng và quy tắc đề xuất (D-13)

- `eval/sweep.py` (`make eval-sweep`, `PARAM=` tuỳ chọn) quét một chiều từng tham số, các tham số khác giữ giá trị hiện tại, chỉ trên tuning, bằng cách ghi đè ngưỡng trong bộ nhớ qua `eval/evalkit/overrides.py` (khôi phục trong `finally`, có test AST bắt module mới bind hằng ngưỡng mà quên đăng ký). Lưới (04-01 mục G): `STRESS_MARGIN_Z` 0.3 0.4 0.5 0.6 0.7 0.8 1.0 1.2 · `PAUSE_USER_MS` 150 200 250 300 350 400 · `PAUSE_REF_MS` 60 80 100 120 150 · `FINAL_SLOPE_MIN_ST_S` 3 4 5 6 7 8 10 · `FLAT_RATIO` 0.40 0.45 0.50 0.55 0.60 0.65 0.70 · `FLAT_REF_MIN_STD_ST` 1.0 1.5 2.0 2.5 3.0 · `PITCH_DEVIATION_ST` 2.0 2.5 3.0 3.5 4.0 5.0 · `PD_SIGN_CONSISTENCY` 0.6 0.7 0.8 0.9 · `ALIGN_COST_MAX` 0.90 1.00 1.10 1.20 1.30.
- Đề xuất = giá trị có recall cao nhất trong các giá trị có precision tuning >= 0.95 và n >= 1; hoà thì chọn giá trị gần giá trị hiện tại; không có thì in "không có giá trị đạt 95 %". Tham số dùng chung với điểm tổng hoặc căn (`PAUSE_USER_MS` cũng đổi `metrics.speed`; `ALIGN_COST_MAX` đổi `alignment.ok` của cả ba rule theo từ) có ghi chú ngay trên bảng.
- Sweep chỉ in stdout, không ghi `thresholds.py`. Liam chọn giá trị, tự sửa `thresholds.py` và tăng `THRESHOLDS_VERSION`; Claude không tự ghi ngưỡng.

### 9. Cờ tắt rule (D-15)

- Năm cờ `STRESS_MISMATCH_ENABLED`, `FINAL_CONTOUR_ENABLED`, `EXTRA_PAUSE_ENABLED`, `PITCH_DEVIATION_ENABLED`, `FLAT_PITCH_ENABLED` trong `thresholds.py`, mặc định `True`. `run_rules` bỏ hẳn lời gọi của rule tắt: không issue, không tip (thứ tự các rule còn lại giữ nguyên). Report ghi `TẮT (D-15)` ở mọi ô của rule đó.
- **Thêm cờ không đổi hành vi nên không tăng `THRESHOLDS_VERSION`** (vẫn `p2-1` khi thêm). Đổi giá trị một cờ thì tăng version, với nhãn do Liam chọn. Cờ chỉ được đổi sau khi Liam duyệt danh sách rule trượt ở 04-11. Lý do tắt từng rule được ghi ở mục "Kết quả" bên dưới; Phase 8 xem lại theo nhãn người chấm. Không chỉnh tiếp dựa trên held-out.

### 10. Trạng thái rule và gate (D-14, D-21)

- Trạng thái held-out của từng rule đang bật và của dòng gộp (04-01 F2): `TẮT` (cờ = False), `FAIL` (precision < 0.90 với n >= 1), `CHƯA ĐỦ MẪU` (n < 5 và không FAIL), `PASS` (n >= 5 và precision >= 0.90). Chỉ `PASS` mới tính là đạt SC1.
- Mã thoát của `analyze.py` (F3): 0 = OK; 1 chỉ khi chạy có held-out VÀ (có rule đang bật `FAIL` hoặc mốc tự so có issue); 2 = dữ liệu hoặc tham số sai (D-05, thiếu split, case sai bất biến, log hoặc nhãn held-out bị đổi). Chạy chỉ tuning không trả 1 (vẫn in cảnh báo khi mốc tự so có issue). Khi thoát 0 hoặc 1, dòng cuối của stdout là `EVAL OK` (kèm cảnh báo nếu có) hoặc `EVAL FAILED: <lý do>`; khi thoát 2 lý do nằm ở stderr và `report.md` không bị ghi đè. Không đặt ngân sách thời gian cứng.

### 11. Test-retest, kiểm tất định và đo điểm tổng (D-19, D-17)

- **Test-retest:** nhóm = (lessonId, segmentIndex, kind, errorType, wordIndex) có >= 2 clip đã gắn và có tiếng trong tập đang chấm. Mỗi nhóm in SD mẫu (ddof 1) của `overall`, `speed`, `pitchRange`, `melodyMatch` và Jaccard trung bình theo cặp của tập (code, wordIndex) giữa các lượt; dòng tổng có SD gộp trong nhóm, Jaccard trung bình và ICC(1,1) một chiều của `overall` khi có >= 5 nhóm, ít hơn thì ghi "chưa đủ mẫu (k nhóm)". Hàm thuần ở `eval/evalkit/stats.py`. Speaker invariance của product.md §4 thuộc Phase 6, không đo ở đây.
- **Kiểm tất định:** mỗi lần chạy chấm lại 5 clip đầu (theo caseId) lần hai từ đầu (nạp lại WAV, tính lại feature bản gốc) và so `overall` bằng `==` và issues theo JSON chuẩn hoá. Report in `Tất định: PASS (n/n)` hoặc `Tất định: FAIL — <caseId…>`; FAIL còn cảnh báo ra stderr. Không vào exit code (D-21 không liệt kê).
- **Đo điểm tổng (D-17), chỉ đo:** theo từng bài, trung vị `overall` chéo câu (bản ghi mốc tự so của câu i chấm với bản gốc câu kế tiếp, vòng; cùng quy ước `scripts/smoke_score.py`) kèm nhãn "rủi ro D-a" khi >= 0.6 và tỉ lệ cặp căn ok; cộng phân bố `overall` (n, trung vị, p25, p75) của mốc tự so, clip `correct` và clip lỗi. Công thức D-04 và trọng số không đổi, `SCORER_VERSION` không đổi; Phase 8 hiệu chỉnh. Phase 4 chỉ chỉnh ngưỡng rule (và `ALIGN_COST_MAX` nếu số liệu cho thấy cần).

### 12. Eval gate cho PR (SC3)

- Từ Phase 4, mọi PR đổi model, ngưỡng hoặc rule chạy `make eval` và dán **khối tóm tắt ở đầu `eval/report.md`** (bảng rule x precision/recall/n/CI x tuning|held-out, `THRESHOLDS_VERSION`, `SCORER_VERSION`, `FEAT_VERSION`, git sha) vào mô tả PR. Báo cáo đầy đủ (danh sách FP, tỉ lệ căn thất bại, test-retest, điểm tổng, nhật ký mở held-out) nằm trong `eval/report.md`, được commit cùng PR (D-20).
- Lần đổi nào dùng số held-out để quyết định thì phải mở held-out có log (`HOLDOUT=1`), không chỉnh ngưỡng tiếp dựa trên số đó.

## Kết quả

Để trống tới 04-12. Mục này chỉ được điền từ `eval/report.md` do một lần `make eval` thật tạo ra, ở đúng git sha và versions ghi ở đầu file: bảng precision/recall theo rule, trạng thái từng rule, rule bị tắt kèm lý do, test-retest, tỉ lệ căn thất bại và điểm tổng.

## Hệ quả

- Rule có thể bị tắt (mục 9). Rule tắt không sinh issue hay tip; Phase 8 xem lại theo nhãn người chấm và bật lại bằng cách sửa cờ, kèm `make eval` và version mới.
- `ALIGN_COST_MAX = 1.10` (ADR 0006, RESEARCH A1) được đo lại qua sweep và bảng "tỉ lệ căn thất bại"; giá trị mới, nếu có, do Liam chọn và tăng `THRESHOLDS_VERSION`.
- Điểm tổng chỉ được đo. Rủi ro D-a (câu sai của cùng một người nói vẫn đạt khoảng 60 % overall vì D-04 là trung bình cộng ba chỉ số) còn nguyên tới Phase 8.
- Ràng buộc vận hành (D-05): không xoá hay xử lý lại các bài dùng cho eval, và không dùng "Sửa câu" hay "Mất chữ cuối?" trên câu đã có case; nếu vi phạm, `analyze.py` thoát 2 nêu caseId thay vì bỏ qua.
- Giới hạn đã biết: sweep quét một chiều (không quét lưới hai chiều giữa hai tham số của cùng một rule); issue khớp `alsoPresent` chỉ là trung tính (không tính TP) nên không làm đẹp precision; số liệu trên một người nói (Liam) chưa chứng minh bất biến theo người nói (Phase 6).
- Từ nay, đổi `eval/cases.jsonl` hay shape `EvalCase` là đổi hợp đồng của regression suite (costly): cần migrate file nhãn và ADR mới.
