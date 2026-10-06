# packages/contracts — Zod schema dùng chung

Nguồn sự thật cho mọi kiểu dữ liệu giữa Next.js, FastAPI và app eval. Viết bằng Zod 4 (`zod` 4.6.5), JSON qua ranh giới là camelCase (D-02).

## Có gì

`src/index.ts` export sáu kiểu qua `Schemas` (thứ tự: `Segment`, `Lesson`, `ScoreResult`, `IssueCode`, `ClipManifest`, `Label`), cùng các kiểu lồng nhau:

| File | Nội dung |
| --- | --- |
| `src/common.ts` | primitive dùng chung: `Seconds`, `Milliseconds`, `Score01`, `Probability`, `IsoTimestamp` |
| `src/lesson.ts` | `Word`, `Segment`, `TimeRange`, `AudioQuality`, `LessonError`, `LessonStatus`, `Lesson` |
| `src/score.ts` | `IssueCode`, bảy `*Issue` + `Issue` (union theo `code`), `WordScore`, `Contour`, `Prosody`, `Scores`, `Tip`, `Versions`, `ScoreResult` |
| `src/eval.ts` | `WordFlags`, `Label`, `ClipWord`, `ClipManifest` |
| `src/generate.ts` | sinh `schema/contracts.schema.json` từ `Schemas` |
| `src/cli-parse.ts` | đọc JSON từ stdin, parse bằng `Schemas[name]`, in JSON ra stdout; test Python gọi nó để Zod làm một đầu của vòng round-trip |
| `schema/contracts.schema.json` | JSON Schema 2020-12 sinh ra, **được commit** |
| `fixtures/<Type>.json` | mảng `{ name, data }` cho round-trip (`ScoreResult`, `Lesson`, `Label`, `ClipManifest`) |

Mọi object contract có `.meta({ id })` để `$defs` có tên ổn định (không có `__schemaN`).

## Đổi contract

Contract do Liam chốt: đổi shape phải được Liam duyệt, không tự đổi (xem `CLAUDE.md`). Quy trình khi đã được duyệt:

1. Sửa `src/*.ts`; thêm hoặc sửa fixture trong `fixtures/<Type>.json`.
2. `make contracts` sinh lại `schema/contracts.schema.json` và `services/audio/src/audio_service/contracts_gen.py` (pydantic v2, file sinh tự động, không sửa tay).
3. Commit cả hai file sinh cùng thay đổi Zod.
4. `make test`: drift gate (`scripts/contracts_check.sh`) sinh lại vào thư mục tạm và thoát 1 với "CONTRACT DRIFT" nếu lệch bản đã commit; sau đó vitest và pytest, trong đó có test round-trip Zod → JSON Schema → pydantic → Zod trên mọi fixture (`services/audio/tests/test_contracts_roundtrip.py`).
5. Đổi shape lệch `docs/product.md` mục 3–4 thì sửa `product.md` trước và thêm ADR trong `docs/decisions/`.

## Lệnh

```bash
make contracts                                  # sinh lại JSON Schema + pydantic
pnpm --filter @shadowenglab/contracts test      # chỉ vitest của package này
```

`apps/web` và `apps/eval` import `@shadowenglab/contracts` qua `transpilePackages` (package chỉ có TypeScript nguồn, không có bước build).
