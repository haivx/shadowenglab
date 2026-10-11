---
phase: 04-p3-eval-n-i-b-v-hi-u-ch-nh-ng-ng-ng-i-u
plan: 01
subsystem: contracts
tags: [zod, json-schema, pydantic, eval, contract-first, tdd]

requires:
  - phase: 01-p0-n-n-t-ng
    provides: đường Zod -> JSON Schema -> pydantic (scripts/contracts_gen.sh), drift gate, ScoreResult/IssueCode/Label/ClipManifest đã khoá
provides:
  - "ErrorType (7 giá trị D-03), EvalAlsoPresent, EvalCase ở Zod, JSON Schema và pydantic"
  - "Fixture EvalCase.json (5 case) round-trip Zod <-> JSON Schema <-> pydantic"
  - "Bảng 'Quyết định đã chốt' A1..L do Liam duyệt, các plan 04-02..04-12 đọc từ đây"
affects: [04-02, 04-03, 04-04, 04-05, 04-06, 04-07, 04-08, 04-09, 04-10, 04-11, 04-12]

actuals:
  tokens: 4000
  tasks: 2
  commits: 2
plan_head_before: 225700747972b1dfce029fc0c4473be86abafe1c
plan_head_after: e4d1721d408694a8d7d1adc0c1c446139ce9a56b

tech-stack:
  added: []
  patterns:
    - "Bất biến EvalCase kiểm ở Python (evalkit/cases.py), không dùng refine Zod vì refine không sinh sang JSON Schema"
    - "Optional là vắng mặt, không bao giờ null (giữ quy ước các contract trước)"

key-files:
  created:
    - packages/contracts/fixtures/EvalCase.json
  modified:
    - packages/contracts/src/eval.ts
    - packages/contracts/src/index.ts
    - packages/contracts/src/contracts.test.ts
    - packages/contracts/schema/contracts.schema.json
    - services/audio/src/audio_service/contracts_gen.py

key-decisions:
  - "Liam duyệt nguyên văn `approved` toàn bộ A..L như đề xuất (2026-10-11), gồm B1-a; không có ghi đè"
  - "EvalCase.split là optional (A4, lệch shape dự kiến của D-02): vắng mặt = chưa chốt"
  - "Dấu nhận diện câu dùng cả mốc thời gian (segStartMs, segEndMs, segEndExtraMs) lẫn hash text (segTextHash 16 hex) (D-05)"

requirements-completed: [EVL-01, EVL-03]

coverage:
  - id: D1
    description: "Liam chốt A..L trong một lần dừng; bảng 'Quyết định đã chốt' có giá trị cuối từng mục"
    requirement: "EVL-01"
    verification: []
    human_judgment: true
    rationale: "Quyết định sản phẩm của Liam (câu trả lời `approved`); không có test nào khẳng định điều này"
  - id: D2
    description: "ErrorType đúng 7 giá trị D-03 theo thứ tự, EvalAlsoPresent và EvalCase ở Zod, có trong Schemas (ErrorType, EvalCase)"
    requirement: "EVL-01"
    verification:
      - kind: unit
        ref: "packages/contracts/src/contracts.test.ts#phase 4 contract edges (EvalCase)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Zod từ chối kind/errorType/split lạ, wordIndex âm, segTextHash sai độ dài, thiếu segTextHash, null ở trường optional, alsoPresent sai"
    requirement: "EVL-03"
    verification:
      - kind: unit
        ref: "packages/contracts/src/contracts.test.ts#phase 4 contract edges (EvalCase)"
        status: pass
    human_judgment: false
  - id: D4
    description: "JSON Schema và pydantic sinh lại, round-trip fixture EvalCase.json (5 case), drift gate xanh, ScoreResult/IssueCode/Label/ClipManifest không đổi (diff chỉ thêm)"
    requirement: "EVL-03"
    verification:
      - kind: integration
        ref: "uv run pytest services/audio/tests/test_contracts_roundtrip.py services/audio/tests/test_contracts_drift.py (70 passed)"
        status: pass
      - kind: other
        ref: "sh scripts/contracts_check.sh -> 'contracts: không lệch'"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-10-11
status: complete
---

# Phase 4 Plan 01: Contract EvalCase và cổng quyết định Summary

**`ErrorType` (7 giá trị D-03), `EvalAlsoPresent` và `EvalCase` (dấu nhận diện câu D-05, `split` optional) có ở Zod, JSON Schema và pydantic với fixture 5 case round-trip, sau khi Liam duyệt nguyên văn `approved` toàn bộ mục A..L; `ScoreResult` không đổi.**

## Performance

- **Duration:** 14 min (phần tiếp tục sau checkpoint; Task 1 do executor trước dừng ở checkpoint)
- **Completed:** 2026-10-11T16:15Z
- **Tasks:** 2 (Task 1 = quyết định, không commit; Task 2 = TDD)
- **Files modified:** 6 (5 sửa, 1 tạo)

## Accomplishments

- Hiện thực đúng contract Liam duyệt: `ErrorType`, `EvalAlsoPresent`, `EvalCase` trong `packages/contracts/src/eval.ts`; `Schemas` thêm `ErrorType`, `EvalCase` ngay sau `Label`.
- Sinh lại `contracts.schema.json` và `contracts_gen.py` qua `scripts/contracts_gen.sh`; diff chỉ thêm (109 dòng schema, 46 dòng Python, 0 dòng xoá), nên `ScoreResult`, `IssueCode`, `Label`, `ClipManifest` giữ nguyên.
- Fixture `EvalCase.json` gồm 5 case (`error-word`, `error-sentence-heldout`, `correct`, `pending`, `also-present`); test đếm fixture lên 17 file.
- Tám test mới cho các cạnh âm và thứ tự `ErrorType.options`.

## Quyết định đã chốt

Nguồn mọi dòng: **đề xuất, Liam duyệt `approved` ngày 2026-10-11** (không có ghi đè). Các plan sau đọc giá trị từ bảng này.

| Mục | Giá trị cuối | Nguồn |
|---|---|---|
| A1 | `ErrorType` = enum `wrong_stress \| flat \| extra_pause \| final_rise \| pitch_off \| weak_form \| final_drop` (D-03 nguyên văn), `.meta({ id: "ErrorType" })`, có trong `Schemas` | đề xuất (Liam approved 2026-10-11) |
| A2 | `EvalAlsoPresent` = `{ errorType: ErrorType, wordIndex?: int >= 0 }`, meta id `EvalAlsoPresent` (D-09: lỗi có thật Liam nghe thấy ngoài kịch bản) | đề xuất (Liam approved 2026-10-11) |
| A3 | `EvalCase` (meta id `EvalCase`, có trong `Schemas`): `caseId: string` (min 1; `tag_clips.py add` cấp `c0001`, `c0002`... tăng dần) · `lessonId: string` · `segmentIndex: int >= 0` · `segStartMs`, `segEndMs`, `segEndExtraMs` (Milliseconds = round(start*1000), round(end*1000), endExtraMs của segment lúc viết case) · `segTextHash` (16 ký tự hex đầu của sha256(text UTF-8), `z.string().length(16)`) · `kind: "error" \| "correct"` · `errorType?: ErrorType` · `wordIndex?: int >= 0` · `alsoPresent?: EvalAlsoPresent[]` · `split?: "tuning" \| "heldout"` · `clip?: string` (stem `{lessonId}_{NNNN}_{AA}` do `tag_clips.py tag` điền) · `note?: string`. Optional là vắng mặt, không bao giờ null | đề xuất (Liam approved 2026-10-11) |
| A4 | `split` là optional (lệch shape dự kiến của D-02): vắng mặt = chưa chốt; `analyze.py` và `sweep.py` thoát 2 nếu còn case thiếu split (D-12 phân tầng theo errorType nên chỉ tính được khi đã viết đủ kịch bản) | đề xuất (Liam approved 2026-10-11) |
| A5 | Bất biến kiểm ở Python (`eval/evalkit/cases.py`) và ghi JSDoc, không refine Zod: kind `error` <=> có errorType; `correct` => không errorType, không wordIndex; errorType theo từ (`wrong_stress`, `extra_pause`, `pitch_off`, `weak_form`, `final_drop`) bắt buộc wordIndex; mức câu (`flat`, `final_rise`) không có wordIndex; caseId duy nhất; clip duy nhất; wordIndex < số từ của câu; câu có >= `STRESS_MIN_WORDS` (5) từ (D-11) | đề xuất (Liam approved 2026-10-11) |
| A6 | Lệch bất kỳ trường dấu nhận diện nào (bài bị xoá, "Sửa câu", "Mất chữ cuối?") -> `tag_clips.py` và `analyze.py` báo lỗi nêu caseId và thoát 2, không bỏ qua (D-05) | đề xuất (Liam approved 2026-10-11) |
| B1 | **B1-a**: `wrong_stress.wordIndex` = từ Liam cố ý nhấn thay (từ sai). TP khi có STRESS_MISMATCH mà `data.userWord` đúng là chữ của từ đó. `tag_clips.py add` từ chối khi chữ của từ đó xuất hiện hơn một lần trong câu | đề xuất (Liam approved 2026-10-11) |
| B2 | `pitch_off`: từ Liam nói lệch cao độ | đề xuất (Liam approved 2026-10-11) |
| B3 | `extra_pause`: từ đứng ngay TRƯỚC chỗ ngắt (= `EXTRA_PAUSE.wordIndex`), cho lệch +-1 (D-08) | đề xuất (Liam approved 2026-10-11) |
| B4 | `weak_form`, `final_drop`: từ bị đọc yếu / nuốt âm cuối (để Phase 5 PHN-06 dùng; D-07) | đề xuất (Liam approved 2026-10-11) |
| C | Bảng mã (w = wordIndex đã khai báo, n = số từ): `wrong_stress` -> chính STRESS_MISMATCH, vị trí theo B1-a, phụ PITCH_DEVIATION tại w · `pitch_off` -> chính PITCH_DEVIATION, wordIndex = w, phụ STRESS_MISMATCH có `data.userWord` = chữ của từ w · `extra_pause` -> chính EXTRA_PAUSE, abs(wordIndex - w) <= 1, không mã phụ · `flat` -> chính FLAT_PITCH cả câu, phụ PITCH_DEVIATION tại bất kỳ từ · `final_rise` -> chính FINAL_CONTOUR cả câu, phụ PITCH_DEVIATION tại từ cuối (n - 1) · `weak_form`, `final_drop` -> không mã chính (Lớp A, Phase 5), mọi issue Lớp C là FP (D-07) · `correct` (D-18b) và tự so (D-18a) -> mọi issue là FP. Mã phụ là trung tính (không TP, không FP) | đề xuất (Liam approved 2026-10-11) |
| C1 | Mỗi case tối đa 1 TP cho mã chính; nhiều issue cùng mã chính khớp vị trí -> issue gần w nhất là TP (hoà: chỉ số nhỏ hơn), các issue còn lại là FP | đề xuất (Liam approved 2026-10-11) |
| C2 | Issue khớp một mục `alsoPresent` (mã chính hoặc mã phụ của errorType trong mục đó, cùng quy tắc vị trí) -> trung tính (bảo thủ, không làm đẹp precision) (D-09) | đề xuất (Liam approved 2026-10-11) |
| C3 | Mọi issue còn lại -> FP, kể cả đúng mã sai từ (D-08, D-09) | đề xuất (Liam approved 2026-10-11) |
| C4 | Recall của rule R = số case có TP / số case có mã chính R trong tập đang chấm. Clip lỗi theo từ mà căn thất bại -> FN (D-11b) và vào bảng "tỉ lệ căn thất bại" theo bài x errorType. Clip không có tiếng (VAD) -> không issue, FN | đề xuất (Liam approved 2026-10-11) |
| D1 | `tag_clips.py split` gán một lần cho mọi câu chưa có split: sắp các câu theo `sha256("{lessonId}:{segmentIndex}")` (16 hex đầu -> số trong [0, 1)), duyệt tăng dần; đưa câu vào held-out nếu với mọi tầng có trong câu (mỗi errorType là một tầng, `correct` là một tầng) số case held-out của tầng sau khi thêm <= ceil(0.30 * tổng case của tầng). In bảng tỉ lệ đạt được của từng tầng. Không bao giờ đổi split đã ghi | đề xuất (Liam approved 2026-10-11) |
| D2 | Case viết sau khi chốt: câu đã có split -> nhận split đó; câu mới -> `heldout` khi số hash < 0.30, ngược lại `tuning` | đề xuất (Liam approved 2026-10-11) |
| D3 | Split được commit TRƯỚC KHI THU clip nào (app chấm mọi lượt ghi, nên "trước khi chấm clip nào" = trước khi thu) | đề xuất (Liam approved 2026-10-11) |
| E1 | Trong phase, `make eval` chỉ đọc case tuning; chỉ `make eval HOLDOUT=1` (`analyze.py --holdout`) mới chấm held-out. `sweep.py` không có cách nào đọc held-out | đề xuất (Liam approved 2026-10-11) |
| E2 | Mỗi lần mở thêm một dòng vào `eval/holdout_log.jsonl` (commit): `openedAt` (UTC ISO), `thresholdsVersion`, `scorerVersion`, `featVersion`, `gitSha` (thêm `-dirty` khi cây làm việc có thay đổi), `splits` {caseId: split} của mọi case và `digests` {caseId held-out: sha256 của JSON chuẩn hoá}. Report in toàn bộ log | đề xuất (Liam approved 2026-10-11) |
| E3 | Từ lần mở thứ hai: case có ở dòng đầu mà split khác, hoặc (held-out) digest khác -> thoát 2 "nhãn held-out đã đổi sau lần mở đầu (D-09)". Case held-out mới (không có ở dòng đầu) vẫn được chấm nhưng đánh dấu "thêm sau lần mở đầu". `tag_clips.py also` từ chối case held-out khi log đã có dòng | đề xuất (Liam approved 2026-10-11) |
| E4 | Khi đóng phase (04-12), Makefile đổi thành `HOLDOUT ?= 1` để `make eval` mặc định in cả hai tập (D-16, SC3); `HOLDOUT=0` chỉ chạy tuning | đề xuất (Liam approved 2026-10-11) |
| F1 | Mỗi rule x tập: P = TP/(TP+FP), R, n = TP+FP, khoảng tin cậy Wilson 95 % (z = 1.96) cho P và R; thêm dòng gộp các rule đang bật | đề xuất (Liam approved 2026-10-11) |
| F2 | Trạng thái held-out: `TẮT` (cờ D-15 = False), `FAIL` (P < 0.90 với n >= 1), `CHƯA ĐỦ MẪU` (n < 5 và không FAIL), `PASS` (n >= 5 và P >= 0.90). Chỉ PASS được tính là đạt SC1 | đề xuất (Liam approved 2026-10-11) |
| F3 | Exit: 0 OK; 1 chỉ khi chạy có held-out VÀ (có rule đang bật FAIL hoặc mốc tự so có issue) (D-21 nguyên văn); 2 = dữ liệu/tham số sai (D-05, thiếu split, case sai bất biến, log bị đổi). Chạy chỉ tuning không trả 1 (vẫn in cảnh báo khi tự so có issue) | đề xuất (Liam approved 2026-10-11) |
| G | Sweep một chiều từng tham số (các tham số khác giữ giá trị hiện tại), chỉ trên tuning. Lưới: STRESS_MISMATCH `STRESS_MARGIN_Z` 0.3 0.4 0.5 0.6 0.7 0.8 1.0 1.2 · EXTRA_PAUSE `PAUSE_USER_MS` 150 200 250 300 350 400 và `PAUSE_REF_MS` 60 80 100 120 150 · FINAL_CONTOUR `FINAL_SLOPE_MIN_ST_S` 3 4 5 6 7 8 10 · FLAT_PITCH `FLAT_RATIO` 0.40 0.45 0.50 0.55 0.60 0.65 0.70 và `FLAT_REF_MIN_STD_ST` 1.0 1.5 2.0 2.5 3.0 · PITCH_DEVIATION `PITCH_DEVIATION_ST` 2.0 2.5 3.0 3.5 4.0 5.0 và `PD_SIGN_CONSISTENCY` 0.6 0.7 0.8 0.9 · căn thời gian (D-11b, D-17) `ALIGN_COST_MAX` 0.90 1.00 1.10 1.20 1.30. Đề xuất = giá trị có recall cao nhất trong các giá trị có P tuning >= 0.95 và n >= 1; hoà thì chọn giá trị gần giá trị hiện tại; không có -> "không có giá trị đạt 95 %". Tham số dùng chung với điểm tổng hoặc căn (`PAUSE_USER_MS` cũng vào `metrics.speed`; `ALIGN_COST_MAX` đổi `alignment.ok`) có ghi chú trong bảng. Sweep chỉ in stdout, không ghi `thresholds.py`; Liam chọn giá trị và tự sửa `thresholds.py`, tăng `THRESHOLDS_VERSION` (D-13) | đề xuất (Liam approved 2026-10-11) |
| H | Năm cờ `STRESS_MISMATCH_ENABLED`, `FINAL_CONTOUR_ENABLED`, `EXTRA_PAUSE_ENABLED`, `PITCH_DEVIATION_ENABLED`, `FLAT_PITCH_ENABLED` = `True` trong `thresholds.py`; `run_rules` bỏ hẳn lời gọi của rule tắt (không issue, không tip). Thêm cờ không đổi hành vi nên KHÔNG tăng `THRESHOLDS_VERSION` (vẫn `p2-1`). Cờ chỉ được Claude đổi sau khi Liam duyệt danh sách ở 04-11, kèm nhãn version mới do Liam chọn | đề xuất (Liam approved 2026-10-11) |
| I | Mốc tự so (D-18a): mọi câu có case trong tập đang chấm; "người học" = lát vocal của câu, đệm 0.3 s, mã hoá webm/opus rồi chuẩn hoá như một lượt tải lên, dùng chính các hàm của `scripts/smoke_score.py`. Issue trên mốc tự so tính FP và vào gate F3 | đề xuất (Liam approved 2026-10-11) |
| J | Test-retest (D-19): nhóm = (lessonId, segmentIndex, kind, errorType, wordIndex) có >= 2 clip đã gắn trong tập đang chấm; in SD trong nhóm của overall, speed, pitchRange, melodyMatch; Jaccard của tập (code, wordIndex) giữa các lượt; ICC(1,1) một chiều của overall khi có >= 5 nhóm, ít hơn -> "chưa đủ mẫu". Kiểm tất định: chấm lại 5 clip đầu (theo caseId) lần hai, overall và issues phải bằng nhau tuyệt đối; in PASS/FAIL trong report, không vào exit code (D-21 không liệt kê) | đề xuất (Liam approved 2026-10-11) |
| K | Ngưỡng phủ nghiệm thu EVL-01 (diễn giải "~100"): >= 90 clip lỗi đã gắn, mỗi errorType ngữ điệu >= 10, mỗi errorType âm >= 10, >= 8 clip `correct`, >= 8 nhóm retest | đề xuất (Liam approved 2026-10-11) |
| L | `eval/cases.jsonl`, `eval/report.md`, `eval/holdout_log.jsonl` được commit (D-04, D-20); `.gitignore` không đổi (audio vẫn bị bỏ qua qua `*.wav`, `eval/clips/`); Makefile có `eval` (thật), `eval-tag`, `eval-sweep`; ADR mới `docs/decisions/0007-eval-noi-bo-p3.md` | đề xuất (Liam approved 2026-10-11) |

## Lớp pydantic sinh ra

Trong `services/audio/src/audio_service/contracts_gen.py`:

- `ErrorType` — sinh dưới dạng `RootModel[Literal[...]]` (cùng cách `IssueCode` đang được sinh), nên trường `EvalCase.error_type` và `EvalAlsoPresent.error_type` có kiểu `ErrorType` / `ErrorType | None`; **đọc giá trị bằng `.root`** (ví dụ `case.error_type.root == "flat"`). Gán chuỗi thường khi validate vẫn được.
- `EvalAlsoPresent(BaseModel)` — `error_type`, `word_index: int | None`.
- `EvalCase(BaseModel)` — `case_id`, `lesson_id`, `segment_index`, `seg_start_ms`, `seg_end_ms`, `seg_end_extra_ms`, `seg_text_hash` (min/max length 16), `kind: Literal["error","correct"]`, `error_type`, `word_index`, `also_present: list[EvalAlsoPresent] | None`, `split: Literal["tuning","heldout"] | None`, `clip`, `note`. Alias camelCase giữ nguyên trên dây (`populate_by_name=True`). Validate dòng JSONL bằng `EvalCase.model_validate_json(line)`.

## TDD (RED / GREEN)

- **RED** `d7ad239` `test(04-01)`: tám test mới + đổi đếm fixture 16 -> 17 + `$defs` mới. Bằng chứng: `vitest run --reporter=tap -t 'registers EvalCase and ErrorType in Schemas'`, exit 1, `gsd-tools check tdd-red-evidence` trả `RED_EVIDENCE_OK` (`target_test_failed`). Đánh giá ngữ nghĩa: test đích chạy thật và fail ở assertion đã định (`Object.keys(Schemas)` chưa chứa `EvalCase`); 10/77 test fail, mọi fail đều do thiếu `ErrorType`/`EvalCase`/`EvalCase.json`/`$defs` (các test khác gọi `EvalCase.safeParse` trên `undefined` nên nổ `TypeError`, đúng nguyên nhân kỳ vọng trước khi hiện thực). Reporter `tap`/`tap-flat` in cả mảng nhiều dòng của test đếm fixture nên bị bộ phân loại từ chối ("Non-TAP data"); đã chọn test đích có thông báo một dòng.
- **GREEN** `e4d1721` `feat(04-01)`: hiện thực `eval.ts`, `index.ts`, fixture, sinh lại schema và pydantic. 82/82 test vitest pass; pytest round-trip + drift 70 passed.
- **REFACTOR:** không có.

## Task Commits

1. **Task 1: Liam duyệt A..L** — không commit (checkpoint quyết định; Liam trả lời `approved`, ghi trong bảng ở trên)
2. **Task 2: contract EvalCase** — `d7ad239` (test, RED), `e4d1721` (feat, GREEN)

**Plan metadata:** commit `docs(04-01)` chứa file SUMMARY này.

## Files Created/Modified

- `packages/contracts/src/eval.ts` — `ErrorType`, `EvalAlsoPresent`, `EvalCase` + type export; JSDoc liệt kê bất biến A5 và quy ước `split` vắng mặt
- `packages/contracts/src/index.ts` — `Schemas.ErrorType`, `Schemas.EvalCase`
- `packages/contracts/src/contracts.test.ts` — đếm 17 fixture, `describe("phase 4 contract edges (EvalCase)")`, `$defs` mới
- `packages/contracts/fixtures/EvalCase.json` — 5 case
- `packages/contracts/schema/contracts.schema.json`, `services/audio/src/audio_service/contracts_gen.py` — sinh, không sửa tay

## Decisions Made

Mọi quyết định thuộc bảng "Quyết định đã chốt" ở trên. Ngoài bảng: không thêm kiểu, trường hay giá trị nào (prohibition EVL-01). `EvalAlsoPresent` không nằm trong `Schemas` mà vào `$defs` qua tham chiếu từ `EvalCase` (đúng plan: chỉ `ErrorType` và `EvalCase` được thêm vào `Schemas`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree thiếu node_modules và .venv**
- **Found during:** bắt đầu Task 2
- **Issue:** worktree mới không có `node_modules` / `services/audio/.venv`
- **Fix:** `pnpm install --frozen-lockfile` và `uv sync --project services/audio --frozen` (chỉ theo lockfile, không thêm package, lockfile không đổi)
- **Files modified:** không có file được theo dõi nào

**2. [Rule 1 - Bug] ESLint `no-unused-vars` trong test mới**
- **Found during:** Task 2, bước lint trước GREEN
- **Issue:** destructuring `{ segTextHash: _omit, ...rest }` bị `@typescript-eslint/no-unused-vars` báo lỗi
- **Fix:** dùng bản sao `Record<string, unknown>` rồi `delete withoutHash.segTextHash`
- **Files modified:** `packages/contracts/src/contracts.test.ts`
- **Commit:** `e4d1721`

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug). **Impact:** không ảnh hưởng phạm vi; không đổi contract ngoài bảng đã duyệt.

## Authentication Gates

Không có.

## Issues Encountered

- Plan ghi `ErrorType` là "pydantic (Literal)"; thực tế codegen cho ra `RootModel[Literal[...]]` (giống `IssueCode`). Không phải lỗi, nhưng 04-02 phải dùng `.root` khi so sánh errorType.
- Không ghi được ledger `gsd-plan-head-before-04-01` trong `.git/worktrees/` (harness chặn ghi ngoài worktree); `plan_head_before` lấy từ SHA base của prompt và đã đối chiếu `git rev-list --count` = 2.

## Known Stubs

Không có.

## Threat Flags

Không có bề mặt mới ngoài threat model của plan (T-04-01, T-04-02 đã được giảm thiểu: chỉ sinh qua `contracts_gen.sh`, drift gate xanh, `score.ts` không đổi).

## Next Phase Readiness

Sẵn sàng cho 04-02: `ErrorType`, `EvalCase` có ở pydantic để `eval/evalkit/cases.py` parse từng dòng `cases.jsonl` và kiểm bất biến A5; mọi giá trị A..L chốt ở bảng trên.

## Self-Check: PASSED

- `packages/contracts/fixtures/EvalCase.json`: FOUND
- `packages/contracts/src/eval.ts` chứa `meta({ id: "EvalCase" })`, `meta({ id: "ErrorType" })`, `meta({ id: "EvalAlsoPresent" })`, `segTextHash: z.string().length(16)`: FOUND
- Commit `d7ad239`, `e4d1721`: FOUND (ancestor của HEAD)
- `sh scripts/contracts_check.sh`: thoát 0; vitest 82/82; pytest 70 passed; `git diff HEAD -- packages/contracts/src/score.ts`: rỗng
