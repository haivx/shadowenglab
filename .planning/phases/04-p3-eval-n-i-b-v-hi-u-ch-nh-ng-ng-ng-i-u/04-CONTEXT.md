# Phase 4: P3 · Eval nội bộ và hiệu chỉnh ngưỡng ngữ điệu - Context

**Gathered:** 2026-10-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Ngưỡng các rule ngữ điệu (Lớp C: `STRESS_MISMATCH`, `EXTRA_PAUSE`, `FINAL_CONTOUR`, `FLAT_PITCH`, `PITCH_DEVIATION`) có số liệu chứng minh trên bộ lỗi cố ý. Phạm vi gồm:
- Liam thu khoảng 100 clip lỗi cố ý (mỗi clip 1 lỗi) và khoảng 8 clip mốc đúng, mỗi clip kèm loại lỗi và vị trí từ (EVL-01).
- `make eval` chạy `eval/analyze.py` để chấm lại offline và sinh `eval/report.md`: precision/recall theo từng rule, test-retest (EVL-02).
- Held-out 30% được tách cố định và không dùng khi chỉnh ngưỡng (EVL-03).
- Precision của rule ngữ điệu trên held-out phải ≥ 90% (EVL-04).

Ngoài phạm vi: chấm âm Lớp A (Phase 5), app eval online và nhãn người bản xứ (Phase 6), đổi công thức hay trọng số điểm tổng (Phase 8), CI chạy eval (Step 2).

</domain>

<decisions>
## Implementation Decisions

> Kế thừa, không đổi: contract `ScoreResult`/`Issue` (Phase 1), công thức điểm D-04 của Phase 3, căn thời gian MFCC-DTW và cổng D-02 (ADR 0006), một file ngưỡng có version `scoring/thresholds.py` (D-12), nút "Lưu clip cho eval" ghi WAV + sidecar vào `DATA_DIR/eval_clips/` (REC-04). Các quyết định dưới đây là **Liam đã chốt** trong Discuss Phase 4.

### Gắn nhãn clip lỗi cố ý
- **D-01:** **Khai báo kịch bản trước rồi mới thu.** Liam viết trước từng case trong `eval/cases.jsonl` (câu nào, lỗi gì, từ nào). Sau đó thu trong app như bình thường và bấm "Lưu clip cho eval". `eval/tag_clips.py` (CLI) ghép mỗi clip chưa có nhãn trong `DATA_DIR/eval_clips/` với một case đang chờ. Không thêm UI vào app. Vì nhãn có trước khi nói, nó không bị điểm hệ thống làm lệch.
- **D-02:** **Contract Zod `EvalCase`** nằm trong `packages/contracts/src/eval.ts` và sinh pydantic qua `make contracts` (có drift gate). Shape dự kiến: `caseId`, `lessonId`, `segmentIndex`, dấu nhận diện câu (D-05), `kind: 'error' | 'correct'`, `errorType?`, `wordIndex?`, `alsoPresent?` (D-09), `split: 'tuning' | 'heldout'` (D-12), `clip?` (stem file đã ghép, thêm khi tag), `note?`. Shape cụ thể Liam duyệt ở checkpoint PR contract. — **Reversibility:** costly — `cases.jsonl` đã commit và các script eval phụ thuộc vào nó; đổi shape thì phải migrate file nhãn.
- **D-03:** **`errorType` là enum riêng, tách khỏi `IssueCode`.** Các giá trị mô tả cách Liam cố ý nói sai: `wrong_stress`, `flat`, `extra_pause`, `final_rise` (lên giọng cuối câu), `pitch_off`, `weak_form`, `final_drop` (nuốt âm cuối). `analyze.py` có một bảng ánh xạ errorType → IssueCode kỳ vọng (xem D-10). Đổi rule thì không phải gắn nhãn lại.
- **D-04:** **Commit `eval/cases.jsonl`.** Đây là kịch bản của Liam, không phải "nhãn thô của người chấm", nên được commit và dùng làm regression suite. Audio vẫn gitignored.
- **D-05:** **Audio ở lại `DATA_DIR/eval_clips/`, không chép sang repo.** `EvalCase` lưu dấu nhận diện câu (`startMs`/`endMs` của segment hoặc hash text câu, Claude chọn). Nếu bài bị xoá hoặc câu không còn khớp dấu, `tag_clips.py` và `analyze.py` **báo lỗi và dừng**, không bỏ qua trong im lặng. Ràng buộc vận hành: không xoá hoặc xử lý lại các bài dùng cho eval.
- **D-06:** **`analyze.py` chấm lại từ WAV đã lưu** bằng scorer và ngưỡng hiện tại, gọi thẳng hàm Python (không qua HTTP, không dùng `result_json` cũ). Nhờ vậy, đổi ngưỡng rồi chạy `make eval` là ra số mới ngay.

### Bộ clip và cách đếm đúng
- **D-07:** **Phân bổ khoảng 100 clip lỗi:** khoảng 70 clip ngữ điệu (5 loại × ~14: `wrong_stress`, `flat`, `extra_pause`, `final_rise`, `pitch_off`) và khoảng 30 clip âm (`weak_form`, `final_drop` × ~15). Ở phase này, clip âm làm **negative** cho rule ngữ điệu (không được báo gì). Chúng được để sẵn cho PHN-06 ở Phase 5, không phải thu lại.
- **D-08:** **Một lần báo tính là TP khi:** rule theo từ (`STRESS_MISMATCH`, `PITCH_DEVIATION`) báo **đúng `wordIndex`** đã khai báo, riêng `EXTRA_PAUSE` cho lệch **±1 từ** (ngắt nằm giữa hai từ). Đúng loại nhưng sai từ thì tính FP. Rule mức câu (`FLAT_PITCH`, `FINAL_CONTOUR`) chỉ cần đúng loại trong clip đó.
- **D-09:** **Báo ở chỗ không khai báo thì tính FP** trong precision chính thức (đánh giá bảo thủ). `report.md` liệt kê từng FP kèm clip để Liam nghe lại. Nếu nghe thấy lỗi có thật, Liam ghi vào `EvalCase.alsoPresent`, và **chỉ được ghi cho clip tuning hoặc trước lần mở held-out đầu tiên**. Sau khi đã mở held-out thì không sửa nhãn held-out nữa.
- **D-10:** **Bảng mã chính và mã phụ.** Mỗi errorType có một IssueCode chính (tính vào recall) và một danh sách mã phụ được chấp nhận nếu đúng từ. Mã phụ không tính FP và không tính vào recall. Ví dụ: `wrong_stress` → `STRESS_MISMATCH` (chính), `PITCH_DEVIATION` cùng từ (phụ); `final_rise` → `FINAL_CONTOUR` (chính), `PITCH_DEVIATION` ở từ cuối (phụ). Claude đề xuất bảng đầy đủ, Liam duyệt ở PR.
- **D-11:** **Nguồn câu:** 3–4 bài YouTube giọng Mỹ, audio sạch, nhiều người nói khác nhau, tổng khoảng 25–30 câu. Câu ≥ 5 từ (`STRESS_MIN_WORDS`) và có đuôi câu rõ. Mỗi câu mang 3–4 lỗi khác nhau, mỗi lần thu một lỗi. Phase 6 dùng lại các bài này.
- **D-11b:** **Căn thời gian thất bại** (D-02 của Phase 3 tắt rule theo từ) trên clip lỗi theo từ được **tính là FN**. `report.md` có dòng riêng "tỉ lệ căn thất bại" theo bài và loại lỗi để đo lại `ALIGN_COST_MAX`.

### Held-out và quy trình chỉnh
- **D-12:** **Tách held-out theo câu và phân tầng theo errorType.** Mọi clip của một câu nằm cùng một phía; khoảng 30% mỗi errorType nằm ở held-out. Việc gán là xác định, bằng hash `lessonId:segmentIndex`. Cột `split` được ghi vào `cases.jsonl` và commit **trước khi chấm clip nào**. — **Reversibility:** one-way — sau khi held-out đã được mở, tách lại thì held-out mất giá trị.
- **D-13:** **Chỉnh ngưỡng bằng script quét, Liam chọn.** `eval/sweep.py` quét 1–2 ngưỡng chính của mỗi rule **chỉ trên tuning**, in bảng precision/recall và đề xuất điểm có recall cao nhất trong khi precision tuning ≥ 95% (chừa biên cho held-out). Liam chọn giá trị và sửa `thresholds.py`, tăng `THRESHOLDS_VERSION`. Claude không tự ghi ngưỡng.
- **D-14:** **Tiêu chí 90% áp cho từng rule đang bật và cho tổng gộp.** Rule báo < 5 lần trên held-out được ghi "chưa đủ mẫu", không tính là pass. Mọi precision/recall in kèm khoảng tin cậy Wilson 95%.
- **D-15:** **Rule trượt 90% trên held-out thì tắt rule đó.** Thêm cờ bật/tắt cho từng rule trong `thresholds.py`; rule tắt không sinh issue/tip. Lý do ghi vào ADR, Phase 8 xem lại theo nhãn người chấm. **Không chỉnh tiếp dựa trên held-out.** — **Reversibility:** reversible — bật lại chỉ là sửa cờ trong `thresholds.py`, có `make eval` đi kèm.
- **D-16:** **Khoá held-out.** Trong lúc chỉnh, `make eval` và `sweep.py` chỉ chạy trên tuning. `make eval HOLDOUT=1` mới chấm held-out, và mỗi lần mở được ghi log (thời điểm, `THRESHOLDS_VERSION`, git sha) vào report. Sau khi Phase 4 chốt, `make eval` mặc định in cả hai tập để làm bảng metric cho PR (SC3).
- **D-17:** **Điểm tổng: chỉ đo, không đổi.** `report.md` đo trung vị chéo câu (rủi ro D-a, bài QWYCtbho-vY = 0.616) và phân bố `overall` trên clip đúng so với clip lỗi theo bài. Công thức D-04 và trọng số giữ nguyên, để Phase 8 hiệu chỉnh. Phase 4 chỉ chỉnh ngưỡng rule (và `ALIGN_COST_MAX` nếu số liệu cho thấy cần).

### Mốc đúng, test-retest, report
- **D-18:** **Mốc đúng gồm hai loại.** (a) **Tự so**: audio vocals của bản gốc so với chính nó, sinh tự động cho mọi câu trong bộ eval; kỳ vọng ≈ 100% và **không có issue nào**. (b) Khoảng 8 clip Liam cố đọc sát nhất (`kind: 'correct'`), dùng làm negative: báo bất kỳ rule nào cũng tính FP.
- **D-19:** **Test-retest.** Với các câu có ≥ 2 clip cùng errorType (kể cả `correct`), đo độ lệch `overall` và các chỉ số phụ, cùng độ trùng issue giữa các lần. Liam thu thêm một lần cho khoảng 10 câu. Report in độ lệch chuẩn, và ICC nếu đủ mẫu. Kèm kiểm tra tất định: chấm lại cùng WAV phải ra cùng kết quả.
- **D-20:** **Commit `eval/report.md`.** File chỉ có số liệu và ID clip, không có audio. Đầu file có bảng tóm tắt (rule × P/R/n/CI × tuning|held-out, `THRESHOLDS_VERSION`/`SCORER_VERSION`/`FEAT_VERSION`, git sha) để copy thẳng vào PR. Danh sách FP, tỉ lệ căn thất bại và test-retest nằm phía dưới.
- **D-21:** **Gate.** Khi chạy có held-out, `make eval` trả exit ≠ 0 nếu có rule đang bật với precision held-out < 90%, hoặc clip tự so có issue. Sẵn cho CI ở Step 2. Không đặt ngân sách thời gian cứng.

### Claude's Discretion
- Dấu nhận diện câu cụ thể (`startMs/endMs` hay hash text, hoặc cả hai).
- UX của `tag_clips.py`: gợi ý ghép theo lessonId/segmentIndex của sidecar, xác nhận từng clip.
- Ngưỡng nào là "ngưỡng chính" cho sweep của mỗi rule, và lưới giá trị.
- Cấu trúc thư mục `eval/` (module dùng chung giữa analyze/sweep/tag), cách gọi scorer từ `eval/` (uv project `services/audio`).
- Cách sinh mốc tự so (đọc vocals từ bài, không cần thu).
- Bố cục chi tiết của `report.md` ngoài khối tóm tắt.
- Đề xuất bảng mã chính/phụ (D-10) để Liam duyệt.
- Viết ADR mới (`docs/decisions/0007-…`) cho quy trình eval, cách đếm và cờ tắt rule.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec sản phẩm và roadmap
- `docs/product.md` §3 (Lớp B/C, bảng rule và ngưỡng ban đầu), §4 (bộ eval 3 tầng, held-out 30%, `analyze.py` metrics, regression suite)
- `.planning/ROADMAP.md` — Phase 4 goal + 3 success criteria
- `.planning/REQUIREMENTS.md` — EVL-01..EVL-04 (và PHN-06 cho clip âm để dành)
- `CLAUDE.md` — eval gate từ P3, không tự đổi ngưỡng/contract, không commit audio eval

### Quyết định đã có
- `docs/decisions/0006-cham-ngu-dieu-p2.md` — căn MFCC-DTW, cổng căn, `prepare_features`, D-a
- `.planning/phases/03-p2-ch-m-ng-i-u/03-CONTEXT.md` — D-02 (căn kém → bỏ rule theo từ), D-04 (công thức điểm), D-12/D-13 (cổng chắc chắn, file ngưỡng)
- `docs/decisions/0005-job-runner-attempts-settings-p1.md` — dataDir, attempts, eval clip

### Code chạm tới
- `services/audio/src/audio_service/scoring/thresholds.py` — mọi ngưỡng + versions
- `services/audio/src/audio_service/scoring/scorer.py` (`score_prosody`, `to_score_result`), `scoring/features.py` (`prepare_features`), `scoring/ref_cache.py`
- `services/audio/src/audio_service/rules/engine.py` — rule Lớp C
- `services/audio/src/audio_service/routers/attempts.py` — `_store_eval_clip` (WAV + sidecar `{lessonId, segmentIndex, attempt, text}`)
- `packages/contracts/src/eval.ts` — `Label`, `ClipManifest`; nơi thêm `EvalCase`
- `scripts/smoke_score.py` — mẫu gọi scorer offline trên dữ liệu thật
- `Makefile` target `eval` (stub hiện tại), `.gitignore` (`eval/clips/`, `eval/labels.jsonl`, `eval/manifest.json`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_store_eval_clip` + nút "Lưu clip cho eval" (`apps/web/components/PracticeRoom.tsx`, REC-04): đã ghi WAV đã chuẩn hoá và sidecar JSON vào `DATA_DIR/eval_clips/{lessonId}_{NNNN}_{AA}.wav`. Không cần UI mới.
- `prepare_features` + `score_prosody`: là hàm thuần, gọi được trực tiếp từ script để chấm lại WAV. `scripts/smoke_score.py` là mẫu (đã có chạy tự so và chéo câu, in `timingMs`).
- `ref_cache.py`: feature bản gốc `seg/NNNN.npz`, tính bù lười nếu thiếu.
- `config.eval_clips_dir()`, `data_root()`: dùng để resolve đường dẫn giống app.

### Established Patterns
- Một file ngưỡng có version; đổi giá trị thì tăng `THRESHOLDS_VERSION`, và các version đi vào `ScoreResult.versions`.
- Contract-first: Zod → `make contracts` → pydantic `contracts_gen.py`, drift gate trong `make test`.
- Python chạy qua `uv run --project services/audio --frozen`; ruff + pytest; hàm audio thuần.
- Precision trước recall: không chắc thì không báo (cổng chắc chắn của từng rule).

### Integration Points
- `Makefile`: thay stub `eval` bằng `uv run … python eval/analyze.py` (+ `HOLDOUT=1`), có thể thêm target `eval-sweep`, `eval-tag`.
- `thresholds.py`: thêm cờ bật/tắt từng rule (D-15) và để `rules/engine.py` tôn trọng cờ này.
- `packages/contracts/src/eval.ts`: thêm `EvalCase` (+ enum errorType).

</code_context>

<specifics>
## Specific Ideas

- Liam tự thu toàn bộ clip; nhãn có trước khi nói (kịch bản), không gắn theo điểm hệ thống.
- Không xoá hoặc xử lý lại bài dùng cho eval; script phải dừng to nếu dữ liệu bị đổi.
- Precision tuning ≥ 95% làm biên để held-out ≥ 90%.
- Clip âm (weak form, nuốt âm cuối) thu luôn ở phase này để Phase 5 dùng.

</specifics>

<deferred>
## Deferred Ideas

- Đổi công thức/trọng số điểm tổng (rủi ro D-a) — Phase 8 (logistic theo nhãn người chấm).
- Người bản xứ đọc câu để đo speaker invariance — Phase 6 (app eval) hoặc sau.
- CI chạy `make eval` và fail khi metric giảm — Step 2 (HRD).
- Rule bị tắt vì trượt held-out — Phase 8 xem lại theo nhãn người chấm.

</deferred>

---

*Phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u*
