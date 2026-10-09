"""MỘT file ngưỡng có version cho chấm ngữ điệu P2 (D-12, D-13).

Mọi giá trị dưới đây là giá trị Liam đã duyệt ở 03-01 mục E (2026-10-09, không sửa). Đổi bất kỳ
giá trị nào ngoài quy trình (Liam duyệt, Phase 4 chỉnh qua eval) là vi phạm CLAUDE.md.
`THRESHOLDS_VERSION` và `SCORER_VERSION` đi vào `ScoreResult.versions`; khi đổi giá trị thì tăng
version.

Các hằng số cuối file (rule Lớp C, prominence) chưa dùng ở 03-03; chúng nằm sẵn đây để 03-06
import mà không phải sửa file này.
"""

from __future__ import annotations

THRESHOLDS_VERSION = "p2-1"  # 03-01 mục E
SCORER_VERSION = "prosody-1"  # 03-01 mục E

# --- Căn thời gian (D-01, D-02; RESEARCH Pattern 2) ------------------------------------------
ALIGN_COST_MAX = 1.10  # căn ok khi chi phí DTW chuẩn hoá <= giá trị này (RESEARCH Pattern 2)
ALIGN_RATIO_MIN = 0.5  # tỉ lệ độ dài người học / bản gốc tối thiểu (giới hạn tập bước DTW)
ALIGN_RATIO_MAX = 2.0  # và tối đa; ngoài khoảng thì không dựng ma trận (RESEARCH Pitfall 6)
ALIGN_SLACK_FRAMES = 30  # biên nới 300 ms hai đầu trục người học (RESEARCH Pattern 2)

# --- Chỉ số (D-05) ------------------------------------------------------------------------------
MIN_COMMON_VOICED_FRAMES = 10  # ít frame hữu thanh chung hơn mức này thì melodyMatch = 0 (D-05)

# --- Độ giống từng từ (03-01 mục G, RESEARCH A9) -------------------------------------------------
SIMILARITY_RMS_ST = 6.0  # RMS lệch semitone ứng với similarity 0
SIMILARITY_MIN_FRAMES = 5  # ít frame chung hơn thì dùng melodyMatch của câu

# --- Rule Lớp C: PITCH_DEVIATION (product.md §3 Lớp C, D-13) ------------------------------------
PITCH_DEVIATION_ST = 3.0  # D-13: đầu trên của khoảng 2-3 st, ưu tiên precision
PD_MIN_FRAMES = 10  # RESEARCH Pattern 4: đủ frame hữu thanh chung trong từ
PD_VOICED_RATIO = 0.5  # RESEARCH Pattern 4: tỉ lệ frame hữu thanh chung tối thiểu của từ
# RESEARCH Pattern 4: tỉ lệ frame cùng dấu của (user - ref - offset câu)
PD_SIGN_CONSISTENCY = 0.8

# --- Rule Lớp C: EXTRA_PAUSE (product.md §3 Lớp C) ----------------------------------------------
PAUSE_USER_MS = 250  # product.md §3: ngắt của người học tối thiểu
PAUSE_REF_MS = 100  # product.md §3: bản gốc phải không có ngắt >= giá trị này ở vị trí đó
PAUSE_SILENCE_DB_BELOW_P95 = 35  # RESEARCH Pattern 3: lặng = dB dưới p95 ít nhất 35 dB
PAUSE_WORD_SNAP_MS = 100  # RESEARCH Pitfall 7: cách đuôi từ gần nhất tối đa

# --- Rule Lớp C: FLAT_PITCH (product.md §3 Lớp C, D-12) -----------------------------------------
FLAT_RATIO = 0.6  # product.md §3: pitchRange < 0.6
FLAT_REF_MIN_STD_ST = 2.0  # D-12: bỏ qua khi chính bản gốc phẳng

# --- Rule Lớp C: FINAL_CONTOUR (product.md §3 Lớp C, D-12) --------------------------------------
FINAL_WINDOW_FRAMES = 30  # 300 ms cuối câu
FINAL_MIN_VOICED_FRAMES = 15  # frame hữu thanh tối thiểu mỗi bên trong cửa sổ cuối
FINAL_SLOPE_MIN_ST_S = 6.0  # |độ dốc| tối thiểu (st/s), RESEARCH Pitfall 4
FINAL_SLOPE_MAX_ST_S = 30.0  # |độ dốc| tối đa (Theil-Sen), hai bên ngược dấu

# --- Rule Lớp C: STRESS_MISMATCH và prominence (product.md §3 Lớp B/C, D-12) --------------------
STRESS_MARGIN_Z = 0.5  # biên z giữa từ nổi nhất và từ thứ hai, cả hai bên (RESEARCH Pattern 4)
STRESS_MIN_WORDS = 5  # prominence chỉ đáng tin với câu từ 5 từ (RESEARCH Pattern 3)
PROMINENCE_MIN_VOICED_FRAMES = 3  # từ có ít frame hữu thanh hơn thì không xếp hạng
