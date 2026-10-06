---
phase: 01-p0-n-n-t-ng
plan: 04
subsystem: audio-pipeline
tags: [python, tdd, sentence-splitting, url-validation, ssrf, atomic-write, pydantic, numpy]

requires:
  - phase: 01-01
    provides: "uv.lock đã duyệt, quyết định mục 7 (ngưỡng nonVocalRatio -15 dB), mục 4 (Word.i theo segment)"
provides:
  - "split_sentences + AsrWord: tách danh sách từ Whisper thành span nửa mở (hàm thuần)"
  - "parse_youtube_url / canonical_watch_url / InvalidYoutubeUrl: cổng URL YouTube (T-01-10, T-01-11)"
  - "non_vocal_ratio / audio_quality_label / MUSIC_THRESHOLD_DB: nhãn clean|music (D-09)"
  - "dump_contract / write_json_atomic / write_contract_json: serializer và writer atomic duy nhất cho contract JSON"
affects: [01-06, 01-08]

tech-stack:
  added: []
  patterns:
    - "Hàm thuần có test đỏ-rồi-xanh (RED commit có stub trả giá trị rỗng để RED fail trên assertion, không phải import error)"
    - "Cổng URL: allow-list host + scheme, chặn userinfo/cổng/ký tự điều khiển/nhiều id, yt-dlp chỉ nhận URL dựng lại"
    - "Ghi file atomic: serialize trước khi đụng filesystem, file tạm cùng thư mục, fsync, os.replace, dọn tạm khi lỗi"

key-files:
  created:
    - services/audio/src/audio_service/lesson/__init__.py
    - services/audio/src/audio_service/lesson/segment.py
    - services/audio/src/audio_service/lesson/urls.py
    - services/audio/src/audio_service/lesson/quality.py
    - services/audio/src/audio_service/contract_io.py
    - services/audio/tests/test_segment.py
    - services/audio/tests/test_urls.py
    - services/audio/tests/test_quality.py
    - services/audio/tests/test_contract_io.py
  modified: []

key-decisions:
  - "Chọn điểm cắt cho span dài theo tầng: dấu phẩy/chấm phẩy/hai chấm, nếu không có thì khoảng lặng >= 0.25 s, nếu không có thì khoảng lặng lớn nhất; trong tầng chọn điểm gần giữa nhất và ưu tiên hai nửa >= 1.5 s"
  - "Gộp mảnh ngắn chỉ vào hàng xóm có khoảng lặng nhỏ hơn (hoà thì chọn bên trước); nếu gộp vượt 9 s thì để nguyên, không thử hàng xóm còn lại"
  - "Cổng URL từ chối thêm: cổng tường minh, mọi khoảng trắng/ký tự điều khiển (urlsplit âm thầm bỏ tab/xuống dòng nên có thể lách), dấu gạch ngược"
  - "non_vocal_ratio tích luỹ bằng float64 (float32 tràn khi bình phương biên độ lớn)"
  - "Ngưỡng 'music' so ở miền tỉ lệ: ratio > 10 ** (threshold_db / 10), nên đúng ngưỡng là 'clean'"

patterns-established:
  - "Contract JSON luôn đi qua dump_contract (by_alias + exclude_unset); dựng model thì bỏ hẳn field tuỳ chọn thay vì truyền None"

requirements-completed: [FND-07]

actuals:
  tokens: 7500
  tasks: 3
  commits: 6
plan_head_before: df5a1a61d987445f78dfb1f15efdd2413c6fc929
plan_head_after: 0890092c92dc9f61bfbf2d1a1738638fcb1902aa

coverage:
  - id: D1
    description: "split_sentences phủ mỗi từ đúng một lần, cắt theo dấu câu/khoảng lặng >= 0.7 s, tách span > 8 s hoặc > 15 từ tại dấu phẩy/lặng/khoảng lớn nhất, gộp mảnh < 1.5 s khi kết quả <= 9 s"
    requirement: FND-07
    verification:
      - kind: test
        ref: "services/audio/tests/test_segment.py (86 test gồm 60 seed property)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Cổng URL YouTube chỉ nhận http(s) tới youtube.com/www/m/youtu.be với đúng một id 11 ký tự; yt-dlp chỉ nhận canonical_watch_url"
    requirement: FND-07
    verification:
      - kind: test
        ref: "services/audio/tests/test_urls.py (accept 12 dạng, reject 36 dạng gồm look-alike host, userinfo, 2 id, URL 3000 ký tự, --exec=x)"
        status: pass
    human_judgment: false
  - id: D3
    description: "audio_quality_label trả 'music' chỉ khi nonVocalRatio lớn hơn hẳn ngưỡng 01-01 mục 7 (-15 dB); đúng ngưỡng là 'clean'"
    requirement: FND-07
    verification:
      - kind: test
        ref: "services/audio/tests/test_quality.py#test_label_is_exact_at_the_threshold"
        status: pass
    human_judgment: false
  - id: D4
    description: "write_contract_json không bao giờ để lại file ghi dở; giữ null tường minh, bỏ field tuỳ chọn chưa set, giữ nguyên Unicode, từ chối NaN/Infinity"
    requirement: FND-07
    verification:
      - kind: test
        ref: "services/audio/tests/test_contract_io.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "Chất lượng thực tế của các ngưỡng tách câu và ngưỡng nhãn music trên video thật"
    requirement: FND-07
    verification: []
    human_judgment: true
    rationale: "Ngưỡng là giá trị khởi đầu (RESEARCH A1/A2); unit test chỉ bảo vệ hành vi, không đo chất lượng. 01-06/01-08 in ratio và danh sách segment trên video smoke để Liam xem."

duration: 14min
completed: 2026-10-06
status: complete
---

# Phase 1 Plan 04: Khối xây dựng thuần của pipeline bài Summary

**Bốn khối không cần model của pipeline tạo bài, mỗi khối có test đỏ rồi xanh: tách câu theo dấu câu/khoảng lặng/độ dài, cổng URL YouTube chống SSRF, nhãn clean|music từ tỉ lệ công suất no_vocals/vocals, và writer JSON atomic cho contract.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-10-06T08:00:00Z (xấp xỉ)
- **Completed:** 2026-10-06T08:15:00Z
- **Tasks:** 3 (cả ba TDD)
- **Files created:** 9 (5 module nguồn gồm `lesson/__init__.py`, 4 file test)

## Accomplishments

- `split_sentences(words) -> list[tuple[int, int]]`: span nửa mở liền kề, phủ mỗi từ đúng một lần (property test 60 seed). Cắt sau `.?!` kể cả khi có nháy/ngoặc đóng, hoặc khi lặng >= 0.7 s; tách đệ quy span > 8 s hoặc > 15 từ; gộp mảnh < 1.5 s vào hàng xóm gần hơn khi kết quả <= 9 s.
- `parse_youtube_url` / `canonical_watch_url`: allow-list scheme + host, chặn userinfo, cổng, ký tự điều khiển, hai tham số `v`, URL > 2048 ký tự; id fullmatch `[A-Za-z0-9_-]{11}` (kể cả id bắt đầu bằng `-`).
- `non_vocal_ratio` + `audio_quality_label`: `MUSIC_THRESHOLD_DB = -15.0` (01-01 mục 7), so ở miền tỉ lệ nên `nextafter` của ngưỡng mới thành `music`.
- `dump_contract` + `write_json_atomic` + `write_contract_json`: một serializer (`by_alias=True`, `exclude_unset=True`, `mode="json"`) và một writer atomic dùng `os.replace`.
- Không module nào trong plan import contract sinh tự động (giữ song song với 01-02).

## TDD Gate Compliance

Cả ba task đi đủ RED rồi GREEN; mỗi RED commit chứa stub trả giá trị rỗng để test fail trên assertion cho hành vi dự kiến (không phải lỗi import hay collect). Không có commit REFACTOR (không cần).

| Task | RED (commit) | RED thực tế | GREEN (commit) |
|------|--------------|-------------|----------------|
| 1 split_sentences | `f2d6aaf` | 83 fail / 3 pass (3 pass là hằng số, rỗng, không-đổi-input, đúng với stub) | `0b58ff4` 86 pass |
| 2 URL + quality | `1953864` | 65 fail / 5 pass (các ca không liên quan stub) | `47ddb0f` 70 pass |
| 3 contract_io | `16cde41` | 11 fail / 0 pass (assertion hoặc file không được ghi) | `0890092` 11 pass |

Đánh giá ngữ nghĩa RED: mọi test mục tiêu thực sự chạy và fail vì stub không làm gì (so sánh danh sách rỗng, "DID NOT RAISE", file không tồn tại), không do import/fixture. Ghi chú: `gsd_run check tdd-red-evidence` không được chạy vì workflow.tdd_mode không được orchestrator bật cho plan này; bằng chứng RED là các lần chạy pytest nêu trên.

## Task Commits

1. **Task 1: split_sentences** — `f2d6aaf` (test) rồi `0b58ff4` (feat)
2. **Task 2: Cổng URL YouTube + nhãn chất lượng** — `1953864` (test) rồi `47ddb0f` (feat)
3. **Task 3: contract_io** — `16cde41` (test) rồi `0890092` (feat)

**Plan metadata:** commit `docs(01-04): complete plan summary` (SUMMARY.md). `commits: 6` ở frontmatter là số commit mã nguồn đo từ `df5a1a6..0890092`, chưa tính commit SUMMARY. STATE.md và ROADMAP.md không đụng tới (orchestrator sở hữu).

## Files Created/Modified

- `services/audio/src/audio_service/lesson/__init__.py` — package marker
- `services/audio/src/audio_service/lesson/segment.py` — `AsrWord`, `split_sentences` và các hằng số ngưỡng
- `services/audio/src/audio_service/lesson/urls.py` — cổng URL YouTube
- `services/audio/src/audio_service/lesson/quality.py` — `non_vocal_ratio`, `audio_quality_label`
- `services/audio/src/audio_service/contract_io.py` — serializer và writer atomic
- `services/audio/tests/test_segment.py`, `test_urls.py`, `test_quality.py`, `test_contract_io.py`

## Decisions Made

Xem `key-decisions` ở frontmatter. Hai điểm plan để ngỏ và đã chốt khi hiện thực: (1) "dấu phẩy, else khoảng lặng, else lớn nhất" được hiểu là ba tầng ưu tiên (không gộp dấu phẩy và khoảng lặng vào một tập ứng viên như văn bản RESEARCH); (2) mảnh ngắn chỉ thử gộp vào hàng xóm có khoảng lặng nhỏ hơn. Cả hai thoả mọi ca hành vi của plan; nếu thử video thật cho kết quả kém, đổi ở `_choose_cut` / `_merge_short` là thay đổi cục bộ.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Thiếu bảo vệ bắt buộc] Cổng URL cần từ chối thêm cổng, khoảng trắng/ký tự điều khiển, dấu gạch ngược**
- **Found during:** Task 2 (thiết kế test từ T-01-10)
- **Issue:** `urllib.parse.urlsplit` âm thầm bỏ tab và xuống dòng nên `https://www.you\ttube.com/...` hoặc id bị chèn `\n` vẫn parse ra host/id hợp lệ; cổng tường minh và `youtube.com\@evil.com` cũng là cách lách host. Plan chỉ liệt kê userinfo và host giả.
- **Fix:** từ chối mọi ký tự khoảng trắng/không in được và `\` trong URL sau khi `strip()`, từ chối cổng tường minh, từ chối mọi `@` trong netloc. Có test cho từng dạng.
- **Files modified:** `lesson/urls.py`, `tests/test_urls.py`
- **Verification:** `test_urls.py` 59 pass
- **Commit:** `1953864` (test), `47ddb0f` (code)

**Total deviations:** 1 (Rule 2). **Impact:** chỉ siết chặt thêm biên bảo mật T-01-10/T-01-11, không đổi giao diện công khai hay phạm vi.

## Issues Encountered

None. Cả ba GREEN đạt ngay lần chạy đầu; ruff cảnh báo một biến vòng lặp không dùng (B007) trong test, đã đổi tên.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Threat Flags

None. Plan này chỉ thêm hàm thuần, bộ kiểm tra URL (giảm thiểu T-01-10, T-01-11) và writer file (T-01-12); không thêm endpoint hay bề mặt mới ngoài threat_model.

## Known Stubs

None. (Các stub dùng cho RED commit đã được thay bằng hiện thực thật ở GREEN.)

## Next Phase Readiness

- 01-06 có thể import `split_sentences`, `parse_youtube_url`/`canonical_watch_url`, `non_vocal_ratio`/`audio_quality_label`, `write_contract_json`; 01-06 cần thêm test khẳng định `urls.VIDEO_ID_RE` bằng `config.VIDEO_ID_RE` của 01-02 (theo plan).
- Ngưỡng tách câu và ngưỡng `music` là giá trị khởi đầu; smoke ở 01-08 nên in ratio và danh sách segment để Liam chốt.
- Không có blocker.

## Self-Check: PASSED

- File tồn tại: segment.py, urls.py, quality.py, `lesson/__init__.py`, contract_io.py, bốn file test (đã kiểm khi chạy pytest và ruff).
- Commit `f2d6aaf`, `0b58ff4`, `1953864`, `47ddb0f`, `16cde41`, `0890092` đều là tổ tiên của HEAD (`git log df5a1a6..HEAD` liệt kê đủ sáu).
- Acceptance criteria chạy lại: segment.py có `class AsrWord`, `def split_sentences(`, `HARD_GAP_S = 0.7`, `MAX_DUR_S = 8.0`, `MAX_WORDS = 15`, `MIN_DUR_S = 1.5`, không chứa `contracts_gen`, không IO; urls.py có `ALLOWED_HOSTS`, `class InvalidYoutubeUrl(ValueError)`, `def parse_youtube_url(`, `def canonical_watch_url(`; quality.py có `MUSIC_THRESHOLD_DB: float = -15.0`, `def audio_quality_label(`; contract_io.py có `exclude_unset=True`, `by_alias=True`, `os.replace`, `os.fsync`, `allow_nan=False`, `ensure_ascii=False`.
- Verification plan-level: `uv run --project services/audio --frozen pytest` bốn file test: 167 passed; `ruff format --check` và `ruff check` sạch.

---
*Phase: 01-p0-n-n-t-ng*
*Completed: 2026-10-06*
