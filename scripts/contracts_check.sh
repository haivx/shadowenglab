#!/bin/sh
# Drift gate D-20: sinh lại JSON Schema + pydantic vào thư mục tạm rồi diff với bản đã commit.
# Lệch thì in diff và "CONTRACT DRIFT" (thoát 1); không lệch thì in "contracts: không lệch".
#
# Env tuỳ chọn (dùng cho test): CONTRACTS_SCHEMA_COMMITTED, CONTRACTS_PYDANTIC_COMMITTED.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

SCHEMA_COMMITTED=${CONTRACTS_SCHEMA_COMMITTED:-$ROOT/packages/contracts/schema/contracts.schema.json}
PYDANTIC_COMMITTED=${CONTRACTS_PYDANTIC_COMMITTED:-$ROOT/services/audio/src/audio_service/contracts_gen.py}

# Thư mục tạm nằm TRONG services/audio: datamodel-codegen chạy ruff-format với cwd là nơi đặt
# file output, nên ngoài project ruff không thấy [tool.ruff] (line-length 100) và xuống dòng
# khác bản đã commit, gây "drift" giả.
T=$(mktemp -d "$ROOT/services/audio/.contracts-check.XXXXXX")
# Chỉ xoá đúng thư mục tạm này.
trap 'rm -rf "$T"' EXIT

sh "$ROOT/scripts/contracts_gen.sh" "$T/schema" "$T/contracts_gen.py" >/dev/null

drift=0
if ! diff -u "$SCHEMA_COMMITTED" "$T/schema/contracts.schema.json"; then
  drift=1
fi
if ! diff -u "$PYDANTIC_COMMITTED" "$T/contracts_gen.py"; then
  drift=1
fi

if [ "$drift" -ne 0 ]; then
  echo "CONTRACT DRIFT: sửa Zod rồi chạy make contracts và commit"
  exit 1
fi

echo "contracts: không lệch"
