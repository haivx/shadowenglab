---
phase: 03-p2-ch-m-ng-i-u
plan: 11
subsystem: scoring
tags: [smoke, scoring, f0, vad, adr, sqlite]

requires:
  - phase: 03-p2-ch-m-ng-i-u
    provides: "ref_prosody_for_segment(write_cache=False) (03-05), prepare_features / score_prosody (03-03, 03-06), thresholds p2-1 and criterion D-a (03-01)"
provides:
  - "make smoke-score: read-only real-data self-compare, cross-sentence and timing check"
  - "ADR 0006 (Phase 3 scoring decisions + 03-11 fixes)"
  - "Scoring robustness fixes found by the real-data smoke: SCORER_VERSION prosody-2, FEAT_VERSION pf-2, VAD absolute branch, FINAL_CONTOUR aligned tail"
affects: [03-verify, 03-ship, phase-04-eval]

actuals:
  tasks: 3
  commits: 10

key-files:
  created:
    - scripts/smoke_score.py
    - services/audio/tests/test_smoke_score.py
    - docs/decisions/0006-cham-ngu-dieu-p2.md
  modified:
    - Makefile
    - CLAUDE.md
    - scripts/README.md
    - services/audio/src/audio_service/lesson/vad.py
    - services/audio/src/audio_service/scoring/metrics.py
    - services/audio/src/audio_service/scoring/thresholds.py
    - services/audio/src/audio_service/scoring/features.py
    - services/audio/src/audio_service/rules/engine.py
    - services/audio/src/audio_service/db.py
    - services/audio/tests/test_vad.py
    - services/audio/tests/test_scoring_metrics.py
    - services/audio/tests/test_scoring_features.py
    - services/audio/tests/test_scoring_rules.py

key-decisions:
  - "Liam (2026-10-10): pitchRange uses a robust spread (1.4826 * MAD); SCORER_VERSION prosody-2"
  - "Liam (2026-10-10): octave-jump runs fixed at the F0 source (to_semitone second pass, 41 frames, 9-15 st); the approved diff-based melodyMatch filter was tried and dropped because it raised cross-sentence melodyMatch from 0.00 to 0.71"
  - "Liam (2026-10-10): one peak-relative trim rule for both sides, max(p95 - 30, -60) dB; FEAT_VERSION pf-2"
  - "Liam (2026-10-10): VAD counts frames > -35 dBFS when p95 - p10 >= 6 dB; smoke pads 0.3 s silence"
  - "Liam (2026-10-10): FINAL_CONTOUR reads the aligned user tail when alignment is ok"
  - "Liam (2026-10-10): criterion D-a relaxed to the cross median < 0.6; ALIGN_COST_MAX stays 1.10; the 0.6 mark stays and lesson 1 (0.616) is recorded as a risk"

requirements-completed: [PRO-03, PRO-04]

completed: 2026-10-10
status: complete-pending-uat
---

# Phase 3 Plan 11: smoke chấm trên dữ liệu thật, ADR 0006, cổng cuối phase

**`make smoke-score` lần đầu chấm trên audio thật và lộ ra năm lỗi độ bền của bộ chấm. Liam duyệt hướng sửa cho từng lỗi; sau khi sửa, tự so đạt ≥ 0.94 và không còn issue trên cả hai bài. Bài 2 `SCORE OK`. Bài 1 chỉ còn trượt trung vị chéo câu 0.616, Liam chọn ghi nhận là rủi ro thay vì đổi mốc.**

## Accomplishments

- `scripts/smoke_score.py` + `make smoke-score [LESSON=]`: chỉ đọc DATA_DIR (test so danh sách file trước và sau), in bảng gồm tự so / issue / ms / cặp chéo / căn / cost / tỉ lệ cùng các dòng tóm tắt, `SCORE OK` hoặc `SCORE FAILED: <lý do>`.
- Smoke thật tìm ra 5 lỗi, mỗi lỗi có test RED → GREEN và được Liam duyệt hướng sửa:
  1. Qua webm/opus, ~3 % khung F0 nhảy quãng tám thành cụm 9–12 khung (có khi ở phía bản gốc, có khi ở phía người học), kéo pitchRange xuống 0.64 và melodyMatch xuống 0.70 khi tự so. Sửa: pitchRange dùng MAD, `to_semitone` thêm lượt lọc cửa sổ 41 khung.
  2. VAD tương đối trả `no_speech` cho câu nói liền không có lặng (một câu thật tự so ra 0.000). Sửa: thêm nhánh tuyệt đối −35 dBFS khi clip có dao động năng lượng.
  3. Cắt lặng bất đối xứng: lặng thật làm ngưỡng của lượt ghi tụt về sàn, giữ đuôi mà bản gốc đã cắt (tỉ lệ độ dài 1.15, speed 0.87). Sửa: một quy tắc `p95 − 30 dB` cho cả hai phía.
  4. FINAL_CONTOUR báo nhầm khi tự so (−8.2 so với +8.4 st/s) vì mỗi bên lấy đuôi riêng. Sửa: dùng đuôi đã căn khi căn ok.
  5. Tiêu chí D-a "mọi cặp chéo căn không ok" không đạt trên dữ liệu thật (2–7/20 cặp có cost 1.03–1.10). Nới còn tiêu chí trung vị, các cặp này được in ra để theo dõi.
- Ngoài phạm vi chấm: `test_concurrent_*` chập chờn `database is locked` (Phase 2 đã ghi nhận). Nguyên nhân là mỗi connection đều đổi journal mode sang WAL; giờ chỉ đặt một lần cho mỗi DB. Trước khi sửa fail 2/15 lần, sau khi sửa 0/30.
- ADR 0006, CLAUDE.md "Lệnh", scripts/README.md.

## Task Commits

1. **Task 1: smoke-score (tracer, TDD)**: `f08979d` (test), `6be3cc8` (feat), `cf0047c` (cột cost/tỉ lệ), `a4ecc5f` (đệm lặng, nới D-a)
   - Các bản sửa do smoke tìm ra: `8ae5ff4` (VAD), `fc2e8f7` (pitchRange MAD), `60bbf8a` (octave + cắt lặng, pf-2), `24e9f2e` (FINAL_CONTOUR)
2. **Task 2: ADR 0006 + docs**: `e5646ca`
3. **Task 3: cổng cuối**: `df6de33` (sửa WAL để `make test` ổn định)

## Kết quả cổng tự động (2026-10-10)

| Cổng | Kết quả |
|------|---------|
| `make test` | exit 0: drift "contracts: không lệch", contracts 69/69, web 275/275, pytest 1047/1047 |
| `make lint` | exit 0 (eslint, prettier, tsc, ruff check + format) |
| `pnpm --filter @shadowenglab/web build` | exit 0 |
| `make eval` | in stub "make eval: stub — Phase 4 (EVL-02) sẽ chạy eval/analyze.py → eval/report.md" (mục K) |
| `make smoke-score LESSON=01M4C1HEW5RJ475HSYQHWAFWCW` | `SCORE OK` |
| `make smoke-score` (bài mới nhất 01M4CS7EGSP0EBXMAJH7S2APSK) | `SCORE FAILED: trung vị chéo câu 0.616 >= 0.6` (đã báo Liam; giữ mốc 0.6, ghi rủi ro ở ADR 0006) |

## Khối dán vào PR (eval)

> **Eval: chưa có eval (make eval là stub tới Phase 4).** Không có bảng metric. Các số dưới đây là smoke và test tổng hợp, không phải metric eval.
>
> **Smoke trên dữ liệu thật** (`make smoke-score`, audio THẬT của video; "người học" là chính lát vocal của bản gốc, đệm 0.3 s lặng, qua webm/opus; 20 câu mỗi bài; máy rảnh, không tính HTTP):
>
> | Bài | Tự so trung vị / nhỏ nhất | Issue khi tự so | Thời gian chấm p50 / p95 / max | Chéo câu trung vị | Cặp chéo căn không ok | Kết quả |
> |---|---|---|---|---|---|---|
> | dUDi-F6eAvk (hội thoại) | 0.986 / 0.944 | 0 | 70 / 93 / 133 ms | 0.518 | 20/20 | SCORE OK |
> | QWYCtbho-vY (một người nói) | 0.985 / 0.956 | 0 | 68 / 79 / 112 ms | 0.616 | 18/20 | SCORE FAILED (chéo ≥ 0.6) |
>
> Trước các bản sửa của 03-11, cũng hai bài đó: tự so nhỏ nhất 0.000 và 0.778, 1 issue khi tự so, 13/20 cặp chéo căn không ok.
>
> **Phát hiện rule trên dữ liệu TỔNG HỢP** (03-06, bảng đầy đủ ở `03-06-SUMMARY.md`): tự so không issue; EXTRA_PAUSE bắt +300/+500 ms; PITCH_DEVIATION bắt ±4 st (đo 3.1–3.3), bỏ qua +2 st và cả câu +4 st; FINAL_CONTOUR bắt đuôi lên thay vì xuống; STRESS_MISMATCH bắt khi đổi từ nhấn; FLAT_PITCH bắt giọng phẳng, bỏ qua khi bản gốc phẳng; căn kém thì chỉ còn rule mức câu.
>
> **timingMs TỔNG HỢP** (03-05, câu tổng hợp 3 s, sidecar đã cache): total 61 ms, wall 66 ms.

## Smoke đầy đủ (bài 1, số thật, chỉ in số)

```
   #  dài(s)  tự so  issue      ms  chéo vs  chéo  căn  cost  tỉ lệ
   0     3.6  0.983      0      64       #3  0.39  kém  1.21   0.71
   3     4.2  0.986      0     112       #5  0.72  kém  1.15   0.81
   5     5.3  0.980      0      77       #7  0.41  kém  1.10   1.68
   7     3.1  0.978      0      63       #9  0.36  kém  1.19   0.68
   9     4.9  0.990      0      68      #11  0.58  kém  1.18   1.00
  11     5.0  0.989      0      73      #13  0.54  kém  1.16   1.42
  13     3.5  0.986      0      67      #15  0.69   ok  1.05   0.92
  15     4.0  0.977      0      69      #18  0.77  kém  1.12   1.05
  18     3.8  0.988      0      67      #20  0.68  kém  1.17   1.02
  20     3.9  0.983      0      68      #22  0.66  kém  1.15   1.13
  22     3.5  0.983      0      66      #24  0.65  kém  1.18   0.70
  24     5.3  0.992      0      75      #26  0.68  kém  1.14   1.59
  26     3.3  0.983      0      65      #28  0.43  kém  1.23   0.68
  28     5.2  0.992      0      75      #30  0.58  kém  1.12   1.27
  30     4.5  0.992      0      69      #32  0.66  kém  1.16   0.87
  32     4.8  0.956      0      72      #34  0.41  kém  1.15   1.36
  34     3.6  0.971      0      67      #36  0.65   ok  1.07   0.96
  36     3.9  0.967      0      69      #38  0.46  kém  1.15   0.96
  38     4.1  0.989      0      69      #41  0.74  kém  1.22   1.26
  41     3.3  0.988      0      66       #0  0.36  kém  1.17   1.21
```

## Deviations from Plan

- Plan dự kiến chỉ ghi số rồi báo lên nếu smoke trượt. Smoke trượt vì 5 lỗi thật của bộ chấm; với từng lỗi, Liam được hỏi và duyệt hướng sửa trước khi làm (key-decisions). Thay đổi chạm công thức (D-05 pitchRange), feature (cắt lặng, octave), rule FINAL_CONTOUR, VAD và tiêu chí D-a; không đổi ngưỡng nào trong `thresholds.py` (`THRESHOLDS_VERSION` vẫn `p2-1`).
- Lệch khỏi phương án đã duyệt: lọc melodyMatch theo hiệu bị bỏ sau khi đo (làm hỏng độ phân biệt chéo câu), Liam đã duyệt thay bằng sửa ở nguồn F0. Nhánh VAD tuyệt đối có thêm điều kiện dao động ≥ 6 dB để giữ test ồn đều của P2.
- Sửa WAL trong `db.py` nằm ngoài phạm vi plan (test chập chờn chặn cổng `make test`); không đổi schema.

## Issues Encountered

- `make smoke-score` mặc định chọn bài ready mới nhất (bài 1), bài này trượt mốc chéo 0.6. Dùng `LESSON=01M4C1HEW5RJ475HSYQHWAFWCW` để có `SCORE OK`. Không hard-code id bài trong Makefile vì DATA_DIR là dữ liệu cục bộ.

## UAT (chờ Liam, `make dev` tại http://localhost:3000)

| # | Mục | Kết quả |
|---|-----|---------|
| 1 | Giọng thật: 3–5 câu đọc đúng, 3–5 câu đọc sai rõ (câu khác / phẳng / ngắt thêm / lên thay vì xuống cuối câu); ghi overall, issue, tip; xem cost căn có ≤ 1.10 khi đọc đúng (RESEARCH A1) | chờ |
| 2 | Sáu trạng thái vùng câu so với `S3-trang-thai-cau.png` (đang phát, đang ghi, không có tiếng, skeleton chấm, kết quả, lỗi khi tắt API) và "Thử lại" giữ bản ghi | chờ |
| 3 | Panel kết quả so với `S3-S4-phong-tap.png`: ScoreHero, biểu đồ "So sánh ngữ điệu" (câu 1 từ và ~25 từ), tip 01–03 hover/focus, tip dài / câu 18 từ ở 1280 px | chờ |
| 4 | O / M / B; `R` hai lần với lượt sau kém hơn: "tốt nhất" đứng yên, chip cũ hiện kết quả đã lưu, M/B tắt kèm tooltip; danh sách câu và thanh tiến độ theo điểm tốt nhất | chờ |
| 5 | Không có API key: chấm và tip template vẫn chạy, không có nhãn "AI" | chờ |

## Next Phase Readiness

- Sau UAT: Verify Phase 3 đối chiếu tiêu chí ROADMAP 1–5, rồi Ship (PR dùng khối eval ở trên).
- Phase 4 nhận: `ALIGN_COST_MAX` cần đo trên giọng thật, trọng số overall (câu sai cùng người nói ~0.6), recall của STRESS_MISMATCH / FINAL_CONTOUR.

## Self-Check: PASSED (phần tự động); UAT chờ Liam
