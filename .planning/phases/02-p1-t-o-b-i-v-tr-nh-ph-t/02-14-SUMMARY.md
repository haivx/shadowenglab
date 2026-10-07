---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 14
subsystem: ui
tags: [mediarecorder, web-audio, xstate-v5, sonner, tanstack-query, keyboard-shortcuts]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-04 api client (uploadAttempt, saveEvalClip) and primitives; 02-05 playerMachine, shortcuts, level detector; 02-09 PracticeRoom and playback actors"
provides:
  - "makeRecordActor / openMic / MIC_DEVICE_STORAGE_KEY: raw-mic MediaRecorder actor feeding the pure level detector (LEVEL, SILENCE, STOPPED, RECORD_FAILED), StrictMode-safe cleanup"
  - "pickMimeType: webm/opus -> mp4 -> webm picker"
  - "makePlayBlob / makePlayBoth / makePlayOriginalOnce: listen-back actors with object URLs always revoked"
  - "LevelMeter (10 bars, reusable by S8), SentenceStatePanel variants recording, processing, noVoice, micError, uploadError"
  - "ResultActionBar sticky footer, AttemptStrip, ReviewBlock with Luu clip cho eval"
  - "PracticeRoom wired: record + uploadAttempt (saveForEval false) + playBlob + playBoth actors, progress invalidation, persistent upload-error toast with Thu lai"
affects: [02-18 IPA/translate/edit/extend, 02-17 Settings (LevelMeter, mic device key), 02-19 UAT, Phase 3 scoring]

actuals:
  tokens: 13200
  tasks: 3
  commits: 3

plan_head_before: dd556e3d20e358aa260d8144b8a281d9c52762d5
plan_head_after: 502c368

tech-stack:
  added: []
  patterns:
    - "Browser seams injected as small structural types (RecordDeps, RecorderLike, BlobPlaybackDeps, AudioLike) so mic, MediaRecorder and audio playback are tested in node with fakes"
    - "Footer buttons derive their event and disabled state from shortcutToAction, the same table the keyboard uses"
    - "Top-level machine state via topLevelState(value): scoring/reviewing/noVoice/error have child states so state.value is an object there"

key-files:
  created:
    - apps/web/lib/audio/mime.ts
    - apps/web/lib/audio/mime.test.ts
    - apps/web/lib/audio/recorder.ts
    - apps/web/lib/audio/recorder.test.ts
    - apps/web/lib/player/listenActors.ts
    - apps/web/lib/player/listenActors.test.ts
    - apps/web/components/LevelMeter.tsx
    - apps/web/components/ResultActionBar.tsx
    - apps/web/components/AttemptStrip.tsx
    - apps/web/components/ReviewBlock.tsx
  modified:
    - apps/web/components/SentenceStatePanel.tsx
    - apps/web/components/PracticeRoom.tsx

key-decisions:
  - "getUserMedia deviceId is passed as { ideal } instead of a bare value, so a saved device that was unplugged falls back to the default mic instead of failing with OverconstrainedError"
  - "Footer Ban goc follows the shortcut table (disabled while playing, recording or processing) rather than UI-SPEC's 'always enabled', so a button is disabled exactly where its key is ignored"
  - "Reviewing title and the Luot k strip both use voicedAttempts from the progress query (fallback 1), so a no-voice attempt never makes the two disagree; PUT eval-clip uses the server attempt number from AttemptAck"
  - "Countdown starts when RecordingPanel mounts, which coincides with machine entry into recording and its recordDelay timer"

patterns-established:
  - "Pattern: recorders and players take injectable deps with browser defaults; tests drive them with fake rAF and fake recorders"
  - "Pattern: ReviewBlock is keyed by sentence:attempt so mutation state never leaks between attempts"

requirements-completed: [REC-01, REC-03, REC-04, PLY-07]

coverage:
  - id: D1
    description: "Recorder actor opens a raw mono mic (no AEC/NS/AGC), picks the first supported MIME, emits LEVEL and a single SILENCE, sends STOPPED with blob and duration, and releases tracks, AudioContext and rAF on every exit including cleanup before the mic opens"
    requirement: "REC-01"
    verification:
      - kind: unit
        ref: "apps/web/lib/audio/recorder.test.ts"
        status: pass
      - kind: unit
        ref: "apps/web/lib/audio/mime.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Listen-back actors play the kept blob and original-then-yours, abort cleanly and always revoke object URLs"
    requirement: "PLY-07"
    verification:
      - kind: unit
        ref: "apps/web/lib/player/listenActors.test.ts"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sentence panels (recording with countdown and meter, processing, no-voice, mic error, upload error), sticky footer in every S3 state, attempt strip and reviewing block render as UI-SPEC specifies, with no score or score colour"
    requirement: "REC-03"
    verification:
      - kind: other
        ref: "pnpm --filter @shadowenglab/web build; pnpm exec eslint apps/web; sh -c '! grep -rn \"score-\" apps/web/components'"
        status: pass
    human_judgment: true
    rationale: "Visual fidelity to the design (footer wrap at 1024 px, panel spacing, meter shape) needs a browser; the machine paths themselves are covered by the 02-05 tests"
  - id: D4
    description: "Upload failure keeps the recording (M plays it), shows a persistent toast with Thu lai, and Thu lai re-sends the same blob; recordings are never written to browser storage"
    requirement: "REC-03"
    verification:
      - kind: other
        ref: "sh -c '! grep -rnE \"localStorage\\.setItem\\([^)]*[Bb]lob|indexedDB|caches\\.open\" apps/web/lib apps/web/components' (no persistence); retry path is playerMachine tests (02-05)"
        status: pass
    human_judgment: true
    rationale: "Stopping and restarting the real API during an upload, and the toast action, need a running stack (plan human-check)"
  - id: D5
    description: "Luu clip cho eval re-sends the kept blob to PUT eval-clip; success disables the button as Da luu clip, failure toasts and re-enables"
    requirement: "REC-04"
    verification: []
    human_judgment: true
    rationale: "Needs the 02-10 backend endpoint; verified only against the typed client contract here (no mocked component test: vitest cannot render JSX in this setup)"
  - id: D6
    description: "Silence/level thresholds, auto-stop, mic light off after leaving S3, 30-sentence mouse-only and keyboard-only passes with real hardware"
    requirement: "REC-01"
    verification: []
    human_judgment: true
    rationale: "Microphone hardware, autoplay policy and VAD thresholds (RESEARCH A1) cannot be automated; queued for the end-of-phase UAT (02-19)"

duration: 15min
completed: 2026-10-07
status: complete
---

# Phase 2 Plan 14: Recording, upload, listen-back footer and recovery states Summary

**S3 now records the learner after the sample (raw-mic MediaRecorder with a live 10-bar meter, countdown and 1 s silence auto-stop), uploads during `scoring`, and offers listen-back (O/M/B), no-voice, mic-error and retryable upload-error states plus `Luu clip cho eval`, all without a score and with nothing persisted in the browser.**

## Performance

- **Duration:** about 15 min
- **Completed:** 2026-10-07
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files:** 10 created, 2 modified (apps/web only)

## Accomplishments

- `makeRecordActor` (id `recorder` in the machine): opens the mic with echo cancellation, noise suppression and auto gain off, mono; records with the first supported MIME; a rAF loop feeds `getFloatTimeDomainData` into `updateLevel` and forwards `LEVEL` (only when bars or speech change) and one `SILENCE`; `STOP` ends recording and sends `STOPPED {blob, durationMs}`; permission or recorder errors send `RECORD_FAILED`. Cleanup stops the recorder, cancels rAF, stops every track and closes the AudioContext, including when the actor is disposed before `getUserMedia` resolves (StrictMode).
- `LevelMeter`, and `SentenceStatePanel` variants `recording` (2 px red border, `Đang ghi · còn {s.s}s` chip, hint), `processing` (`aria-busy`, 6 skeleton chips, caption with Kbd M), `noVoice`, `micError`, `uploadError`.
- `PracticeRoom` provides `record`, `uploadAttempt` (`saveForEval: false`, machine `signal`), `playBlob`, `playBoth`; invalidates the progress query on `scoring -> reviewing|noVoice` so the practiced dot and `Lượt k` update; shows a persistent sonner toast with `Thử lại` (RETRY_UPLOAD) on `scoring -> error`, dismissed on leaving error or S3.
- `ResultActionBar`: sticky footer in all states (`Nghe lại` · `Bản gốc` O · `Của bạn` M · `Lần lượt cả hai` B · `Ghi lại` R / `Dừng ghi` Space · `Câu tiếp`), `aria-disabled` Của bạn / Lần lượt until a recording exists, `aria-pressed` plus inset ring and play-to-stop icon for the playing button, last-sentence title `Đây là câu cuối`.
- `AttemptStrip` (`Câu n`, `Lượt k` only when k >= 1; right side left open as a `trailing` slot for 02-18) and `ReviewBlock` (`Đã ghi lượt k`, duration, `Chưa chấm điểm ở bản này.`, `Lưu clip cho eval` -> `saveEvalClip`, `Đã lưu clip`, failure toast).
- Verification: 123 tests pass across 10 files (new: mime 4, recorder 7, listenActors 4); `next build`, `eslint apps/web`, `prettier --check apps/web` and `tsc --noEmit` are clean; no-persistence and no-`score-` greps pass.

## Task Commits

1. **Task 1 (tracer): record, upload, reviewing loop** - `9021899` (feat)
2. **Task 2: footer, attempt strip, review block, listen actors** - `0b370e4` (feat)
3. **Task 3: no-voice, mic-error, upload-error states and toast** - `502c368` (feat)

Tracer gate: interactive run, `human_verify_mode` end-of-phase, tracer `<verify>` automated-only, so the verify was re-run (tests + build) and passed before expansion.

## Decisions Made

See `key-decisions`. No contract, schema, threshold or model change. Level and silence thresholds in `level.ts` are untouched (still the RESEARCH A1 starting values awaiting a real mic).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 02-09's `top` only saw string states**
- **Found during:** Task 1 (type check of the new `reviewing`/`noVoice`/`scoring` comparisons)
- **Issue:** `PracticeRoom` computed `top` as `typeof value === "string" ? value : ""`, but `scoring`, `reviewing`, `noVoice` and `error` have child states, so their `state.value` is an object and `top` was `""` there.
- **Fix:** added a `topLevelState(value)` helper in `PracticeRoom.tsx` (same logic as `PlayerControls`), used for panel selection and the effect transitions.
- **Files modified:** `apps/web/components/PracticeRoom.tsx`
- **Commit:** `9021899`

**2. [Rule 2 - Missing critical] Tests for the privacy/cleanup mitigations**
- **Issue:** T-02-39 and T-02-40 (mic released on every exit, object URLs revoked) are mitigations in the threat register but the plan listed only `mime.test.ts`.
- **Fix:** added `recorder.test.ts` (cleanup before mic opens, cleanup while recording, failure paths, silence once, constraints) and `listenActors.test.ts` (URL revoke on end, abort, refused play). Both are outside the plan's `files_modified` list but touch no sibling's files.
- **Commits:** `9021899`, `0b370e4`

**3. [Rule 3 - Blocking] No `@/` alias in vitest**
- **Issue:** vitest has no path alias, so `lib/audio/recorder.ts` importing `@/lib/player/...` could not load in tests.
- **Fix:** relative imports inside `lib/` (`../player/playerMachine`, `../player/playRange`).
- **Commit:** `9021899`

### Plan wording interpreted

- `getUserMedia` `deviceId` is sent as `{ ideal }` (see key-decisions) rather than a bare string.
- `Bản gốc` is disabled while playing, recording or processing (the shortcut table ignores O there); UI-SPEC says "always enabled". Disabled only where the key is a no-op keeps button and key consistent.
- `Nghe lại` footer buttons are not gated on `videoReady` except Bản gốc and Lần lượt (they play the video); `Ghi lại`, `Của bạn` and `Câu tiếp` work even if the video failed to load.

**Total deviations:** 3 auto-fixed (1 Rule 1, 1 Rule 2, 1 Rule 3), 3 interpretation notes. No scope creep.

## Authentication Gates

None.

## Issues Encountered

- Vitest here cannot parse JSX (tsconfig `jsx: preserve`), so components are verified by build/lint/typecheck, not rendered. A scratch SSR render attempt was discarded. Visual checks stay for UAT.
- Not exercised against the real backend: the upload endpoint is built by 02-10 in parallel, so the flow is verified against the typed client contract and the machine tests only.
- `Đã ghi lượt {k}` reads k from the progress query after invalidation, so on a slow refetch it can briefly show the previous count.
- Human-check from the plan (30 sentences by mouse and keyboard, silent attempt, API stop and `Thử lại`, one `Lưu clip cho eval`, mic light off after leaving S3, footer wrap at 1024 px) was not performed; it joins the end-of-phase UAT queue (02-19) along with the RESEARCH A1 threshold tuning.

## Known Stubs

None. `Chọn micro` links to `/settings`, which 02-17 builds in the same wave; until it lands the link 404s.

## Threat Flags

None. T-02-39 (no browser storage, URLs revoked): grep check passes, `listenActors.test.ts` covers revoke. T-02-40 (mic open after leaving S3): `recorder.test.ts` covers cleanup on every path. T-02-41 accepted. T-02-SC: `pnpm install --frozen-lockfile` only, no package added or changed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 02-18 can pass IPA toggle and `Mất chữ cuối?` through `AttemptStrip`'s `trailing` prop and wire `onToggle` in `useShortcuts`.
- 02-17 can import `LevelMeter` and `MIC_DEVICE_STORAGE_KEY` (`shadowenglab.micDeviceId`) for `Thử micro` and the device select.
- UAT queue additions: mic open and release, thresholds (A1), footer wrap at 1024 px, toast and retry against a stopped API, eval clip file in `DATA_DIR/eval_clips`.

## Self-Check: PASSED

Created files exist, `9021899`, `0b370e4` and `502c368` are ancestors of HEAD, `git rev-list --count dd556e3..HEAD` = 3 before this docs commit, and the plan verification (tests, build, eslint, prettier, persistence and score greps) passes.

---
*Phase: 02-p1-t-o-b-i-v-tr-nh-ph-t*
*Completed: 2026-10-07*
