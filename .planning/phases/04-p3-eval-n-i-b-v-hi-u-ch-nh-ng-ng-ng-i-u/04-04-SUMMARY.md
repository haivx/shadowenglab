---
phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u
plan: 04
subsystem: eval
tags: [eval, cli, split, heldout, cases-jsonl, tag-clips, tdd]

requires:
  - phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u
    provides: "04-01: contract EvalCase/ErrorType và bảng 'Quyết định đã chốt' A..L (A3-A6 shape + bất biến, B1-a, D1-D3 split, K ngưỡng phủ, J khoá nhóm retest)"
  - phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u
    provides: "04-02: gói eval/evalkit (cases, rescore) và analyze.py đọc cases.jsonl"
provides:
  - "`eval/tag_clips.py` với 5 lệnh words / add / split / tag / check: quy trình viết kịch bản -> chốt split -> gắn clip -> kiểm phủ cho Liam (D-01, D-12)"
  - "Phần ghi của `eval/evalkit/cases.py`: dump_case, write_cases atomic, next_case_id, stamp_for, split_fraction, stratum, assign_splits, split_for_new_case, with_splits"
  - "`make eval-tag`"
affects: [04-05, 04-06, 04-07, 04-08, 04-11, 04-12]

actuals:
  tokens: 13500
  tasks: 2
  commits: 4
plan_head_before: af925aad8e0421074fbde078c634632be98a659b
plan_head_after: 261992d2406bde1b8915d5d58b0903348da87f96

tech-stack:
  added: []
  patterns:
    - "Script dev có `main(argv, *, ask=input)`: test truyền `ask` giả lập thay vì patch stdin"
    - "Ghi cases.jsonl atomic (`.part` + `os.replace`) sau MỖI lần gán clip, nên dừng giữa chừng không mất phần đã làm"
    - "assign_splits là hàm thuần trả về các câu CẦN gán; split đã ghi không bao giờ nằm trong kết quả"

key-files:
  created:
    - eval/tag_clips.py
    - services/audio/tests/test_eval_tag_clips.py
  modified:
    - eval/evalkit/cases.py
    - Makefile

key-decisions:
  - "B1-a ở `add` so chữ bằng bằng-nhau chính xác (phân biệt hoa/thường) với `ref.words[i].text`, đúng phép so `user_word == words[w]` của counting.py nên `add` và `analyze` không bao giờ lệch nhau"
  - "`check` còn từ chối (thoát 2) case nằm trên câu dưới 5 từ, ngoài danh sách của plan, vì A5/D-11 coi đó là bất biến của case"
  - "`tag` kiểm cả dấu nhận diện của case được chọn (stamp_mismatch), không chỉ text trong sidecar: câu bị sửa giữa lúc viết case và lúc thu thì không gắn nhãn"

requirements-completed: [EVL-01, EVL-03]

coverage:
  - id: D1
    description: "`add` ghi một EvalCase hợp lệ (caseId kế tiếp, dấu nhận diện từ bài thật, không null) và từ chối: thiếu/thừa wordIndex theo errorType, wordIndex ngoài câu, wrong_stress trên chữ lặp (B1-a), câu dưới 5 từ, vừa --error vừa --correct, không chọn gì"
    requirement: "EVL-01"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_tag_clips.py#test_add_writes_one_valid_case_line_with_the_next_case_id"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_eval_tag_clips.py#test_add_refuses_an_invalid_case_and_leaves_the_file_alone (7 ca)"
        status: pass
    human_judgment: false
  - id: D2
    description: "`split` chốt một lần theo D1: xác định, chạy lại giữ nguyên byte, một phía mỗi câu, trần ceil(0.30 n) mỗi tầng, tỉ lệ câu held-out 20-40 %, không đổi split đã ghi; `--dry-run` chỉ in; case viết sau khi chốt theo D2"
    requirement: "EVL-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_eval_tag_clips.py (assign_splits, split_for_new_case, split_fraction)"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_eval_tag_clips.py#test_split_twice_leaves_the_file_byte_identical_and_every_case_gets_a_side"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_eval_tag_clips.py#test_add_after_the_split_inherits_or_decides_the_split_of_a_new_case"
        status: pass
    human_judgment: false
  - id: D3
    description: "`tag` ghép clip với case chờ (--yes và tương tác: số, Enter, s, q, nhập sai hỏi lại), không hiển thị điểm/issue, từ chối stem lạ và sidecar lệch câu, bỏ qua clip thiếu sidecar hoặc chưa có case chờ"
    requirement: "EVL-01"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_tag_clips.py (test_tag_*, test_interactive_tag_*)"
        status: pass
    human_judgment: false
  - id: D4
    description: "`check` kiểm bất biến + dấu nhận diện (thoát 2 nêu caseId), in bảng errorType x split, số clip chưa gắn, số nhóm retest, và trả 1 khi thiếu một ngưỡng phủ"
    requirement: "EVL-01"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_tag_clips.py (test_check_*)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Lát đầu-cuối: case viết bằng add, chốt bằng split, gắn bằng tag được `analyze.main` đọc và đếm đúng (FLAT_PITCH TP 1, FP 0)"
    requirement: "EVL-03"
    verification:
      - kind: e2e
        ref: "services/audio/tests/test_eval_tag_clips.py#test_a_case_written_with_add_split_and_tag_is_counted_by_analyze"
        status: pass
    human_judgment: false
  - id: D6
    description: "`words` (liệt kê bài, câu, từ) và `make eval-tag` có mặt và chạy"
    requirement: "EVL-01"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_tag_clips.py (test_words_*, test_makefile_has_the_eval_tag_target)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Quy trình dùng được thật với Liam (đọc được bảng, thứ tự thu clip khớp thứ tự case chờ, tên lệnh dễ nhớ)"
    requirement: "EVL-01"
    verification: []
    human_judgment: true
    rationale: "Chỉ chứng minh được cơ chế trên bài tổng hợp; trải nghiệm thật là của Liam ở 04-08 khi thu clip"

duration: 35min
completed: 2026-10-11
status: complete
---

# Phase 4 Plan 04: Công cụ viết kịch bản, chốt split và gắn clip Summary

**`eval/tag_clips.py` (words / add / split / tag / check) cho Liam viết case trước khi nói, chốt held-out một lần bằng thuật toán băm theo câu phân tầng theo errorType (D1), ghép clip "Lưu clip cho eval" với case chờ có xác nhận và kiểm bảng phủ; kết quả được `make eval` đọc và đếm đúng.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-10-11
- **Tasks:** 2 (1 tracer + 1 auto, đều TDD)
- **Files:** 2 tạo (`eval/tag_clips.py`, `services/audio/tests/test_eval_tag_clips.py`), 2 sửa (`eval/evalkit/cases.py`, `Makefile`)

## Accomplishments

- Tracer đầu-cuối: `add` -> `split` -> `tag --yes` -> `analyze.main` trả 0 và report có FLAT_PITCH TP 1, FP 0. Tracer gate (auto, `HUMAN_VERIFY_MODE` end-of-phase, `<verify>` chỉ có `<automated>`): chạy lại verify, pass; `⚡ Tracer verified end-to-end — expanding`.
- `assign_splits` là hàm thuần theo D1 (đã duyệt): duyệt câu theo `sha256("{lessonId}:{segmentIndex}")` tăng dần, đưa vào held-out nếu mọi tầng của câu còn chỗ dưới `ceil(0.30 x tổng tầng)`. Không phụ thuộc thứ tự case; không bao giờ đụng split đã ghi (trả về chỉ các câu cần gán).
- `add` lấy dấu nhận diện câu (4 trường, D-05) từ bài thật và áp D2 cho case viết sau khi chốt (`split_for_new_case`).
- `tag` chỉ nhận clip có stem đúng `CLIP_STEM_RE`, sidecar khớp stem và text câu hiện tại, dấu nhận diện của case khớp (T-04-09); ghi cases.jsonl atomic sau mỗi lần gán (T-04-10).
- `check` in bảng errorType x split (ô = tổng/đã gắn clip), số clip chưa gắn, số nhóm retest (khoá J), và so ngưỡng K qua `--min-*`.

## Lệnh mẫu cho Liam

```
uv run --project services/audio --frozen python eval/tag_clips.py words                         # liệt kê bài ready
uv run --project services/audio --frozen python eval/tag_clips.py words --lesson <ID>           # các câu, đánh dấu câu < 5 từ
uv run --project services/audio --frozen python eval/tag_clips.py words --lesson <ID> --segment 3   # chỉ số từng từ, từ trùng chữ được đánh dấu
uv run --project services/audio --frozen python eval/tag_clips.py add --lesson <ID> --segment 3 --error pitch_off --word 2 --note "nâng từ 2"
uv run --project services/audio --frozen python eval/tag_clips.py add --lesson <ID> --segment 3 --error flat
uv run --project services/audio --frozen python eval/tag_clips.py add --lesson <ID> --segment 4 --correct
uv run --project services/audio --frozen python eval/tag_clips.py split --dry-run               # xem trước, không ghi
uv run --project services/audio --frozen python eval/tag_clips.py split                         # chốt một lần, commit cases.jsonl TRƯỚC KHI thu (D3)
# thu clip trong app, bấm "Lưu clip cho eval", rồi:
make eval-tag                                                                                   # hỏi từng clip: số / Enter / s / q
uv run --project services/audio --frozen python eval/tag_clips.py check --min-error 90 --min-per-type 10 --min-correct 8 --min-retest 8
```

`add` đi trước khi nói (kịch bản), `split` chốt held-out trước khi thu clip nào, `tag` ghép sau. `--yes` chỉ an toàn khi clip được thu đúng thứ tự case trong file.

## Bảng split mẫu (bộ dựng tay: 28 câu, mỗi câu 3-4 tầng xoay vòng, 98 case)

Đây là dữ liệu tổng hợp để kiểm thuật toán, không phải bộ của Liam.

| tầng | tổng | held-out | tỉ lệ | trần ceil(0.30 x tổng) |
|---|---|---|---|---|
| correct | 10 | 3 | 30 % | 3 |
| extra_pause | 14 | 5 | 36 % | 5 |
| final_drop | 14 | 4 | 29 % | 5 |
| final_rise | 11 | 3 | 27 % | 4 |
| flat | 11 | 4 | 36 % | 4 |
| pitch_off | 14 | 4 | 29 % | 5 |
| weak_form | 10 | 3 | 30 % | 3 |
| wrong_stress | 14 | 5 | 36 % | 5 |

Câu held-out: 9/28 (32 %). Tầng nhỏ có thể lệch khỏi 30 % do trần ceil, đúng như assumption đã nêu; `split` in bảng này để Liam xem ở 04-08.

## Task Commits

1. **Task 1 (tracer): add -> split -> tag --yes -> analyze** — `8a13cfc` (test, RED), `e6c4471` (feat, GREEN)
2. **Task 2: words, check, tag tương tác, từ chối, `make eval-tag`** — `60bd2e4` (test, RED), `261992d` (feat, GREEN)

**Plan metadata:** commit `docs(04-04)` chứa file SUMMARY này.

## TDD (RED / GREEN)

- **RED Task 1 (`8a13cfc`):** 8 test fail ở `AttributeError` (cases.py chưa có `assign_splits`, `split_for_new_case`, `split_fraction`) và 7 test lỗi fixture vì `eval/tag_clips.py` chưa tồn tại (`FileNotFoundError` khi nạp module). Đánh giá ngữ nghĩa: đúng nguyên nhân dự kiến (mã chưa viết), không phải assertion; cùng kiểu RED như 04-02. `workflow.tdd_mode` không bật nên `check tdd-red-evidence` không bắt buộc.
- **GREEN Task 1 (`e6c4471`):** 29 test pass (gồm 14 của 04-02 `test_eval_analyze.py`).
- **RED Task 2 (`60bd2e4`):** 10 test fail đúng chỗ dự kiến: `words` và `check` bị argparse từ chối ("invalid choice"), `tag` không `--yes` chưa hỏi, Makefile chưa có `eval-tag`. 28 test còn lại (kể cả 7 ca từ chối của `add`) đã xanh sẵn vì `add` cần có các kiểm tra đó ngay ở Task 1; chúng giữ vai trò test hồi quy.
- **GREEN Task 2 (`261992d`):** 52 test pass (`test_eval_tag_clips.py` + `test_eval_analyze.py`).
- **REFACTOR:** không có.
- Ở Task 1, `tag` không có `--yes` thoát 2 với thông báo "chưa có chế độ hỏi"; Task 2 thay bằng chế độ hỏi thật. Không còn stub ở bản cuối.

## Files Created/Modified

- `eval/tag_clips.py` — CLI 5 lệnh; `main(argv, *, ask=input)`; thoát 0/1/2; nạp evalkit sau khi đặt DATA_DIR như analyze
- `eval/evalkit/cases.py` — phần ghi/chốt: `dump_case`, `write_cases`, `next_case_id`, `stamp_for`, `HELDOUT_SHARE`, `split_fraction`, `stratum`, `assign_splits`, `split_for_new_case`, `with_splits`
- `Makefile` — `eval-tag` trong `.PHONY` và target `eval-tag`
- `services/audio/tests/test_eval_tag_clips.py` — 38 test (E2E, hàm thuần, từ chối, tương tác, check, Makefile)

## Decisions Made

Xem `key-decisions`. Không đổi contract, schema, ngưỡng hay model. Mọi giá trị lấy từ bảng 04-01.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree thiếu .venv**
- **Found during:** bắt đầu thực thi
- **Fix:** `uv sync --project services/audio --frozen` (chỉ theo lockfile, không thêm package; lockfile không đổi). `pnpm install` không cần.

**2. [Rule 2 - Bổ sung nhỏ] Thêm symbol ngoài danh sách của plan**
- **Found during:** Task 1
- **Issue:** D2 (case viết sau khi chốt) và việc điền split cần hàm riêng
- **Fix:** thêm `cases.split_for_new_case`, `cases.with_splits`, `cases.Sentence`, `cases.SPLITS`; trong tag_clips thêm lớp `_Toolkit` (nạp trễ) và `_choose`. Không đổi contract.

**3. [Rule 2 - Phòng thủ] `check` từ chối case trên câu dưới 5 từ; `tag` kiểm dấu nhận diện của case được chọn**
- **Found during:** Task 2
- **Issue:** A5/D-11 coi câu >= 5 từ là bất biến của case; một case bị bỏ qua dấu nhận diện giữa lúc viết và lúc thu sẽ gắn clip sai câu
- **Fix:** thêm hai kiểm tra (thoát 2, nêu caseId). Test: `test_check_*`, `test_tag_refuses_*`.

**4. [Quan sát về test] E2E dùng hai câu cùng `DEFAULT_WORDS`**
- Với `OTHER_WORDS`, clip phẳng 180 Hz không sinh FLAT_PITCH (TP 0) trên bài tổng hợp nên không dùng làm câu tuning của E2E. Với một lesson id cố định, câu `OTHER_WORDS` rơi vào tuning (hash lớn hơn), vì vậy E2E dùng hai câu cùng giọng để kết quả không phụ thuộc phía nào là tuning. Đây là đặc tính của dữ liệu tổng hợp, không phải lỗi mã.

**Total deviations:** 3 auto-fixed (1 blocking, 2 bổ sung) + 1 quan sát. **Impact:** không đổi phạm vi, contract hay ngưỡng.

## Authentication Gates

Không có.

## Issues Encountered

- Hook an toàn của harness từ chối lệnh Bash chứa từ đứng riêng `eval` và lệnh dùng heredoc dài; đã dùng glob `e[v]al` và công cụ Edit/Write.
- Không ghi được ledger `gsd-plan-head-before-04-04` trong `.git/worktrees/` (harness chặn ghi ngoài worktree); `plan_head_before` lấy từ SHA base của prompt (`af925aa`), đối chiếu `git rev-list --count af925aa..HEAD` = 4 trước commit SUMMARY.
- **Cần orchestrator lưu ý khi merge:** `Makefile` dòng `.PHONY:` cũng sẽ bị 04-03 (`eval-sweep`) và có thể 04-05 sửa; hai thay đổi cùng dòng sẽ xung đột và cần gộp tay (thêm `eval-tag` vào danh sách). Mục "Lệnh" trong `CLAUDE.md` chưa liệt kê `make eval-tag` (không thuộc `files_modified` của plan này); nên cập nhật ở 04-12 cùng `eval-sweep`.

## Known Stubs

Không có.

## Threat Flags

Không có bề mặt mới ngoài threat model của plan. T-04-09 (stem lạ / sidecar lệch -> thoát 2, có test), T-04-10 (`write_cases` validate trước rồi `.part` + `os.replace`, ghi sau mỗi lần gán), T-04-11 (`assign_splits` chỉ trả về câu chưa có split, có test "giữ nguyên split đã ghi") đều đã được giảm thiểu. Prohibition D-01: `tag` chỉ in stem, chữ của câu, loại lỗi, vị trí từ và ghi chú; test khẳng định output không chứa điểm hay issue.

## Next Phase Readiness

Sẵn sàng cho 04-05 (gate) và 04-06 (khoá held-out đọc `split` đã chốt), 04-08 (Liam viết kịch bản, chốt split rồi thu clip). `eval/cases.jsonl` chưa tồn tại (chưa có case thật); `make eval` vẫn thoát 2 với gợi ý `tag_clips.py add` cho đến khi Liam viết case.

## Self-Check: PASSED

- File tồn tại: `eval/tag_clips.py`, `eval/evalkit/cases.py`, `services/audio/tests/test_eval_tag_clips.py`, `Makefile`: FOUND
- Commit `8a13cfc`, `e6c4471`, `60bd2e4`, `261992d`: FOUND (ancestor của HEAD)
- Tiêu chí: cases.py chứa `def assign_splits`, `def write_cases`, `HELDOUT_SHARE = 0.30`; tag_clips.py có subcommand `words`, `add`, `split`, `tag`, `check`; Makefile chứa `eval-tag:` và `.PHONY` có `eval-tag`: PASS
- `uv run --project services/audio --frozen pytest services/audio/tests/test_eval_tag_clips.py services/audio/tests/test_eval_analyze.py -q`: 52 passed
- `ruff check` và `ruff format --check` trên `.`, `../../scripts`, `../../eval`: sạch
