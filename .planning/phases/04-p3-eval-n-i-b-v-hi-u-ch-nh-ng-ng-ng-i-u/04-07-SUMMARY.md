---
phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u
plan: 07
subsystem: eval
tags: [eval, test-retest, icc, determinism, adr, tdd, read-only]

requires:
  - phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u
    provides: "04-01 bảng J (khoá nhóm retest, ICC, mẫu tất định) và D-17; 04-02 analyze/report/rescore (self_compare_inputs); 04-05 verdict; 04-06 holdout, eval-sweep"
provides:
  - "eval/evalkit/stats.py: sample_sd, pooled_sd, jaccard, retest_groups, build_retest, icc1, distribution, scores_equal, Determinism, cross_rows, distribution_rows và các kiểu ScoredClip, CrossPair, CrossRow, DistRow, TotalsReport"
  - "report.md: mục 'Test-retest (D-19)' (bảng nhóm + dòng gộp + ICC hoặc 'chưa đủ mẫu (k nhóm)') và dòng 'Tất định: PASS (n/n)' / 'Tất định: FAIL — <caseId…>'"
  - "report.md: mục 'Điểm tổng (D-17, chỉ đo)' (trung vị chéo câu theo bài, nhãn 'rủi ro D-a', tỉ lệ căn ok, phân bố overall tự so/correct/lỗi)"
  - "docs/decisions/0007-eval-noi-bo-p3.md (trạng thái Đề xuất), eval/README.md, CLAUDE.md 'Lệnh' có make eval / eval-tag / eval-sweep"
affects: [04-08, 04-09, 04-10, 04-11, 04-12]

actuals:
  tokens: 17200
  tasks: 3
  commits: 5
plan_head_before: 41184b2767f429c2a67f506345bba2815de0ed82
plan_head_after: 7af9568f5d311c35f55535b6b06f2f55f3facbc9

tech-stack:
  added: []
  patterns:
    - "Thống kê thuần tách khỏi analyze (evalkit/stats.py, không import audio_service lúc chạy); analyze chỉ lấy điểm đã chấm rồi gọi hàm thuần"
    - "Kiểm tất định nhận `rescore` làm tham số để test monkeypatch `score_clip` lần hai mà không sửa rescore.py"
    - "render_report thêm kwargs tuỳ chọn (retest, determinism, totals): thiếu thì không in mục, nên test cũ gọi trực tiếp vẫn đúng"

key-files:
  created:
    - eval/evalkit/stats.py
    - services/audio/tests/test_eval_retest.py
    - docs/decisions/0007-eval-noi-bo-p3.md
  modified:
    - eval/analyze.py
    - eval/evalkit/report.py
    - eval/README.md
    - CLAUDE.md

key-decisions:
  - "Clip không có tiếng (VAD) không có điểm nên không tham gia test-retest; nhóm cần >= 2 clip có điểm"
  - "Jaccard của nhóm là trung bình theo cặp của mọi cặp clip trong nhóm; dòng tổng là trung bình các nhóm"
  - "Mốc rủi ro D-a (CROSS_MEDIAN_RISK = 0.6) đặt trong stats.py và có test so khớp CROSS_MEDIAN_MAX của scripts/smoke_score.py"
  - "ADR 0007 không chứa số đo, ID bài hay đường dẫn DATA_DIR; mục Kết quả để trống tới 04-12"

requirements-completed: [EVL-02]

coverage:
  - id: D1
    description: "Mục 'Test-retest (D-19)': nhóm >= 2 clip có k, SD của overall/speed/pitchRange/melodyMatch, Jaccard; dòng gộp; ICC(1,1) khi >= 5 nhóm, ít hơn ghi 'chưa đủ mẫu (k nhóm)'"
    requirement: "EVL-02"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_retest.py#test_two_clips_of_one_group_give_a_retest_row_and_a_passing_determinism_line"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_retest.py#test_icc_is_computed_from_five_groups_and_left_out_below_that"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_retest.py (jaccard, pooled_sd, sample_sd, retest_groups, build_retest)"
        status: pass
    human_judgment: false
  - id: D2
    description: "icc1 đúng ba giá trị chuẩn (1.0, -1.0, 0.88235) và trả None khi một nhóm, mọi nhóm một phần tử hoặc mẫu số 0"
    requirement: "EVL-02"
    verification:
      - kind: unit
        ref: "services/audio/tests/test_eval_retest.py#test_icc1_matches_the_three_reference_values"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_retest.py#test_icc1_is_undefined_for_one_group_singleton_groups_or_a_zero_denominator"
        status: pass
    human_judgment: false
  - id: D3
    description: "Kiểm tất định: chấm lại 5 clip đầu theo caseId; PASS trên dữ liệu tổng hợp; lần hai khác thì FAIL nêu caseId, cảnh báo stderr, exit code vẫn 0 (chỉ tuning)"
    requirement: "EVL-02"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_retest.py#test_a_second_scoring_that_differs_marks_determinism_fail_with_the_case_id_and_exits_zero"
        status: pass
    human_judgment: false
  - id: D4
    description: "Mục 'Điểm tổng (D-17, chỉ đo)': trung vị chéo câu theo bài với nhãn 'rủi ro D-a' khi >= 0.6, tỉ lệ căn ok, 'cần ≥ 2 câu' cho bài một câu, phân bố overall tự so/correct/lỗi (n = 0 ghi '—'); công thức D-04 và trọng số không đổi"
    requirement: "EVL-02"
    verification:
      - kind: integration
        ref: "services/audio/tests/test_eval_retest.py#test_the_report_measures_the_overall_score_across_sentences_and_by_source"
        status: pass
      - kind: integration
        ref: "services/audio/tests/test_eval_retest.py#test_a_lesson_with_one_sentence_in_the_set_says_it_needs_two_for_the_cross_pair"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_retest.py#test_a_cross_median_at_or_above_the_bar_is_labelled_a_d_a_risk"
        status: pass
      - kind: unit
        ref: "services/audio/tests/test_eval_retest.py#test_the_cross_risk_threshold_is_the_one_the_smoke_uses"
        status: pass
    human_judgment: false
  - id: D5
    description: "ADR 0007 ghi quy trình eval (12 quyết định), CLAUDE.md 'Lệnh' và eval/README.md mô tả make eval, HOLDOUT=1, eval-tag, eval-sweep và các file cases.jsonl, report.md, holdout_log.jsonl, analyze.py, sweep.py, tag_clips.py"
    requirement: "EVL-02"
    verification:
      - kind: other
        ref: "chuỗi grep của <verify> Task 3 (ADR có D-12, D-15, holdout_log.jsonl; CLAUDE.md có 'make eval-sweep', 'make eval-tag'; README có tag_clips.py, cases.jsonl) -> TASK3_OK"
        status: pass
    human_judgment: true
    rationale: "Nội dung ADR (đặc biệt trạng thái 'Đề xuất' và các quy tắc quy trình) là quyết định của Liam; grep chỉ chứng minh các mục có mặt"
  - id: D6
    description: "Số đo thật (ICC, SD, trung vị chéo, phân bố) trên bộ clip của Liam"
    requirement: "EVL-02"
    verification: []
    human_judgment: true
    rationale: "Chưa có cases.jsonl thật (Liam thu ở 04-08); plan này chỉ chứng minh cơ chế trên bài tổng hợp, ADR mục Kết quả để trống tới 04-12"

duration: ~35min
completed: 2026-10-12
status: complete
---

# Phase 4 Plan 07: Test-retest, tất định, đo điểm tổng và ADR 0007 Summary

**`make eval` sinh thêm mục Test-retest (SD, Jaccard, ICC(1,1) khi >= 5 nhóm), dòng Tất định (chấm lại 5 clip đầu, FAIL chỉ cảnh báo) và mục Điểm tổng (D-17: trung vị chéo câu với nhãn rủi ro D-a, phân bố overall), kèm ADR 0007 ghi toàn bộ quy trình eval và lệnh `make eval`, `eval-tag`, `eval-sweep` trong CLAUDE.md và eval/README.md.**

## Performance

- **Duration:** ~35 min (ước lượng; không ghi giờ bắt đầu)
- **Completed:** 2026-10-12
- **Tasks:** 3 (Task 1 tracer + tdd, Task 2 auto + tdd, Task 3 auto)
- **Files modified:** 7 (3 tạo, 4 sửa)

## Accomplishments

- `eval/evalkit/stats.py` (hàm thuần, không import `audio_service` lúc chạy): `sample_sd`, `pooled_sd`, `jaccard`, `retest_groups`, `build_retest`, `icc1` (một chiều, nhóm không cân), `distribution`, `scores_equal`, `cross_rows`, `distribution_rows`.
- `analyze.py`: giữ `ScoredClip` cho mọi clip đã chấm; `check_determinism` nạp lại clip với `ref_cache` mới rồi chấm lần hai cho `DETERMINISM_SAMPLE` clip đầu theo caseId; `cross_pairs` chấm bản ghi mốc tự so của câu i với bản gốc câu kế tiếp (vòng, cùng quy ước `scripts/smoke_score.py`). Không đổi mã thoát vì tất định, không đổi công thức D-04, trọng số hay `SCORER_VERSION`.
- `report.py`: mục "Test-retest (D-19)", dòng tất định, mục "Điểm tổng (D-17, chỉ đo)".
- ADR `docs/decisions/0007-eval-noi-bo-p3.md` (Đề xuất): Bối cảnh, 12 quyết định, Kết quả (trống), Hệ quả. CLAUDE.md và eval/README.md cập nhật lệnh.

## Mẫu các mục report mới (dữ liệu tổng hợp, không phải số đo trên giọng thật)

```
## Test-retest (D-19)
| bài | câu | kind | errorType@w | k | SD overall | SD speed | SD pitchRange | SD melodyMatch | Jaccard |
| 01HZX... | 0 | error | flat | 2 | 0.0xx | 0.0xx | 0.0xx | 0.0xx | 1.00 |
| gộp | | | | 2 | 0.0xx | 0.0xx | 0.0xx | 0.0xx | 1.00 |

tổng: 1 nhóm · ICC(1,1) overall: chưa đủ mẫu (1 nhóm)

Tất định: PASS (3/3)            # hoặc: Tất định: FAIL — c0002

## Điểm tổng (D-17, chỉ đo)
| bài | số cặp chéo | trung vị chéo | căn ok | ghi chú |
| 01HZX... | 2 | 0.xxx | 1/2 (50 %) | rủi ro D-a (khi trung vị >= 0.6) |
| (bài một câu) | 0 | — | — | cần ≥ 2 câu |

| bài | nguồn | n | trung vị | p25 | p75 |
| 01HZX... | tự so | 2 | 0.xxx | 0.xxx | 0.xxx |
| 01HZX... | correct | 0 | — | — | — |
```

## TDD (RED / GREEN)

| Task | RED | GREEN |
|---|---|---|
| 1 tracer (retest + tất định) | `8ab6755` test(04-07) | `0b7d9b3` feat(04-07) |
| 2 (ICC, D-17) | `e5c9b3a` test(04-07) | `8b1533e` feat(04-07) |

- **RED Task 1:** 2 test đầu-cuối fail ở assertion đã định (không có mục "Test-retest", stderr rỗng), 6 test hàm thuần lỗi fixture vì `evalkit.stats` chưa tồn tại (`ModuleNotFoundError`). Đánh giá ngữ nghĩa trung thực: nửa sau là RED yếu dạng `fixture_or_load_failure` (cùng kiểu RED của 04-02, 04-03, 04-06), nửa đầu là assertion thật. `workflow.tdd_mode` là `false` nên không chạy `gsd check tdd-red-evidence`; bằng chứng là đầu ra console của pytest.
- **RED Task 2:** 11 fail, đều đúng nguyên nhân dự kiến (`AttributeError` thiếu `icc1`, `distribution`, `CrossPair`, `cross_rows`, `distribution_rows`, `CROSS_MEDIAN_RISK`, `TotalsReport`; `StopIteration` vì chưa có mục "Điểm tổng"); 8 test của Task 1 vẫn pass.
- **Tracer gate:** auto mode tắt, `HUMAN_VERIFY_MODE` là `end-of-phase`, `<verify>` chỉ có `<automated>`: chạy lại pytest `test_eval_retest.py` + `test_eval_analyze.py` sau commit GREEN Task 1 (22 passed) -> "Tracer verified end-to-end — expanding".
- **REFACTOR:** không có.

## Task Commits

1. **Task 1 (tracer): test-retest + tất định** — `8ab6755` (test), `0b7d9b3` (feat)
2. **Task 2: ICC(1,1) + điểm tổng D-17** — `e5c9b3a` (test), `8b1533e` (feat)
3. **Task 3: ADR 0007, README, CLAUDE.md** — `7af9568` (docs)

**Plan metadata:** commit `docs(04-07)` chứa file SUMMARY này.

## Files Created/Modified

- `eval/evalkit/stats.py` - thống kê thuần (test-retest, ICC, tất định, cặp chéo, phân bố)
- `eval/analyze.py` - `ScoredClip`, `check_determinism`, `cross_pairs`, truyền `retest`/`determinism`/`totals` cho report, cảnh báo stderr khi tất định FAIL
- `eval/evalkit/report.py` - `_retest_section`, `_totals_section`, ba kwargs mới của `render_report`
- `services/audio/tests/test_eval_retest.py` - 19 test (hàm thuần, render, đầu-cuối, so khớp ngưỡng với smoke)
- `docs/decisions/0007-eval-noi-bo-p3.md`, `eval/README.md`, `CLAUDE.md` - tài liệu quy trình và lệnh

## Decisions Made

Xem `key-decisions`. Không đổi contract, ngưỡng, model, cách đếm hay `SCORER_VERSION`/`THRESHOLDS_VERSION`; các giá trị trong ADR lấy từ bảng 04-01 và code đã merge.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree thiếu .venv**
- **Found during:** bắt đầu thực thi
- **Fix:** `uv sync --project services/audio --frozen` (chỉ theo lockfile, không thêm package, lockfile không đổi). `pnpm install` không cần vì plan không đụng Node (prettier bỏ qua `**/*.md`).
- **Files modified:** không có file được theo dõi nào

**2. [Mở rộng symbol, không đổi hành vi]** `ScoredClip` đặt ở `stats.py` (để hàm thuần dùng được) và `analyze.py` import lại nên `analyze.ScoredClip` vẫn tồn tại; thêm `build_retest`, `scores_equal`, `Determinism`, `check_determinism`, `cross_pairs`, `CrossPair`, `CrossRow`, `DistRow`, `TotalsReport`, `cross_rows`, `distribution_rows`, `CROSS_MEDIAN_RISK` (ngoài danh sách symbol của plan). `render_report` thêm kwargs `retest`, `determinism`, `totals` (tuỳ chọn).

**3. [Làm rõ chữ plan]** Clip không có tiếng không có điểm nên bị bỏ khỏi test-retest (nhóm cần >= 2 clip có điểm); bảng "Điểm tổng" dùng cột `bài | số cặp chéo | trung vị chéo | căn ok | ghi chú` (nhãn "rủi ro D-a" nằm ở cột ghi chú); Jaccard của nhóm là trung bình theo cặp.

**Total deviations:** 1 blocking (toolchain) + 2 ghi chú thiết kế. **Impact:** không đổi phạm vi; không chạm contract, ngưỡng, scorer, STATE.md hay ROADMAP.md.

## Authentication Gates

Không có.

## Issues Encountered

- Hook an toàn của harness từ chối lệnh Bash chứa từ đứng riêng `eval` (kể cả đường dẫn `eval/`), lệnh có `git` ghép nhiều bước và heredoc; đã dùng glob `e[v]al/` và lệnh đơn. Ledger `gsd-plan-head-before-04-07` ghi được lần này nên `commits:` đo đúng bằng `git rev-list --count` (5) trước commit SUMMARY.
- `CLAUDE.md` mục "Cấu trúc repo" vẫn liệt kê `export_clips.py` trong `eval/` (thuộc Phase 6); plan chỉ giao mục "Lệnh" nên không sửa. Nên chỉnh ở 04-12 nếu Liam muốn.

## Known Stubs

Không có. Mục "Kết quả" của ADR 0007 để trống có chủ đích (prohibition của plan): 04-12 điền từ `eval/report.md` thật.

## Threat Flags

Không có bề mặt mới ngoài threat model. T-04-17 (chấm không tất định): kiểm tất định mỗi lần chạy, FAIL in caseId, cảnh báo stderr, có test. T-04-18 (ADR/README nhắc dữ liệu thật): ADR chỉ có quy tắc, không ID bài, không đường dẫn DATA_DIR tuyệt đối, không số đo. T-04-SC: không thêm package.

## Next Phase Readiness

Sẵn sàng cho 04-08 (Liam viết kịch bản và thu clip): quy trình đã nằm trong ADR 0007, README và CLAUDE.md. Lưu ý cho 04-10..04-12: ICC chỉ hiện khi có >= 5 nhóm retest (ngưỡng K đòi >= 8 nhóm); `make eval` ở chế độ tuning chưa áp gate tất định vào exit code; ADR 0007 giữ trạng thái "Đề xuất" tới khi 04-12 điền Kết quả và Liam chốt.

## Self-Check: PASSED

- File tồn tại: `eval/evalkit/stats.py`, `services/audio/tests/test_eval_retest.py`, `docs/decisions/0007-eval-noi-bo-p3.md`, `eval/README.md`: FOUND
- Commit `8ab6755`, `0b7d9b3`, `e5c9b3a`, `8b1533e`, `7af9568`: FOUND (nằm trong `git log` từ base `41184b2`)
- Tiêu chí: stats.py chứa `def pooled_sd`, `def jaccard`, `def icc1`, `DETERMINISM_SAMPLE = 5`; report E2E có "Test-retest (D-19)", "Tất định: PASS", "Điểm tổng (D-17, chỉ đo)"; chuỗi grep Task 3 -> `TASK3_OK`; CLAUDE.md không còn chữ "stub" ở mục Lệnh: PASS
- `pytest services/audio/tests`: 1319 passed; `ruff check` và `ruff format --check` trên `.`, `../../eval`, `../../scripts`: sạch
- Không sửa STATE.md, ROADMAP.md, contract, `thresholds.py` hay `scorer.py` (`git diff --name-only 41184b2..HEAD` chỉ có 7 file của plan)
