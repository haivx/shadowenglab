---
phase: 01-p0-n-n-t-ng
plan: 01
subsystem: infra
tags: [pnpm, uv, workspace, lockfile, supply-chain, zod, next, fastapi, demucs]

requires: []
provides:
  - "10 quyết định mở của P0 đã chốt (bảng bên dưới) — các plan 01-02..01-09 đọc từ đây"
  - "pnpm workspace (apps/web, apps/eval, packages/contracts) + uv project services/audio (Python 3.11, macOS arm64)"
  - "pnpm-lock.yaml và services/audio/uv.lock đã resolve và được Liam duyệt trước khi cài bất kỳ package nào"
affects: [01-02, 01-03, 01-04, 01-05, 01-06, 01-07, 01-08, 01-09]

actuals:
  tokens: 28000
  tasks: 3
  commits: 1
plan_head_before: 4e8bb95fb96d646477d896b273b2bff6cc485f6d
plan_head_after: 0a3639324bb8986322670c75f11f711b8e5abcd5

tech-stack:
  added: [pnpm 11.9.0, zod 4.6.5, next 14.2.35, react 18.3.1, vitest 4.1.11, tsx 4.23.15, typescript 5.9.3, eslint 9.39.5, typescript-eslint 8.71.0, prettier 3.9.9, fastapi 0.142.2, pydantic 2.13.5, demucs 4.1.0, mlx-whisper 0.4.3, torch 2.14.1, transformers 5.18.0, praat-parselmouth 0.4.7, yt-dlp 2026.8.19, datamodel-code-generator 0.83.0, ruff 0.16.10, pytest 9.1.1, uv_build]
  patterns:
    - "Lockfile-first: resolve (--lockfile-only / uv lock) -> human review -> install --frozen"
    - "Manifest khai báo đủ dependency cho cả phase; plan sau không thêm package"

key-files:
  created:
    - package.json
    - pnpm-workspace.yaml
    - pnpm-lock.yaml
    - packages/contracts/package.json
    - apps/web/package.json
    - apps/eval/package.json
    - services/audio/pyproject.toml
    - services/audio/src/audio_service/__init__.py
    - services/audio/uv.lock
  modified: []

key-decisions:
  - "Toolchain: Node >= 22.13 + pnpm 11.9.0, trustPolicy: off, allowBuilds { esbuild: true }"
  - "pydantic alias: Field(alias=camelCase) sinh tường minh + populate_by_name=True"
  - "Schema: một bundle contracts.schema.json với $defs dùng chung"
  - "Word.i: chỉ số trong segment, từ 0; Word.prominence để trống ở P0"
  - "/health là model riêng của Python, không thuộc contract"
  - "nonVocalRatio tạm thời: music khi > 10^(-15/10) ~ 0.0316"
  - "Demucs: Separator(model=htdemucs, shifts=0, overlap=0.25, split=True)"
  - "Cận contract: seconds >= 0, ms nguyên >= 0, tỷ lệ/xác suất trong [0,1], index nguyên >= 0, attempt nguyên >= 1"
  - "Video smoke: https://www.youtube.com/watch?v=dUDi-F6eAvk"

requirements-completed: []  # FND-01 chỉ hoàn tất một phần ở plan này (xem Issues Encountered) — plan khai báo requirements: [FND-01]

coverage:
  - id: D1
    description: "Liam chốt 10 quyết định mở của P0 trong một lần dừng; bảng 'Quyết định đã chốt' ghi giá trị cuối từng mục"
    requirement: FND-01
    verification: []
    human_judgment: true
    rationale: "Quyết định sản phẩm/kiến trúc của Liam, ghi lại nguyên văn từ phản hồi; không có test tự động"
  - id: D2
    description: "Workspace manifests + pnpm-lock.yaml + uv.lock resolve nhất quán, chưa cài gì (không có node_modules/, .venv/)"
    requirement: FND-01
    verification:
      - kind: other
        ref: "uv lock --project services/audio --check && grep zod@4.6.5 pnpm-lock.yaml && grep next@14.2.35 pnpm-lock.yaml && test ! -e node_modules && test ! -e services/audio/.venv"
        status: pass
    human_judgment: false
  - id: D3
    description: ".gitignore đã chặn .env, node_modules/, .venv/, .next/, audio, eval/clips/, eval/labels.jsonl"
    requirement: FND-01
    verification:
      - kind: other
        ref: "git check-ignore -q <child path> cho node_modules/x, services/audio/.venv/x, apps/web/.next/x, eval/clips/a.wav, eval/labels.jsonl, clip.mp4"
        status: pass
    human_judgment: false
  - id: D4
    description: "Liam duyệt danh sách package trong cả hai lockfile trước lần cài đầu tiên (package-legitimacy gate T-01-SC)"
    verification: []
    human_judgment: true
    rationale: "Cổng con người có chủ đích: Liam phản hồi 'approved' ngày 2026-10-06"

# Metrics
duration: 17min
completed: 2026-10-06
status: complete
---

# Phase 1 Plan 01: Gate quyết định + lockfile Summary

**pnpm 11 workspace (zod 4.6.5, Next 14.2.35) + uv project Python 3.11 (FastAPI, demucs, mlx-whisper), cả hai lockfile được resolve không cài gì và Liam duyệt trước khi cài, cùng 10 quyết định mở của P0 đã chốt.**

## Performance

- **Duration:** ~17 min (phần chạy của agent kế tục; tính từ 14:50 giờ máy tới 15:07 cho Task 2 + thu thập danh sách; các checkpoint chờ Liam không tính)
- **Started:** 2026-10-06T07:50:00Z
- **Completed:** 2026-10-06T08:08:00Z
- **Tasks:** 3 (Task 1 và 3 là checkpoint của Liam, Task 2 auto)
- **Files modified:** 9 (tất cả là file mới)

## Quyết định đã chốt

Liam phản hồi nguyên văn: `recommended https://www.youtube.com/watch?v=dUDi-F6eAvk`

| # | Mục | Giá trị cuối | Nguồn |
|---|-----|--------------|-------|
| 1 | Toolchain | Node >= 22.13 + pnpm 11.9.0, `trustPolicy: off`, `allowBuilds: { esbuild: true }` (máy: Node v24.16.0, pnpm 11.9.0, uv 0.12.10) | recommended |
| 2 | pydantic alias | Sinh tường minh `Field(alias="camelCase")` từng field + `populate_by_name=True` | recommended |
| 3 | Schema layout | Một bundle `packages/contracts/schema/contracts.schema.json` với `$defs` dùng chung | recommended |
| 4 | `Word.i` | Chỉ số trong segment của nó, bắt đầu từ 0 | recommended |
| 5 | `Word.prominence` | Để trống ở P0 (Phase 3 tính) | recommended |
| 6 | `/health` | Model riêng của Python `{status: "ok", service: "audio", version}`, không phải contract type | recommended |
| 7 | `nonVocalRatio` tạm thời | `music` khi > 10^(−15/10) ≈ 0.0316 (trên −15 dB), ngược lại `clean` | recommended |
| 8 | Demucs | `demucs.api.Separator(model="htdemucs", shifts=0, overlap=0.25, split=True)`, `no_vocals` = tổng các stem không phải vocals | recommended |
| 9 | Cận contract | seconds >= 0; ms là số nguyên >= 0; điểm/tỷ lệ/xác suất trong [0,1]; index là số nguyên >= 0; `attempt` là số nguyên >= 1 | recommended |
| 10 | URL video smoke | https://www.youtube.com/watch?v=dUDi-F6eAvk | Liam |

## Phê duyệt lockfile (package-legitimacy gate, T-01-SC)

Liam phản hồi `approved` ngày 2026-10-06 sau khi xem hai danh sách bên dưới (node_modules/ và .venv/ chưa tồn tại tại thời điểm duyệt). Các ghi chú Liam đã biết và chấp nhận:

- Chỉ `esbuild@0.28.2` chạy install script (`node install.js`), được cho phép qua `allowBuilds`.
- `fsevents@2.3.3` (optional, chỉ macOS, kéo vào qua tsx/vite) khai báo `node-gyp rebuild` trong metadata registry nhưng pnpm không gắn cờ và không được thêm vào `allowBuilds`.
- Cảnh báo deprecated của `eslint@9.39.5` được giữ có chủ đích (Pitfall 2/3: typescript-eslint chưa hỗ trợ eslint 10).

Packages có install script (nguồn: scripts.txt):

```
esbuild@0.28.2 => "node install.js"
fsevents@2.3.3 => scripts.install "node-gyp rebuild", gypfile true (không chạy, không trong allowBuilds)
```

### Danh sách package Python (uv export --frozen --no-hashes --no-emit-project, 93 mục)

```
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.15.1
argcomplete==3.7.2
attrs==26.1.0
black==26.10.0
brotli==1.2.0
brotlicffi==1.2.0.2
certifi==2026.7.22
cffi==2.1.1
charset-normalizer==3.5.2
click==8.5.0
datamodel-code-generator==0.83.0
demucs==4.1.0
deno==2.9.7
einops==0.8.2
fastapi==0.142.2
filelock==4.0.12
fsspec==2026.9.0
genson==1.4.0
h11==0.16.0
hf-xet==1.6.0
httpcore==1.0.9
httpx==0.28.1
huggingface-hub==1.33.0
idna==3.20
inflect==7.5.0
iniconfig==2.3.0
isort==8.0.1
jinja2==3.1.6
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
julius==0.2.8
lameenc==1.8.4
llvmlite==0.50.0
markdown-it-py==4.2.0
markupsafe==3.0.4
mdurl==0.1.2
mlx==0.32.3
mlx-metal==0.32.3
mlx-whisper==0.4.3
more-itertools==11.1.0
mpmath==1.3.0
mutagen==1.48.1
mypy-extensions==1.1.0
networkx==3.6.1
numba==0.68.0
numpy==2.4.6
opentelemetry-api==1.45.0
packaging==26.3
pathspec==1.1.1
platformdirs==4.12.3
pluggy==1.6.0
praat-parselmouth==0.4.7
pycparser==3.0
pycryptodomex==3.24.0
pydantic==2.13.5
pydantic-core==2.46.5
pydantic-settings==2.15.0
pygments==2.21.0
pytest==9.1.1
python-dotenv==1.2.4
python-ulid==4.0.1
pytokens==0.4.1
pyyaml==6.0.3
referencing==0.37.0
regex==2026.9.29
requests==2.34.2
rich==15.0.0
rpds-py==2026.9.1
ruff==0.16.10
safetensors==0.8.0
scipy==1.17.1
setuptools==84.0.0
shellingham==1.5.4
soundfile==0.14.0
sphn==0.2.1
starlette==1.7.0
sympy==1.14.0
tiktoken==0.14.0
tokenizers==0.23.2
torch==2.14.1
tqdm==4.70.1
transformers==5.18.0
typeguard==4.6.0
typer==0.27.2
typing-extensions==4.16.0
typing-inspection==0.4.4
urllib3==2.8.0
uvicorn==0.54.0
websockets==17.2
yt-dlp==2026.8.19
yt-dlp-ejs==0.8.0
```

### Danh sách package JS (khoá `packages:` của pnpm-lock.yaml, 272 mục)

```
@babel/code-frame@7.29.7
@babel/compat-data@7.29.7
@babel/core@7.29.7
@babel/generator@7.29.8
@babel/helper-compilation-targets@7.29.7
@babel/helper-globals@7.29.7
@babel/helper-module-imports@7.29.7
@babel/helper-module-transforms@7.29.7
@babel/helper-string-parser@7.29.7
@babel/helper-validator-identifier@7.29.7
@babel/helper-validator-option@7.29.7
@babel/helpers@7.29.7
@babel/parser@7.29.9
@babel/template@7.29.7
@babel/traverse@7.29.8
@babel/types@7.29.8
@esbuild/aix-ppc64@0.28.2
@esbuild/android-arm64@0.28.2
@esbuild/android-arm@0.28.2
@esbuild/android-x64@0.28.2
@esbuild/darwin-arm64@0.28.2
@esbuild/darwin-x64@0.28.2
@esbuild/freebsd-arm64@0.28.2
@esbuild/freebsd-x64@0.28.2
@esbuild/linux-arm64@0.28.2
@esbuild/linux-arm@0.28.2
@esbuild/linux-ia32@0.28.2
@esbuild/linux-loong64@0.28.2
@esbuild/linux-mips64el@0.28.2
@esbuild/linux-ppc64@0.28.2
@esbuild/linux-riscv64@0.28.2
@esbuild/linux-s390x@0.28.2
@esbuild/linux-x64@0.28.2
@esbuild/netbsd-arm64@0.28.2
@esbuild/netbsd-x64@0.28.2
@esbuild/openbsd-arm64@0.28.2
@esbuild/openbsd-x64@0.28.2
@esbuild/openharmony-arm64@0.28.2
@esbuild/sunos-x64@0.28.2
@esbuild/win32-arm64@0.28.2
@esbuild/win32-ia32@0.28.2
@esbuild/win32-x64@0.28.2
@eslint-community/eslint-utils@4.10.1
@eslint-community/regexpp@4.12.2
@eslint/config-array@0.21.2
@eslint/config-helpers@0.4.2
@eslint/core@0.17.0
@eslint/eslintrc@3.3.7
@eslint/js@9.39.5
@eslint/object-schema@2.1.7
@eslint/plugin-kit@0.4.1
@humanfs/core@0.19.2
@humanfs/node@0.16.8
@humanfs/types@0.15.0
@humanwhocodes/module-importer@1.0.1
@humanwhocodes/retry@0.4.3
@jridgewell/gen-mapping@0.3.13
@jridgewell/remapping@2.3.5
@jridgewell/resolve-uri@3.1.2
@jridgewell/sourcemap-codec@1.6.0
@jridgewell/trace-mapping@0.3.31
@next/env@14.2.35
@next/swc-darwin-arm64@14.2.33
@next/swc-darwin-x64@14.2.33
@next/swc-linux-arm64-gnu@14.2.33
@next/swc-linux-arm64-musl@14.2.33
@next/swc-linux-x64-gnu@14.2.33
@next/swc-linux-x64-musl@14.2.33
@next/swc-win32-arm64-msvc@14.2.33
@next/swc-win32-ia32-msvc@14.2.33
@next/swc-win32-x64-msvc@14.2.33
@oxc-project/types@0.152.0
@rolldown/binding-android-arm-eabi@1.2.12
@rolldown/binding-android-arm64@1.2.12
@rolldown/binding-darwin-arm64@1.2.12
@rolldown/binding-darwin-x64@1.2.12
@rolldown/binding-freebsd-x64@1.2.12
@rolldown/binding-linux-arm-gnueabihf@1.2.12
@rolldown/binding-linux-arm64-gnu@1.2.12
@rolldown/binding-linux-arm64-musl@1.2.12
@rolldown/binding-linux-ppc64-gnu@1.2.12
@rolldown/binding-linux-s390x-gnu@1.2.12
@rolldown/binding-linux-x64-gnu@1.2.12
@rolldown/binding-linux-x64-musl@1.2.12
@rolldown/binding-openharmony-arm64@1.2.12
@rolldown/binding-win32-arm64-msvc@1.2.12
@rolldown/binding-win32-x64-msvc@1.2.12
@rolldown/pluginutils@1.0.1
@standard-schema/spec@1.1.0
@swc/counter@0.1.3
@swc/helpers@0.5.5
@types/chai@5.2.3
@types/deep-eql@4.0.2
@types/estree@1.0.9
@types/json-schema@7.0.15
@types/node@22.20.5
@types/prop-types@15.7.15
@types/react-dom@18.3.7
@types/react@18.3.31
@typescript-eslint/eslint-plugin@8.71.0
@typescript-eslint/parser@8.71.0
@typescript-eslint/project-service@8.71.0
@typescript-eslint/scope-manager@8.71.0
@typescript-eslint/tsconfig-utils@8.71.0
@typescript-eslint/type-utils@8.71.0
@typescript-eslint/types@8.71.0
@typescript-eslint/typescript-estree@8.71.0
@typescript-eslint/utils@8.71.0
@typescript-eslint/visitor-keys@8.71.0
@vitest/expect@4.1.11
@vitest/mocker@4.1.11
@vitest/pretty-format@4.1.11
@vitest/runner@4.1.11
@vitest/snapshot@4.1.11
@vitest/spy@4.1.11
@vitest/utils@4.1.11
acorn-jsx@5.3.2
acorn@8.18.0
ajv@6.15.0
ansi-styles@4.3.0
argparse@2.0.1
assertion-error@2.0.1
balanced-match@1.0.2
balanced-match@4.0.4
baseline-browser-mapping@2.11.27
brace-expansion@1.1.21
brace-expansion@5.0.12
browserslist@4.29.3
busboy@1.6.0
callsites@3.1.0
caniuse-lite@1.0.30001814
chai@6.3.0
chalk@4.1.2
client-only@0.0.1
color-convert@2.0.1
color-name@1.1.4
concat-map@0.0.1
convert-source-map@2.0.0
cross-spawn@7.0.6
csstype@3.2.3
debug@4.4.3
deep-is@0.1.4
detect-libc@2.1.2
electron-to-chromium@1.5.444
es-module-lexer@2.3.2
esbuild@0.28.2
escalade@3.2.0
escape-string-regexp@4.0.0
eslint-config-prettier@10.1.8
eslint-plugin-react-hooks@7.1.1
eslint-scope@8.4.0
eslint-visitor-keys@3.4.3
eslint-visitor-keys@4.2.1
eslint-visitor-keys@5.0.1
eslint@9.39.5
espree@10.4.0
esquery@1.7.0
esrecurse@4.3.0
estraverse@5.3.0
estree-walker@3.0.3
esutils@2.0.3
expect-type@1.4.0
fast-deep-equal@3.1.3
fast-json-stable-stringify@2.1.0
fast-levenshtein@2.0.6
fdir@6.5.0
file-entry-cache@8.0.0
find-up@5.0.0
flat-cache@4.0.1
flatted@3.4.4
fsevents@2.3.3
gensync@1.0.0-beta.2
glob-parent@6.0.2
globals@14.0.0
graceful-fs@4.2.11
has-flag@4.0.0
hermes-estree@0.25.1
hermes-parser@0.25.1
ignore@5.3.2
ignore@7.0.12
import-fresh@3.3.1
imurmurhash@0.1.4
is-extglob@2.1.1
is-glob@4.0.3
isexe@2.0.0
js-tokens@4.0.0
js-yaml@4.3.2
jsesc@3.1.0
json-buffer@3.0.1
json-schema-traverse@0.4.1
json-stable-stringify-without-jsonify@1.0.1
json5@2.2.3
keyv@4.5.4
levn@0.4.1
lightningcss-android-arm64@1.33.0
lightningcss-darwin-arm64@1.33.0
lightningcss-darwin-x64@1.33.0
lightningcss-freebsd-x64@1.33.0
lightningcss-linux-arm-gnueabihf@1.33.0
lightningcss-linux-arm64-gnu@1.33.0
lightningcss-linux-arm64-musl@1.33.0
lightningcss-linux-x64-gnu@1.33.0
lightningcss-linux-x64-musl@1.33.0
lightningcss-win32-arm64-msvc@1.33.0
lightningcss-win32-x64-msvc@1.33.0
lightningcss@1.33.0
locate-path@6.0.0
lodash.merge@4.6.2
loose-envify@1.4.0
lru-cache@5.1.1
magic-string@0.30.21
minimatch@10.2.6
minimatch@3.1.5
ms@2.1.3
nanoid@3.3.19
natural-compare@1.4.0
next@14.2.35
node-releases@2.0.57
obug@2.2.1
optionator@0.9.4
p-limit@3.1.0
p-locate@5.0.0
parent-module@1.0.1
path-exists@4.0.0
path-key@3.1.1
pathe@2.0.3
picocolors@1.1.1
picomatch@4.0.7
postcss@8.4.31
postcss@8.5.28
prelude-ls@1.2.1
prettier@3.9.9
punycode@2.3.1
react-dom@18.3.1
react@18.3.1
resolve-from@4.0.0
rolldown@1.2.12
scheduler@0.23.2
semver@6.3.1
semver@7.8.5
shebang-command@2.0.0
shebang-regex@3.0.0
siginfo@2.0.0
source-map-js@1.2.2
stackback@0.0.2
std-env@4.3.0
streamsearch@1.1.0
strip-json-comments@3.1.1
styled-jsx@5.1.1
supports-color@7.2.0
tinybench@2.9.0
tinyexec@1.3.1
tinyglobby@0.2.17
tinyrainbow@3.2.0
ts-api-utils@2.5.0
tslib@2.8.1
tsx@4.23.15
type-check@0.4.0
typescript-eslint@8.71.0
typescript@5.9.3
undici-types@6.21.0
update-browserslist-db@1.3.3
uri-js@4.4.1
vite@8.3.2
vitest@4.1.11
which@2.0.2
why-is-node-running@2.3.0
word-wrap@1.2.5
yallist@3.1.1
yocto-queue@0.1.0
zod-validation-error@4.0.2
zod@4.6.5
```

## Accomplishments

- 10 quyết định mở của P0 được Liam chốt trong một lần dừng, ghi lại trong bảng trên để mọi plan sau đọc mà không phải hỏi lại.
- Workspace pnpm (3 package) và uv project `audio-service` (Python `>=3.11,<3.12`, chỉ `darwin/arm64`) khai báo đủ dependency cho cả phase.
- `pnpm-lock.yaml` và `services/audio/uv.lock` resolve không cài gì; `uv lock --check` pass, không có `node_modules/` hay `.venv/`.
- Liam duyệt hai danh sách package (package-legitimacy gate T-01-SC) trước lần cài đầu tiên; các plan sau cài bằng `--frozen`.

## Task Commits

1. **Task 1: Liam chốt 10 quyết định mở** — checkpoint:decision, không có commit (kết quả nằm trong bảng ở trên)
2. **Task 2: Manifest workspace + lockfile (không cài gì)** — `0a36393` (chore)
3. **Task 3: Liam duyệt danh sách package** — checkpoint:human-verify, không có commit (Liam `approved` 2026-10-06)

**Plan metadata:** commit `docs(01-01): complete plan summary` (sau commit này) và commit tracking STATE/ROADMAP/REQUIREMENTS.

## Files Created/Modified

- `package.json` — manifest gốc: `packageManager pnpm@11.9.0`, `engines.node >=22.13`, devDependencies lint/format/TS
- `pnpm-workspace.yaml` — globs `apps/*`, `packages/*`; `trustPolicy: off`; `allowBuilds: { esbuild: true }`
- `pnpm-lock.yaml` — lockfile JS đã duyệt
- `packages/contracts/package.json` — `@shadowenglab/contracts`, zod 4.6.5 (exact), vitest, tsx, scripts `test`/`gen`
- `apps/web/package.json`, `apps/eval/package.json` — Next 14.2.35 / React 18.3 (cổng 3000 và 3001)
- `services/audio/pyproject.toml` — uv project audio-service, nhóm `dev`, ruff, pytest, `[tool.uv] environments`
- `services/audio/src/audio_service/__init__.py` — package marker `__version__ = "0.1.0"`
- `services/audio/uv.lock` — lockfile Python đã duyệt (94 package resolve, gồm cả project)

## Decisions Made

Xem bảng "Quyết định đã chốt" — toàn bộ theo khuyến nghị của plan; chỉ mục 10 là giá trị Liam tự cung cấp.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Defect trong bước verify] `git check-ignore` báo "not ignored" cho pattern chỉ-thư-mục chưa tồn tại**
- **Found during:** Task 2 (verify tự động thứ hai)
- **Issue:** Lệnh verify của plan chạy `git check-ignore -q node_modules`, `services/audio/.venv`, `apps/web/.next` trên đường dẫn thư mục chưa tồn tại. Pattern dạng `node_modules/`, `.venv/`, `.next/` chỉ khớp thư mục có thật, nên git trả "not ignored" dù `.gitignore` đúng.
- **Fix:** Kiểm tra bằng đường dẫn con (`node_modules/x`, `services/audio/.venv/x`, `apps/web/.next/x`, `eval/clips/a.wav`, `eval/labels.jsonl`, `clip.mp4`) — tất cả đều bị ignore. Kiểm tra `.env` bị hook chặn đọc secret; xác nhận `.gitignore` dòng 2 là literal `.env`.
- **Files modified:** không (chỉ đổi cách kiểm tra)
- **Verification:** `git check-ignore -q` trả 0 cho cả sáu đường dẫn con
- **Committed in:** không áp dụng

**2. [Quy trình - theo quyết định của Liam] Đổi nhánh sang `gsd/phase-01-p0-n-n-t-ng`**
- **Found during:** commit Task 2
- **Issue:** Executor trước từ chối commit lên `main` (nhánh protected, guard #2924/#3819).
- **Fix:** Liam chọn phương án (b): orchestrator tạo và chuyển sang nhánh `gsd/phase-01-p0-n-n-t-ng` (`git.base-branch --is-protected` trả false). Mọi commit của phase 1 nằm trên nhánh này; không đổi git config.
- **Files modified:** không
- **Committed in:** `0a36393` nằm trên nhánh mới

**3. [Ghi nhận] `pyproject.toml` có thêm trường `description`**
- Trường `description` không có trong đặc tả plan; chỉ là metadata, không ảnh hưởng resolve hay lockfile.

---

**Total deviations:** 3 (1 Rule 1 verify defect, 1 thay đổi quy trình do Liam quyết, 1 ghi nhận nhỏ)
**Impact on plan:** Không ảnh hưởng phạm vi; không có package nào ngoài danh sách được duyệt.

## Issues Encountered

- FND-01 yêu cầu repo "có ESLint, Prettier, ruff và `.gitignore` cấu hình sẵn". Plan này chỉ khai báo dependency và cấu hình ruff trong `pyproject.toml`; file cấu hình ESLint/Prettier và các lệnh chạy do plan sau của phase (Makefile ở 01-08) đảm nhiệm. Vì vậy `requirements-completed` để trống và không đánh dấu FND-01 xong ở đây (cổng shared-ID `requirements.ready-ids` quyết định).
- `fsevents@2.3.3` khai báo `node-gyp rebuild` trong metadata registry nhưng không bị pnpm gắn cờ; Liam đã biết và chấp nhận, không thêm vào `allowBuilds`.

## User Setup Required

None - no external service configuration required. (Prerequisite Node >= 22.13: máy hiện có v24.16.0; README/CLAUDE.md/PROJECT.md được cập nhật ở 01-09.)

## Threat Flags

None - không có bề mặt mạng, auth hay file mới ngoài threat_model của plan (T-01-01, T-01-02, T-01-03, T-01-SC đều đã giảm thiểu như kế hoạch).

## Known Stubs

None.

## Next Phase Readiness

- Quyết định 1–10 và lockfile đã duyệt; 01-02 (tracer: walking skeleton), 01-03, 01-04 có thể chạy song song ở wave kế tiếp và cài bằng `pnpm install --frozen-lockfile` / `uv sync --frozen`.
- Không có blocker.

## Self-Check: PASSED

- Files: package.json, pnpm-workspace.yaml, pnpm-lock.yaml, packages/contracts/package.json, apps/web/package.json, apps/eval/package.json, services/audio/pyproject.toml, services/audio/src/audio_service/__init__.py, services/audio/uv.lock — tất cả FOUND
- Commit `0a36393` là tổ tiên của HEAD (FOUND); `git rev-list --count 4e8bb95..HEAD` = 1
- Acceptance criteria chạy lại: `uv lock --check` exit 0; zod@4.6.5 và next@14.2.35 có trong pnpm-lock.yaml; node_modules/ và services/audio/.venv/ không tồn tại; packageManager `pnpm@11.9.0`, engines `>=22.13`, `trustPolicy: off` + `esbuild: true`, `requires-python = ">=3.11,<3.12"`, `datamodel-code-generator==0.83.0`, `yt-dlp[default,deno]`, `uv_build`, `extend-exclude` đều có mặt
- Ignore: sáu đường dẫn con đều bị ignore; `.gitignore` dòng 2 là `.env`

---
*Phase: 01-p0-n-n-t-ng*
*Completed: 2026-10-06*
