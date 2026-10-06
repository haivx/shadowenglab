#!/bin/sh
# Sinh lại JSON Schema (từ Zod) và pydantic (từ JSON Schema). Đây là cửa duy nhất (make contracts + drift gate).
# Dùng: sh scripts/contracts_gen.sh [schema_dir] [pydantic_file]
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

abspath() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "$(pwd)" "$1" ;;
  esac
}

SCHEMA_DIR=$(abspath "${1:-$ROOT/packages/contracts/schema}")
PYDANTIC_FILE=$(abspath "${2:-$ROOT/services/audio/src/audio_service/contracts_gen.py}")

mkdir -p "$SCHEMA_DIR" "$(dirname -- "$PYDANTIC_FILE")"

pnpm --dir "$ROOT" --filter @shadowenglab/contracts exec tsx src/generate.ts "$SCHEMA_DIR"

# cd vào project Python để ruff-format đọc [tool.ruff] của project (output ổn định).
(
  cd "$ROOT/services/audio"
  uv run --frozen datamodel-codegen \
    --input "$SCHEMA_DIR/contracts.schema.json" \
    --input-file-type jsonschema \
    --output-model-type pydantic_v2.BaseModel \
    --target-python-version 3.11 \
    --snake-case-field \
    --use-annotated \
    --use-union-operator \
    --use-standard-collections \
    --allow-population-by-field-name \
    --strict-nullable \
    --enum-field-as-literal all \
    --skip-root-model \
    --disable-timestamp \
    --custom-file-header "# GENERATED từ packages/contracts/schema/contracts.schema.json — không sửa tay (chạy make contracts)" \
    --formatters ruff-format \
    --output "$PYDANTIC_FILE"
)
