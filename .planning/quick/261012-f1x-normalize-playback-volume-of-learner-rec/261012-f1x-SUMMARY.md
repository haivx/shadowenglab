---
phase: quick-261012-f1x
plan: 01
subsystem: web/player
tags: [web-audio, playback, gain, limiter, PLY-07]
requires: []
provides:
  - "playbackGain(channels) / measureLevel(samples) pure functions"
  - "playBlobOnce plays via Web Audio: source -> GainNode -> DynamicsCompressorNode limiter -> destination"
affects: [apps/web/lib/player/listenActors.ts]
tech-stack:
  added: []
  patterns: ["BlobPlaybackDeps seam { readBlob, createContext } for node-testable Web Audio playback"]
key-files:
  created:
    - apps/web/lib/audio/playbackGain.ts
    - apps/web/lib/audio/playbackGain.test.ts
  modified:
    - apps/web/lib/player/listenActors.ts
    - apps/web/lib/player/listenActors.test.ts
key-decisions:
  - "Gain constants (target RMS -20 dBFS, max x8, peak ceiling 0.89, silence 1e-4) are playback-only starting values, to be tuned by ear at UAT; not scoring thresholds"
  - "Limiter set explicitly (threshold -1, knee 0, ratio 20, attack 0.003, release 0.1)"
status: complete
metrics:
  duration: ~10 min
  completed: 2026-10-12
commits: 2
plan_head_before: ef0808c8724193d0cd58423a915fb3562a903f57
plan_head_after: 3463369
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
---

# Quick 261012-f1x: Normalize playback volume of learner recording Summary

Quiet learner recordings (raw mic, AGC/NS/AEC off for scoring) now play back louder when listening again ("Của bạn" M, "Lần lượt cả hai" B), using a pure RMS/peak gain (max x8, never below x1, peak-safe) through a GainNode and an explicit limiter, while the Blob sent for scoring is never touched.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Tracer: Blob -> ArrayBuffer copy -> decode -> playbackGain -> GainNode -> limiter -> speaker | 9698b91 |
| 2 | Edge cases of gain function and all playBlobOnce exit paths | 3463369 |

## Verification

- `vitest run lib/player lib/audio`: 8 files, 110 tests pass
- `tsc --noEmit` (apps/web): clean
- `eslint apps/web/lib/player apps/web/lib/audio`: clean
- `prettier --check apps/web/lib/player apps/web/lib/audio`: clean
- `git diff HEAD` over components, recorder.ts, playerMachine.ts, packages/contracts, services: empty (untouched)

## Deviations from Plan

None - plan executed exactly as written. Task 2 tests all passed against the Task 1 implementation, so no code fix was needed in Task 2.

## Pending human verification

Manual Chrome listening check (not done by the executor): run `make dev`, open a lesson, record a sentence at normal distance and volume, press "Của bạn" (M) and confirm it is clearly louder, comparable to the original, with no distortion; record loudly close to the mic and confirm no clipping; press "Lần lượt cả hai" (B) and confirm original then normalized recording; stop mid-playback and confirm immediate silence; confirm the sentence score is unchanged and "Lưu clip cho eval" still saves. Gain constants may need tuning by ear.

## Known Stubs

None.

## Threat Flags

None. No new network endpoints, storage, or trust-boundary surface; decoding and playback stay in browser memory.

## Self-Check: PASSED

- apps/web/lib/audio/playbackGain.ts, playbackGain.test.ts, apps/web/lib/player/listenActors.ts, listenActors.test.ts present
- Commits 9698b91 and 3463369 present in history
