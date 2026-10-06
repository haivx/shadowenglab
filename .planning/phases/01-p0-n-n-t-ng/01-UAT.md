---
status: testing
phase: 01-p0-n-n-t-ng
source: [01-VERIFICATION.md]
started: 2026-10-06T15:25:21Z
updated: 2026-10-06T15:25:21Z
---

## Current Test

number: 1
name: make eval stub chạy được
expected: |
  `make eval` in dòng "make eval: stub — Phase 4 (EVL-02) ..." và exit 0
awaiting: user response

## Tests

### 1. make eval stub chạy được
expected: `make eval | grep stub` in dòng stub, exit 0 (agent không chạy được vì sandbox từ chối chữ "eval")
result: [pending]

### 2. Ranh giới câu nghe hợp lý để shadowing
expected: Sau `make smoke END=300`, nghe các câu (ffplay theo start/end trong lesson.json): câu không cắt giữa ý, câu ngắn (39/62 câu < 3 s) không quá vụn. Nếu vụn: Liam quyết chỉnh ngưỡng tách câu (RESEARCH A1) ngay hay để Phase 2
result: [pending]

### 3. Nhãn audioQuality "clean" đúng với tai nghe
expected: Nghe `no_vocals.wav` của video smoke: chỉ còn im lặng/tiếng phòng/giọng sót nhỏ, không có nhạc nền rõ (nonVocalRatio −17.5 dB, ngưỡng tạm −15 dB)
result: [pending]

### 4. (Tuỳ chọn) make setup trên cache sạch
expected: `HF_HOME=$(mktemp -d) make setup` tải đủ 3 model có tiến độ và mọi hàng OK (cần mạng, ~3 GB)
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
