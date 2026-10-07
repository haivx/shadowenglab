---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 05
subsystem: ui
tags: [xstate, xstate-v5, vitest, keyboard-shortcuts, web-audio, tdd]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-01 contracts (AttemptAck), 02-02 web workspace/test tooling"
provides:
  - "playerMachine: XState v5 practice-room machine with injected actors (no React/DOM/fetch)"
  - "shortcuts.ts: pure shouldHandleShortcut + shortcutToAction following the UI-SPEC map"
  - "level.ts: pure RMS/dB level meter, noise floor, speech start and 1 s silence detector"
affects: [02-09 player UI + playback actors, 02-14 recording actor + upload wiring, Phase 3 scoring]

actuals:
  tokens: 12400
  tasks: 2
  commits: 4

plan_head_before: d725816d5e3527d6137378caff1d85e39a1c3eda
plan_head_after: 4d3108c885d563ac27deb87e7d75e3801abc18d1

tech-stack:
  added: []
  patterns:
    - "XState v5 setup({...}) with stub actors, replaced via machine.provide in tests and UI"
    - "Structural event/target types so tests pass plain objects and the UI passes real KeyboardEvent"
    - "Pure audio functions: (state, samples, dtMs) -> state, no Web Audio objects"

key-files:
  created:
    - apps/web/lib/player/playerMachine.ts
    - apps/web/lib/player/playerMachine.test.ts
    - apps/web/lib/player/shortcuts.ts
    - apps/web/lib/player/shortcuts.test.ts
    - apps/web/lib/audio/level.ts
    - apps/web/lib/audio/level.test.ts
  modified: []

key-decisions:
  - "Event type split into PlayerUiEvent (UI/keyboard) and PlayerActorEvent (sent back by actors), PlayerEvent = union"
  - "recordDelay is capped at 60 s (MAX_RECORD_MS) to match the backend limit"
  - "previewing and the SAMPLE_DONE return path resolve to reviewing/noVoice/error/idle through a guarded choice on recordings[segmentIndex].status"
  - "scoring keeps a substate idle|yours so M (listen to your take) still works during upload; scoring is the P1 upload step (D-05)"
  - "Silence/level thresholds are starting values (RESEARCH A1) to tune with a real mic in end-of-phase UAT"

patterns-established:
  - "Navigation (NEXT/PREV/GOTO) and settings events are declared only on states that allow them; recording and scoring omit them, which makes them ignored by construction"
  - "Machine context never carries score values, colours or correct/incorrect judgments (D-05, D-08)"

requirements-completed: [PLY-02, PLY-07, REC-01]

coverage:
  - id: D1
    description: "playerMachine encodes the P1 loop idle -> playing -> recording -> scoring -> reviewing/noVoice/error with injected actors, concurrency guards and retry"
    requirement: "PLY-02"
    verification:
      - kind: unit
        ref: "apps/web/lib/player/playerMachine.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Keyboard shortcut rules ignore inputs, comboboxes, contenteditable, dialogs, modifiers and key repeat; map keys to events per state"
    requirement: "PLY-07"
    verification:
      - kind: unit
        ref: "apps/web/lib/player/shortcuts.test.ts"
        status: pass
    human_judgment: false
  - id: D3
    description: "Pure level meter and 1 s post-speech silence detector for early auto-stop of recording"
    requirement: "REC-01"
    verification:
      - kind: unit
        ref: "apps/web/lib/audio/level.test.ts"
        status: pass
    human_judgment: false
  - id: D4
    description: "Level/silence thresholds (+10 dB over 300 ms noise floor, 1000 ms silence) behave well with Liam's real microphone"
    requirement: "REC-01"
    verification: []
    human_judgment: true
    rationale: "Thresholds are starting values (RESEARCH A1); only a real microphone in the end-of-phase UAT can confirm them"

duration: 9min
completed: 2026-10-07
status: complete
---

# Phase 2 Plan 05: Player state machine, shortcuts and level detector Summary

**XState v5 practice-room machine with injected actors, pure per-state keyboard shortcut rules, and a pure RMS level meter with a 1 s silence detector, all proven in node-env vitest before any UI exists**

## Performance

- **Duration:** about 9 min of commit time (17:50 to 17:54 +0700), then interrupted by an API rate limit; verified and summarised in a continuation run
- **Tasks:** 2 (both TDD, RED then GREEN)
- **Files modified:** 6 created, 0 modified

## Accomplishments

- `playerMachine` (id `player`) covers idle, previewing, playing, recording, scoring, reviewing, noVoice and error. It imports no React, DOM or fetch. Every side effect is an actor replaced through `machine.provide`.
- `scoring` exists as the P1 upload step, so Phase 3 attaches scoring without changing the machine shape (D-05). Context carries no scores or judgments, only voiced / not voiced.
- `shortcuts.ts` implements the UI-SPEC map and the T-02-13 mitigation: target filter plus modifiers and key repeat.
- `level.ts` computes RMS in dB, a noise floor from the first 300 ms, speech start at +10 dB, silence only after speech, and 10 bar levels.
- Verification: 51 tests pass in 3 files (playerMachine 20, shortcuts 14 plus parametrised cases, level 8). `tsc --noEmit` and prettier are clean, eslint reports nothing, and the React/DOM/fetch grep on the machine file finds nothing.

## Interface reference for 02-09 and 02-14

**Input (`PlayerInput`):** `{ segmentCount, startIndex, segmentDurationsMs: number[], repeat: 1|2|3, rate, recordFactor }`

**Context (`PlayerContext`):** `segmentCount, segmentIndex, segmentDurationsMs, repeat, rate, recordFactor, rep, recordings: Record<number, {blob, durationMs, status: "pending"|"uploaded"|"noVoice"|"failed", attempt?}>, lastError?, level: {bars 0..10, speech}`

**UI events (`PlayerUiEvent`):** `PLAY, STOP, RECORD, PREVIEW, NEXT, PREV, GOTO{index}, LISTEN_ORIGINAL, LISTEN_YOURS, LISTEN_BOTH, RETRY_UPLOAD, SET_RATE{rate}, SET_REPEAT{repeat}, SET_RECORD_FACTOR{recordFactor}, SEGMENTS_UPDATED{segmentDurationsMs}`

**Actor events (`PlayerActorEvent`, sent by the real actors):** `REP{n}, SAMPLE_DONE, SAMPLE_FAILED, LEVEL{bars, speech}, SILENCE, STOPPED{blob, durationMs}, RECORD_FAILED{reason}`

**Actors and input shapes:**

| Actor | Kind | Input | Contract |
|---|---|---|---|
| `playSample` | fromCallback | `{segmentIndex, repeat, rate}` | sends REP, then SAMPLE_DONE or SAMPLE_FAILED; cleanup stops audio |
| `playBlob` | fromPromise | `{blob}` | resolves when playback ends |
| `playBoth` | fromPromise | `{segmentIndex, rate, blob}` | original then yours |
| `record` (id `recorder`) | fromCallback | `{segmentIndex}` | receives STOP; sends LEVEL, SILENCE, STOPPED, RECORD_FAILED |
| `uploadAttempt` | fromPromise | `{segmentIndex, blob}` | returns `AttemptAck` (`voiced`, `attempt`) |

**Delay:** `recordDelay` = `min(60000, segmentDurationsMs[segmentIndex] * recordFactor)`.

**Shortcuts:** `shouldHandleShortcut(event)`, `shortcutToAction(key, stateValue)` returns a `PlayerEvent`, `{type: "TOGGLE_IPA" | "TOGGLE_TRANSLATION"}` or null. The caller calls `preventDefault()` only for a non-null result.

**Level:** `createLevelState()`, `updateLevel(state, samples: Float32Array, dtMs)`. Exposes `bars`, `speech`, `silenceDetected` (true on exactly one frame). The 02-14 actor forwards these as LEVEL and SILENCE events.

## Task Commits

1. **Task 1: playerMachine with injected actors** - `0b39659` (test, RED), `f354f20` (feat, GREEN)
2. **Task 2: shortcut rules and level/silence detector** - `04162a4` (test, RED), `4d3108c` (feat, GREEN)

**Plan metadata:** committed with this SUMMARY (docs: complete plan)

## Files Created/Modified

- `apps/web/lib/player/playerMachine.ts` - XState v5 machine, types and actor input shapes
- `apps/web/lib/player/playerMachine.test.ts` - transition tests with fake actors and fake timers
- `apps/web/lib/player/shortcuts.ts` - shortcut gating and key-to-event mapping
- `apps/web/lib/player/shortcuts.test.ts` - dialog, input, modifier, repeat, uppercase and per-state cases
- `apps/web/lib/audio/level.ts` - pure level/silence detector
- `apps/web/lib/audio/level.test.ts` - noise floor, speech, silence-once and silence-before-speech cases

## Decisions Made

See `key-decisions` in the frontmatter. No change to contracts, schema, thresholds or models was made.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The original executor was killed by an API rate limit after its last task commit (`4d3108c`) and before it wrote SUMMARY.md. A continuation run re-verified the worktree state (HEAD `4d3108c`, 4 commits since `d725816`), re-ran the full verification, and wrote this SUMMARY. No task work was lost or redone.
- The `gsd-plan-head-before-02-05` ledger had survived on disk, so `commits: 4` is measured with `git rev-list --count`.

## Known Stubs

None. The default actors inside `setup` (`playSample`, `record`, and so on) are intentional no-op placeholders, replaced by 02-09 (playback) and 02-14 (recording, upload). The default `uploadAttempt` throws if left unprovided.

## Threat Flags

None. T-02-13 (keyboard events into player actions) is mitigated and tested. No new package was installed (T-02-SC).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 02-09 can wire the real `playSample`, `playBlob` and `playBoth` actors and the S3 UI against this machine.
- 02-14 supplies the `record` actor (feeding `updateLevel`) and `uploadAttempt`.
- Open item for the end-of-phase UAT: tune `SPEECH_MARGIN_DB`, `SILENCE_MS` and `NOISE_WINDOW_MS` in `level.ts` with a real microphone (RESEARCH A1).

## Self-Check: PASSED

All six source/test files exist, the four task commits (`0b39659`, `f354f20`, `04162a4`, `4d3108c`) are ancestors of HEAD, and the plan verification (`vitest` 51/51, `tsc`, prettier, eslint, machine-file grep) passes.

---
*Phase: 02-p1-t-o-b-i-v-tr-nh-ph-t*
*Completed: 2026-10-07*
