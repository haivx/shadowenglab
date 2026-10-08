---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 18
subsystem: ui
tags: [ipa, translation, inline-edit, extend-end, tanstack-query, xstate-v5, react-18]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-04 typed client (translateSegment, updateSegmentText, extendSegmentEnd); 02-05 playerMachine SEGMENTS_UPDATED and useShortcuts onToggle; 02-09 TranscriptList and PracticeRoom; 02-12 Word.ipa data; 02-14 AttemptStrip"
provides:
  - "ipaLine(words) -> {text, allMissing}: renders only Word.ipa, never derives IPA from text (D-14)"
  - "SpokenIpa block (badge, /…/ line with dash for uncertain words, helper, all-missing fallback)"
  - "useTranslationTool + Dich toggle (button and key T): cached or on-demand translation line, aria-disabled with tooltip without key"
  - "Sua cau inline edit on the current transcript row (Luu / Huy, Enter / Esc)"
  - "Mat chu cuoi? button in AttemptStrip: POST extend-end, role=status notice, toast on busy/conflict"
  - "segmentCache helper (replaceSegment, patchLessonSegment) writing a returned Segment into the lesson query"
affects: [02-19 UAT, Phase 3 scoring]

actuals:
  tokens: 8000
  tasks: 3
  commits: 3

plan_head_before: 389eec0efbdc8edf93811761c877c07073bafbcc
plan_head_after: bb7cdc88fddcdda40975e25b048a42635e0f8b31

tech-stack:
  added: []
  patterns:
    - "UI toggles (IPA, Dich) are state in PracticeRoom passed to children; the T key and the button share one toggle function"
    - "Server-returned Segment is written into the ['lessons', id] query with patchLessonSegment; the room reacts to changed durations by sending SEGMENTS_UPDATED"
    - "Button and Input are not forwardRef (React 18): tooltip trigger is a wrapper span, the edit input is focused through its form"

key-files:
  created:
    - apps/web/lib/ipaLine.ts
    - apps/web/lib/ipaLine.test.ts
    - apps/web/lib/segmentCache.ts
    - apps/web/lib/segmentCache.test.ts
    - apps/web/components/SpokenIpa.tsx
  modified:
    - apps/web/components/AttemptStrip.tsx
    - apps/web/components/TranscriptList.tsx
    - apps/web/components/PracticeRoom.tsx
    - .planning/phases/02-p1-t-o-b-i-v-tr-nh-ph-t/02-UI-SPEC.md

key-decisions:
  - "PracticeRoom detects changed segment durations (key of the joined array) and sends SEGMENTS_UPDATED from one effect, so the same path covers extend-end success, the refetch after a busy answer, and any later lesson refresh"
  - "The Dich toggle also acts as retry: pressing it while the current sentence shows the failure copy retries instead of switching off; turning it off and on again also clears the failure"
  - "Dich is blocked (aria-disabled + tooltip) only while off; once on it can always be switched off, even on a sentence with no cache and no key"
  - "Sua cau is offered only in idle, reviewing, noVoice and error; leaving the edited sentence or entering another state exits edit mode and drops the draft"

patterns-established:
  - "Pattern: shared lesson-cache patch helper for any endpoint returning a Segment"

requirements-completed: [PLY-04, PLY-05, PLY-06]

coverage:
  - id: D1
    description: "IPA line is built only from Word.ipa: words joined by spaces inside one slash pair, dash for words without IPA, allMissing when none has IPA"
    requirement: "PLY-06"
    verification:
      - kind: unit
        ref: "apps/web/lib/ipaLine.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "SpokenIpa shows the badge IPA tu audio mau, the line in font-ipa teal-12, the helper copy, or Chua nhan dang chac cau nay.; toggled by the IPA button and key I; shown only in idle and reviewing; UI-SPEC example is unstressed"
    requirement: "PLY-06"
    verification:
      - kind: other
        ref: "pnpm --filter @shadowenglab/web build; pnpm exec eslint apps/web; grep acceptance strings; sh -c '! grep -n \"ˈɑnɪstli\" 02-UI-SPEC.md'"
        status: pass
    human_judgment: true
    rationale: "IPA glyph coverage in Noto Sans (RESEARCH A6, no tofu boxes), wrapping of a 20-word line and visual fidelity need a browser"
  - id: D3
    description: "Dich (key T) toggles translation lines: cached translation shown, Dang dich… while POST translate runs, failure copy with retry, aria-disabled + tooltip Can OPENAI_API_KEY without key and cache, one request per sentence"
    requirement: "PLY-06"
    verification:
      - kind: other
        ref: "pnpm --filter @shadowenglab/web build; pnpm exec eslint apps/web; grep acceptance strings in TranscriptList.tsx"
        status: pass
    human_judgment: true
    rationale: "Needs the 02-16 backend and a real OPENAI_API_KEY to check translation quality, key-less behaviour and tooltip focus reachability; vitest here cannot render JSX"
  - id: D4
    description: "Sua cau turns the current row into an Input with Luu and Huy, PATCH via updateSegmentText, new text shown with translation cleared, failure keeps edit mode with Khong luu duoc. Thu lai., shortcuts inactive while typing"
    requirement: "PLY-04"
    verification:
      - kind: unit
        ref: "apps/web/lib/segmentCache.test.ts"
        status: pass
    human_judgment: true
    rationale: "Edit flow against the real PATCH endpoint (02-15) and persistence after reload need a running stack"
  - id: D5
    description: "Mat chu cuoi? calls POST extend-end with a pending state, shows Da noi cau them 0.3 giay (role=status), sends SEGMENTS_UPDATED so playback and the record countdown use the longer sentence, toasts the backend message on busy or conflict and refetches"
    requirement: "PLY-05"
    verification:
      - kind: unit
        ref: "apps/web/lib/player/playerMachine.test.ts#SEGMENTS_UPDATED thay do dai cau (02-05)"
        status: pass
    human_judgment: true
    rationale: "Audible end-of-sentence fix and the longer replay need the 02-15 backend and a human listening"

duration: 25min
completed: 2026-10-08
status: complete
---

# Phase 2 Plan 18: IPA, translation, inline edit and Mất chữ cuối? Summary

**S3 gains the four sentence tools: speaker-derived IPA (button or I), on-demand cached Vietnamese translation (button or T, locked without a key), inline `Sửa câu` with `Lưu`/`Huỷ`, and `Mất chữ cuối?` that nudges the sentence end by 0.3 s and tells the state machine the new length.**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-10-08
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files:** 5 created, 4 modified (apps/web plus the UI-SPEC example)

## Accomplishments

- `ipaLine` reads only `Word.ipa` and never derives IPA (D-14); `SpokenIpa` renders badge, line and helper (or the all-uncertain fallback) under the sentence when IPA is on and the room is idle or reviewing. The UI-SPEC IPA example is now unstressed, with the D-20 note.
- `useTranslationTool` (in `TranscriptList.tsx`): when `Dịch` is on, the current sentence is translated once (POST translate), the result goes into the lesson query; cached translations show on any row, with or without a key; `Đang dịch…` and the failure copy appear inline on the current row and in a screen-reader status region. Without key and without cache the button is `aria-disabled` with the `Cần OPENAI_API_KEY` tooltip.
- `Sửa câu`: current row becomes a form with a 500-char Input, `Lưu` solid and `Huỷ` ghost, Enter saves, Esc cancels; success replaces the Segment (server clears the translation); failure stays in edit mode with `Không lưu được. Thử lại.`. Unchanged text just closes edit mode.
- `Mất chữ cuối?` in `AttemptStrip`: pending state (disabled, spinner), `Đã nới câu thêm 0.3 giây` in a `role="status"` span, toast with the backend message on error, lesson refetch on 503 or 409.
- `PracticeRoom` owns `ipaOn`, wires the T/I keys through `useShortcuts` `onToggle`, passes `canEdit`, and sends `SEGMENTS_UPDATED` whenever the lesson's segment durations change.
- Verification: 156 tests pass across 13 files (new: ipaLine 5, segmentCache 3); `next build`, `eslint apps/web` and `prettier --check apps/web` are clean; all acceptance strings found; the stress-marked example is gone from UI-SPEC.

## Task Commits

1. **Task 1 (tracer): IPA toggle and SpokenIpa** - `435c4be` (feat)
2. **Task 2: Dịch toggle, translation lines, cache** - `558a78b` (feat)
3. **Task 3: Sửa câu and Mất chữ cuối?** - `bb7cdc8` (feat)

Tracer gate: `human_verify_mode` end-of-phase with an automated-only tracer `<verify>`, so tests and build were re-run and passed before expansion.

## Decisions Made

See `key-decisions`. No contract, schema, threshold or model change. No score or score colour anywhere in the new UI.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Button and Input do not forward refs under React 18**
- **Found during:** Task 2 and Task 3
- **Issue:** `TooltipTrigger asChild` around `Button`, and a `ref` on `Input`, would hand a ref to a function component that drops it (tooltip anchoring and autofocus silently broken).
- **Fix:** tooltip trigger is a wrapper `<span>` (the button's focus event bubbles to it, so the tooltip is reachable by keyboard focus); the edit input is focused through the form ref. No change to `components/ui`.
- **Files modified:** `apps/web/components/TranscriptList.tsx`
- **Commits:** `558a78b`, `bb7cdc8`

**2. [Rule 2 - Missing critical] Shared cache-patch helper and tests**
- **Issue:** translate, edit and extend-end all have to write a returned Segment into the lesson cache; duplicating that in three components invites divergence (T-02-49 depends on only Zod-parsed Segments reaching the cache).
- **Fix:** new `lib/segmentCache.ts` (`replaceSegment`, `patchLessonSegment`) with `segmentCache.test.ts`. A new lib file, not in the plan's `files_modified`, but it touches no sibling plan's files.
- **Commit:** `558a78b`

### Plan wording interpreted

- Task 2's wiring needed `useSystemStatus().hasKey` in `PracticeRoom` (key state is not in settings). While the status query is loading or failed, `hasKey` is treated as false (cached translations still show).
- `AttemptStrip`'s `trailing` slot from 02-14 was replaced by explicit props (`ipaOn`, `onToggleIpa`, `lessonId`, `segmentIndex`), and `TranscriptList`'s `toolbar` slot by `translation`, `lessonId` and `canEdit` props: both slots were only placeholders for this plan.
- The plan says PracticeRoom sends `SEGMENTS_UPDATED` "after extendSegmentEnd"; it is sent from an effect on changed durations instead, which also covers the refetch after a busy answer.
- Non-API failure of extend-end (for example a response that fails Zod parsing) toasts `Không nới được câu này. Thử lại.`, copy not in UI-SPEC (gap); API errors show the backend message as specified.

**Total deviations:** 2 auto-fixed (1 Rule 2, 1 Rule 3), 4 interpretation notes. No scope creep.

## Authentication Gates

None.

## Issues Encountered

- Vitest here cannot parse or render JSX, so components are verified by build, lint and typecheck only; hooks and the edit/translate/extend flows are not exercised by automated UI tests.
- Backends for PATCH segment, extend-end (02-15) and translate (02-16) are built in parallel; everything is coded against the approved typed client and not run against the real endpoints.
- The plan's human check (press I and T with and without `OPENAI_API_KEY`, edit and cancel, `Mất chữ cuối?` and replay, IPA glyph coverage in Noto Sans, 20-word IPA and translation wrapping) was not performed; it joins the end-of-phase UAT (02-19). If IPA glyphs show as boxes, adding an IPA-capable font is a new design decision for Liam (RESEARCH A6).
- `Dịch` auto-translates an edited sentence again if Dịch is on and a key exists (the edit clears the translation); this costs one API call per edited sentence and is the direct reading of "on when on".

## Known Stubs

None.

## Threat Flags

None. T-02-49: translation and edited text are rendered as React text only and every Segment in the cache came through `Segment.parse` in `lib/api.ts`. T-02-50: one translate request per sentence in flight (ref guard) and a failed sentence is not retried until the user presses `Dịch`; backend caching is 02-16. T-02-SC: `pnpm install --frozen-lockfile` only, no package added or changed.

## User Setup Required

None - no external service configuration required.

## Self-Check: PASSED

Created files exist on disk; commits `435c4be`, `558a78b`, `bb7cdc8` are on the branch; `pnpm --filter @shadowenglab/web test` (156 pass), `next build`, `eslint apps/web` and `prettier --check apps/web` re-run clean after the last code commit; every acceptance string was found by grep.
