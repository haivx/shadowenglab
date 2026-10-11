---
phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u
plan: 06
subsystem: testing
tags: [eval, holdout, freeze, sha256, tdd, make]

requires:
  - phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u
    provides: "04-01 bảng E1..E4/F2/F3; 04-02 analyze/report/counting; 04-04 tag_clips/cases; 04-05 cờ rule, rule_status, verdict (D-21)"
provides:
  - "eval/evalkit/holdout.py: HoldoutEntry, case_digest, make_entry, read_log, append_entry (atomic), is_opened, count_openings, check_frozen, HoldoutViolation, HoldoutLogError"
  - "analyze.py --holdout / --holdout-log: chấm cả hai tập, một dòng log mỗi lần mở, gate D-21 thật"
  - "report.md: cột Held-out P/R/n + trạng thái F2, mục 'Nhật ký mở held-out (D-16)', mục con 'Case held-out thêm sau lần mở đầu'"
  - "tag_clips.py also (D-09), Makefile HOLDOUT ?= và target eval-sweep"
affects: [04-07, 04-08, 04-09, 04-10, 04-11, 04-12]

actuals:
  tokens: 32000
  tasks: 2
  commits: 4
plan_head_before: 7ef6ebbc4d44652173fb612b248a818cbaed5988
plan_head_after: 6dcc3a2fa23d0caed27612cb89b12866349d1ce7

tech-stack:
  added: []
  patterns:
    - "Log append-only ghi `.part` rồi os.replace (cùng cách write_cases/write_report)"
    - "Đóng băng bằng so khớp với dòng log ĐẦU (splits + digest sha256 của JSON chuẩn hoá), thoát 2 trước khi chấm"
    - "Chọn tập chấm bằng một cờ rõ ràng; mặc định không đọc WAV held-out và không chạm log"

key-files:
  created:
    - eval/evalkit/holdout.py
    - services/audio/tests/test_eval_holdout.py
  modified:
    - eval/analyze.py
    - eval/evalkit/report.py
    - eval/tag_clips.py
    - Makefile

key-decisions:
  - "Giữ nguyên 04-01 E1..E4, F2, F3; không đổi contract, ngưỡng hay model"
  - "check_frozen theo đúng chữ của plan: case có ở splits của dòng đầu mà biến mất cũng là vi phạm, kể cả case tuning"
  - "RunInfo.mode là chuỗi hiển thị nguyên văn do analyze dựng ('tuning (held-out khoá, D-16)' hoặc 'tuning + held-out (lần mở thứ k)')"

requirements-completed: [EVL-03]

coverage:
  - id: D1
    description: "Mặc định `make eval` không đọc WAV held-out và không tạo/đụng holdout_log.jsonl; chỉ `--holdout` (HOLDOUT=1) mới chấm held-out"
    requirement: "EVL-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_without_the_holdout_flag_heldout_wavs_are_never_read_and_no_log_is_created"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_a_tuning_run_after_an_opening_leaves_the_log_alone_and_says_how_often_it_was_opened"
        status: pass
    human_judgment: false
  - id: D2
    description: "Mỗi lần mở held-out thành công thêm đúng một dòng log 7 khoá; report in toàn bộ log, cột held-out và dòng chế độ 'lần mở thứ k'"
    requirement: "EVL-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_holdout_run_with_a_failing_rule_exits_one_and_appends_one_seven_key_log_line"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_a_clean_holdout_run_exits_zero_and_adds_a_second_log_line_listed_in_the_report"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_the_report_shows_heldout_precision_recall_n_and_status_for_each_rule"
        status: pass
    human_judgment: false
  - id: D3
    description: "Gate D-21 áp thật khi có held-out: rule đang bật FAIL hoặc mốc tự so có issue -> thoát 1; mốc tự so gồm câu held-out"
    requirement: "EVL-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_the_self_compare_baseline_includes_the_heldout_sentence_only_with_the_flag"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_gate.py (verdict, 04-05)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Nhãn held-out đóng băng từ lần mở đầu: sửa nhãn, đổi/mất split, xoá case -> thoát 2 nêu caseId và D-09, không chấm, không ghi log, không đè report; case held-out mới được chấm và liệt kê; sửa case tuning vẫn chạy"
    requirement: "EVL-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_editing_a_heldout_label_after_the_first_opening_exits_two_naming_the_case_and_d09"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_check_frozen_rejects_any_edit_to_a_heldout_label_naming_case_and_d09"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_a_new_heldout_case_is_scored_and_listed_as_added_after_the_first_opening"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_editing_a_tuning_case_after_the_opening_still_runs_normally"
        status: pass
    human_judgment: false
  - id: D5
    description: "tag_clips.py also: thêm alsoPresent vào case tuning bất kỳ lúc nào, vào held-out chỉ khi log rỗng, từ chối (thoát 2, D-09) sau lần mở đầu; kiểm wordIndex theo loại như add"
    requirement: "EVL-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_also_refuses_a_heldout_case_once_the_log_has_a_line_and_leaves_the_file_alone"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_also_rejects_a_bad_entry_with_exit_two_and_writes_nothing"
        status: pass
    human_judgment: false
  - id: D6
    description: "Makefile có HOLDOUT ?=, nhánh --holdout và target eval-sweep (PARAM= tuỳ chọn)"
    requirement: "EVL-03"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_eval_holdout.py#test_the_makefile_has_the_holdout_variable_the_holdout_branch_and_the_sweep_target"
        status: pass
      - kind: other
        ref: "make -n e''val HOLDOUT=1 -> '... eval/analyze.py --holdout'; make -n e''val-sweep PARAM=FLAT_RATIO -> '... eval/sweep.py --param FLAT_RATIO'"
        status: pass
    human_judgment: false
  - id: D7
    description: "Kỷ luật 'không chỉnh ngưỡng dựa trên số held-out' (D-15): công cụ chỉ chặn sửa nhãn và ghi dấu vết, không ngăn người nhìn số held-out rồi chỉnh tay"
    requirement: "EVL-03"
    verification: []
    human_judgment: true
    rationale: "Phần còn lại là kỷ luật của Liam (D-15, ADR 0007), không có test nào khẳng định được"

duration: 48min
completed: 2026-10-12
status: complete
---

# Phase 4 Plan 06: Khoá held-out Summary

**`make eval HOLDOUT=1` mở held-out qua `analyze.py --holdout`: mỗi lần chấm xong ghi đúng một dòng vào `eval/holdout_log.jsonl` (versions, git sha, split + digest sha256 của nhãn), nhãn held-out bị đóng băng theo dòng đầu (vi phạm -> thoát 2 nêu caseId và D-09 trước khi chấm), report có cột held-out và nhật ký, gate D-21 áp thật; thêm `tag_clips.py also` và `make eval-sweep`.**

## Performance

- **Duration:** 48 min (ước lượng từ mốc commit đầu 03:07 đến commit cuối 03:15 +0700, cộng thời gian đọc ngữ cảnh)
- **Completed:** 2026-10-11T20:15Z
- **Tasks:** 2 (Task 1 tracer + tdd, Task 2 auto + tdd)
- **Files modified:** 6 (2 tạo, 4 sửa)

## Accomplishments

- `eval/evalkit/holdout.py` mới: `case_digest` (sha256 JSON chuẩn hoá), `make_entry`, `read_log` (dòng hỏng -> `HoldoutLogError` nêu số dòng), `append_entry` (cũ + mới -> `.part` -> `os.replace`), `is_opened`, `count_openings`, `check_frozen` + `HoldoutViolation`.
- `analyze.py`: thêm `--holdout`, `--holdout-log`. Không cờ: không đọc WAV held-out, không đụng log, chỉ in "held-out đã mở k lần" nếu log có dòng. Có cờ: `check_frozen` TRƯỚC khi chấm, chấm cả hai tập, tally theo từng split, mốc tự so cho mọi câu của hai tập, `verdict(..., holdout_included=True)`, `append_entry` rồi mới ghi report (report in cả dòng vừa thêm). Lỗi dữ liệu (2) không ghi log.
- `report.py`: thêm cột `Held-out R (k/N) [CI95]` cạnh `Held-out P [CI95] (n)` và `Trạng thái` (F2); mục "Nhật ký mở held-out (D-16)"; mục con "Case held-out thêm sau lần mở đầu" ("không có" khi rỗng).
- `tag_clips.py also`: thêm `alsoPresent` (không trùng), kiểm wordIndex theo loại như `add` (dùng chung `_check_error_word`), kiểm dấu nhận diện câu (D-05), từ chối case held-out khi `is_opened`.
- Makefile: `HOLDOUT ?=`, recipe `eval` thêm `$(if $(filter 1,$(HOLDOUT)),--holdout)`, target `eval-sweep` (trong `.PHONY`, `PARAM=` tuỳ chọn).

## Định dạng một dòng log (`eval/holdout_log.jsonl`)

Một dòng JSON, khoá theo 04-01 E2 (ví dụ minh hoạ, xuống dòng chỉ để dễ đọc):

```json
{"openedAt":"2026-10-12T01:02:03Z","thresholdsVersion":"p2-1","scorerVersion":"prosody-2",
 "featVersion":"pf-2","gitSha":"7ef6ebbc4d44-dirty",
 "splits":{"c0001":"tuning","c0002":"heldout"},
 "digests":{"c0002":"<sha256 64 hex của JSON chuẩn hoá của case c0002>"}}
```

`gitSha` = 12 ký tự đầu của HEAD, thêm `-dirty` khi cây có thay đổi. `digests` chỉ có case held-out.

## Thông báo D-09 (thoát 2, stderr)

- Sửa nhãn: `c0002: nhãn held-out đã đổi sau lần mở đầu (D-09); khôi phục đúng nhãn cũ rồi chạy lại`
- Đổi split: `c0001: split đổi từ tuning sang heldout sau lần mở held-out đầu (D-09)`
- Mất case: `c0002: có ở lần mở held-out đầu (heldout) nhưng không còn trong cases.jsonl; không được xoá case sau lần mở đầu (D-09)`
- `also` sau lần mở: `c0002: case held-out đã bị đóng băng từ lần mở đầu, không thêm alsoPresent được nữa (D-09)`

## Lệnh make

```
make eval                  # tuning, held-out khoá
make eval HOLDOUT=1        # uv run ... eval/analyze.py --holdout   (thêm một dòng vào holdout_log.jsonl, áp gate D-21)
make eval-sweep            # uv run ... eval/sweep.py               (chỉ tuning, chỉ in)
make eval-sweep PARAM=FLAT_RATIO
uv run --project services/audio --frozen python eval/tag_clips.py also --case c0001 --error extra_pause --word 2
```

## TDD (RED / GREEN)

- **Task 1 RED** `df3bbc5`: 12 test, 6 fail + 6 error. Bằng chứng là đầu ra console của pytest (chưa qua bộ phân loại `gsd check tdd-red-evidence`). Đánh giá ngữ nghĩa trung thực: các test đầu-cuối fail vì `argparse: unrecognized arguments: --holdout-log` (SystemExit 2, đúng nguyên nhân thiếu tính năng nhưng không phải assertion), các test thuần lỗi ở fixture do `evalkit.holdout` chưa tồn tại. Theo luật nghiêm của `tdd.md` đây là dạng `fixture_or_load_failure`, nên coi là RED yếu: nó chứng minh tính năng chưa có chứ không chứng minh assertion mục tiêu sai.
- **Task 1 GREEN** `dd828e1`: 12/12 pass; 139 passed trên 6 file test eval (gồm các test cũ).
- **Task 2 RED** `de58242`: 21 fail (không có lỗi không liên quan); 13 test Task 1 vẫn pass. Cùng lưu ý về dạng lỗi (argparse `invalid choice: 'also'`, `AttributeError` thiếu `check_frozen`, assertion Makefile `eval-sweep` thiếu là assertion thật).
- **Task 2 GREEN** `6dcc3a2`: 34/34 trong file mới, 161/161 trên toàn bộ test eval.
- **REFACTOR:** không có commit riêng (đã gom `_check_error_word` vào commit GREEN Task 2).

## Task Commits

1. **Task 1 (tracer): mở held-out, log, report, gate** — `df3bbc5` (test), `dd828e1` (feat)
2. **Task 2: đóng băng, `also`, `eval-sweep`** — `de58242` (test), `6dcc3a2` (feat)

**Tracer gate:** `<verify>` chỉ có phần tự động; chạy lại pytest 3 file + grep Makefile sau commit GREEN Task 1: pass (55 passed, MAKE_OK) -> mở rộng sang Task 2.

**Plan metadata:** commit `docs(04-06)` chứa file SUMMARY này.

## Files Created/Modified

- `eval/evalkit/holdout.py` - log mở held-out, digest, `check_frozen`
- `eval/analyze.py` - `--holdout`, `--holdout-log`, đóng băng, gate, ghi log trước report
- `eval/evalkit/report.py` - cột held-out R, nhật ký mở, mục "thêm sau lần mở đầu", `RunInfo.mode` là chuỗi hiển thị
- `eval/tag_clips.py` - subcommand `also`, helper `_check_error_word` dùng chung với `add`
- `Makefile` - `HOLDOUT ?=`, nhánh `--holdout`, `eval-sweep`
- `services/audio/tests/test_eval_holdout.py` - 34 test (đầu-cuối, hàm thuần, `also`, Makefile)

## Decisions Made

- Theo đúng 04-01 E1..E4, F2, F3: không đổi contract, ngưỡng, model hay schema.
- `check_frozen` làm đúng chữ plan/E3: mọi caseId có ở `splits` của dòng đầu mà biến mất hoặc đổi split đều là vi phạm, kể cả case tuning. Hệ quả cần Liam biết: sau lần mở đầu không xoá được case tuning nào (kể cả case viết nhầm) mà không bị chặn; muốn gỡ phải sửa `holdout_log.jsonl` (lộ trong diff vì file được commit, T-04-14).
- `HoldoutLogError` cũng bắt ở `tag_clips` nên log hỏng làm `also` thoát 2 thay vì traceback.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree thiếu .venv**
- **Found during:** bắt đầu Task 1
- **Issue:** worktree mới không có `services/audio/.venv`
- **Fix:** `uv sync --project services/audio --frozen` (chỉ theo lockfile, không thêm package, lockfile không đổi). Không cần `pnpm install` vì plan không đụng Node.
- **Files modified:** không có file được theo dõi nào

**2. [Rule 1 - Bug] Fixture test dùng `OTHER_WORDS` không bắn FLAT_PITCH**
- **Found during:** chạy GREEN Task 1
- **Issue:** giọng phẳng trên `OTHER_WORDS` không tạo issue FLAT_PITCH nên test "held-out FAIL" không thể xảy ra
- **Fix:** dùng `DEFAULT_WORDS` cho cả hai câu của bài tổng hợp (cùng cách các test 04-05 dựng FLAT_PITCH)
- **Files modified:** `services/audio/tests/test_eval_holdout.py`
- **Committed in:** `dd828e1`

**3. [Rule 2 - Missing critical] `analyze` bắt lỗi ghi log**
- **Found during:** Task 1
- **Issue:** `append_entry` lỗi OSError sẽ ra traceback thay vì thoát 2
- **Fix:** bắt `OSError`/`HoldoutLogError` quanh `append_entry` + `read_log`, trả `_usage_error`
- **Files modified:** `eval/analyze.py`
- **Committed in:** `dd828e1`

---

**Total deviations:** 3 auto-fixed (1 blocking, 1 bug trong test, 1 missing critical).

**Thay đổi định dạng report ngoài chữ plan (cần cho "cột held-out có P/CI/R/n"):** bảng tóm tắt thêm một cột (8 cột thay vì 7), dòng "Chế độ" nay in `info.mode` nguyên văn (trước đó hậu tố "(held-out khoá, D-16)" nằm cứng trong `render_report`), tiêu đề mục là "Tóm tắt theo rule" (bỏ "(tuning)"), dòng "Case" ghi "đã chấm N clip". Các test cũ không phụ thuộc chữ này vẫn pass; `[3]` (tuning P) và `[-1]` (trạng thái) của hàng bảng giữ nguyên vị trí. Test `also` nằm trong `test_eval_holdout.py` vì plan chỉ liệt kê file này.

## Authentication Gates

Không có.

## Issues Encountered

- Harness chặn heredoc và từ `eval` đứng riêng trong lệnh Bash: dùng Edit/Write cho file, glob `e[v]al/` cho đường dẫn và `e""val-sweep` cho target make.
- Không ghi được ledger `gsd-plan-head-before-04-06` trong `.git/worktrees/` (cùng giới hạn đã ghi ở 04-01); `plan_head_before` lấy từ SHA base của prompt và khớp `git rev-list --count 7ef6ebb..HEAD` = 4 lúc viết SUMMARY.

## Known Stubs

Không có. `eval/holdout_log.jsonl` chưa tồn tại trong repo: nó chỉ sinh ra ở lần `make eval HOLDOUT=1` thật đầu tiên trên dữ liệu thật (04-11/04-12), rồi commit.

## Threat Flags

Không có bề mặt mới ngoài threat model (T-04-14 `check_frozen` + `also` từ chối, T-04-15 một dòng log mỗi lần mở trước khi ghi report, T-04-16 `.part` + `os.replace` và `HoldoutLogError` đều đã có test).

## Next Phase Readiness

Sẵn sàng cho 04-07..04-12. Lưu ý cho 04-12: đổi `HOLDOUT ?= 1` (E4) sẽ làm mọi `make eval` mở held-out và thêm dòng log; `HOLDOUT=0` mới giữ khoá. Lần mở thật đầu tiên là mốc đóng băng nhãn, nên chỉ chạy sau khi Liam đã chốt toàn bộ case held-out.

## Self-Check: PASSED

- `eval/evalkit/holdout.py` chứa `def append_entry`, `def case_digest`, `def read_log`, `HOLDOUT_LOG_PATH`, `def check_frozen`, `class HoldoutViolation`: FOUND
- `eval/analyze.py` có `--holdout`, `--holdout-log`; `eval/tag_clips.py` có `also` gọi `is_opened(`: FOUND
- Makefile có `HOLDOUT ?=`, `filter 1,$(HOLDOUT)`, `eval-sweep:` và `eval/sweep.py`: FOUND (`make -n` in đúng lệnh)
- Commit `df3bbc5`, `dd828e1`, `de58242`, `6dcc3a2`: FOUND (tổ tiên của HEAD)
- `pytest` 6 file eval: 161 passed; `ruff check` và `ruff format --check` trên `. ../../scripts ../../eval`: sạch
- Không sửa STATE.md, ROADMAP.md, contract, ngưỡng hay model
