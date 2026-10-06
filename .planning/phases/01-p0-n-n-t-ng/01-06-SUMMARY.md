---
phase: 01-p0-n-n-t-ng
plan: 06
subsystem: audio-pipeline
tags: [yt-dlp, ffmpeg, demucs, mlx-whisper, wav2vec2, parselmouth, atomic-status, tracer]

requires:
  - phase: 01-p0-n-n-t-ng
    provides: "01-02 config.py + Lesson sinh tự động, 01-03 models.py, 01-04 split_sentences/urls/quality/contract_io"
provides:
  - "run_lesson(url, start, end): URL -> lesson.json ready + seg/NNNN.npz (f0_hz, energy, ppg, window) + timing.json, ghi lại atomic ở mọi lần đổi trạng thái"
  - "scripts/smoke_lesson.py: CLI in LESSON_ID, bảng thời gian, SELF-CHECK OK, BUDGET OK/EXCEEDED (thoát 0/1/2/3)"
  - "PipelineDeps/default_deps: stage tiêm được (test dùng stage giả, 01-08 tối ưu thời gian chỉ đổi default_deps/pipeline)"
  - "scripts/smoke_video.url: video smoke Liam đã duyệt (01-01 mục 10)"
affects: [01-07, 01-08, 01-09, phase-2]

actuals:
  tokens: 14100
  tasks: 2
  commits: 2
plan_head_before: 9a59e51123d14e6580bb785b01b0a88e63049bf1
plan_head_after: 5ad72cf9319cc20cb68542854b6256addfd92748

tech-stack:
  added: []
  patterns:
    - "Stage nặng tiêm qua PipelineDeps; hàm DSP thuần (mảng vào, mảng ra), chỉ audio_io/download/pipeline chạm file"
    - "File audio/cache ghi qua tên .part rồi os.replace, nên wav dở dang không bao giờ trông như cache hợp lệ"
    - "lesson.json ghi lại atomic ở mọi trạng thái, on_status(lesson) chỉ gọi SAU khi file đã nằm trên đĩa"
    - "Model nạp tuần tự, giải phóng giữa stage (free_memory), MPS có fallback CPU cho Demucs và PPG"

key-files:
  created:
    - services/audio/src/audio_service/lesson/timing.py
    - services/audio/src/audio_service/lesson/download.py
    - services/audio/src/audio_service/lesson/audio_io.py
    - services/audio/src/audio_service/lesson/separate.py
    - services/audio/src/audio_service/lesson/transcribe.py
    - services/audio/src/audio_service/lesson/features.py
    - services/audio/src/audio_service/lesson/pipeline.py
    - scripts/smoke_lesson.py
    - scripts/smoke_video.url
    - services/audio/tests/test_pipeline.py
    - services/audio/tests/test_features.py
  modified: []

key-decisions:
  - "Separator nạp model `hf://htdemucs` (không phải `htdemucs` trần) để Demucs không bao giờ rơi về repo AWS cũ, khớp 01-03"
  - "Không có lời nói trong khoảng đã chọn -> failed ở bước segmenting (NoSpeech), không ghi lesson ready rỗng"
  - "on_status nhận cả Lesson (không chỉ tên trạng thái) để script biết id và error.step khi lỗi"
  - "Cache theo videoId kiểm tra file trước khi gọi stage: pipeline bỏ qua download/extract/separate, không phụ thuộc stage tự cache"

requirements-completed: [FND-07]

coverage:
  - id: D1
    description: "smoke_lesson.py trên lát 60 s video thật tạo lesson ready hợp lệ với contract, mỗi segment một .npz đủ f0_hz/energy/ppg/window, in bảng thời gian và SELF-CHECK OK"
    requirement: FND-07
    verification:
      - kind: other
        ref: "uv run --project services/audio --frozen python scripts/smoke_lesson.py 'https://www.youtube.com/watch?v=dUDi-F6eAvk' --start 0 --end 60 -> SELF-CHECK OK (chạy hai lần: lạnh 92.9 s, cache 36.2 s)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Thứ tự trạng thái queued..ready, failed + error{step,message} khi lỗi, tái dùng cache video/audio/stem, URL/khoảng sai không tạo gì, Word.i từ 0 mỗi segment, padMs 150 và endExtraMs 0 ghi tường minh"
    requirement: FND-07
    verification:
      - kind: unit
        ref: "services/audio/tests/test_pipeline.py (35 test, không nạp model)"
        status: pass
    human_judgment: false
  - id: D3
    description: "F0 trên sine 200 Hz, bước năng lượng 10 ms, segment_window kẹp biên, PPG chuyển MPS sang CPU khi lỗi"
    requirement: FND-07
    verification:
      - kind: unit
        ref: "services/audio/tests/test_features.py (19 test)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Chất lượng thực tế của việc tách câu và nhãn music trên video smoke (13 segment, nonVocalRatio -19.1 dB)"
    requirement: FND-07
    verification: []
    human_judgment: true
    rationale: "Ngưỡng tách câu (RESEARCH A1) và ngưỡng music (A2) chỉ kiểm bằng một video; Liam cần xem danh sách segment bên dưới. Mốc 5 phút <= 5 phút đo ở 01-08 Task 3, không ở plan này"

duration: 35min
completed: 2026-10-06
status: complete
---

# Phase 1 Plan 06: Pipeline tạo bài đầu-cuối Summary

**`scripts/smoke_lesson.py <url>` chạy yt-dlp (Python API) -> ffmpeg -> Demucs htdemucs trên MPS -> mlx-whisper (word timestamps) -> split_sentences -> F0 + energy + PPG theo segment và ra lesson.json hợp lệ với contract, chứng minh trên lát 60 s thật của video smoke: 13 segment, nonVocalRatio -19.1 dB (clean), tổng 92.9 s lần chạy lạnh.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-10-06T08:32Z
- **Tasks:** 2 (Task 1 tracer, Task 2 TDD hardening)
- **Files created:** 11, modified: 0
- **Commits:** 2 (`a37a3e9` tracer, `5ad72cf` test) cộng commit SUMMARY

## Bảng thời gian lát 60 s (lần chạy lạnh, video 308 s: tải + tách giọng TOÀN video theo D-07)

Video: "Will Colbert Reunites With Rachel Green on Thanksgiving | Friends | Max" (`dUDi-F6eAvk`, 308 s). Máy: Apple Silicon 8 GB, MPS.

```
step              seconds
--------------  ---------
download             5.40
write                0.05
extract_audio        0.49
demucs              45.43
quality              0.03
resample             0.15
whisper             24.47
segment              0.00
ppg                 15.55
f0                   0.86
write_features       0.13
--------------  ---------
total               92.56

range            0.0-60.0 s (60.0 s)
wall time        92.9 s
realtime factor  1.55x   (so với 60 s lát; Demucs vẫn xử lý cả 308 s)
nonVocalRatio    1.222e-02 (-19.1 dB) -> clean   (ngưỡng tạm -15 dB = 3.16e-02)
segments         13
SELF-CHECK OK
```

Chạy lại ngay sau đó (cache): download 0.00, extract_audio 0.00, demucs 0.13 (chỉ đọc hai stem), whisper 14.37, ppg 19.97, tổng wall 36.2 s, `BUDGET OK` với `--budget-s 300`. Whisper và PPG dao động giữa hai lần (24.5 và 14.4 s; 15.6 và 20.0 s) vì chia sẻ máy với các agent khác nên số này chỉ là chỉ báo; 01-08 Task 3 đo mốc 5 phút trên máy yên.

## Danh sách segment cho Liam xem (lát 0-60 s)

| # | Bắt đầu | Kết thúc | Văn bản |
|---|---------|----------|---------|
| 0 | 0.00 | 2.18 | Will! Hey, you came! |
| 1 | 2.80 | 6.12 | Man, you look incredible! Hot stuff! |
| 2 | 8.40 | 12.82 | Hot stuff? It's good to see you, man. Yeah, you too. |
| 3 | 13.28 | 14.86 | Man, so what are you up to? |
| 4 | 15.38 | 16.98 | I'm a commodities broker. |
| 5 | 17.18 | 20.18 | Really? Yeah, that sounds interesting. Yeah, it's not. |
| 6 | 22.08 | 23.60 | But I'm rich and thin. Oh. |
| 7 | 25.68 | 32.02 | Man, I don't think I've seen you since, uh, Lance Davis' graduation party. That was such a fun night. |
| 8 | 32.16 | 35.18 | Yeah, it would have been good if we had gotten in, but still, real fun. |
| 9 | 36.86 | 38.36 | God, we were lame back then. |
| 10 | 38.42 | 39.92 | Do you remember how into dinosaurs we were? |
| 11 | 44.44 | 46.72 | Yeah. So, what do you do now? |
| 12 | 49.04 | 57.58 | So, how long are you in town? Hi, hey Rachel green |

Nhận xét để Liam quyết (thuộc 01-04, không sửa ở đây): segment 12 dài 8.5 s, gồm hai câu có khoảng lặng nhỏ hơn 0.7 s và câu cuối có vẻ là tiếng một người khác chen vào; segment 2 và 5 gộp nhiều lượt thoại ngắn. Whisper không tách người nói nên đây là giới hạn của dữ liệu đầu vào, không phải lỗi pipeline. Ngưỡng nonVocalRatio -15 dB cho kết quả `clean` với -19.1 dB nhưng video là cảnh phim có nhạc nền nhẹ; ngưỡng vẫn là giá trị tạm (A2).

## Accomplishments

- `run_lesson` đi trọn chuỗi stage và ghi `lesson.json` atomic ở mọi trạng thái; mọi ngoại lệ sau lần ghi đầu để lại `failed` + `error {step, message}` (cắt 500 ký tự) rồi ném lại. `on_status` chỉ được gọi sau khi file đã nằm trên đĩa (test kiểm từng lần).
- Cache theo videoId (D-07): `video.mp4`, `audio.wav`, `vocals.wav`, `no_vocals.wav`, `info.json`; lần chạy thứ hai không gọi download/extract/separate. Mọi file ghi qua `.part` + `os.replace`.
- Tách giọng trên TOÀN video rồi mới cắt theo `range` (D-07/D-08); nonVocalRatio tính trên đúng khoảng của bài; feature cắt theo `[start - padMs, end + padMs + endExtraMs]` kẹp trong `[0, durationSec]` (D-05).
- `Word.i` từ 0 trong từng segment (01-01 mục 4), `Word.prominence` không tính (mục 5), `padMs 150` và `endExtraMs 0` ghi tường minh, optional vắng mặt chứ không `null`.
- 54 test mới chạy trong ~3 s, không nạp model; toàn bộ suite 271 test pass; ruff check/format sạch trên `src tests scripts` (cả hai cách gọi, xem Deviation 5).

## Task Commits

1. **Task 1: Tracer smoke_lesson.py trên lát 60 s thật** - `a37a3e9` (feat)
2. **Task 2: Test pipeline/feature với stage giả** - `5ad72cf` (test)

Tracer feedback gate (HUMAN_VERIFY_MODE end-of-phase, verify chỉ có `<automated>`): chạy lại verify cuối-đến-cuối (đường cache) trước khi mở rộng, pass, "Tracer verified end-to-end — expanding".

**Plan metadata:** commit `docs(01-06): complete pipeline plan summary`. STATE.md và ROADMAP.md không đụng tới (orchestrator sở hữu).

## Files Created/Modified

- `lesson/timing.py` — `StepTimer` (cộng dồn theo tên), `format_timing_table`
- `lesson/download.py` — `VideoInfo`, `fetch_info`, `download_video` (yt-dlp Python API, `js_runtimes deno`, chỉ nhận `canonical_watch_url`)
- `lesson/audio_io.py` — `extract_audio` (ffmpeg argv, `.part`), `read_audio`, `write_audio`, `to_mono_16k`, `slice_seconds`
- `lesson/separate.py` — `pick_device`, `load_separator` (shifts=0, overlap=0.25, split=True), `separate_vocals`, `free_accelerator_memory`
- `lesson/transcribe.py` — `transcribe_words` (word_timestamps, language en, condition_on_previous_text False)
- `lesson/features.py` — `extract_f0`, `frame_energy`, `PpgModel`, `load_ppg_model`, `compute_ppg` (MPS -> CPU), `segment_window`
- `lesson/pipeline.py` — `PipelineDeps`, `default_deps`, `LessonRun`, `build_segments`, `run_lesson`
- `scripts/smoke_lesson.py`, `scripts/smoke_video.url`
- `tests/test_pipeline.py`, `tests/test_features.py`

## Decisions Made

Xem `key-decisions` ở frontmatter. `on_status(lesson)` thay vì `on_status(status)` là mở rộng nhỏ so với plan, không đổi hành vi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Thiếu bảo vệ bắt buộc] `Separator(model="hf://htdemucs")` thay vì `model="htdemucs"`**
- **Found during:** Task 1 (đọc `demucs/pretrained.py`: `get_model("htdemucs")` âm thầm rơi về repo AWS cũ khi HF lỗi)
- **Issue:** Plan viết "model `DEMUCS_MODEL`"; dùng nguyên văn có thể tải trọng số ngoài nguồn đã khoá (prohibition về model, T-01-09/T-01-18), cùng vấn đề 01-03 đã sửa ở `setup_models`.
- **Fix:** `separate.load_separator` truyền `f"hf://{DEMUCS_MODEL}"`; id vẫn chỉ lấy từ `audio_service.models`.
- **Files modified:** `lesson/separate.py`
- **Commit:** `a37a3e9`

**2. [Rule 2 - Thiếu xử lý lỗi] Không có lời nói -> failed ở `segmenting`**
- **Found during:** Task 1 (thiết kế bước segmenting)
- **Issue:** Plan không nói gì khi Whisper không trả từ nào; ghi `ready` với 0 segment là một bài vô dụng nhưng trông như thành công.
- **Fix:** raise `RuntimeError("NoSpeech: ...")` trước khi sang analyzing; đi qua nhánh failed thông thường. Có test.
- **Files modified:** `lesson/pipeline.py`, `tests/test_pipeline.py`
- **Commit:** `a37a3e9`, `5ad72cf`

**3. [Ghi nhận] Task 2 TDD: không có pha RED thật**
- Fallback MPS -> CPU của `compute_ppg`, `on_status` và nhánh cache được hiện thực luôn trong tracer (Task 1) vì tracer cần chúng chạy trên video thật, nên test của Task 2 pass ngay lần chạy đầu (54 passed). Để chứng minh test không vacuous, đã chủ ý phá hai chỗ: bỏ điều kiện `device == "mps"` của fallback và bỏ kiểm tra cache `video.mp4`; 4 test fail đúng chỗ (`test_ppg_retries_on_cpu_when_mps_raises`, `test_ppg_after_fallback_stays_on_cpu`, `test_second_run_reuses_video_audio_and_stems`, `test_partial_cache_without_stems_still_separates`), rồi hoàn nguyên. Không có commit `refactor`.

**4. [Ghi nhận] Bước timing chi tiết hơn plan**
- Thêm các dòng `write`, `quality`, `resample`, `write_features` ngoài bộ bắt buộc (download, demucs, whisper, segment, f0, ppg), vì resample và ghi file là chi phí thật và 01-08 cần thấy chúng. `ppg` gồm cả thời gian nạp wav2vec2.

**5. [Ghi nhận] ruff cho `scripts/` phụ thuộc thư mục chạy**
- Chạy từ gốc repo với `--config services/audio/pyproject.toml` ruff coi `audio_service` là third-party, chạy từ `services/audio` thì first-party, nên thứ tự import của `scripts/smoke_lesson.py` đòi hai kiểu khác nhau. Dùng `# isort: split` để cả hai cách gọi đều sạch. 01-08 (Makefile lint) nên chọn một cách gọi và giữ nguyên.

**6. [Ghi nhận] Quy trình**
- Lần chạy `ruff format`/`ruff check --fix` đầu tiên (từ gốc repo) vô tình định dạng lại 7 file test của plan khác; đã hoàn nguyên bằng `git checkout -- <từng file>` trước mọi commit, không file ngoài phạm vi nào nằm trong commit.
- Ledger commit (`gsd-plan-head-before-01-06`) không ghi được vào git dir dùng chung từ worktree (công cụ Write bị chặn); dùng trực tiếp base SHA trong prompt (`9a59e51`) để đo `commits: 2` (`git rev-list --count 9a59e51..HEAD` trước commit SUMMARY).
- Chạy thật dùng `DATA_DIR` trong thư mục scratch qua `.env` cục bộ của worktree (đã gitignore, không commit); không đụng `~/shadowenglab-data`.

---

**Total deviations:** 2 auto-fixed (Rule 2) + 4 ghi nhận. **Impact:** siết chặt prohibition về model và trạng thái lỗi; không đổi phạm vi hay giao diện công khai.

## Issues Encountered

- yt-dlp in thanh tiến độ ra stdout làm bẩn output của smoke (thấy ở lần chạy đầu); thêm `noprogress=True` trước khi commit tracer.
- Mốc "bài 5 phút <= 5 phút" CHƯA đo ở plan này (thuộc 01-08 Task 3). Lần chạy lạnh trên video 308 s với range 60 s mất 92.9 s; Demucs (45 s trên cả video) là bước lớn nhất, Whisper trên 300 s đo ở research là 76 s nên tổng cho 300 s dự kiến vào khoảng 190 s, còn dư so với 300 s nhưng cần đo thật.

## Authentication Gates

None. Mạng YouTube hoạt động, không cần đăng nhập.

## User Setup Required

None.

## Threat Flags

None. Mọi bề mặt mới nằm trong threat_model: T-01-15 (ffmpeg argv không shell, yt-dlp Python API chỉ nhận `canonical_watch_url`, đường dẫn qua helper config), T-01-16 (không có HTTP client trong pipeline; chỉ yt-dlp tải video, model chạy cục bộ từ HF cache), T-01-17 (nạp tuần tự, `free_memory` giữa stage), T-01-18 (id model từ `models.py`, không remote code, không processor/phonemizer), T-01-SC (chỉ `uv sync --frozen`, không thêm package).

## Known Stubs

None.

## Next Phase Readiness

- 01-08 Task 3 chạy `make smoke END=300 BUDGET=300` trên DATA_DIR mới; dòng `LESSON_ID=` nằm đầu dòng (đúng mẫu `sed -n 's/^LESSON_ID=//p'`), `SELF-CHECK OK`, `BUDGET OK/EXCEEDED` đã có. Nếu vượt ngân sách, tối ưu (D-26) chỉ đụng `default_deps`/`pipeline.py`/`separate.py`, không đổi model.
- Phase 2 job runner dùng lại `run_lesson` nguyên trạng và poll `lesson.json`.
- `services/audio/README.md` (01-09) cần liệt kê thêm `timing.json` và `info.json` trong DATA_DIR.
- Không có blocker.

## Self-Check: PASSED

- File tồn tại: 7 module `lesson/*.py`, `scripts/smoke_lesson.py`, `scripts/smoke_video.url`, `tests/test_pipeline.py`, `tests/test_features.py` (tất cả trong `git ls-files`).
- Commit `a37a3e9` và `5ad72cf` là tổ tiên của HEAD; `git rev-list --count 9a59e51..HEAD` = 2 trước commit SUMMARY.
- Acceptance Task 1: separate.py có `shifts=0`, `overlap=0.25`; transcribe.py có `word_timestamps=True`, `language="en"`, `condition_on_previous_text=False`; download.py có `canonical_watch_url`, `js_runtimes`; audio_io.py dựng ffmpeg bằng list; features.py có `inference_mode`, `to_pitch_ac`, `segment_window`; ba module import id model từ `audio_service.models`; pipeline.py có `write_contract_json`, `split_sentences`, `"failed"`, `savez_compressed`; output smoke có đủ các dòng download, demucs, whisper, segment, f0, ppg và `SELF-CHECK OK`.
- Verify Task 2: `pytest tests/test_pipeline.py tests/test_features.py -q` -> 54 passed; toàn suite 271 passed; ruff sạch.
- Smoke: thoát 2 với URL ngoài YouTube, `BUDGET EXCEEDED` khi `--budget-s 1`, `BUDGET OK` khi `--budget-s 300`.

---
*Phase: 01-p0-n-n-t-ng*
*Completed: 2026-10-06*
