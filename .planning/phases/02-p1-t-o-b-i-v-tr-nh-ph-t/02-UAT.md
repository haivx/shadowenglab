---
status: testing
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
source: [02-VERIFICATION.md]
started: 2026-10-08T03:13:00Z
updated: 2026-10-08T03:13:00Z
---

## Current Test

number: 1
name: SC3 mouse only: practise 30 sentences end to end in Chrome (hear sample, record, listen back, next) using only buttons and the transcript list
expected: |
  No dead end; no greyed button without a way out; every action reachable by a labelled 44-48 px button
awaiting: user response

## Tests

### 1. SC3 mouse only: practise 30 sentences end to end in Chrome (hear sample, record, listen back, next) using only buttons and the transcript list
expected: No dead end; no greyed button without a way out; every action reachable by a labelled 44-48 px button
result: [pending]

### 2. SC3 keyboard only: the same 30 sentences using only Space, R, Left/Right, O, M, B, I, T
expected: Focus never trapped in a dialog or input; Space never scrolls the page; the full loop completes
result: [pending]

### 3. SC5 UI fidelity: compare S1, S2, S3, S8 side by side with docs/design/screens (S1-thu-vien, S2-tao-bai, S3-S4-phong-tap, S3-trang-thai-cau, S8-settings) in Chrome
expected: Matches design apart from approved deviations G1-G24 and D-09; Figtree and Vietnamese diacritics render; no box shadows; footer wrap at 1024 px; 20-word sentence at 1280 px
result: [pending]

### 4. SC4 UI pass without a key: remove OPENAI_API_KEY from .env, restart make dev
expected: Yellow banner shows and does not block; a lesson can be created and practised; Dich is aria-disabled with the 'Can OPENAI_API_KEY' tooltip; S8 still accepts a key
result: [pending]

### 5. First-run microphone permission (review finding WR-01): clear the site's mic permission, press Space on a short sentence and take longer than the countdown to click Allow
expected: The attempt is still recorded normally (or Liam accepts the behaviour); the recording window should not be consumed by the permission prompt
result: [pending]

### 6. Recording with the real mic: quiet-but-spoken attempt counts as voiced; silence or a tap does not; auto-stop after 1 s of silence; mic light off after leaving S3; upload failure toast with Thu lai keeps the recording; 'Luu clip cho eval' writes .wav + .json to DATA_DIR/eval_clips/
expected: As stated; thresholds in level.ts and vad.py (flagged assumption A1) feel right
result: [pending]

### 7. Remaining 02-19 UAT groups C-F: IPA glyph rendering in Noto Sans (no tofu), real-key translation spot check, Sua cau, Mat chu cuoi? (300 ms step, 3000 ms cap pending Liam), real yt-dlp playback and seeking in Chrome, AV1/VP9 cache from Phase 1 plus 'Tai lai video', live-video code on POST /lessons, S2 and S1 edge cases, real warm-up on the 8 GB machine, real key check, data-dir change, gap-copy strings
expected: Per checklist in 02-19-SUMMARY.md
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
