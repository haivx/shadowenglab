---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 09
subsystem: ui
tags: [nextjs, xstate-v5, video, requestAnimationFrame, keyboard-shortcuts, tanstack-query, radix-select]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-04 api client (lessonVideoUrl, reloadLessonVideo), query hooks, primitives; 02-05 playerMachine, shortcuts"
provides:
  - "S3 route /lessons/[id] and PracticeRoom: opens at the first unpracticed sentence, plays the padded sentence from the self-hosted video through the machine"
  - "playRange / sampleWindow / makePlaySample: rAF stop-at-end, repeat with gap, abortable, real playSample actor"
  - "PlayerControls, PracticeHeader (+ SegmentedProgress, BackToLibraryLink), TranscriptList (+ skeleton), SentenceStatePanel (playing), VideoPane with loading and error states"
  - "useShortcuts + releaseFocusOnPointerUp: global keydown binding over shouldHandleShortcut / shortcutToAction"
affects: [02-14 recording/upload/footer, 02-18 IPA/translate/edit/extend, 02-19 UAT]

actuals:
  tokens: 14100
  tasks: 3
  commits: 3

plan_head_before: 57cd5d456e98a0b3a8ee370782f8e5fd2d4f211b
plan_head_after: f2abd460048a3cba72bec87c84d9ff81f7566b40

tech-stack:
  added: []
  patterns:
    - "Browser seams as structural types (VideoLike, RafLike) so playback is tested in node with a fake video and fake rAF"
    - "Machine built once with useState(() => playerMachine.provide(...)); actors read the video element and lesson through refs"
    - "Buttons and keys share one rule table: button disabled exactly where shortcutToAction returns null"

key-files:
  created:
    - apps/web/lib/player/playRange.ts
    - apps/web/lib/player/playRange.test.ts
    - apps/web/lib/player/useShortcuts.ts
    - "apps/web/app/lessons/[id]/page.tsx"
    - apps/web/components/PracticeRoom.tsx
    - apps/web/components/VideoPane.tsx
    - apps/web/components/PlayerControls.tsx
    - apps/web/components/PracticeHeader.tsx
    - apps/web/components/TranscriptList.tsx
    - apps/web/components/SentenceStatePanel.tsx
  modified:
    - apps/web/components/ui/badge.tsx

key-decisions:
  - "Replay icon button maps to the O action (PREVIEW in idle, LISTEN_ORIGINAL after an attempt), title `Phát lại câu mẫu (O)`: plays the original once without starting a recording"
  - "Playing panel hint omits `Phát xong sẽ tự chuyển sang lượt của bạn` for previewing (O), because no recording follows"
  - "Space on a Tab-focused button/link is left to native activation; Space elsewhere goes to the machine"
  - "Chip and progress bar use the video clock: progress = ((rep-1) + passFraction) / repeat"
  - "Settings values outside the select options (e.g. playbackRate 0.5) snap to the nearest option for the session"

patterns-established:
  - "Pattern: PracticeRoom splits into a loader (queries, skeleton, error) and LoadedRoom (actor, layout); plug points for 02-14/02-18 are marked inline"

requirements-completed: [PLY-01, PLY-03, PLY-04, PLY-07]

coverage:
  - id: D1
    description: "playRange stops at the end mark within one frame, clamps the padded window to [0, duration], repeats with REP events, aborts cleanly and reports a refused play()"
    requirement: "PLY-03"
    verification:
      - kind: unit
        ref: "apps/web/lib/player/playRange.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "playerMachine driven by the real playSample actor: PLAY goes playing -> recording, STOP and GOTO return to idle with the video paused"
    requirement: "PLY-03"
    verification:
      - kind: unit
        ref: "apps/web/lib/player/playRange.test.ts#playerMachine with the real playSample actor (tracer)"
        status: pass
    human_judgment: false
  - id: D3
    description: "S3 opens at the first unpracticed sentence; transcript marks practiced rows with a neutral dot and the current row with aria-current; no score colours in components"
    requirement: "PLY-04"
    verification:
      - kind: other
        ref: "SSR render of PracticeRoom with a seeded query cache (scratch smoke, not committed) plus sh -c '! grep -rn \"score-\" apps/web/components'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Sentence audio starts about 150 ms before and ends about 150 ms after the sentence without an audible cut; 0.75x keeps pitch; Space never scrolls the page; Tải lại video restores playback"
    requirement: "PLY-03"
    verification: []
    human_judgment: true
    rationale: "Audio timing, autoplay policy and focus behaviour need a real Chrome session (plan human-check, queued for UAT)"
  - id: D5
    description: "Every action is a 44-48 px labelled button with its shortcut hint and the same action works by keyboard; mouse-clicked buttons release focus"
    requirement: "PLY-07"
    verification:
      - kind: other
        ref: "pnpm --filter @shadowenglab/web build, eslint, SSR render of PlayerControls"
        status: pass
    human_judgment: true
    rationale: "The 30-sentence mouse-only and keyboard-only passes are the manual UAT item flagged for 02-19"

duration: 25min
completed: 2026-10-07
status: complete
---

# Phase 2 Plan 09: S3 playback, control bar, transcript and shortcuts Summary

**S3 practice room left column and playback: the self-hosted video plays each padded sentence through playerMachine with a rAF-stopped, repeating, rate-aware `playSample` actor, opens at the first unpracticed sentence, and is fully operable by labelled buttons, list clicks and global shortcuts.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files:** 10 created, 1 modified

## Accomplishments

- `playRange` seeks to `start - pad`, sets rate and pitch preservation, and polls `currentTime` each animation frame until the padded end (clamped to the video). It never listens to the video time-update event. `makePlaySample` turns it into the machine's `playSample` actor: REP before each pass, a 300 ms gap between passes, SAMPLE_DONE at the end, SAMPLE_FAILED if `play()` is refused or the video is missing, and cleanup that cancels the frame loop and pauses.
- `PracticeRoom` loads lesson, progress and settings, then builds the actor once (`useActorRef(playerMachine.provide(...))`) with `startIndex = firstUnpracticedIndex ?? 0` and the session defaults. Settings failure falls back to 1x, x1, +50%. Progress failure keeps practice working without the dots.
- `PlayerControls`: `Trước`, `Nghe câu mẫu` (Space hint), replay icon, `Tiếp`, and the `Tốc độ`, `Lặp`, `Thời gian ghi` selects, all 44 px, disabled until `canplay`; buttons are disabled exactly where the shortcut table ignores the key.
- `TranscriptList`: `Transcript · n câu`, rows with mm:ss, wrapped text, neutral practiced dot (with screen-reader text), `aria-current` row with the 3 px left border, `scrollIntoView({block: "nearest"})`, skeleton rows while loading, and a toolbar slot.
- `PracticeHeader` with `SegmentedProgress` (neutral grays only) and `BackToLibraryLink`; `SentenceStatePanel` playing variant (`Đang phát bản gốc · lần i/n`, progress bar from the video clock, `aria-live`).
- `VideoPane`: `Đang tải video…`, error state with `Không phát được video của bài này.` and `Tải lại video` (pending label `Đang tải lại…`, cache-busting `?v=` then `load()`, toast on failure).
- `useShortcuts`: one window keydown listener, `preventDefault()` only for handled keys, cleans up on unmount.

## Task Commits

1. **Task 1 (tracer): playRange, route, PracticeRoom, VideoPane** - `b04911c`
2. **Task 2: controls, header, transcript list** - `9faf082`
3. **Task 3: shortcuts, playing panel, video and lesson states** - `f2abd46`

## Plug points for later plans

- **02-14 (record/upload/footer):** in `LoadedRoom` (`PracticeRoom.tsx`) add `record` and `uploadAttempt` to the `playerMachine.provide({ actors })` call next to `playSample`; add the sticky `ResultActionBar` after the body row in the root column; replace the non-listening branch of the sentence region (marked with a comment) with the other `SentenceStatePanel` variants (the props type is already a union to extend). The reviewing block and `AttemptStrip` go in the right `main` under the `Câu n` strip. After each upload, invalidate `queryKeys.lessonProgress(id)` so the dots and header update.
- **02-18 (IPA, translate, edit, extend):** `useShortcuts(actorRef, { onToggle })` is already wired without `onToggle`, so I and T are ignored until 02-18 passes a handler. `TranscriptList` takes a `toolbar` prop for `Dịch` and `Sửa câu`. `Mất chữ cuối?` should send `SEGMENTS_UPDATED` and invalidate the lesson query; `makePlaySample` reads the lesson through a ref, so a longer `endExtraMs` applies on the next play.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan verify grep matched a pre-existing comment**
- **Found during:** Task 3 (`sh -c '! grep -rn "score-" apps/web/components'`)
- **Issue:** `components/ui/badge.tsx` (02-04) had the text `"score-good"` in a comment, so the plan's no-score-colour check failed although no colour class is used.
- **Fix:** reworded the comment to `"điểm tốt"`. Comment only, no behaviour change.
- **Files modified:** `apps/web/components/ui/badge.tsx`
- **Commit:** `f2abd46`

### Gaps resolved by the executor (copy not in UI-SPEC)

**2. [Rule 2 - Missing critical] Lesson not ready or empty**
- **Issue:** opening `/lessons/{id}` for a lesson that is not `ready` (or has no segments) would build the machine with `segmentCount` 0.
- **Fix:** inline error `Bài này chưa sẵn sàng để tập.` with `Tải lại` and the `Thư viện` link. The copy is new and should be reviewed with the other gap strings.
- **Commit:** `f2abd46`

**3. [Rule 2 - Missing critical] Playing hint for the O action**
- **Issue:** the S3s hint says playback ends by moving to the learner's turn, which is false for `O` (previewing).
- **Fix:** for previewing the panel shows only `Space dừng`.
- **Commit:** `f2abd46`

**Total deviations:** 3 (1 Rule 3, 2 Rule 2). No contract, schema, threshold or model change.

## Authentication Gates

None.

## Issues Encountered

- **Interim dead end until 02-14:** the `record` and `uploadAttempt` actors are still the 02-05 stubs. After a sample finishes, `Nghe câu mẫu` / Space moves the machine to `recording` and it stays there, because the stub recorder never sends STOPPED. Navigation is ignored in `recording` by design, so the room cannot be used end to end until 02-14 provides those actors. `O` (replay) and list navigation work before any Space press. The plan human-check (10 sentences by mouse, then keyboard) therefore belongs to the end-of-phase UAT.
- Vitest runs the whole `apps/web` suite whatever file filter is passed (`pnpm --filter @shadowenglab/web test -- playRange` ran 6 files, 76 tests); the playRange file alone is 18 tests.
- No browser session was available, so the visual test with a 20-word sentence at 1280 px (backstop truth) and all audio and focus checks remain for UAT. A server-side render of `PracticeRoom` with a seeded query cache (scratch test outside the repo) confirmed: opens at the first unpracticed sentence, `Tiến độ 2 trên 3 câu`, `aria-current` row, practiced dot with text, controls disabled and `Đang tải video…` before `canplay`, no `controls` attribute, skeleton while pending.

## Known Stubs

None in this plan's files. The unprovided `record` and `uploadAttempt` actors are the intentional 02-05 stubs that 02-14 replaces (see Issues Encountered).

## Threat Flags

None. T-02-23: segment text is rendered only as React children; T-02-24: `<video src>` comes only from `lessonVideoUrl(id)` (plus a numeric cache-busting query after `Tải lại video`); T-02-SC: install used `pnpm install --frozen-lockfile`, no package added or changed.

## Verification

- `pnpm --filter @shadowenglab/web test`: 6 files, 76 tests pass (playRange 18).
- `pnpm --filter @shadowenglab/web build`: succeeds; route `/lessons/[id]` built.
- `pnpm exec eslint apps/web` and `prettier --check apps/web`: clean; `tsc --noEmit` clean.
- `sh -c '! grep -rn "score-" apps/web/components'`: passes.
- Acceptance greps for all three tasks pass (playRange exports and `requestAnimationFrame`, `playerMachine.provide`, `useActorRef`, `playsInline`, `lessonVideoUrl`, no `controls`, control-bar labels, `aria-current`, `Transcript ·`, `scrollIntoView`, `Tiến độ`, `Thư viện`, shortcut helpers, `Đang phát bản gốc`, `aria-live`, video state copy, `reloadLessonVideo`).

## Next Phase Readiness

- 02-14 can plug the recorder, uploader, footer and remaining panel variants as described above; 02-18 can plug the toggles, `toolbar` and `SEGMENTS_UPDATED`.
- UAT queue: audio padding and repeat feel, 0.75x pitch, Space never scrolling, `Tải lại video` after deleting `video.mp4`, 20-word sentence at 1280 px, mouse-only and keyboard-only passes (02-19).

## Self-Check: PASSED

All ten created files exist, `b04911c`, `9faf082` and `f2abd46` are ancestors of HEAD, `git rev-list --count 57cd5d4..HEAD` = 3 before this docs commit, and the plan verification passes.

---
*Phase: 02-p1-t-o-b-i-v-tr-nh-ph-t*
*Completed: 2026-10-07*
