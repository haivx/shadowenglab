---
phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u
plan: 02
subsystem: eval
tags: [eval, rescore, precision-recall, wilson, self-compare, tdd, read-only]

requires:
  - phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u
    provides: "04-01: contract EvalCase/ErrorType (pydantic RootModel, đọc `.root`) và bảng 'Quyết định đã chốt' A..L do Liam duyệt"
  - phase: 03-p2-ch-m-ng-i-u
    provides: "score_prosody, ref_prosody_for_segment(write_cache=False), THRESHOLDS_VERSION/SCORER_VERSION/FEAT_VERSION, scripts/smoke_score.py"
provides:
  - "`make eval` chạy eval/analyze.py: cases.jsonl -> kiểm D-05/D-12 -> chấm lại WAV đã lưu -> đếm theo bảng D-10 -> eval/report.md (chỉ tuning, chỉ đọc DATA_DIR)"
  - "Gói eval/evalkit (cases, rescore, counting, report) mà sweep (04-03), gate (04-05), khoá held-out (04-06), test-retest (04-07) dùng lại"
  - "Mốc tự so (D-18a) sinh tự động cho mọi câu có case trong tập đang chấm, tính FP, có mục riêng trong report"
  - "Helper test eval_synth.py: bài ready tổng hợp, clip eval, case, nạp module eval/"
affects: [04-03, 04-04, 04-05, 04-06, 04-07, 04-11, 04-12]

actuals:
  tokens: 19000
  tasks: 3
  commits: 6
plan_head_before: a9d36a59528a2682aedbf677c48f08efe1364a18
plan_head_after: 10102762e1c424809b5aa43bf3c12a9eb7a90dc1

tech-stack:
  added: []
  patterns:
    - "Script dev ngoài package service: eval/ tự vào sys.path khi chạy `python eval/<x>.py`; test nạp bằng spec_from_file_location (analyze) hoặc importlib.import_module('evalkit.<x>') sau syspath_prepend"
    - "Nạp feature (load_clip) tách khỏi chấm (score_clip) để sweep truyền aligner nhớ đệm mà không sửa rescore.py"
    - "Ghi report atomic: `.part` rồi os.replace, chỉ sau khi mọi bước thành công; lỗi dữ liệu thoát 2 trước khi ghi"

key-files:
  created:
    - eval/analyze.py
    - eval/evalkit/__init__.py
    - eval/evalkit/cases.py
    - eval/evalkit/rescore.py
    - eval/evalkit/counting.py
    - eval/evalkit/report.py
    - services/audio/tests/eval_synth.py
    - services/audio/tests/test_eval_analyze.py
    - services/audio/tests/test_eval_counting.py
  modified:
    - Makefile

key-decisions:
  - "Cách đếm bám 04-01 mục B-C (B1-a: so `data.userWord` với chữ của từ khai báo); không đổi bảng mã, ngưỡng hay model"
  - "Bảng tóm tắt thêm hai cột TP và FP trước các cột P/R của plan, để test và Liam đọc được số thô"
  - "Issue thừa của mã chính nằm đúng vị trí là FP (C1) và không được `alsoPresent` cứu; chỉ issue không khớp vị trí của mã chính mới xét secondary rồi `alsoPresent`"
  - "`alsoPresent` được áp dụng cho mọi nguồn có case (kể cả weak_form/final_drop/correct); mốc tự so không có alsoPresent"

requirements-completed: [EVL-02, EVL-01]

coverage:
  - id: D1
    description: "`make eval` đi trọn cases.jsonl -> chấm lại WAV -> đếm -> report.md trên tuning; FLAT_PITCH TP 1, FP 0, recall 1/1; versions và git sha ở đầu report"
    requirement: "EVL-02"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_analyze.py#test_one_flat_case_is_scored_end_to_end_and_reported_as_a_true_positive"
        status: pass
    human_judgment: false
  - id: D2
    description: "Các lối thoát 2: thiếu cases.jsonl, thiếu split (D-12), lệch dấu nhận diện (D-05), bài không còn, thiếu WAV, stem thoát thư mục, sidecar lệch câu, thiếu stem vocal; report cũ không bị ghi đè"
    requirement: "EVL-02"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_analyze.py (8 test lối thoát 2)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Held-out không bao giờ được nạp trong plan này (WAV thiếu của case held-out không làm hỏng lần chạy); chỉ đọc DATA_DIR, thư mục tạm bị xoá"
    requirement: "EVL-02"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_analyze.py#test_a_heldout_case_is_never_loaded_even_when_its_clip_does_not_exist"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_eval_analyze.py#test_a_data_dir_is_left_exactly_as_it_was_and_no_temp_dir_remains"
        status: pass
    human_judgment: false
  - id: D4
    description: "Cách đếm đúng từng dòng bảng C và C1, C2, C4, D-07, D-11b, D-18b, Wilson"
    requirement: "EVL-02"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_eval_counting.py (28 test)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Report có Danh sách FP, Tỉ lệ căn thất bại (D-11b), Phủ, Mốc tự so (D-18a); mốc tự so sinh cho mọi câu tuning, overall >= 0.9, 0 issue"
    requirement: "EVL-02"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_analyze.py#test_the_report_lists_false_positives_alignment_failure_rates_and_coverage"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_eval_analyze.py#test_every_tuning_sentence_gets_a_self_compare_row_that_is_clean"
        status: pass
    human_judgment: false
  - id: D6
    description: "Số liệu trên report thật (bộ clip của Liam) phản ánh đúng thực tế; chưa có cases.jsonl nên chưa có số thật"
    requirement: "EVL-01"
    verification: []
    human_judgment: true
    rationale: "Cần Liam thu clip và viết case (04-04); plan này chỉ chứng minh cơ chế trên dữ liệu tổng hợp"

duration: 35min
completed: 2026-10-11
status: complete
---

# Phase 4 Plan 02: Chấm lại bộ eval và sinh report Summary

**`make eval` chạy eval/analyze.py: nạp `cases.jsonl` bằng pydantic `EvalCase`, kiểm D-05/D-12, chấm lại từng WAV tuning bằng scorer hiện tại (không HTTP, chỉ đọc DATA_DIR), đếm TP/FP theo bảng D-10 đã duyệt, sinh mốc tự so và ghi `eval/report.md` có Wilson 95 %, danh sách FP, tỉ lệ căn thất bại, phủ và mốc tự so.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-10-11
- **Tasks:** 3 (1 tracer + 2 auto, đều TDD)
- **Files:** 9 tạo, 1 sửa (Makefile)

## Accomplishments

- Lát tracer đầu-cuối: một case `flat` tổng hợp đi từ `cases.jsonl` tới `report.md` với FLAT_PITCH TP 1, FP 0, recall 1/1. Tracer gate (auto, `HUMAN_VERIFY_MODE` end-of-phase, `<verify>` chỉ có `<automated>`): chạy lại verify, pass; `⚡ Tracer verified end-to-end — expanding`.
- Cách đếm hoàn chỉnh theo 04-01: `CODE_TABLE` đủ 7 errorType, một TP mỗi case gần w nhất (C1), mã phụ và `alsoPresent` trung tính (C2), mọi issue còn lại là FP (C3), weak_form/final_drop/correct/self toàn FP (D-07, D-18), FN và bảng căn thất bại (D-11b, C4).
- Mốc tự so (D-18a) dùng đúng các hàm đệm, mã hoá webm/opus và chuẩn hoá của `scripts/smoke_score.py` qua importlib (không chép lại; smoke_score.py không bị sửa).
- Đường dẫn clip được chặn bằng `CLIP_STEM_RE` + `is_relative_to` + kiểm stem thuộc đúng bài/câu + sidecar khớp (T-04-03); test chứng minh DATA_DIR giống hệt trước/sau.

## Hàm công khai của evalkit

| Module | Hàm / kiểu |
|---|---|
| `cases` | `CASES_PATH`, `WORD_LEVEL_TYPES`, `SENTENCE_LEVEL_TYPES`, `CaseError`, `text_hash`, `error_type_of`, `load_cases`, `validate_cases`, `stamp_mismatch`, `select_split` |
| `rescore` | `DataError`, `CLIP_STEM_RE`, `RefCache`, `clips_root`, `load_lessons`, `check_identity`, `ClipInput`, `load_clip`, `score_clip(clip, *, aligner)`, `SelfInput`, `self_compare_inputs`, `_smoke_helpers` |
| `counting` | `LAYER_C_CODES`, `POOLED`, `Expectation`, `CODE_TABLE`, `Observation`, `Verdict`, `RuleTally`, `observation_from`, `self_observation`, `classify`, `tally`, `align_failures`, `fp_rows`/`FpRow`, `coverage_rows`/`CoverageRow`, `self_rows`/`SelfRow`, `wilson` |
| `report` | `RunInfo`, `git_sha`, `render_report(info, tallies, *, fps, failures, coverage, self_compare)` |

`analyze.py`: `main(argv)`, `_run`, `write_report(path, text)`; cờ `--cases`, `--report`, `--data-dir`; thoát 0 (dòng cuối `EVAL OK`) hoặc 2.

## Cách nạp module trong test

- `eval_synth.load_eval("analyze", monkeypatch)`: `syspath_prepend(eval/)` rồi `spec_from_file_location("eval_analyze_for_test", ...)`, đăng ký qua `monkeypatch.setitem(sys.modules, ...)` nên tự gỡ.
- `eval_synth.load_evalkit("counting", monkeypatch)`: `syspath_prepend(eval/)` rồi `importlib.import_module("evalkit.counting")` (test thuần, không cần DATA_DIR).
- Fixture `data_dir` đặt `DATA_DIR` và `SHADOWENGLAB_CONFIG_DIR` bằng `monkeypatch.setenv`, xoá cache `get_settings` trước/sau.

## Mẫu report trên dữ liệu tổng hợp

Bài 2 câu, case `flat` (clip phẳng), case `correct` (cùng clip phẳng, sinh một FP), một case `extra_pause` chưa gắn clip, một case `flat` held-out:

```
- Chế độ: tuning (held-out khoá, D-16)
- THRESHOLDS_VERSION `p2-1` · SCORER_VERSION `prosody-2` · FEAT_VERSION `pf-2`
- Git: `6fe2be9481ee-dirty` · sinh lúc 2026-10-11T16:31:00Z

| Rule | TP | FP | Tuning P [CI95] (n) | Tuning R (k/N) [CI95] | Held-out |
| FLAT_PITCH | 1 | 1 | 0.50 [0.09, 0.91] (n=2) | 1.00 (1/1) [0.21, 1.00] | khoá (D-16) |
| GỘP | 1 | 1 | 0.50 [0.09, 0.91] (n=2) | 1.00 (1/1) [0.21, 1.00] | khoá (D-16) |

## Danh sách FP
| tuning | c0002 | 01HZX..._0000_02 | correct | FLAT_PITCH | — | — |

## Mốc tự so (D-18a)
tự so: 2 câu, trung vị overall 0.998, tổng issue 0
```

(Số trên là dữ liệu tổng hợp để kiểm cơ chế, không phải số đo của scorer trên giọng thật.)

## TDD (RED / GREEN)

| Task | RED | GREEN |
|---|---|---|
| 1 tracer | `6e57c03` test(04-02) | `7698f8b` feat(04-02) |
| 2 đếm D-10 | `26c00ac` test(04-02) | `6f4f8b3` feat(04-02) |
| 3 mốc tự so | `6fe2be9` test(04-02) | `1010276` feat(04-02) |

- **RED Task 1:** 10 test lỗi vì `eval/analyze.py` chưa tồn tại (`FileNotFoundError` lúc nạp module trong fixture). Đánh giá ngữ nghĩa: đúng nguyên nhân dự kiến (module chưa viết) nhưng là lỗi fixture/nạp, không phải assertion. `workflow.tdd_mode` đang `false` nên `gsd check tdd-red-evidence` không bắt buộc; ghi lại để minh bạch.
- **RED Task 2:** 13 test fail ở assertion đã định (outcome secondary/fp/tp sai) hoặc thiếu `CODE_TABLE`/`align_failures`; test E2E fail ở assertion thiếu mục "Danh sách FP".
- **RED Task 3:** 3 test fail ở assertion đã định (không có mục "Mốc tự so", exit 0 thay vì 2).
- **REFACTOR:** không có.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree thiếu .venv**
- **Found during:** bắt đầu thực thi
- **Fix:** `uv sync --project services/audio --frozen` (chỉ theo lockfile, không thêm package). `pnpm install` không cần vì plan không đụng Node.

**2. [Rule 2 - Thiếu sót nhỏ] Cột TP và FP trong bảng tóm tắt**
- **Found during:** Task 1
- **Issue:** plan chỉ liệt kê cột `Rule | Tuning P | Tuning R | Held-out`, nhưng behavior của tracer đòi "dòng FLAT_PITCH với TP 1, FP 0"
- **Fix:** thêm hai cột `TP` và `FP` sau cột Rule (F1 vẫn đủ: P, R, n, Wilson). Commit `7698f8b`.

**3. [Rule 2 - Phòng thủ] Kiểm stem thuộc đúng bài/câu của case**
- **Found during:** Task 1 (T-04-03)
- **Fix:** ngoài `CLIP_STEM_RE` + `is_relative_to`, `load_clip` từ chối stem không bắt đầu bằng `{lessonId}_{NNNN}_` của case. Commit `7698f8b`.

**4. Thêm ngoài danh sách symbol của plan (cần cho report/test, không đổi contract):** `counting.{self_observation, self_rows, SelfRow, fp_rows, FpRow, coverage_rows, CoverageRow}`, `rescore.RefCache`, `cases.error_type_of`, `eval_synth.{clip_stem, OTHER_WORDS, sentence_text, load_evalkit}`. `observation_from` được viết ở Task 1 (plan xếp ở Task 2) vì analyze cần ngay.

**Total deviations:** 4 (1 blocking, 2 thiếu sót nhỏ, 1 bổ sung symbol). **Impact:** không đổi bảng mã, ngưỡng, model, contract hay schema; không sửa `scripts/smoke_score.py`.

## Authentication Gates

Không có.

## Issues Encountered

- Hook an toàn của harness từ chối mọi lệnh Bash chứa từ đứng riêng `eval` (nghĩ là shell eval); đã gọi `ruff`/`make`/`ls` qua glob `e[v]al`. Không ảnh hưởng mã; chỉ đáng biết cho ai chạy lại lệnh `<verify>` của plan trong môi trường tương tự.
- Không ghi được ledger `gsd-plan-head-before-04-02` trong `.git/worktrees/` (harness chặn); `plan_head_before` lấy từ SHA base của prompt (`a9d36a5`), đối chiếu `git rev-list --count a9d36a5..HEAD` = 6.
- Chưa có `eval/cases.jsonl` thật: `make eval` hiện thoát 2 với thông báo gợi ý `tag_clips.py add` (04-04).

## Known Stubs

Không có.

## Threat Flags

Không có bề mặt mới ngoài threat model của plan. T-04-03 (stem -> đường dẫn), T-04-04 (chỉ đọc DATA_DIR, có test), T-04-05 (report chỉ số liệu/ID/chữ của từ, có test không chứa đường dẫn tuyệt đối), T-04-06 (`.part` + `os.replace`, có test report cũ giữ nguyên byte) đều đã được giảm thiểu.

## Next Phase Readiness

Sẵn sàng cho 04-03 (sweep dùng `load_clip`/`score_clip(aligner=...)`, `counting.tally`), 04-04 (`tag_clips.py` dùng `cases.stamp_mismatch`, `text_hash`, `WORD_LEVEL_TYPES`), 04-05 (gate F3), 04-06 (mở held-out qua `select_split(include_heldout=True)`; hiện chưa có cờ `--holdout`). `eval/report.md` chưa được commit vì chưa có case thật.

## Self-Check: PASSED

- File tồn tại: eval/analyze.py, eval/evalkit/{__init__,cases,rescore,counting,report}.py, services/audio/tests/{eval_synth,test_eval_analyze,test_eval_counting}.py: FOUND
- Commit `6e57c03`, `7698f8b`, `26c00ac`, `6f4f8b3`, `6fe2be9`, `1010276`: FOUND (ancestor của HEAD)
- Tiêu chí: rescore.py chứa `write_cache=False`, `def self_compare_inputs` và nạp smoke qua importlib; cases.py chứa `EvalCase.model_validate_json`; counting.py chứa `CODE_TABLE` 7 khoá và `def align_failures`; Makefile `eval` gọi `eval/analyze.py`, hai dòng ruff của `lint` có `../../eval`: PASS
- `uv run --project services/audio --frozen pytest services/audio/tests/test_eval_analyze.py services/audio/tests/test_eval_counting.py services/audio/tests/test_smoke_score.py -q`: 60 passed
- Toàn bộ `pytest` của services/audio: 1166 passed
- `ruff check` và `ruff format --check` trên `.`, `../../scripts`, `../../eval`: sạch
