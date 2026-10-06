# 0003 · Contract P0, toolchain Zod → JSON Schema → pydantic, model và môi trường

Ngày: 2026-10-06 · Trạng thái: Chấp nhận · Người quyết: Liam

## Bối cảnh

P0 dựng monorepo, chốt `packages/contracts`, FastAPI skeleton và chứng minh pipeline tạo bài chạy đầu–cuối bằng script. Contract chốt ở Discuss lệch so với bản nháp trong `docs/product.md` mục 3–4 (thêm `scores`, đổi `status` của từ, `refMs`/`userMs`, union `issues`, `source` của tip, metadata lượt chấm), nên theo CLAUDE.md phải ghi lại bằng ADR và sửa `product.md` trong cùng PR (D-27).

ADR này gom mọi quyết định của phase: D-01..D-27 từ `01-CONTEXT.md`, 10 mục mở Liam đã chốt ở plan 01-01 (bản ghi: `.planning/phases/01-p0-n-n-t-ng/01-01-SUMMARY.md`, "Quyết định đã chốt") và các chi tiết hiện thực lệch hoặc làm rõ trong 01-02..01-08. Tên field cụ thể trong `data` của từng mã lỗi và vài ràng buộc số là đề xuất ở mức shape, Liam được xem lại ở PR contract.

## Quyết định

Các mục "mục N" là 10 mục mở của 01-01; Liam trả lời "recommended" cho mục 1–9 và tự cung cấp URL ở mục 10.

1. **Quy ước chung của contract**
   - **D-01:** mốc thời gian (`start`, `end`) là giây float tính từ đầu video gốc; độ dài khoảng lặng/đệm là ms nguyên (`refMs`, `userMs`, `padMs`, `endExtraMs`).
   - **D-02:** JSON qua ranh giới là camelCase; Python đặt tên snake_case và map bằng alias. Theo mục 2, thay vì `alias_generator=to_camel` lúc chạy, `datamodel-code-generator` sinh `Field(alias="camelCase")` tường minh cho từng field cùng `populate_by_name=True`, cho kết quả tương đương và đọc được trong diff. Bảng SQL của app eval (`clips`, `labels`) vẫn snake_case, việc map nằm ở tầng app eval/export.
   - **D-03:** điểm số là float 0..1; web `scoreLevel()` nhân 100 rồi áp ngưỡng đỏ < 60, vàng 60–79, xanh ≥ 80.

2. **Lesson / Segment / Word**
   - **D-04:** `Word` có đủ field ngay từ P0 (`ipa`, `refConfidence`, `prominence` là optional). Mục 4: `Word.i` là chỉ số trong segment chứa nó, bắt đầu từ 0. Mục 5: `Word.prominence` để trống ở P0, Phase 3 tính.
   - **D-05:** `Segment` giữ mốc gốc chưa đệm; đệm và "Mất chữ cuối?" lưu riêng (`endExtraMs` mặc định 0). Đoạn thực tế = `[start − padMs, end + padMs + endExtraMs]`, kẹp trong `[0, durationSec]`.
   - **D-06:** trạng thái job nằm trong `Lesson` (8 trạng thái từ `queued` đến `failed`, kèm `error {step, message}`), không có contract Job riêng. `padMs` mặc định 150.
   - **D-07:** nhiều bài trên một video: `lessonId` là ulid riêng kèm `videoId` + `range`; file tải về và output Demucs cache theo `videoId`.
   - **D-08:** feature bản gốc (PPG, F0, energy) nằm ngoài contract, lưu theo quy ước `DATA_DIR/videos/{videoId}/…` và `DATA_DIR/lessons/{lessonId}/{lesson.json, seg/NNNN.npz}`.
   - **D-09:** nhãn `audioQuality` tính từ tỉ lệ công suất `no_vocals` / `vocals` của Demucs. Mục 7 (tạm thời, Liam duyệt lại sau): `music` khi tỉ lệ > 10^(−15/10) ≈ 0.0316 (trên −15 dB), ngược lại `clean`; đúng ngưỡng là `clean`.
   - Mục 9, cận của contract: seconds ≥ 0; ms là số nguyên ≥ 0; điểm/tỷ lệ/xác suất trong [0,1]; index là số nguyên ≥ 0; `attempt` là số nguyên ≥ 1.

3. **ScoreResult**
   - **D-10:** thêm khối `scores {overall, sound | null, intonation, rhythm}`; công thức gộp do P2 và P4 quyết.
   - **D-11:** `words[].status` ∈ `scored | missing | ref_unclear`; màu chip suy từ `similarity` qua `scoreLevel()`.
   - **D-12:** `issues` là `discriminatedUnion("code", …)` với `data` riêng cho từng mã trong 7 mã (`STRESS_MISMATCH`, `EXTRA_PAUSE`, `FINAL_CONTOUR`, `FLAT_PITCH`, `PITCH_DEVIATION`, `PHONE`, `WORD_MISSING`); `IssueCode` là enum export riêng. Thêm rule mới nghĩa là sửa contract.
   - **D-13:** `prosody.contour {ref, user, wordBounds}` trên trục thời gian chuẩn hoá chung, frame không hữu thanh là `null`; `pauses[]` dùng `refMs`/`userMs`.
   - **D-14:** `tips[] {text, issueRef, source: template | llm}`; UI chỉ hiện nhãn "AI" khi `source === "llm"`.
   - **D-15:** metadata lượt chấm: `lessonId`, `segmentIndex`, `attempt`, `mode` (`full | intonationOnly`), `versions {scorer, thresholds}`, `timingMs`.
   - Tinh chỉnh kiểu ở 01-05 (không thêm/bớt field hay mã nào): `StressMismatchData.refWord`/`userWord` là chữ của từ (string), không phải index; `timingMs` là `Record<string, number ≥ 0>`; `WordMissingData` là object rỗng; `Contour.ref`/`user` không ràng buộc độ dài hay thứ tự của `wordBounds`.

4. **Label và ClipManifest**
   - **D-16:** `Label {clipId, raterId, overall 1..5, wordFlags[], finalContourMatch, unsure, note?, durationMs, createdAt}`; chỉ lưu từ có cờ, `wordIndex` khớp `ClipManifest.words[].i`; map sang cột SQL `word_flags jsonb`.
   - **D-17:** `ClipManifest` giữ bản nháp product.md mục 4 (`i` nguyên ≥ 0, `gold` mặc định `none`), `systemScore?` nằm trong [0,1].

5. **Toolchain contract (Zod → JSON Schema → pydantic)**
   - **D-18:** Zod v4 (4.6.5, khoá chính xác), sinh JSON Schema bằng `z.toJSONSchema()` có sẵn (draft 2020-12, union rời thành `oneOf`); mọi object có `.meta({ id })` để `$defs` ổn định. Không thêm `zod-to-json-schema`. Mục 3: một bundle duy nhất `packages/contracts/schema/contracts.schema.json` với `$defs` dùng chung.
   - **D-19:** JSON Schema sinh ra được commit để Liam review diff ở ranh giới và Python không cần Node để đọc.
   - **D-20:** pydantic v2 sinh tự động bằng `datamodel-code-generator` ghim `==0.83.0` ra `services/audio/src/audio_service/contracts_gen.py` (có header "GENERATED … không sửa tay"). Cờ: `--output-model-type pydantic_v2.BaseModel --target-python-version 3.11 --snake-case-field --use-annotated --use-union-operator --use-standard-collections --allow-population-by-field-name --strict-nullable --enum-field-as-literal all --skip-root-model --disable-timestamp --formatters ruff-format`. Cửa sinh duy nhất là `make contracts` (`scripts/contracts_gen.sh`). `make test` chạy drift gate (`scripts/contracts_check.sh`) sinh lại vào thư mục tạm và thoát 1 kèm "CONTRACT DRIFT" khi lệch bản đã commit.
   - **D-21:** test round-trip bắt buộc: Zod → JSON → JSON Schema → pydantic → dump (`by_alias`, `exclude_unset`) → Zod, bằng nhau, trên mọi fixture trong `packages/contracts/fixtures/` và test biên cho cùng kết luận ở cả ba bên.

6. **Model, setup và ngân sách thời gian**
   - **D-22:** transcribe bằng `mlx-community/whisper-large-v3-turbo` (mlx-whisper, `word_timestamps=True`). Đổi model cần Liam duyệt.
   - **D-23:** tách giọng bằng Demucs `htdemucs` chạy MPS (CPU khi MPS lỗi). Mục 8: chạy trong tiến trình qua `demucs.api.Separator` với `shifts=0`, `overlap=0.25`, `split=True`; `no_vocals` là tổng các stem không phải `vocals`. Trọng số được nạp bằng `hf://htdemucs` (không bao giờ dùng `htdemucs` trần, vì demucs 4.1.0 âm thầm rơi về repo AWS cũ khi HF lỗi; ghi nhận ở 01-03 và 01-06).
   - **D-24:** PPG bằng `facebook/wav2vec2-lv-60-espeak-cv-ft`, chỉ tải các file cần cho `Wav2Vec2ForCTC` và feature extractor.
   - **D-25:** `make setup` chỉ kiểm tra và hướng dẫn system dependency (`scripts/check_deps.sh`: macOS Apple Silicon, ffmpeg, espeak-ng, uv, pnpm, Node ≥ 22.13): thiếu thì in lệnh cài rồi thoát 1, không tự cài. Sau đó cài từ lockfile (`--frozen`) và `audio_service.setup_models` tải/xác minh ba model, parselmouth, ffmpeg, MPS.
   - **D-26:** nếu smoke video 5 phút vượt 5 phút thì được tối ưu phần không phải model. Đo thực tế ở 01-08: video 308 s (range 0–300 s) xử lý trong 125.3 s và 115.8 s từ `DATA_DIR` rỗng (ngân sách 300 s). Không knob D-26 nào được đổi: `pipeline.py`, `features.py`, `separate.py`, `models.py` giữ nguyên.

7. **Môi trường và công cụ (mục 1 và các lựa chọn hiện thực)**
   - Mục 1: Node ≥ 22.13 và pnpm 11.9.0 (`packageManager` ghim chính xác), thay cho "Node 20+" của bản nháp. Máy hiện tại: Node 24.16.0, uv 0.12.10.
   - pnpm 11: `trustPolicy: off` và `allowBuilds: { esbuild: true }` trong `pnpm-workspace.yaml` (chỉ `esbuild` chạy install script; `fsevents` có khai báo `node-gyp rebuild` nhưng không được cho phép).
   - Python: build backend `uv_build`; `[tool.uv] environments` giới hạn macOS arm64; `yt-dlp[default,deno]` (yt-dlp cần JS runtime để giải mã YouTube); ruff `line-length = 100`, loại `contracts_gen.py` khỏi lint.
   - TypeScript `~5.9.3`; ESLint 9 flat config (`eslint.config.mjs`) không dùng `@next/eslint-plugin-next` (crash với ESLint 9); `next build` bỏ qua ESLint (`eslint.ignoreDuringBuilds`), lint chạy bằng `make lint`.
   - Makefile viết cho GNU Make 3.81 của macOS: không dùng `-O`, `.ONESHELL`, `$(file)`; `make dev` là `$(MAKE) -j2 dev-api dev-web`, FastAPI chỉ bind `127.0.0.1`. `make lint` có một cách gọi duy nhất cho ruff: chạy từ `services/audio` (`ruff check/format --check --config pyproject.toml . ../../scripts`).
   - `scripts/dev_smoke.sh` kiểm tra tự động `make dev` (hai cổng 8000/3000 cùng lên, một SIGTERM tới process group dừng cả hai) và `make smoke` kiểm tra pipeline tạo bài; hai lệnh này là cổng kiểm tra tự động của P0.
   - Video smoke: `https://www.youtube.com/watch?v=dUDi-F6eAvk` (mục 10), lưu ở `scripts/smoke_video.url`.

8. **`/health` (mục 6):** là model riêng của Python `{status: "ok", service: "audio", version}`, không thuộc `packages/contracts`.

9. **D-27:** PR contract cập nhật `docs/product.md` mục 3–4 (và danh sách contract ở mục 5) cho khớp contract đã chốt, đồng thời thêm ADR này.

**Phân chia nguồn sự thật:** kiểu dữ liệu nằm ở `packages/contracts` (Zod). `docs/product.md` chỉ tóm tắt shape cho người đọc; khi hai nơi lệch nhau thì `packages/contracts` đúng và `product.md` phải sửa.

## Lý do

- Contract-first: đổi shape sau này phải đi qua Liam và qua diff schema đã commit, nên một bundle JSON Schema và pydantic sinh tự động (D-18..D-20) giữ Zod, JSON Schema và Python không thể lệch âm thầm; drift gate nằm trong `make test`.
- Alias tường minh trong code sinh (mục 2) cho cùng wire format như `alias_generator` nhưng diff của `contracts_gen.py` cho thấy từng field.
- Chuẩn hoá đơn vị (giây float, ms nguyên, điểm 0..1) một lần ở contract tránh mỗi consumer (web, FastAPI, eval) tự đoán.
- Node ≥ 22.13 / pnpm 11.9.0 theo toolchain đã resolve và được duyệt lockfile ở 01-01; ghim chính xác để `make setup` lặp lại được.
- Ngân sách 5 phút còn dư lớn (115.8–125.3 s), nên không cần tối ưu hay đổi model ở P0.

## Hệ quả và rủi ro

- Mọi thay đổi shape phải sửa Zod, chạy `make contracts`, commit schema và `contracts_gen.py`, rồi `make test`; Liam duyệt contract trước khi merge.
- `data` của từng mã lỗi và vài ràng buộc số (liệt kê ở mục 3) là đề xuất ở mức shape, có thể tinh chỉnh khi Liam review PR contract; không được thêm hay bớt mã lỗi.
- Ngưỡng `nonVocalRatio` (−15 dB) là tạm thời. Phase 5 sẽ bổ sung tỉ lệ `ref_unclear` để hiệu chỉnh nhãn.
- Ngưỡng tách câu (3–8 s, mảnh < 1.5 s thì gộp) là giá trị khởi đầu. Trên video smoke 5 phút có 62 segment, trung bình 3.03 s và 39 segment ngắn hơn 3 s; cần Liam nghe và quyết trước khi dùng cho P1.
- Drift gate tạo thư mục tạm `services/audio/.contracts-check.*` (nằm trong `services/audio` để ruff đọc đúng cấu hình) và xoá khi thoát; nếu gate bị ngắt giữa chừng thư mục này có thể còn lại và chưa nằm trong `.gitignore`.
- Phụ thuộc vào `yt-dlp` và YouTube: yt-dlp có thể hỏng khi YouTube đổi; cập nhật định kỳ theo lockfile đã duyệt.
- Nền tảng chỉ macOS Apple Silicon (mlx-whisper, MPS); `check_deps.sh` từ chối nền tảng khác.
