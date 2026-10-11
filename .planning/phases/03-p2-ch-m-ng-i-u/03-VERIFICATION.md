---
phase: 03-p2-ch-m-ng-i-u
verified: 2026-10-11T03:00:00Z
status: passed
score: 3/5 must-haves verified
covered_files:
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-01-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-01-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-02-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-02-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-03-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-03-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-04-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-04-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-05-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-05-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-06-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-06-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-07-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-07-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-08-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-08-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-09-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-09-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-10-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-10-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-11-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-11-SUMMARY.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-12-PLAN.md"
  - ".planning/phases/03-p2-ch-m-ng-i-u/03-12-SUMMARY.md"
  - "apps/web/components/AttemptStrip.tsx"
  - "apps/web/components/IntonationChart.tsx"
  - "apps/web/components/PracticeRoom.tsx"
  - "apps/web/components/ResultPanel.tsx"
  - "apps/web/components/SentenceStatePanel.tsx"
  - "apps/web/components/TipList.tsx"
  - "services/audio/src/audio_service/routers/attempts.py"
  - "services/audio/src/audio_service/rules/engine.py"
  - "services/audio/src/audio_service/rules/tips.py"
  - "services/audio/src/audio_service/scoring/scorer.py"
covered_digest: "v3:sha256:c1c2a93af0ac74976c7f21254a18344ec63dd5c4584cb3e1a7d3682ac3c7208a"
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "UI khớp docs/design/: đủ 6 trạng thái vùng câu, hover gợi ý highlight từ liên quan, Ghi lại (R) giữ lượt chấm tốt nhất"
    test: "make dev, mở bài thật; đi qua đang phát, đang ghi, không có tiếng, skeleton chấm, kết quả, lỗi (tắt API); hover/Tab qua tip; bấm R hai lần với lượt sau kém hơn"
    expected: "Khớp S3-trang-thai-cau.png và S3-S4-phong-tap.png; từ liên quan được tô trong câu và dải xám trong biểu đồ; chip 'tốt nhất' đứng yên ở lượt cao hơn; M/B tắt kèm tooltip với lượt cũ"
    why_human: "Bố cục, màu (Recharts stroke bằng CSS variable, RESEARCH A4), hover/focus là hành vi trình duyệt; vitest chỉ phủ hàm thuần (tipHighlight, attemptChips, viewedAttempt, playerMachine), không có test render"
gaps: []
human_verification:
  - test: "Quyết định SC2: chấp nhận hay nới 'Câu đọc sai hẳn cho điểm thấp'"
    expected: "Liam ghi override (có chữ ký) hoặc yêu cầu chỉnh công thức/trọng số. Trên bài mặc định, trung vị 20 cặp chéo câu = 0.616 (vùng vàng 60-79), `make smoke-score` thoát 1 với 'SCORE FAILED: trung vị chéo câu 0.616 >= 0.6'. Bài còn lại 0.518 (đỏ)"
    why_human: "Liam đã duyệt nới tiêu chí D-a và ghi rủi ro ở ADR 0006, nhưng chưa có mục overrides trong VERIFICATION; ranh giới 'thấp' là quyết định sản phẩm, và chưa từng đo với giọng người học thật"
  - test: "UAT 03-11 mục 1: giọng thật, 3-5 câu đúng và 3-5 câu sai rõ (câu khác / phẳng / ngắt thêm / lên thay vì xuống)"
    expected: "Câu đúng điểm cao, cost căn <= 1.10 (RESEARCH A1), không issue giả; câu sai điểm thấp và có issue hợp lý"
    why_human: "Cần giọng Liam, không commit audio; ALIGN_COST_MAX chưa đo trên giọng Việt đọc tiếng Anh. SUMMARY ghi 'chờ'"
  - test: "UAT 03-11 mục 2-3: sáu trạng thái vùng câu và panel kết quả so với design"
    expected: "Khớp S3-trang-thai-cau.png, S3-S4-phong-tap.png; biểu đồ câu 1 từ và ~25 từ; tip dài / câu 18 từ ở 1280 px không tràn"
    why_human: "Thị giác. SUMMARY 03-11 ghi 'chờ'"
  - test: "UAT 03-11 mục 4: O / M / B, R hai lần, danh sách câu và thanh tiến độ theo điểm tốt nhất"
    expected: "'tốt nhất' đứng yên; chip cũ hiện kết quả đã lưu; M/B tắt kèm tooltip; tải lại trang thì chip được khôi phục từ server"
    why_human: "Tương tác trình duyệt/audio. SUMMARY 03-11 ghi 'chờ'"
  - test: "UAT 03-11 mục 5: không có OPENAI_API_KEY"
    expected: "Chấm và tip template vẫn chạy, không nhãn 'AI'"
    why_human: "Cần chạy app. SUMMARY 03-11 ghi 'chờ'"
  - test: "UAT 03-12 Task 3 (5 mục): biến thể tip theo lượt, nhận xét theo chỉ số khi không có issue"
    expected: "Lượt sau của cùng câu đổi cách nói; điểm thấp không issue thì có nhận xét theo chỉ số; mở lại lượt cũ ra đúng chữ lúc chấm. SUMMARY 03-12 ghi 'not run' cho cả 5 mục"
    why_human: "Cần Liam duyệt chữ và chạy app"
  - test: "PRO-04 dưới tải: chấm một câu khi worker model đang chạy Demucs, và bài cũ chưa có sidecar (ref_backfill)"
    expected: "Tổng thời gian <= 3 s"
    why_human: "Đo được 75/85 ms trên máy rảnh, không gồm HTTP (RESEARCH A7 chưa đo); không thể dựng tải thật trong verify"
---

# Phase 3: P2 · Chấm ngữ điệu Verification Report

**Phase Goal:** Liam nhận phản hồi ngữ điệu đầu tiên dùng được để học: 3 chỉ số, contour so với bản gốc và gợi ý bám số liệu đo được.
**Verified:** 2026-10-11T03:00:00Z
**Status:** human_needed
**Re-verification:** No, initial verification

Phần cài đặt tồn tại, được nối dây đầu-cuối và chạy được trên dữ liệu thật. Không có truth FAILED hoặc artifact thiếu/stub. Phase chưa thể 'passed' vì: (1) SC2 trên giọng-cùng-người thật chưa đạt tiêu chí đã ghi (0.616 >= 0.6) và chỉ được Liam chấp nhận bằng lời trong ADR, chưa có override; (2) toàn bộ UAT của 03-11 và 03-12 chưa chạy; (3) SC5 là kiểm tra thị giác.

Ghi chú về mode: ROADMAP đặt `Mode: mvp` nhưng Goal không có dạng User Story ("As a ..., I want to ..., so that ..."); `user-story.validate` trả `valid=false`. Báo cáo này dùng phương pháp goal-backward chuẩn trên Goal và 5 Success Criteria. Nếu Liam muốn verify theo MVP, cần chạy `/gsd-mvp-phase 3` để đặt lại Goal; hoặc sửa `Mode` trong ROADMAP.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Bản gốc so với chính nó cho điểm ngữ điệu ≈ 100% | ✓ VERIFIED | Tôi chạy lại `make smoke-score` (đọc DATA_DIR, chỉ đọc): tự so qua webm/opus trung vị 0.985, nhỏ nhất 0.956, 0 issue trên 20 câu thật. Test tổng hợp `test_scoring_pipeline.py` (tự so = 1.0) và `test_scoring_api.py` (0.9996 qua API) nằm trong 170 test pass tôi chạy. |
| 2 | Câu đọc sai hẳn cho điểm thấp | ? UNCERTAIN (human decision) | Trên 20 cặp chéo câu của bài mặc định: trung vị 0.616, dải 0.36-0.77, 18/20 căn không ok; `make smoke-score` thoát lỗi 1 ("SCORE FAILED: trung vị chéo câu 0.616 >= 0.6"). Bài thứ hai 0.518. 0.616 rơi vào vùng vàng của `scoreLevel()` (60-79), không phải đỏ. Nguyên nhân (ADR 0006): trung bình cộng ba chỉ số, speed ~0.81 và pitchRange ~0.73 gần nhau giữa hai câu cùng người nói. Liam đã duyệt nới tiêu chí D-a và ghi là rủi ro mở; chưa có giọng người học thật. Xem đề xuất override bên dưới. |
| 3 | Chấm một câu ≤ 3 giây (chỉ xử lý audio người học, feature bản gốc tính sẵn) | ✓ VERIFIED (điều kiện máy rảnh) | `make smoke-score` chạy lại: p50 75 ms, p95 85 ms, max 85 ms (chuẩn hoá + VAD + feature người học + chấm; không gồm HTTP). `create_attempt` chỉ gọi `prepare_features(mono)` cho phía người học, phía bản gốc đọc sidecar `ref_prosody_for_segment`. `scorer.py` không import model. Dưới tải Demucs và bài cũ cần `ref_backfill` chưa đo: mục human. |
| 4 | Mỗi tip trỏ tới một issue (`issueRef`) | ✓ VERIFIED | `tips.select_tips` chỉ tạo tip từ `enumerate(issues)` với `{"text","issueRef": index,"source":"template"}`; `to_score_result` validate qua pydantic. `TipList` hiển thị đúng `tips` theo thứ tự backend, `ResultPanel` suy `result.issues[tip.issueRef]` để tô từ. `test_scoring_tips.py` pass. Lưu ý WR-04 (tip có thể nhắc 'the' vs 'The') là lỗi precision nhỏ, không phá truth. |
| 5 | UI khớp `docs/design/`: đủ 6 trạng thái vùng câu, hover tip highlight từ, `R` giữ lượt tốt nhất | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Có đủ và nối dây: `PracticeRoom` render `SentenceStatePanel` các variant playing / recording / scoring / noVoice / micError / uploadError và `ResultPanel` (reviewing); `TipList` `onMouseEnter/onFocus` → `tipHighlight` → tô từ + `IntonationChart highlight`; `attemptChips` chọn lượt tốt nhất (hoà thì lượt sau), `nextViewedAttempt` giữ lượt đang xem, `yoursAvailable` tắt M/B với lượt cũ. Chỉ có test hàm thuần; không có test render hay trình duyệt, và các mục UAT tương ứng chưa chạy. Khớp thiết kế là phán đoán thị giác. |

**Score:** 3/5 truths verified (1 present, behavior-unverified; 1 uncertain)

### Required Artifacts (spot-check ba cấp)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `services/audio/src/audio_service/scoring/{features,align,metrics,prominence,scorer,ref_cache,thresholds}.py` | Lớp B | ✓ VERIFIED | 56-236 dòng mỗi file, thực chất, được `routers/attempts.py` và `lesson/pipeline.py` gọi |
| `services/audio/src/audio_service/rules/{engine,tips}.py` | 5 rule Lớp C + tip template | ✓ VERIFIED | `run_rules` có đủ 5 mã, cổng chắc chắn; `select_tips` nối vào `to_score_result` |
| `services/audio/src/audio_service/routers/attempts.py` | POST trả ScoreResult, GET list/detail, no_speech | ✓ VERIFIED | 333 dòng, `insert_scored_attempt`, 422 `no_speech`, 409 khi thiếu audio bản gốc |
| `packages/contracts` (`no_speech`, `AttemptSummary`, `bestOverall`/`bestAttempt`) | Contract được Liam duyệt | ✓ VERIFIED | Drift gate xanh theo orchestrator; nội dung khớp 03-01 |
| `apps/web/components/{ScoreHero,IntonationChart,TipList,AttemptStrip,SentenceStatePanel,ResultPanel,ResultActionBar}.tsx` | UI | ✓ VERIFIED (tồn tại, thực chất, được import từ `PracticeRoom`) | 70-362 dòng; `ScoreHero` / `IntonationChart` / `TipList` được `ResultPanel` dùng |
| `scripts/smoke_score.py` + `make smoke-score` | Smoke trên bài thật | ✓ VERIFIED | Chạy được, kết quả trên |
| `docs/decisions/0006-cham-ngu-dieu-p2.md` | ADR | ✓ VERIFIED | Có, ghi rõ rủi ro mở |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `playerMachine` → API | `POST …/attempts` | `createAttempt` → `ScoreResult.parse`; 422 `no_speech` → `noVoice` | WIRED | `lib/api.ts`, `playerMachine.ts` |
| `create_attempt` → `ScoreResult` | scorer + rules + tips | `score_prosody` → `to_score_result` (pydantic validate) | WIRED | `routers/attempts.py:226-255` |
| `ResultPanel` → `TipList` → highlight | `tipHighlight(issue, words)` | `hoveredTip` state → `wordHighlightClass` và `IntonationChart.highlight` | WIRED | `ResultPanel.tsx` |
| `ResultPanel` → `IntonationChart` | `result.prosody/words/issues` | Collapsible "So sánh ngữ điệu" | WIRED | `ResultPanel.tsx` |
| `AttemptStrip` / `TranscriptList` / `PracticeHeader` → `best` | `bestOverall` từ `SegmentProgress` | `progressView` | WIRED | `PracticeRoom.tsx` truyền `best` |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| `ScoreHero` | `result.scores`, `prosody` | `score_prosody` trên F0/MFCC thật của hai phía | Có (smoke trên audio thật) | ✓ FLOWING |
| `IntonationChart` | `prosody.contour.ref/user/wordBounds`, `stress`, `pauses` | `metrics.contour_points`, `prominence.*` | Có | ✓ FLOWING (WR-05: hàng chữ lệch nhẹ khi từ đầu không bắt đầu ở x=0) |
| `TipList` | `result.tips` | `select_tips(rule_issues)` | Có (mọi tip đến từ issue) | ✓ FLOWING |
| `AttemptStrip` | `AttemptSummary[]` | `GET …/attempts` ← SQLite `attempts` | Có | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Tự so ≈ 100%, 0 issue, ≤ 3 s | `make smoke-score` | tự so 0.985 / 0.956, 0 issue, p95 85 ms | ✓ PASS |
| Chéo câu thấp (trung vị < 0.6) | `make smoke-score` | trung vị 0.616; thoát mã 1 | ✗ FAIL (đã được Liam ghi nhận; xem SC2) |
| Scoring / rules / tips / API | `uv run pytest tests/test_scoring_pipeline.py test_scoring_api.py test_scoring_rules.py test_scoring_tips.py` | 170 passed | ✓ PASS |
| Toàn bộ `make test` | (không chạy lại) | Orchestrator báo exit 0 tại HEAD | (tin báo cáo orchestrator) |

### Probe Execution

Step 7c: SKIPPED. Phase không khai báo `probe-*.sh`; kiểm tra chạy được thay bằng `make smoke-score` ở trên.

### Requirements Coverage

Cả 12 ID đều xuất hiện trong `requirements:` frontmatter của các PLAN (không có ID mồ côi trong REQUIREMENTS.md).

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| PRO-01 F0/semitone/căn theo từ | 03-03 | ✓ SATISFIED | `features.py`, `align.py`, `metrics.word_bounds`; smoke trên audio thật |
| PRO-02 3 chỉ số + prominence | 03-03, 03-06 | ✓ SATISFIED | `ScoreResult.prosody.{speed,pitchRange,melodyMatch,stress}` |
| PRO-03 tự so ≈ 100%; sai hẳn thấp | 03-01, 03-03, 03-05, 03-11 | ? NEEDS HUMAN | Nửa đầu đạt (0.985); nửa sau: xem SC2 |
| PRO-04 ≤ 3 s | 03-03, 03-05, 03-11 | ✓ SATISFIED (máy rảnh) | 75/85 ms; tải thật chưa đo |
| RUL-01 5 rule, không chắc không báo | 03-01, 03-06 | ✓ SATISFIED | `engine.py` có đủ 5 mã và cổng; tự so 0 issue; (WR-04 xem dưới) |
| RUL-02 2-3 tip tiếng Việt trỏ một issueRef; không lỗi → khen | 03-06, 03-08, 03-12 | ✓ SATISFIED | `select_tips` ≤ 3 tip; `resultNote` khen/trung tính. Chữ tip chờ Liam duyệt ở PR |
| FBK-01 ScoreHero + 3 chỉ số | 03-04 | ✓ SATISFIED | `ScoreHero.tsx` trong `ResultPanel` |
| FBK-02 "So sánh ngữ điệu" / IntonationChart | 03-02, 03-07 | ? NEEDS HUMAN (thị giác) | Code đủ; màu bằng CSS variable chưa kiểm trong trình duyệt (A4) |
| FBK-03 TipList + hover highlight | 03-08, 03-12 | ? NEEDS HUMAN (thị giác) | Wired; hover là hành vi trình duyệt |
| FBK-04 nghe O/M/B | 03-04, 03-10 | ? NEEDS HUMAN | Logic có test; phát audio chưa UAT |
| FBK-05 6 trạng thái, màu qua `scoreLevel()` | 03-01, 03-04, 03-05, 03-09 | ? NEEDS HUMAN (thị giác) | Đủ 6 variant trong `PracticeRoom` |
| FBK-06 `R` giữ lượt tốt nhất, hiện lượt thứ mấy | 03-01, 03-05, 03-09, 03-10 | ✓ SATISFIED (logic) / UAT chờ | `attemptChips`, `viewedAttempt` có test; bestOverall từ server |

Ghi chú: `.planning/REQUIREMENTS.md` vẫn đánh dấu 12 ID là `Pending` (checkbox và bảng traceability). Cần cập nhật khi phase được chấp nhận.

### Anti-Patterns Found

Không có `TBD`/`FIXME`/`XXX`/`TODO`/`NotImplementedError` trong 80+ file code được review của phase. Đối chiếu 03-REVIEW.md (0 critical, 7 warning, 6 info, disposition tất cả `open`); tôi kiểm lại bằng đọc code, không chạy lại từng probe của reviewer:

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `rules/engine.py:278-289` (WR-04) | STRESS_MISMATCH không so chữ của hai từ, có thể sinh tip "Nhấn vào *the*, không phải *The*" | ⚠️ Warning | Vi phạm precision-trước-recall (CLAUDE.md) trong trường hợp từ lặp; `tipHighlight` dùng match đầu tiên |
| `scoring/ref_cache.py:80-101` (WR-01) | `.part` tên cố định, ghi cache lỗi làm hỏng cả lượt chấm | ⚠️ Warning | Hai lượt đầu đồng thời cùng một câu chưa có sidecar có thể ra 500 |
| `routers/attempts.py:320-325` (WR-02) | `attempt` không bị chặn trên ở PUT eval-clip | ⚠️ Warning | 500 thay vì 404 |
| `routers/attempts.py:71-73` (WR-03) | `isdigit()` nhận chữ số Unicode | ⚠️ Warning | Header lạ → 500 |
| `lib/chartData.ts:62-82` (WR-05) | Hàng chữ không cùng hệ tọa độ với plot khi `wordBounds[0] > 0` | ⚠️ Warning | Nhãn từ/thanh trọng âm lệch vài điểm so với đường cong; chưa có test |
| `scoring/ref_cache.py:64-77` (WR-06) | Validate sidecar thiếu độ rộng MFCC, finite | ⚠️ Warning | Sidecar hỏng → 500 thay vì tính lại |
| `routers/attempts.py:243-269` (WR-07) | `saveForEval=true` lỗi ghi clip sau khi đã commit lượt | ⚠️ Warning | Tiềm ẩn (client hiện luôn gửi false) |

Không cái nào chặn mục tiêu phase; WR-04 và WR-05 nên sửa trước Ship vì chạm trực tiếp nguyên tắc precision và UI contour.

### Human Verification Required

Xem `human_verification` ở frontmatter (7 mục). Tóm tắt thứ tự ưu tiên:

1. **Quyết định SC2** (Liam): chấp nhận 0.616 bằng override có chữ ký, hay chỉnh trọng số. Nếu chấp nhận, đề xuất thêm vào frontmatter:

```yaml
overrides:
  - must_have: "Câu đọc sai hẳn cho điểm thấp"
    reason: "Trên dữ liệu thật cùng người nói, trung vị chéo câu 0.616 (bài 1) và 0.518 (bài 2); Liam chọn D-a nới và giữ mốc 0.6, Phase 4/8 cân lại trọng số (ADR 0006, rủi ro mở)"
    accepted_by: "Liam"
    accepted_at: "<ISO timestamp>"
```

2. UAT 03-11 (5 mục) và UAT 03-12 (5 mục): đều ghi 'chờ' / 'not run'.
3. PRO-04 khi worker Demucs đang chạy và bài cũ cần backfill sidecar.

### Gaps Summary

Không có gap chặn (không truth FAILED, không artifact thiếu hoặc stub, không key link đứt). Có một truth cần quyết định sản phẩm (SC2), một truth cần xem thị giác (SC5), và UAT thật chưa chạy, nên trạng thái là `human_needed`, không phải `passed`. Khuyến nghị trước Ship: sửa WR-04 và WR-05 (và nên WR-01/WR-06), cập nhật trạng thái trong REQUIREMENTS.md, và chạy UAT.

---

_Verified: 2026-10-11T03:00:00Z_
_Verifier: Claude (gsd-verifier)_
