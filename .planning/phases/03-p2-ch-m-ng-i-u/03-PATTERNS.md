# Phase 3: P2 · Chấm ngữ điệu - Pattern Map

**Mapped:** 2026-10-08
**Files analyzed:** 22 (new/modified)
**Analogs found:** 20 / 22 (all paths verified git-tracked via `git ls-files`; repo-relative)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `services/audio/src/audio_service/scoring/__init__.py` | package | n/a | `lesson/__init__.py` | exact |
| `services/audio/src/audio_service/scoring/align.py` (`align(ref_feats,user_feats)->path`, MFCC DTW) | utility (pure) | transform | `lesson/features.py` (`frame_energy`) | role-match |
| `services/audio/src/audio_service/scoring/prosody.py` (F0->semitone, per-word, 3 chỉ số, prominence) | utility (pure) | transform | `lesson/features.py` (`extract_f0`, `frame_energy`) | role-match |
| `services/audio/src/audio_service/scoring/scorer.py` (ghép ScoreResult, timingMs) | service | request-response | `routers/attempts.py` `_ack` (model_validate dựng contract) | partial |
| `services/audio/src/audio_service/rules/__init__.py`, `rules/engine.py` (5 mã Lớp C), `rules/tips.py` (template VI, D-14) | utility (pure) | transform | `lesson/quality.py` (rule/ngưỡng thuần) | role-match |
| `services/audio/src/audio_service/rules/thresholds.py` (file ngưỡng có version -> `versions.thresholds`) | config | n/a | `services/audio/src/audio_service/models.py` (hằng/phiên bản model) | partial |
| `services/audio/src/audio_service/lesson/features.py` (mod: extract_f0 tham số hoá nếu cần, thêm MFCC/intensity) | utility | transform | chính nó | exact |
| `services/audio/src/audio_service/lesson/pipeline.py` (mod `analyze_segment` ~dòng 518: ghi key mới vào npz; lazy backfill D-03) | service | batch / file-I/O | chính nó | exact |
| `services/audio/src/audio_service/routers/attempts.py` (mod `create_attempt` -> trả `ScoreResult`, lỗi `no_speech`) | controller | request-response | chính nó | exact |
| `services/audio/src/audio_service/routers/scoring.py` (GET đọc lại lượt) | controller | request-response | `routers/attempts.py` (`save_eval_clip` + `_ready_lesson`) | role-match |
| `services/audio/src/audio_service/db.py` (mod: SCHEMA_VERSION=2, migration, insert/update điểm, best attempt) | model/migration | CRUD | chính nó (`ensure_schema`) | exact |
| `packages/contracts/src/api.ts` (thêm `no_speech`; LessonProgress best score nếu cần) | contract | n/a | chính nó (`ApiErrorCode`) | exact |
| `packages/contracts/src/score.ts` | contract | n/a | KHÔNG đổi shape (D-xx Phase 1) | n/a |
| `packages/contracts/fixtures/*.json`, `schema/contracts.schema.json`, `contracts_gen.py` | generated | n/a | `scripts/contracts_gen.sh` (không sửa tay) | exact |
| `services/audio/tests/test_scoring_*.py`, `test_rules_*.py`, `test_attempts_api.py` (mod), `test_db.py` (mod) | test | transform / request-response | `tests/test_features.py`, `tests/test_db.py`, `tests/test_attempts_api.py` | exact |
| `apps/web/lib/scoreLevel.ts` (+ test) | utility | transform | `apps/web/lib/lessonView.ts` (+ `lessonView.test.ts`), `lib/tokens.test.ts` | role-match |
| `apps/web/lib/api.ts` (mod `uploadAttempt` -> `ScoreResult`; thêm GET lượt) | service (client) | request-response | chính nó dòng 207-221 | exact |
| `apps/web/lib/queries.ts` (mod) | hook | request-response | chính nó | exact |
| `apps/web/lib/player/playerMachine.ts` (mod state `scoring`, dòng 393+) | store (XState) | event-driven | chính nó | exact |
| `apps/web/components/ScoreHero.tsx`, `TipList.tsx`, `IntonationChart.tsx` | component | request-response (render props) | `components/AttemptStrip.tsx`, `components/ReviewBlock.tsx` | role-match |
| `apps/web/components/ReviewBlock.tsx`, `SentenceStatePanel.tsx`, `AttemptStrip.tsx`, `ResultActionBar.tsx`, `TranscriptList.tsx` (mod) | component | event-driven | chính chúng | exact |
| `apps/web/lib/player/playerMachine.test.ts` (mod) | test | event-driven | chính nó | exact |

## Pattern Assignments

### Hàm audio thuần: `scoring/*.py`, `rules/*.py`

**Analog:** `services/audio/src/audio_service/lesson/features.py`

Convention: docstring tiếng Việt nêu "hàm nhận mảng, trả mảng, không đọc file"; `from __future__ import annotations`; `import numpy as np`; import nặng (`parselmouth`) làm lazy bên trong hàm; dtype ép tường minh (float32).

```python
# features.py:10-35
from __future__ import annotations
import logging
import numpy as np
SR = 16000

def extract_f0(audio16k: np.ndarray, sr: int = SR) -> np.ndarray:
    """F0 bằng Praat autocorrelation, bước 10 ms. Hz, 0.0 = vô thanh. float32."""
    import parselmouth
    sound = parselmouth.Sound(np.asarray(audio16k, dtype=np.float64), sampling_frequency=sr)
    pitch = sound.to_pitch_ac(time_step=0.01, pitch_floor=75.0, pitch_ceiling=500.0)
    return np.asarray(pitch.selected_array["frequency"], dtype=np.float32)

def frame_energy(audio16k, sr=SR, hop_s=0.01, win_s=0.025) -> np.ndarray:
    x = np.asarray(audio16k, dtype=np.float32)
    ...
    return np.sqrt(np.mean(np.square(windows), axis=1)).astype(np.float32)
```

Dùng chung `extract_f0` + `frame_energy` cho người học (bản gốc và người học xử lý giống nhau, CONTEXT Discretion). `segment_window(start,end,pad_ms,end_extra_ms,*,lo,hi)` (dòng ~108) cho cửa sổ ref. `align` phải đứng sau một giao diện thay được (D-01): định nghĩa `Protocol`/hàm cùng chữ ký, rule Lớp C chỉ nhận `path`.

**Test analog:** `services/audio/tests/test_features.py` — helper tín hiệu tổng hợp, không nạp model:
```python
def _sine(freq, seconds, amp=0.5):
    t = np.arange(int(SR * seconds)) / SR
    return (amp * np.sin(2 * math.pi * freq * t)).astype(np.float32)
def test_f0_of_200_hz_sine_is_about_100_frames_at_200_hz() -> None: ...
```
Tiêu chí kiểm bắt buộc: ref so với chính nó -> melodyMatch = 1, không issue (D-05, specifics); chuỗi sai hẳn -> điểm thấp.

### `routers/attempts.py` (controller, request-response)

**Giữ nguyên** `_BoundedBodyRoute`, `_ready_lesson` (404/409 -> `ApiErrorException`), `_receive`, `_normalize` -> `(wav, duration_ms, voiced)`. Điểm gắn D-09 là `create_attempt` (dòng ~167-190):

```python
@router.post("/lessons/{lesson_id}/segments/{index}/attempts", status_code=201,
             response_model=AttemptAck, response_model_exclude_unset=True)
def create_attempt(lesson_id, index, audio: UploadFile, saveForEval: bool = Form(False)) -> AttemptAck:
    lesson = _ready_lesson(lesson_id, index)
    workdir = Path(tempfile.mkdtemp(dir=tmp_dir()))
    try:
        wav, duration_ms, voiced = _normalize(audio, workdir)
        attempt = db.insert_attempt(lesson.id, index, duration_ms=duration_ms, voiced=voiced)
        if saveForEval:
            _store_eval_clip(lesson, index, attempt, wav)
            db.mark_saved_for_eval(lesson.id, index, attempt)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
```
Đổi: `response_model=ScoreResult`; `not voiced` -> `raise ApiErrorException(<status>, "no_speech", "<VI>")` (pattern lỗi: `ApiErrorException(422, "recording_too_long", "Bản ghi dài quá 60 giây.")`); đọc wav bằng `audio_io.read_audio` + `to_mono_16k` TRONG router (I/O ở router), gọi hàm thuần, lưu `result_json`. Cần quyết định có insert lượt khi không voiced (hiện lượt không tiếng vẫn lấy số, `test_non_voiced_uploads_take_a_number_too`). `save_eval_clip` (PUT) vẫn trả `AttemptAck` qua `_ack`. Lỗi ffmpeg/IO: `except (subprocess.SubprocessError, sf.LibsndfileError): raise _unsupported() from None`. Dựng contract: `AttemptAck.model_validate({...camelCase...})` từ `contracts_gen`.

### `routers/scoring.py` (controller)
Hiện: `router = APIRouter(prefix="/scoring", tags=["scoring"])` rỗng. Nếu thêm GET đọc lại lượt, copy `_ready_lesson` + `db.get_attempt(...)` + 404 `not_found` từ `save_eval_clip`. Lưu ý đường dẫn: prefix `/scoring` không khớp `/lessons/{id}/segments/{i}/attempts/{n}`; đặt endpoint trong `attempts.py` hoặc bỏ prefix (xem `attempts.py` "Không prefix").

### `db.py` migration v1 -> v2 (D-10)

```python
SCHEMA_VERSION = 1
def ensure_schema(conn):
    if conn.execute("PRAGMA user_version").fetchone()[0] >= SCHEMA_VERSION:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
            conn.execute(_DDL)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK"); raise
```
Mở rộng: `SCHEMA_VERSION = 2`; trong khối dưới khoá, `version = PRAGMA user_version`; `if version < 1: _DDL`; `if version < 2: ALTER TABLE attempts ADD COLUMN overall REAL` (x4 REAL + `result_json TEXT`) rồi đặt version. Cập nhật `_DDL` cho DB mới theo cách không ALTER-trùng (DB mới tạo v1 DDL rồi ALTER, hoặc DDL v2 + bỏ ALTER khi mới). `AttemptRow`/`SegmentProgressRow` là frozen dataclass; thêm field điểm tốt nhất (`best_overall`) cho `segment_progress`. Test: `tests/test_db.py::test_ensure_schema_on_existing_v1_db_is_a_noop` (dòng 123) là mẫu dựng DB v1 rồi chạy migration; fixture `data_dir(tmp_path, monkeypatch)` dòng 15.

### `packages/contracts` (D-09 đổi contract, one-way)

```ts
// api.ts:6
export const ApiErrorCode = z.enum(["invalid_request","invalid_url",..."invalid_segment","unsupported_media","payload_too_large", ...]);
```
Thêm `"no_speech"`. Sau đó `make contracts` (-> `scripts/contracts_gen.sh`: Zod -> `schema/contracts.schema.json` -> `contracts_gen.py` bằng datamodel-codegen) và commit cả file sinh; drift gate: `tests/test_contracts_drift.py`, `scripts/contracts_check.sh`. `ScoreResult`/`Issue`/`Prosody` giữ nguyên (`score.ts`: `Scores.sound` nullable, `Tip{text,issueRef,source}`, `Versions{scorer,thresholds}`, `Contour{ref,user,wordBounds}`). Fixture `packages/contracts/fixtures/ScoreResult.json` + `contracts.test.ts` + `tests/test_contracts_roundtrip.py` là mẫu roundtrip; thêm fixture mới nếu thêm schema (vd. response best-score). Chú ý: Issue `wordIndex` là chỉ số trong `ScoreResult.words`.

### `apps/web/lib/api.ts` + `playerMachine.ts`

```ts
// api.ts:207-221
export function uploadAttempt(lessonId, index, blob, options): Promise<AttemptAck> {
  const form = new FormData();
  form.append("audio", blob, "attempt");
  form.append("saveForEval", options.saveForEval ? "true" : "false");
  return request(`${segmentPath(lessonId, index)}/attempts`,
    { method: "POST", body: form, signal: options.signal }, AttemptAck);
}
```
Đổi kiểu trả + schema Zod sang `ScoreResult`. `request(path, init, Schema)` Zod-validate; lỗi là `ApiRequestError` (`.error.code`, `.status`) — dùng để rẽ nhánh `no_speech`.

```ts
// playerMachine.ts:122 actor mặc định, 393-425 state scoring
uploadAttempt: fromPromise<AttemptAck, UploadInput>(async () => { throw ... }),
scoring: { invoke: { src: "uploadAttempt", input: ({context}) => {...},
  onDone: [ { guard: ({event}) => event.output.voiced, target: "reviewing", actions: assign({recordings: ...status:"uploaded", attempt: event.output.attempt}) },
            { target: "noVoice", actions: assign(...) } ] } }
```
Đổi: `onDone` luôn -> `reviewing` (lưu `event.output` ScoreResult vào context.recordings/lastResult), thêm `onError` với guard `isApiError(code==="no_speech")` -> `noVoice`, lỗi khác -> trạng thái lỗi (D-08, toast + Thử lại, giữ bản ghi). Không đổi hình dạng machine. Test: `lib/player/playerMachine.test.ts` có helper `ack(segmentIndex, attempt, voiced)` và `fromPromise` giả (dòng 25-40) -> thay bằng helper `scoreResult(...)`; `fixtures/ScoreResult.json` làm dữ liệu mẫu.

### `scoreLevel()` — `apps/web/lib/scoreLevel.ts` (hoặc `packages/contracts`)
Analog: `apps/web/lib/lessonView.ts` (hàm thuần + hằng + `lessonView.test.ts` cùng thư mục, vitest). Quy tắc theo `docs/design/tokens.md`: đỏ < 60, vàng 60-79, xanh >= 80. Mọi màu điểm đi qua hàm này (cả chấm màu `TranscriptList`, D-11). Đã có `lib/tokens.test.ts` kiểm token — đối chiếu khi thêm.

### Component mới: `ScoreHero.tsx`, `TipList.tsx`, `IntonationChart.tsx`

**Analog:** `apps/web/components/AttemptStrip.tsx`: `"use client"`, props interface có JSDoc tiếng Việt, shadcn `Button` từ `@/components/ui/button`, `toast` từ `sonner`, `releaseFocusOnPointerUp` từ `@/lib/player/useShortcuts`, import contract type từ `@shadowenglab/contracts`.
```tsx
"use client";
import { Button } from "@/components/ui/button";
import { ApiRequestError } from "@/lib/api";
import { queryKeys } from "@/lib/queries";
interface AttemptStripProps { lessonId: string; ... }
export function AttemptStrip({ ... }: AttemptStripProps) { ... }
```
Props nhận `ScoreResult` đã Zod-validate (không `any`). Skeleton "đang chấm": `components/ui/skeleton.tsx`. Tip rỗng -> câu nhận xét sinh client theo `scoreLevel(overall)` (D-15). Không tô chip khi `scores.sound === null` (D-06); ẩn PhonemeDiff/điểm dưới từ (D-07). Spec chi tiết: `docs/design/components.md`, `03-UI-SPEC.md`.

**CẢNH BÁO:** `recharts` KHÔNG có trong `apps/web/package.json` (grep rỗng) và không có `node_modules/recharts`. Dù stack khoá Recharts, cần thêm dependency (pnpm) và lockfile; không có analog Recharts nào trong repo -> xem "No Analog".

## Shared Patterns

### Lỗi API (server)
**Source:** `services/audio/src/audio_service/errors.py` (`ApiErrorException(status, code, message)`), dùng ở `attempts.py`. Thông điệp tiếng Việt, không lộ đường dẫn/chi tiết lỗi nội bộ. **Apply:** router attempts/scoring, mã `no_speech`.

### Dọn file tạm
`workdir = Path(tempfile.mkdtemp(dir=tmp_dir()))` ... `finally: shutil.rmtree(workdir, ignore_errors=True)` (`attempts.py`). **Apply:** mọi đường chấm.

### Ghi file nguyên tử (cache npz bù D-03)
`.part` rồi `os.replace` (`_store_eval_clip`) và `contract_io.write_json_atomic`. **Apply:** ghi lại `seg/NNNN.npz` khi bù feature lười; kiểm tra `pipeline.analyze_segment` (~dòng 518) cách ghi `np.savez` hiện có và giữ nguyên key cũ (`f0_hz`, `energy`, `ppg`, `f0_hop_s`, `ppg_fps`, cửa sổ).

### Contract-first
Sửa Zod -> `make contracts` -> commit file sinh -> `make test` (drift gate). Không sửa tay `contracts_gen.py`. Dựng pydantic từ dict camelCase bằng `Model.model_validate`.

### Thời gian
`timingMs` (record string->number) từ `lesson` có `StepTimer` ở pipeline (`analyze_segment(..., timer: StepTimer)`); đọc `lesson/jobs.py`/`pipeline.py` để dùng lại cách đo, ghi cả bước bù lười.

### Model gate
Phase 3 KHÔNG nạp model khi chấm (D-01, D-18): không đụng `model_gate`, `load_ppg_model`.

### Test
Python: pytest, fixture `tmp_path`/`monkeypatch` (`test_db.py:15`), API test dùng client trong `tests/conftest.py` + `test_attempts_api.py`; vitest node env cho lib (`*.test.ts` cạnh file nguồn).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `apps/web/components/IntonationChart.tsx` | component | render | Chưa có biểu đồ Recharts và chưa cài recharts; dùng `03-RESEARCH.md` + `docs/design/components.md` |
| `scoring/align.py` DTW MFCC | utility | transform | Chưa có DTW/MFCC trong repo; dùng RESEARCH (kiểm thư viện có trong `pyproject.toml`: parselmouth, numpy, torch; librosa/scipy chưa xác nhận) |
| `rules/thresholds.py` | config | n/a | Chưa có file ngưỡng có version; `models.py` chỉ là analog gần về hằng/version |

## Metadata

**Analog search scope:** `services/audio/src/audio_service`, `services/audio/tests`, `packages/contracts`, `scripts`, `apps/web/{lib,components}`
**Pattern extraction date:** 2026-10-08
