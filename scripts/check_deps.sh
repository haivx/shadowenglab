#!/bin/sh
# Kiểm tra và hướng dẫn system dependency cho `make setup` (D-25, FND-04).
#
# Chỉ KIỂM TRA và IN lệnh cài. Script này không bao giờ chạy brew, npm, curl hay bất kỳ
# trình cài đặt nào (Liam chọn "Kiểm tra và hướng dẫn").
#
# Thoát 0 khi mọi thứ đủ, 1 khi thiếu / sai nền tảng.

set -u

NODE_MIN="22.13"
NODE_MIN_MAJOR=22
NODE_MIN_MINOR=13
PNPM_VERSION="11.9.0"

fail=0
need_brew_pkgs=""
need_uv=0
need_node=0
need_pnpm=0

row() {
  # row <tool> <trạng thái> <chi tiết>
  printf '  %-10s %-6s %s\n' "$1" "$2" "$3"
}

first_line() {
  # In dòng đầu tiên của stdin (không phụ thuộc exit code của tool).
  head -n 1
}

echo "Kiểm tra system dependency (ShadowEngLab):"

# --- Nền tảng: macOS Apple Silicon (mlx-whisper) ---
os=$(uname -s 2>/dev/null || echo unknown)
arch=$(uname -m 2>/dev/null || echo unknown)
if [ "$os" = "Darwin" ] && [ "$arch" = "arm64" ]; then
  row "platform" "OK" "$os $arch"
else
  row "platform" "THIẾU" "cần macOS Apple Silicon (Darwin arm64), máy này là $os $arch"
  fail=1
fi

# --- ffmpeg ---
if command -v ffmpeg >/dev/null 2>&1; then
  v=$(ffmpeg -version 2>/dev/null | first_line)
  row "ffmpeg" "OK" "${v:-đã cài}"
else
  row "ffmpeg" "THIẾU" ""
  need_brew_pkgs="$need_brew_pkgs ffmpeg"
  fail=1
fi

# --- espeak-ng ---
if command -v espeak-ng >/dev/null 2>&1; then
  v=$(espeak-ng --version 2>/dev/null | first_line)
  row "espeak-ng" "OK" "${v:-đã cài}"
else
  row "espeak-ng" "THIẾU" ""
  need_brew_pkgs="$need_brew_pkgs espeak-ng"
  fail=1
fi

# --- uv ---
if command -v uv >/dev/null 2>&1; then
  v=$(uv --version 2>/dev/null | first_line)
  row "uv" "OK" "${v:-đã cài}"
else
  row "uv" "THIẾU" ""
  need_uv=1
  fail=1
fi

# --- node (>= NODE_MIN) ---
if command -v node >/dev/null 2>&1; then
  nv=$(node -v 2>/dev/null | first_line)
  nv=${nv#v}
  major=${nv%%.*}
  rest=${nv#*.}
  minor=${rest%%.*}
  node_ok=0
  case "$major$minor" in
    ''|*[!0-9]*) node_ok=0 ;;
    *)
      if [ "$major" -gt "$NODE_MIN_MAJOR" ]; then
        node_ok=1
      elif [ "$major" -eq "$NODE_MIN_MAJOR" ] && [ "$minor" -ge "$NODE_MIN_MINOR" ]; then
        node_ok=1
      fi
      ;;
  esac
  if [ "$node_ok" -eq 1 ]; then
    row "node" "OK" "v$nv (cần >= $NODE_MIN)"
  else
    row "node" "CŨ" "v$nv, cần >= $NODE_MIN"
    need_node=1
    fail=1
  fi
else
  row "node" "THIẾU" "cần >= $NODE_MIN"
  need_node=1
  fail=1
fi

# --- pnpm ---
if command -v pnpm >/dev/null 2>&1; then
  v=$(pnpm --version 2>/dev/null | first_line)
  row "pnpm" "OK" "${v:-đã cài}"
else
  row "pnpm" "THIẾU" ""
  need_pnpm=1
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "Tất cả system dependency đã đủ."
  exit 0
fi

echo ""
echo "make setup dừng: thiếu system dependency"
echo "Chạy các lệnh sau (script này KHÔNG tự cài), rồi chạy lại make setup:"
if [ -n "$need_brew_pkgs" ]; then
  echo "  brew install$need_brew_pkgs"
fi
if [ "$need_uv" -eq 1 ]; then
  echo "  brew install uv"
fi
if [ "$need_node" -eq 1 ]; then
  echo "  brew install node   # cần Node >= $NODE_MIN (đã cài bản cũ: brew upgrade node)"
fi
if [ "$need_pnpm" -eq 1 ]; then
  echo "  npm install -g pnpm@$PNPM_VERSION"
fi
if [ "$os" != "Darwin" ] || [ "$arch" != "arm64" ]; then
  echo "  (nền tảng không được hỗ trợ: dự án chỉ chạy trên macOS Apple Silicon)"
fi
exit 1
