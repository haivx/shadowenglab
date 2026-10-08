---
phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
plan: 17
subsystem: ui
tags: [settings, s8, tanstack-query, auto-save, radix-select, web-audio, microphone]

requires:
  - phase: 02-p1-t-o-b-i-v-tr-nh-ph-t
    provides: "02-04 primitives (select, badge, progress, input, label, skeleton, button); 02-08 system status / settings / key-check endpoints; 02-11 typed client calls getSettings, putSettings, checkOpenAiKey; 02-14 LevelMeter, openMic, MIC_DEVICE_STORAGE_KEY, level detector"
provides:
  - "S8 /settings route with four sections (API key, Luyen tap, Micro, Model va du lieu) in mock order"
  - "KeyField: check-and-save of the OpenAI key via checkOpenAiKey; clears the field and invalidates the system-status query on success so the S1 banner disappears"
  - "settingsReducer / initialField: pure optimistic auto-save state machine with revert-on-failure and retry"
  - "PracticeDefaults: three auto-save selects with inline Da luu / Khong luu duoc. Thu lai. + Thu lai, locked US accent row"
  - "ModelStatusList: per-model San sang / Dang nap... / Chua co status plus editable data dir with 422 and restart-note copy"
  - "MicSection: device select persisted in localStorage, 3 s Thu micro with LevelMeter, permission line"
affects: [02-19 UAT, 02-18 (S3 selects read the same AppSettings defaults)]

estimate:
  tokens: 70000
  raw_tokens: 70000
  tasks: 3
  confidence: low

actuals:
  tokens: 21500
  tasks: 3
  commits: 5

plan_head_before: 389eec0efbdc8edf93811761c877c07073bafbcc
plan_head_after: 9bf7453f4bea531cebcba2be3a70cc72bf5ea0a4

tech-stack:
  added: []
  patterns:
    - "Auto-save field = pure reducer (display / saved / status / pending) + a thin component that dispatches change, then success or failure from the PUT promise; the mounted form takes its initial value once, so no sync effect is needed"
    - "Writers of AppSettings always rebuild the PUT body from queryClient.getQueryData(settings) at send time and write the response back with setQueryData, so the practice defaults and the data dir row never overwrite each other with stale values"
    - "Browser seams used directly only inside an event handler with one dispose() that every exit path calls (mic test)"

key-files:
  created:
    - apps/web/app/settings/page.tsx
    - apps/web/components/KeyField.tsx
    - apps/web/components/PracticeDefaults.tsx
    - apps/web/components/ModelStatusList.tsx
    - apps/web/components/MicSection.tsx
    - apps/web/lib/settingsForm.ts
    - apps/web/lib/settingsForm.test.ts
  modified: []

key-decisions:
  - "While any practice default is saving, all three selects are disabled; this serialises PUTs of the full AppSettings so two quick changes cannot clobber each other server-side"
  - "When GET /settings fails the defaults are shown but the selects are disabled: a full AppSettings (dataDir) cannot be built, so an edit could not be saved honestly"
  - "OpenAiKeyCheckResult.reason 'no_key' (empty field, nothing saved) reads Chua co key instead of 'Key khong hop le'; Kiem tra is disabled in that case"
  - "A data dir saved equal to the active dir shows Da luu instead of the restart note, because nothing needs restarting"

patterns-established:
  - "SETTINGS_SECTION_CLASS in lib/settingsForm.ts is the single source for the S8 section frame"

requirements-completed: [SET-01, SET-03, SET-04]

coverage:
  - id: D1
    description: "Pasting a key and pressing Kiem tra shows Dang kiem tra..., then Key hop le . da luu, Key khong hop le . chua luu or the offline message; empty field tests the saved key; success clears the field and refreshes the S1 banner query; the key is never echoed back, logged or stored client-side"
    requirement: "SET-03"
    verification:
      - kind: build
        ref: "pnpm --filter @shadowenglab/web build && pnpm exec eslint apps/web"
        status: pass
    human_judgment: true
    rationale: "Real OpenAI call and the .env write need a browser and a real key; no component test harness exists in apps/web (node-only vitest)"
  - id: D2
    description: "Practice defaults auto-save through PUT /settings with inline Da luu; failure reverts the select to the last saved value, shows Khong luu duoc. Thu lai. and Thu lai re-sends; an unsaved value is never shown as saved"
    requirement: "SET-04"
    verification:
      - kind: unit
        ref: "apps/web/lib/settingsForm.test.ts#settingsReducer"
        status: pass
    human_judgment: false
  - id: D3
    description: "Label maps: recordFactor +25%/+50%/+100% <-> 1.25/1.5/2.0, playbackRate 0.75x/1x, repeat x1/x2/x3, snap of off-list values"
    requirement: "SET-04"
    verification:
      - kind: unit
        ref: "apps/web/lib/settingsForm.test.ts#tuy chon va nhan"
        status: pass
    human_judgment: false
  - id: D4
    description: "Model va du lieu: per-model status with indeterminate bar while loading, no percentage; data dir editable with Doi thu muc, 422 invalid_settings copy and the D-12 restart note"
    requirement: "SET-01"
    verification:
      - kind: unit
        ref: "apps/web/lib/settingsForm.test.ts#dataDirNeedsRestart"
        status: pass
    human_judgment: true
    rationale: "Visual match with S8 mock and the real 422 / restart flow need the running backend and a browser"
  - id: D5
    description: "Micro: device select persisted under MIC_DEVICE_STORAGE_KEY (not AppSettings), Thu micro runs a 3 s level meter then reports Nghe thay tieng / Khong nghe thay gi and always closes the mic, permission line Da cap / Chua cap / Bi chan"
    requirement: "SET-01"
    verification:
      - kind: unit
        ref: "apps/web/lib/settingsForm.test.ts#micPermissionLabel"
        status: pass
    human_judgment: true
    rationale: "Microphone permission prompts and level-meter movement while speaking cannot be asserted without a browser and real hardware"

duration: 17 min
completed: 2026-10-08
---

# Phase 2 Plan 17: S8 Settings Summary

**S8 Settings with an OpenAI key check-and-save field, optimistic auto-saving practice defaults that revert on failure, model/data-dir status, and a microphone picker with a 3 s level-meter test.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-10-08T02:07:00Z
- **Completed:** 2026-10-08T02:24:00Z
- **Tasks:** 3 (1 tracer, 1 TDD, 1 auto)
- **Files created:** 7 (0 modified)

## Accomplishments

- `/settings` renders four sections in mock order under `AppHeader`: `API key`, `Luyện tập`, `Micro`, `Model và dữ liệu`, all with loading, error and partial states from UI-SPEC E13.
- `KeyField` posts through `checkOpenAiKey` (`{apiKey}` when typed, `{}` when empty), renders the three result lines plus `Đang kiểm tra…`, clears the password input on a saved success and invalidates the system-status query so the S1 yellow banner goes away. The key lives only in component state.
- `settingsReducer` (pure, 8 tests) drives the three practice selects: change shows the new value immediately, success confirms it, failure reverts `display` to `saved` and keeps `pending` for `Thử lại`; stale success/failure responses from an older change are ignored.
- `ModelStatusList` shows `Sẵn sàng` / `Đang nạp…` (+ indeterminate `Progress`) / `Chưa có · chạy make setup` per model, and a `Thư mục dữ liệu` row (mono input, ellipsis + `title`) whose `Đổi thư mục` surfaces `Thư mục không tồn tại hoặc không ghi được.` on 422 `invalid_settings` and `Khởi động lại make dev để áp dụng; dữ liệu cũ vẫn ở {activeDataDir}.` on success.
- `MicSection` lists audio inputs (labels after permission, `Không tìm thấy micro` for none), persists the choice under `MIC_DEVICE_STORAGE_KEY`, runs `Thử micro` for 3 s with `LevelMeter` and `Đang nghe…`, then `Nghe thấy tiếng` / `Không nghe thấy gì`, and shows `Quyền micro: Đã cấp / Chưa cấp / Bị chặn`.

## Task Commits

1. **Task 1 (tracer): S8 route + KeyField** - `f8e4740` (feat). Tracer gate: `<verify>` is automated-only and `human_verify_mode` is `end-of-phase`, so the build + eslint verify was re-run end to end, passed, and expansion continued.
2. **Task 2 RED: failing reducer / option-map tests** - `19a9eb7` (test)
3. **Task 2 GREEN: reducer, option maps, data-dir helper** - `e39c734` (feat)
4. **Task 2: PracticeDefaults, ModelStatusList, page wiring (+ rename to `RATE_OPTIONS`, `dataDirNeedsRestart`)** - `a4b6e8d` (feat)
5. **Task 3: MicSection + `micPermissionLabel`** - `9bf7453` (feat)

## TDD Notes (Task 2)

- **RED:** `settingsForm.test.ts` (14 target tests) run with the `tap-flat` reporter before any implementation: all 14 failed with `TypeError` (`settingsReducer`/`optionLabel`/`dataDirNote` "is not a function", `PLAYBACK_RATE_OPTIONS` "reading 'map' of undefined"), i.e. on the planned behaviour being absent, not on syntax, import or fixture faults. `workflow.tdd_mode` is not enabled in this project's config, so the `gsd_run check tdd-red-evidence` classifier was not run; the semantic assessment above is manual.
- **GREEN:** 14/14 passing after `settingsForm.ts`.
- **REFACTOR:** none as a separate commit; later renames/adjustments (`RATE_OPTIONS`, `dataDirNeedsRestart`) shipped with the component commit with tests updated and green.

## Files Created/Modified

- `apps/web/app/settings/page.tsx` - S8 route, max-width 860, gap 20
- `apps/web/components/KeyField.tsx` - API key field and result line
- `apps/web/components/PracticeDefaults.tsx` - auto-save selects, locked accent row, load-failure and skeleton states
- `apps/web/components/ModelStatusList.tsx` - model rows and data-dir row
- `apps/web/components/MicSection.tsx` - device select, mic test, permission line
- `apps/web/lib/settingsForm.ts` - reducer, option maps, `snapToOption`, `micPermissionLabel`, `dataDirNeedsRestart`, section class
- `apps/web/lib/settingsForm.test.ts` - 16 tests

## Decisions Made

See `key-decisions` in the frontmatter. In short: PUTs serialised by disabling selects while saving; selects disabled when settings failed to load; `no_key` reads `Chưa có key`; restart note only when the saved dir differs from the active one.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Shared section frame lives in `lib/settingsForm.ts`**
- **Found during:** Task 1
- **Issue:** Four components each need the same S8 section frame (white, 1px border, radius 12, padding 24, gap 16). A shared component would be a new file outside `files_modified`, and a `page.tsx` export is not allowed by Next.
- **Fix:** exported `SETTINGS_SECTION_CLASS` from `lib/settingsForm.ts` (created in Task 1 with just that constant).
- **Files modified:** `apps/web/lib/settingsForm.ts`
- **Commit:** `f8e4740`

**2. [Rule 1 - Bug] Type error under `noUncheckedIndexedAccess` in `snapToOption`**
- **Found during:** Task 2 build
- **Issue:** `options[0]` is `T | undefined`; `next build` failed with "'best' is possibly 'undefined'".
- **Fix:** iterate with an optional `best`, throw on an empty list.
- **Files modified:** `apps/web/lib/settingsForm.ts`
- **Commit:** `a4b6e8d`

**3. [Rule 1 - Bug] `prefer-const` lint error in the mic test timer**
- **Found during:** Task 3 eslint
- **Fix:** hold the timeout id on a small object (`stopTimer.id`).
- **Files modified:** `apps/web/components/MicSection.tsx`
- **Commit:** `9bf7453`

**4. [Rule 2 - Missing critical] Concurrent saves and unloadable settings**
- **Found during:** Task 2 design
- **Issue:** The spec says every change PUTs the full `AppSettings`. Two quick changes (or a change while the data dir row writes) would overwrite each other with stale fields, and a failed GET /settings leaves no `dataDir` to send.
- **Fix:** PUT bodies are rebuilt from the query cache at send time and the response is written back with `setQueryData`; selects are disabled while one is saving; with settings unavailable the selects are disabled and defaults are shown with `Tải lại`.
- **Files modified:** `PracticeDefaults.tsx`, `ModelStatusList.tsx`
- **Commit:** `a4b6e8d`

**5. [Plan naming] `RATE_OPTIONS` and `dataDirNeedsRestart`**
- The tests initially used `PLAYBACK_RATE_OPTIONS` and a `dataDirNote` string helper; renamed to `RATE_OPTIONS` (the plan's artifacts table) and to a boolean `dataDirNeedsRestart` so the user-facing note text lives in `ModelStatusList.tsx` as the acceptance criterion requires.

**Total deviations:** 5 (2 bug fixes, 1 blocking, 1 missing-critical, 1 naming). **Impact:** none on scope; all inside the plan's files.

## Authentication Gates

None. The OpenAI key check is the feature itself, not an executor gate.

## Issues Encountered

- `human-check` for Task 3 (real key, microphone permission, data-dir scenarios, API-down reload, visual match with `docs/design/screens/S8-settings.html`) was **not run**: it needs a browser, a real OpenAI key and microphone hardware. Automated verification (tests, build, eslint) passes. Carry this into 02-19 UAT. `.planning/WINDOWS.md` does not exist, so no ledger entry was appended.
- The mic test thresholds come from the level detector's starting constants (RESEARCH A1), still unmeasured on Liam's hardware.

## Known Stubs

None. No placeholder data flows to the UI; every control is wired to the typed client or the browser API.

## Threat Flags

None beyond the plan's register. T-02-47 (key stays in component state, password input, cleared after success, no logging or client storage; only `maskedKey` is displayed) and T-02-48 (mic closed after 3 s, on unmount and on every exit) are mitigated as planned; `localStorage` holds only the mic device id.

## Verification

- `pnpm --filter @shadowenglab/web test`: 12 files, 164 tests pass
- `pnpm --filter @shadowenglab/web build`: compiles; `/settings` 7.16 kB
- `pnpm exec eslint apps/web`: exit 0
- Acceptance greps for KeyField, PracticeDefaults, ModelStatusList (`Khởi động lại make dev để áp dụng`, `Đổi thư mục`, `Chưa có · chạy make setup`) and MicSection: all PASS
- No `score-` class and no `console.*` in the four S8 components

## Next Phase Readiness

S8 is complete for SET-01 (S8 part), SET-03, SET-04. 02-19 UAT should walk the Task 3 human-check list; S3 selects (02-18/other plans) can read the same `settings` query key for their initial values.

## Self-Check: PASSED

- Files exist: `apps/web/app/settings/page.tsx`, `apps/web/components/KeyField.tsx`, `PracticeDefaults.tsx`, `ModelStatusList.tsx`, `MicSection.tsx`, `apps/web/lib/settingsForm.ts`, `settingsForm.test.ts`
- Commits are ancestors of HEAD: `f8e4740`, `19a9eb7`, `e39c734`, `a4b6e8d`, `9bf7453`
- RED (`test(02-17)`) precedes GREEN (`feat(02-17)`) in history
