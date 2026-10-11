# eval — Bộ eval nội bộ và phân tích

Bộ eval nội bộ của Phase 4 (ADR `docs/decisions/0007-eval-noi-bo-p3.md`): Liam viết kịch bản lỗi cố ý trước, thu clip trong app, ghép clip với kịch bản, rồi `make eval` chấm lại từng WAV bằng scorer hiện tại và sinh `report.md`. Chạy trên macOS Apple Silicon qua `uv run --project services/audio --frozen`; mọi lệnh chỉ đọc `DATA_DIR`.

## File được commit

- `cases.jsonl`: kịch bản của Liam, mỗi dòng một `EvalCase` (`packages/contracts/src/eval.ts`): câu nào, lỗi gì, từ nào, `split`, `clip`. Đây là regression suite, không phải nhãn thô của người chấm (D-04).
- `report.md`: số liệu và ID clip do `make eval` sinh, không có audio. Đầu file là khối tóm tắt (rule x precision/recall/n/CI95 x tuning|held-out, versions, git sha) để dán vào PR (D-20, SC3). Phía dưới: danh sách FP, tỉ lệ căn thất bại, mốc tự so, test-retest và dòng tất định, điểm tổng (D-17, chỉ đo), phủ, nhật ký mở held-out.
- `holdout_log.jsonl`: mỗi lần mở held-out thêm một dòng (thời điểm, versions, git sha, split và digest nhãn); nhãn held-out bị đóng băng theo dòng đầu (D-16, D-09). Chỉ sinh ra ở lần `make eval HOLDOUT=1` thật đầu tiên.

## Không commit

- Audio: `DATA_DIR/eval_clips/` (app ghi khi bấm "Lưu clip cho eval") và `eval/clips/`, gitignored qua `*.wav` và `eval/clips/`.
- Nhãn thô của người chấm: `labels.jsonl` (app eval, Phase 6).

## Script và gói

- `analyze.py`: nạp `cases.jsonl`, kiểm dấu nhận diện câu (D-05), chấm lại WAV (D-06), đếm TP/FP/FN theo bảng mã chính/phụ và ghi `report.md`. Mặc định chỉ case `tuning`; `--holdout` mở held-out. Thoát 0 (`EVAL OK`), 1 (chỉ khi chạy có held-out: rule đang bật FAIL hoặc mốc tự so có issue, D-21) hoặc 2 (dữ liệu hoặc tham số sai).
- `sweep.py`: quét từng ngưỡng trên tuning, in precision/recall từng giá trị và dòng "Đề xuất"; không đọc held-out, không ghi `thresholds.py`. Liam chọn giá trị và tự sửa `thresholds.py`, tăng `THRESHOLDS_VERSION`.
- `tag_clips.py`: quy trình viết kịch bản và ghép clip, các lệnh con `words` (liệt kê bài, câu, chỉ số từ), `add` (viết case), `split` (chốt held-out một lần, commit trước khi thu), `tag` (ghép clip với case chờ), `also` (thêm `alsoPresent`) và `check` (bảng phủ, ngưỡng nghiệm thu).
- `evalkit/`: `cases` (nạp, kiểm bất biến, split), `rescore` (nạp WAV, chấm lại, mốc tự so), `counting` (cách đếm, Wilson), `report` (dựng `report.md`), `holdout` (log, đóng băng), `overrides` (ghi đè ngưỡng cho sweep), `stats` (test-retest, ICC(1,1), tất định, điểm tổng).

## Lệnh

```
make eval                       # chấm lại tuning -> eval/report.md (held-out khoá)
make eval HOLDOUT=1             # mở held-out: thêm một dòng vào holdout_log.jsonl, áp gate D-21
make eval-tag                   # ghép clip "Lưu clip cho eval" với kịch bản cases.jsonl
make eval-sweep                 # quét ngưỡng trên tuning, chỉ in
make eval-sweep PARAM=FLAT_RATIO  # chỉ một tham số
```

Quy trình: `tag_clips.py words` và `add` viết kịch bản → `split` chốt held-out và commit `cases.jsonl` → thu clip trong app → `make eval-tag` → `tag_clips.py check` → `make eval` và `make eval-sweep` để chỉnh trên tuning → `make eval HOLDOUT=1` một lần khi Liam đã chốt toàn bộ case held-out.

`export_clips.py` (xuất clip cho app eval) thuộc Phase 6 (RAT-08), chưa có. Spec: `docs/product.md` mục 4.
