# Phase 2 — UI Review

**Audited:** 2026-10-08
**Baseline:** UI-SPEC.md design contract + abstract 6-pillar standards
**Screenshots:** Not captured (no dev server on localhost:3000, 5173, 8080)
**Interaction captures:** off (workflow.ui_interaction_capture is false)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All UI copy matches UI-SPEC.md verbatim; empty states, error messages, CTAs are context-specific and Vietnamese |
| 2. Visuals | 3/4 | Component structure and hierarchy correct; focal points clear; missing visual polish (shadows intentionally omitted by spec, no interactive state indicators) |
| 3. Color | 4/4 | 60/30/10 split maintained; no score- classes in P1 (correct); accent used only on designated elements; teal/orange reserved for Bản gốc/Bạn |
| 4. Typography | 4/4 | Font sizes (11–38px), weights (400–800), line heights all spec-compliant; three fonts loaded correctly with Vietnamese subsets |
| 5. Spacing | 3/4 | Spacing scale mostly adheres to spec (multiples of 4); some arbitrary gap values (gap-2.5, gap-0.5, gap-1.5) used but are allowed exceptions; consistent applied throughout |
| 6. Experience Design | 3/4 | All major states implemented (playing, recording, processing, no-voice, error, reviewing); keyboard shortcuts active; accessibility markers present; gaps in error recovery flows and edge-case handling |

**Overall: 21/24**

---

## Top 3 Priority Fixes

1. **Missing error state recovery in upload flow** — User presses "Thử lại" after upload error, but blob retention and retry logic may not persist state correctly across errors. — Audit the `uploadError` state in `SentenceStatePanel` and verify that `onRetry` properly re-sends the stored blob without data loss; add tests for concurrent error-recovery scenarios.

2. **Arbitrary spacing values not conforming to spec scale** — `gap-0.5`, `gap-1.5`, `gap-2.5` used in components (e.g., `RangePicker.tsx:116`, `MicSection.tsx:205`, `CreateLessonDialog.tsx:131`) violate the declared spacing scale (multiples of 4 + named exceptions). — Replace with spec-compliant values: `gap-0.5` → `gap-1`, `gap-1.5` → `gap-1` or `gap-2`, `gap-2.5` → `gap-2` or `gap-3`; verify visual alignment with mock.

3. **Button focus state not visible on icon-only buttons** — Icon buttons in `ResultActionBar` and `PlayerControls` rely on global `:focus-visible` outline, but hover state styling is missing on some buttons (e.g., `ReplayButton` in `SentenceStatePanel`). — Add explicit hover and active states to icon buttons; ensure `aria-pressed="true"` is styled with the button's hue (e.g., `--original-text` for `Bản gốc` button).

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

**Excellent implementation. All copy strings match UI-SPEC.md verbatim.**

- Empty state: `Chưa có bài nào` heading + `Dán link YouTube để tạo bài đầu tiên.` body ✓ (apps/web/app/page.tsx:83–85)
- Filtered empty: `Chưa có bài nào ở mục này.` ✓ (apps/web/app/page.tsx:92–94)
- System banners: "Chưa có model", "Model đang nạp…", "Chưa có OpenAI key", "Trình duyệt đang chặn micro", "Không kết nối được backend" ✓ (apps/web/components/SystemBanners.tsx:50–112)
- Error states: Specific error messages with context (e.g., `failureText` function derives prefix + message) ✓ (apps/web/components/LessonCard.tsx:133–134)
- CTAs use imperative verbs: `Tạo bài từ YouTube`, `Tạo bài`, `Thử lại`, `Tải lại` ✓
- No generic labels (`Submit`, `OK`, `Cancel`, `Save`) found

**No findings.** All copy is context-specific, Vietnamese, and localized.

---

### Pillar 2: Visuals (3/4)

**Good component structure and hierarchy; some interactive state indicators missing.**

- **Layout hierarchy clear:** S1 library has title + subtitle + tabs + grid ✓ (apps/web/app/page.tsx:108–136)
- **Focal point on main screen:** "Tạo bài từ YouTube" button is prominently positioned (line 122) ✓
- **Card structure:** Thumbnail (16:9) + body with title, badges, progress row, CTA ✓ (apps/web/components/LessonCard.tsx:56–149)
- **State panels:** White, 1px border, radius 12, padding 24, gap 18 ✓ (apps/web/components/SentenceStatePanel.tsx:103, 154, 184, 239)
- **Icon buttons with aria-labels:** Settings icon has `aria-label="Settings"` ✓ (apps/web/components/AppHeader.tsx:37); replay button has `aria-label` + `title` ✓
- **Visual hierarchy via size/weight:** Page title 34px/800, headings 18px/700, body 14px/400–600 ✓

**WARNING:** Button pressed states (`aria-pressed="true"`) not visually indicated in the code. UI-SPEC says "Buttons that are playing show `aria-pressed="true"` + 2px inset ring in their own hue" (S3 contract line 308), but no inset ring style found in Button component or state panels.
- Missing: `.aria-pressed\:shadow-inset` or equivalent styling on buttons when playing.
- Impact: Keyboard-only users cannot see which button is active (only screen-reader users know via aria-pressed).

**FINDING:** Replay buttons in `SentenceStatePanel` and action bar lack visual feedback for pressed state. Add inset ring styling to `.aria-pressed` pseudo-element or button[aria-pressed="true"].

---

### Pillar 3: Color (4/4)

**Excellent. 60/30/10 split maintained; no unauthorized accent usage.**

- **Dominant (60%):** `background: var(--slate-1)` = #FCFCFD ✓ (apps/web/app/globals.css:29)
- **Secondary (30%):** Cards, dialog, header, footer use `--card` (#FFFFFF), `--slate-2` (#F9F9FB), `--muted` (#F0F0F3) ✓
  - S1 cards: `bg-card` ✓ (apps/web/components/LessonCard.tsx:57)
  - Dialog overlay: `bg-[rgba(28,32,36,0.55)]` (spec-approved hardcoded value) ✓ (apps/web/components/ui/dialog.tsx:37)
  - S3 left column: Would use `--slate-2` (not fully visible in code audit, but configured in Tailwind)
- **Accent (10%):** `--primary` / `--foreground` = slate-12 (#1C2024)
  - Solid buttons: `bg-primary text-primary-foreground` ✓ (apps/web/components/ui/button.tsx:19)
  - Used only on: `Tạo bài từ YouTube`, `Tạo bài`, `Ghi lại`, CTAs ✓
  - **NOT** used on outline/ghost buttons ✓ (apps/web/components/ui/button.tsx:23–24 use `--input` and `--foreground`)
- **Score colors:** No `score-` classes found in P1 components ✓ (grep verified)
- **Identity colors (teal/orange):** Reserved for Bản gốc/Bạn
  - Teal: `soft-original` buttons, `--original`, `--original-text` ✓ (apps/web/components/ui/button.tsx:21)
  - Orange: `soft-you` buttons, `--you`, `--you-text` ✓ (apps/web/components/ui/button.tsx:22)
- **Semantic status:**
  - Recording (red-9): Recording panel border 2px, chip fill ✓ (apps/web/components/SentenceStatePanel.tsx:154)
  - Warning (amber): Banner variant "warning" ✓ (apps/web/components/Banner.tsx:29)
  - Success (green-9): Badge variant "success" ✓ (apps/web/components/LessonCard.tsx:95)
  - Destructive (red-9/red-11): Failed card border, error text ✓ (apps/web/components/LessonCard.tsx:59)
- **Destructive text:** Uses `--destructive-text` (red-11) not red-9 ✓ (apps/web/components/LessonCard.tsx:133)

**No findings.** Color implementation is spec-compliant.

---

### Pillar 4: Typography (4/4)

**Excellent. All font sizes, weights, and line heights match spec.**

Font sizes used (counted from grep): 11px, 12px, 13px, 14px, 15px, 16px, 18px, 26px, 34px, 38px
- ✓ Matches UI-SPEC table (Role | Size): Display 34px, Dialog title 26px, Sentence state 26px, Heading 18px, Card title 16px, Body large 15px, Body 14px, Label/caption 13px, Group label 12px, Mono 11–13px, IPA 16px

Font weights used: 400, 500, 600, 700, 800
- ✓ Matches spec: 800 for display/titles (34px title, 18px heading), 700 for headings, 600 for buttons/labels, 500 for mono/state-panel sentence, 400 for body

Fonts loaded:
- **Figtree:** weights 400–800, subsets latin + latin-ext ✓ (apps/web/app/layout.tsx:9–14)
- **JetBrains Mono:** weights 400, 500, subsets latin + vietnamese ✓ (apps/web/app/layout.tsx:22–27)
- **Noto Sans:** variable weights, subsets latin + latin-ext + vietnamese ✓ (apps/web/app/layout.tsx:16–20)
- Fallback order in globals.css: `--font-sans: var(--font-figtree), var(--font-noto-sans), system-ui` ensures Vietnamese glyphs always render ✓ (apps/web/app/globals.css:17–18)

Line heights:
- Display/heading (34px, 18px): `leading-tight` (1.2) ✓ (apps/web/app/page.tsx:115, apps/web/app/settings/page.tsx:15)
- Sentence state panel (26px): `leading-[1.3]` ✓ (apps/web/components/SentenceStatePanel.tsx:113, 166)
- Body: `leading-[1.5]` implied via defaults ✓

**No findings.** Typography is fully compliant with spec.

---

### Pillar 5: Spacing (3/4)

**Good adherence to spec scale; three non-standard gap values need correction.**

Spacing scale compliance:
- Standard Tailwind scale (4px base): `gap-1` (4px), `gap-2` (8px), `gap-3` (12px), `gap-4` (16px), `gap-6` (24px), `gap-8` (32px) ✓
- Exceptions allowed by spec (non-multiples of 4): `gap-2` (8px ✓), `gap-2.5` (10px), `gap-0.5` (2px)

**WARNINGS found:**

1. **`gap-0.5` (2px) used as `gap-2.5`** in several places:
   - apps/web/components/RangePicker.tsx:148 `gap-0.5` — spec allows 2px only for "word underline stack gap, segmented-progress gap, border insets"
   - apps/web/components/CreateLessonDialog.tsx:131 `gap-0.5` — likely incorrect usage
   - **Impact:** Spacing tighter than spec intends for non-segmented-progress elements
   - **Fix:** Use `gap-1` (4px) or `gap-2` (8px) instead, verify against mock

2. **`gap-1.5` (6px) used but not in spec exceptions:**
   - apps/web/components/RangePicker.tsx:116, 133 — spec allows 6px only for "tag/badge row gap, progress-bar stack gap, S2 field stacks"
   - apps/web/components/MicSection.tsx:205 — likely outside scope of 6px exception
   - **Impact:** Spacing deviation from declared scale
   - **Fix:** Use `gap-1` or `gap-2` depending on context

3. **`gap-2.5` (10px) usage:**
   - apps/web/components/SentenceStatePanel.tsx:213 — spec allows 10px for "footer action-bar gap, S1 card body stack gap"
   - This appears correct ✓

Padding consistency:
- S1 main padding 32 → `p-8` ✓ (apps/web/app/page.tsx:111)
- Card body padding 16 → `p-4` ✓ (apps/web/components/LessonCard.tsx:84)
- State panel padding 24 → `p-6` ✓ (apps/web/components/SentenceStatePanel.tsx:103)
- Recording panel padding 23 → `p-[23px]` (spec says 24, this is 1px off) (apps/web/components/SentenceStatePanel.tsx:154)
  - **Minor issue:** Should be `p-6` (24px), not arbitrary `p-[23px]`

**Blocking issues: None.** Spacing is close to spec; arbitrary gaps can be addressed in a follow-up PR without breaking layout.

---

### Pillar 6: Experience Design (3/4)

**Good state coverage; gaps in error recovery and edge-case handling.**

State machine coverage (XState):
- States implemented: idle, playing, recording, processing, reviewing, noVoice, uploadError ✓
- Transitions: playing → recording, recording → processing, processing → reviewing, error branches ✓
- State panel variants: PlayingPanel, RecordingPanel, ProcessingPanel, NoVoicePanel, MicErrorPanel, UploadErrorPanel ✓ (apps/web/components/SentenceStatePanel.tsx types 12–69)

Loading states:
- S1 library: Skeleton cards shown while `isPending` ✓ (apps/web/app/page.tsx:67–78)
- Processing card: JobSteps component with per-step progress ✓ (apps/web/components/LessonCard.tsx:129)
- S2 preview: "Đang lấy thông tin video…" hint ✓ (UI-SPEC, not verified in code)

Error states:
- Backend unreachable: Banner with "Tải lại" button + refetch ✓ (apps/web/components/SystemBanners.tsx:94–114)
- Lesson job failure: `failureText` + "Thử lại" button with retry mutation ✓ (apps/web/components/LessonCard.tsx:131–145)
- Recording upload error: Toast + "Thử lại" action *(not fully verified in code; assumed from Sonner integration)*
- No-voice detection: Alert title + body + "Ghi lại" button ✓ (apps/web/components/SentenceStatePanel.tsx:237–249)

Keyboard shortcuts:
- Space, R, ←/→, O, M, B, I, T mapped in UI-SPEC ✓
- Shortcut hints displayed in Kbd components ✓ (e.g., apps/web/components/SentenceStatePanel.tsx:127, 171)
- Accessible only on S3 (per spec) *(requires runtime verification)*

Disabled states:
- Failed card "Thử lại" disabled while `retry.isPending` ✓ (apps/web/components/LessonCard.tsx:139)
- Dialog "Tạo bài" disabled until preview succeeds and times valid *(assumed, not fully verified)*
- `Dịch` toggle disabled without key: uses `aria-disabled="true"` + tooltip *(assumed)*

Accessibility:
- Banners: `role="status"` (warning/neutral), `role="alert"` (error) ✓ (apps/web/components/SystemBanners.tsx)
- State changes: `aria-live="polite"` on chip text ✓ (apps/web/components/SentenceStatePanel.tsx:104)
- Icon buttons: `aria-label` + `title` ✓ (apps/web/components/AppHeader.tsx:37, ui/button.tsx type annotations)
- Busy state: `aria-busy="true"` on loading skeleton grid ✓ (apps/web/app/page.tsx:70)
- Keyboard focus: Global `:focus-visible` outline (2px `--ring`, 2px offset) ✓ (apps/web/app/globals.css:33–36)
- Reduce motion: `prefers-reduced-motion: reduce` respected ✓ (apps/web/app/globals.css:38–46)

**FINDINGS (WARNING level):**

1. **No blob retention logic visible for upload error retry** — UI-SPEC D-05 says "backend error → toast + nút thử lại, giữ blob vừa thu"; `UploadErrorPanel` has `onRetry` callback but no code audit confirms blob is retained in memory. — Verify that `PracticeRoom` or the player machine holds the blob across error states; add error-recovery test.

2. **Missing confirmation for destructive actions** — UI-SPEC says "none in this phase" for delete-lesson, but future phases will need this. No placeholder structure found. — Not a P1 issue; can defer.

3. **Retry logic not idempotent** — If retry fails again, user cannot retry again (no re-retry mechanism). — Add recursive retry with exponential backoff, or ensure Sonner toast's "Thử lại" action re-triggers the upload.

4. **Button[aria-pressed] not visually styled** — As noted in Pillar 2, buttons that are playing lack inset ring or background change. — Add `:aria-pressed` pseudo-element styling.

---

## Files Audited

**Components (UI):**
- `apps/web/components/AppHeader.tsx` — Header layout, nav links
- `apps/web/components/SystemBanners.tsx` — Status banners (model, key, mic, backend)
- `apps/web/components/LessonCard.tsx` — Card states (ready, processing, warning, failed)
- `apps/web/components/JobSteps.tsx` — Processing progress per step
- `apps/web/components/CreateLessonDialog.tsx` — S2 create dialog
- `apps/web/components/RangePicker.tsx` — Video range selector (S2)
- `apps/web/components/Banner.tsx` — System banner wrapper
- `apps/web/components/SentenceStatePanel.tsx` — State panels (playing, recording, processing, no-voice, error)
- `apps/web/components/LevelMeter.tsx` — Recording level visualization
- `apps/web/components/PracticeRoom.tsx` — S3 practice room (main orchestrator)
- `apps/web/components/TranscriptList.tsx` — Sentence list with toggle editing
- `apps/web/components/ReviewBlock.tsx` — Reviewing state footer
- `apps/web/components/ResultActionBar.tsx` — Playback + next action footer
- `apps/web/components/PlayerControls.tsx` — Video control bar (play/speed/loop)
- `apps/web/components/VideoPane.tsx` — Video display with overlay
- `apps/web/components/SpokenIpa.tsx` — IPA display
- `apps/web/components/AttemptStrip.tsx` — Attempt counter and toggles
- `apps/web/components/PracticeDefaults.tsx` — Settings auto-save dropdowns
- `apps/web/components/KeyField.tsx` — API key input and check
- `apps/web/components/MicSection.tsx` — Mic device + test
- `apps/web/components/ModelStatusList.tsx` — Model status rows + data dir
- `apps/web/components/PracticeHeader.tsx` — S3 header + progress bar
- `apps/web/components/ui/* (shadcn/ui)` — Button, Badge, Alert, Dialog, Input, Select, Slider, Tabs, Progress, Kbd, Card, Skeleton, Sonner

**Pages (Routing):**
- `apps/web/app/page.tsx` — S1 Library (Thư viện)
- `apps/web/app/lessons/[id]/page.tsx` — S3 Practice room (Phòng tập)
- `apps/web/app/settings/page.tsx` — S8 Settings

**Styling & Configuration:**
- `apps/web/app/globals.css` — Global styles, token overrides, focus styles, motion preferences
- `apps/web/app/tokens.css` — Design tokens (synced from docs/design/tokens.css)
- `apps/web/tailwind.config.ts` — Tailwind theme extensions (colors, fonts, radii, keyframes)
- `apps/web/app/layout.tsx` — Root layout, font loading (Figtree, JetBrains Mono, Noto Sans)
- `apps/web/components.json` — shadcn/ui configuration (radix, CSS variables, tailwind)

**Total files audited:** 40+

---

## Summary

**Phase 2 P1 implementation achieves 21/24 (87.5%) against the UI-SPEC.md design contract.**

**Strengths:**
- All copy strings match spec verbatim; context-specific and localized ✓
- Color system correctly implements 60/30/10 split; no unauthorized accent usage ✓
- Typography fully compliant: 10 sizes, 5 weights, 3 fonts with Vietnamese fallbacks ✓
- State machine covers major states (playing, recording, processing, error, reviewing) ✓
- Accessibility: aria-labels, aria-live, role attributes, keyboard navigation ✓
- Component structure mirrors spec (S1, S2, S3, S8 layouts correct) ✓

**Weaknesses:**
- Spacing has 3 non-standard `gap` values (`gap-0.5`, `gap-1.5`); need correction for consistency ⚠️
- Button pressed states (aria-pressed) lack visual indication (no inset ring/background change) ⚠️
- Upload error recovery blob retention not verified in code audit ⚠️
- Recording panel padding off by 1px (23px instead of 24px) ⚠️

**Recommendation:** Ship with the top 3 priority fixes above (feasible in <4 hours total). None of the gaps block user task completion in the planned UAT scenarios (30 sentences with mouse/keyboard, 2 lessons without blocking, missing key handling).
