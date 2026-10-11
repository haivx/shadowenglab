#!/bin/sh
# Đổi đường dẫn tuyệt đối của máy local trong artifact GSD (.planning/) thành đường dẫn tương đối.
# Gốc repo và $HOME lấy lúc chạy, không viết cứng tên máy hay tên user.
# Installer GSD ghi đường dẫn tuyệt đối vào workflow, nên PLAN/SUMMARY mới sinh ra vẫn có; chạy lại trước khi push.
set -eu

ROOT=$(git rev-parse --show-toplevel)
export ROOT
cd "$ROOT"

files=$(git ls-files -co --exclude-standard .planning | xargs grep -lF -e "$ROOT" -e "$HOME/" 2>/dev/null || true)
if [ -z "$files" ]; then
  echo "relpaths: không còn đường dẫn tuyệt đối trong .planning/"
  exit 0
fi

# Đổi text PLAN/SUMMARY làm lệch covered_digest của VERIFICATION.md (GSD báo "stale").
# Ghi lại phase nào đang "passed" trước khi sửa; sau khi sửa chỉ tính lại digest cho đúng các phase đó,
# vì thay đổi duy nhất ở giữa là đường dẫn. Phase vốn đã stale thì giữ nguyên.
GSD="$ROOT/.claude/gsd-core/bin/gsd-tools.cjs"
passed=""
if [ -f "$GSD" ]; then
  for pd in .planning/phases/*/; do
    pd=${pd%/}
    ls "$pd"/*-VERIFICATION.md >/dev/null 2>&1 || continue
    [ "$(node "$GSD" query verification.status "$pd" --pick status 2>/dev/null)" = passed ] && passed="$passed $pd"
  done
fi

# Thứ tự: "<root>/" → "" (đường dẫn tương đối từ gốc repo), "<root>" → ".", "$HOME/" → "~/".
echo "$files" | xargs perl -pi -e 's{\Q$ENV{ROOT}\E/}{}g; s{\Q$ENV{ROOT}\E}{.}g; s{\Q$ENV{HOME}\E/}{~/}g'
echo "relpaths: đã sửa $(echo "$files" | wc -l | tr -d ' ') file"

for pd in $passed; do
  [ "$(node "$GSD" query verification.status "$pd" --pick status)" = stale ] || continue
  vf=$(ls "$pd"/*-VERIFICATION.md | head -1)
  covered=$(awk '/^covered_files:/{p=1;next} p&&/^  - /{gsub(/^  - "?|"$/,"");print;next} p{exit}' "$vf" | paste -sd, -)
  digest=$(node "$GSD" query verification.fingerprint "$pd" --files "$covered" --raw)
  node "$GSD" query frontmatter.set "$vf" --field covered_digest --value "$digest" >/dev/null
  echo "relpaths: tính lại covered_digest cho $pd"
done
